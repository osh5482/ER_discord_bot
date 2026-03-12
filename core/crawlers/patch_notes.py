import re
import asyncio
import platform
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from database.connection import *
from datetime import datetime
from utils.logger import logger


class PatchNoteCrawler:
    """최적화된 Eternal Return 패치노트 크롤링 클래스"""

    def __init__(self):
        self.base_url = (
            "https://playeternalreturn.com/posts/news?categoryPath=patchnote"
        )
        # 브라우저 재사용을 위한 인스턴스 변수
        self._browser = None
        self._context = None

    async def __aenter__(self):
        """컨텍스트 매니저 진입 - 브라우저 초기화"""
        self._playwright = await async_playwright().start()
        self._browser = await self._launch_browser()
        self._context = await self._browser.new_context(
            locale="ko-KR",
            # 성능 최적화 옵션
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
            java_script_enabled=True,
            # 불필요한 리소스 비활성화
            bypass_csp=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 - 리소스 정리"""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def get_patch_info(self, load_all: bool = False, until_version: str = None) -> dict:
        """페이지에 보이는 모든 메이저 버전의 패치 정보 수집 (다중 버전, 다중 파트 지원)

        Args:
            load_all: True이면 더보기 버튼을 끝까지 눌러 전체 히스토리를 수집한다.
                      False이면 until_version이 보일 때까지만 더보기를 클릭한다.
            until_version: 증분 크롤링 시 기준이 되는 버전 문자열 (예: "10.1").
                           이 버전이 페이지에 나타나면 더보기 클릭을 중단한다.
                           load_all=True이면 무시된다.
        """
        crawling_results = {
            "versions": [],  # 버전별 패치 정보 리스트 (최신순)
        }

        try:
            page = await self._context.new_page()

            # 성능 최적화: 불필요한 리소스 차단
            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf}",
                lambda route: route.abort(),
            )
            await page.route("**/analytics**", lambda route: route.abort())
            await page.route("**/ads**", lambda route: route.abort())

            await self._load_page(page, load_all=load_all, until_version=until_version)

            # 페이지에서 모든 고유 메이저 버전 수집 (최신순)
            all_versions = await self._extract_all_major_versions(page)
            logger.info(f"페이지에서 감지된 메이저 버전 목록: {all_versions}")

            for major_version in all_versions:
                # 각 버전의 모든 파트(Part.1, Part.2 등) 수집
                major_patches = await self._extract_major_patches_for_version(
                    page, major_version
                )

                if major_patches:
                    major_date = major_patches[0].get("date")
                    # 해당 버전의 마이너 패치 수집
                    major_urls = {p["url"] for p in major_patches}
                    minor_data = await self._extract_minor_patches(
                        page, major_version, major_urls
                    )

                    crawling_results["versions"].append(
                        {
                            "major_version": major_version,
                            "major_date": major_date,
                            "major_patches": major_patches,
                            "minor_patch_data": minor_data,
                        }
                    )

            await page.close()

        except Exception as e:
            logger.error(f"크롤링 중 오류 발생: {e}")
            return None

        return crawling_results

    async def _launch_browser(self):
        """최적화된 브라우저 설정"""
        current_os = platform.system()
        logger.debug(f"운영체제 감지: {current_os}")

        # 공통 최적화 옵션
        common_args = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
            "--disable-features=VizDisplayCompositor",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-extensions",
            "--disable-default-apps",
            "--disable-sync",
            "--disable-translate",
            "--disable-background-networking",
            "--disable-plugins",
            "--disable-print-preview",
            "--no-first-run",
            "--no-default-browser-check",
            "--single-process",  # 단일 프로세스로 메모리 사용량 줄임
            "--memory-pressure-off",
        ]

        if current_os == "Linux":
            try:
                logger.info("리눅스 환경: Firefox 브라우저 사용")
                browser = await self._playwright.firefox.launch(
                    headless=True,
                    firefox_user_prefs={
                        "dom.webnotifications.enabled": False,
                        "dom.push.enabled": False,
                        "media.autoplay.enabled": False,
                        "permissions.default.image": 2,  # 이미지 차단
                    },
                )
            except Exception as e:
                logger.warning(f"Firefox 실행 실패, Chromium으로 대체 시도: {e}")
                browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=common_args,
                )
        else:
            logger.info(f"{current_os} 환경: Chromium 브라우저 사용")
            browser = await self._playwright.chromium.launch(
                headless=True,
                args=common_args,
            )

        return browser

    async def _load_page(self, page, load_all: bool = False, until_version: str = None):
        """페이지 로드 및 더보기 버튼 클릭 처리

        Args:
            page: Playwright 페이지 객체
            load_all: True이면 더보기 버튼이 없어질 때까지 모두 클릭 (전체 히스토리 수집 시 사용)
                      False이면 until_version이 보일 때까지만 클릭 (증분 업데이트 시 사용)
            until_version: 증분 크롤링 시 기준 버전 (이 버전이 보이면 중단)
        """
        logger.info(f"페이지 로딩 중: {self.base_url}...")
        try:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector("h4.article-title", timeout=30000)
            logger.debug("페이지 초기 로드 완료.")
        except Exception as e:
            logger.warning(f"페이지 로드 중 타임아웃: {e}")
            # 타임아웃이어도 이미 로드된 콘텐츠로 진행

        # 더보기 버튼 클릭하여 추가 패치 로드
        await self._click_load_more(page, load_all=load_all, until_version=until_version)

    async def _is_version_visible(self, page, version: str) -> bool:
        """특정 버전의 메이저 패치노트 제목이 페이지에 보이는지 확인한다.

        Args:
            page: Playwright 페이지 객체
            version: 확인할 버전 문자열 (예: "10.1")

        Returns:
            bool: 해당 버전이 페이지에 존재하면 True
        """
        try:
            article_elements = await page.locator("h4.article-title").all()
            for el in article_elements:
                title_text = await el.text_content()
                if "PATCH NOTES" not in title_text and "패치노트" not in title_text:
                    continue
                # 해당 버전이 정확히 일치하고 마이너(알파벳 접미사) 버전이 아닌 것만 확인
                version_exact = re.search(
                    rf"(?<!\d){re.escape(version)}(?!\d)", title_text
                )
                is_minor = re.search(
                    rf"(?<!\d){re.escape(version)}[a-z]", title_text, re.IGNORECASE
                )
                if version_exact and not is_minor:
                    return True
        except Exception:
            pass
        return False

    async def _click_load_more(self, page, load_all: bool = False, until_version: str = None):
        """더보기 버튼을 클릭하여 추가 패치 목록을 로드한다.

        Args:
            page: Playwright 페이지 객체
            load_all: True이면 버튼이 사라질 때까지 계속 클릭 (전체 히스토리 수집)
                      False이면 until_version이 보일 때까지 클릭 (증분 업데이트)
            until_version: 증분 크롤링 기준 버전. 이 버전이 페이지에 나타나면 클릭 중단.
                           load_all=True이거나 None이면 무시된다.
        """
        # 더보기 버튼 셀렉터 후보 (사이트 구조에 따라 변경될 수 있음)
        MORE_BTN_SELECTORS = [
            "button.more-btn",
            "button.load-more",
            "a.more-btn",
            ".more-view button",
            ".btn-more",
            "button:has-text('더보기')",
            "button:has-text('MORE')",
            "button:has-text('더 보기')",
        ]

        max_clicks = 999  # 항상 충분히 크게 설정 (실제 중단 조건은 아래 로직으로 제어)
        click_count = 0

        # 증분 모드: 초기 로드된 페이지에서 이미 기준 버전이 보이면 더보기 불필요
        if not load_all and until_version:
            if await self._is_version_visible(page, until_version):
                logger.debug(f"기준 버전 {until_version}이 이미 페이지에 존재 — 더보기 클릭 불필요.")
                return

        for _ in range(max_clicks):
            # 더보기 버튼 탐색
            btn = None
            for selector in MORE_BTN_SELECTORS:
                try:
                    candidate = page.locator(selector).first
                    if await candidate.is_visible(timeout=2000):
                        btn = candidate
                        logger.debug(f"더보기 버튼 발견: '{selector}'")
                        break
                except Exception:
                    continue

            if btn is None:
                logger.debug(f"더보기 버튼 없음 — 총 {click_count}회 클릭 완료.")
                break

            # 현재 기사 수 기록 → 클릭 후 새 기사가 로드됐는지 확인
            before_count = await page.locator("h4.article-title").count()

            try:
                await btn.scroll_into_view_if_needed()
                await btn.click()
                click_count += 1
            except Exception as e:
                logger.warning(f"더보기 버튼 클릭 실패: {e}")
                break

            # 새 콘텐츠가 로드될 때까지 대기 (최대 5초)
            try:
                await page.wait_for_function(
                    f"document.querySelectorAll('h4.article-title').length > {before_count}",
                    timeout=5000,
                )
                after_count = await page.locator("h4.article-title").count()
                logger.debug(f"더보기 클릭 {click_count}회: {before_count} → {after_count}개 기사")
            except Exception:
                # 더 이상 새 콘텐츠가 없으면 종료
                logger.debug(f"더 이상 로드할 콘텐츠 없음 ({click_count}회 클릭 완료).")
                break

            # 증분 모드: 기준 버전이 보이면 더보기 중단
            if not load_all and until_version:
                if await self._is_version_visible(page, until_version):
                    logger.info(f"기준 버전 {until_version} 발견 — 더보기 클릭 중단 (총 {click_count}회).")
                    break

    async def _extract_all_major_versions(self, page) -> list:
        """페이지에 보이는 모든 고유 메이저 버전 반환 (최신순)"""
        versions = []
        seen = set()
        try:
            article_elements = await page.locator("h4.article-title").all()
            # 로드된 모든 기사에서 메이저 버전 탐색
            for el in article_elements:
                title_text = await el.text_content()
                if "PATCH NOTES" in title_text or "패치노트" in title_text:
                    version_match = re.search(
                        # (?<!\d) : 숫자 중간에서 매칭되는 것을 방지 (예: "1.15.1"에서 "15.1" 오탐 방지)
                        # (?:\.\d+)? : "X.Y.Z" 형태의 세 자리 버전도 지원
                        r"(?<!\d)(\d+\.\d+(?:\.\d+)?)\s*(?:PATCH NOTES|패치노트)",
                        title_text,
                        re.IGNORECASE,
                    )
                    # 마이너/핫픽스 버전(예: 8.0a, 1.15.1a)은 제외
                    if version_match and not re.search(
                        r"\d+\.\d+(?:\.\d+)?[a-z]", title_text, re.IGNORECASE
                    ):
                        v = version_match.group(1)
                        if v not in seen:
                            versions.append(v)
                            seen.add(v)
                            logger.debug(f"메이저 버전 감지: {v}")
        except Exception as e:
            logger.error(f"버전 목록 추출 중 오류: {e}")
        return versions  # 최신순 (페이지 상단→하단 순서)

    async def _extract_major_patches_for_version(self, page, target_version) -> list:
        """특정 메이저 버전의 모든 파트 수집 (Part.1, Part.2 등)"""
        major_patches = []
        try:
            article_elements = await page.locator("h4.article-title").all()

            for title_locator in article_elements:
                title_text = await title_locator.text_content()
                # 해당 버전이 포함되고, 패치노트이며, 마이너(10.4a 등)가 아닌 것
                # (?<!\d), (?!\d) : "1.4"가 "1.43" 같은 다른 버전 안에서 오탐되는 것 방지
                version_exact = re.search(
                    rf"(?<!\d){re.escape(target_version)}(?!\d)", title_text
                )
                if (
                    version_exact
                    and ("PATCH NOTES" in title_text or "패치노트" in title_text)
                    and not re.search(
                        rf"(?<!\d){re.escape(target_version)}[a-z]",
                        title_text,
                        re.IGNORECASE,
                    )
                ):
                    date_match = re.search(r"(\d{4}\.\d{2}\.\d{2})", title_text)
                    date = date_match.group(1) if date_match else None
                    patch_title = title_text.strip()

                    parent_a = title_locator.locator("xpath=ancestor::a[1]")
                    relative_url = await parent_a.get_attribute("href")
                    if relative_url:
                        url = urljoin(self.base_url, relative_url)
                        major_patches.append(
                            {
                                "version": target_version,
                                "date": date,
                                "url": url,
                                "title": patch_title,
                            }
                        )
                        logger.debug(f"메이저 패치 발견: {target_version} - {patch_title} | URL: {url}")

            # 제목순으로 정렬 (Part.1 -> Part.2)
            major_patches.sort(key=lambda p: p["title"])
            return major_patches

        except Exception as e:
            logger.error(f"메이저 패치 추출 중 오류 ({target_version}): {e}")

        return []

    async def _extract_minor_patches(self, page, major_version, major_urls: set):
        """최���화된 마이너 패치 추출 (메이저 URL set을 받아 중복 방지)"""
        minor_patches = []
        # (?<!\d) : "1.4a"가 "1.43a" 같은 다른 버전에서 오탐되는 것 방지
        minor_pattern = re.compile(
            rf"(?<!\d)({re.escape(major_version)}[a-z])(?!\d)", re.IGNORECASE
        )

        try:
            article_elements = await page.locator("h4.article-title").all()

            tasks = []
            for title_locator in article_elements:
                tasks.append(
                    self._process_minor_patch(title_locator, minor_pattern, major_urls)
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 페이지 순서(최신→오래된)를 유지하여 수집
            for result in results:
                if isinstance(result, dict) and result:
                    minor_patches.append(result)
                    logger.debug(f"마이너 패치 발견: {result['version']}")

        except Exception as e:
            logger.error(f"마이너 패치 추출 중 오류: {e}")

        # 오래된 것이 먼저 오도록 역순 반환 (a → b → c 순서)
        return list(reversed(minor_patches))

    async def _process_minor_patch(self, title_locator, minor_pattern, major_urls: set):
        """개별 마이너 패치 처리 (메이저 URL set과 비교)"""
        try:
            title_text = await title_locator.text_content()
            minor_match = minor_pattern.search(title_text)

            if minor_match:
                minor_version = minor_match.group(1)
                parent_a = title_locator.locator("xpath=ancestor::a[1]")
                relative_url = await parent_a.get_attribute("href")

                if relative_url:
                    url = urljoin(self.base_url, relative_url)
                    if url not in major_urls:  # 메이저 패치 URL들과 중복 방지
                        return {
                            "version": minor_version,
                            "url": url,
                            "title": title_text.strip(),
                        }
        except Exception:
            pass
        return None


# 캐싱 시스템
_patch_cache = {"data": None, "timestamp": 0, "cache_duration": 300}  # 5분 캐시


async def get_patch_info(load_all: bool = False, until_version: str = None):
    """패치노트 정보 반환

    Args:
        load_all: True이면 더보기를 끝까지 눌러 전체 패치 히스토리를 수집한다.
        until_version: 증분 크롤링 시 기준 버전. 이 버전이 보이면 더보기 클릭 중단.
                       load_all=True이거나 None이면 무시된다.
    """
    mode_label = "[전체 히스토리]" if load_all else f"[증분: {until_version}까지]" if until_version else "[최근]"
    logger.info(f"새로운 패치노트 정보 크롤링... {mode_label}")
    async with PatchNoteCrawler() as crawler:
        patch_info = await crawler.get_patch_info(load_all=load_all, until_version=until_version)

        return patch_info


