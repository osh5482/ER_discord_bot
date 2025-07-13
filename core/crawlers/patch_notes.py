import re
import asyncio
import platform
from urllib.parse import urljoin
from playwright.async_api import async_playwright


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

    async def get_patch_info(self) -> dict:
        """
        최적화된 패치노트 정보 수집 (다중 파트 지원)
        """
        crawling_results = {
            "major_patch_version": None,
            "major_patch_date": None,
            "major_patches": [],  # 메이저 패치 파트 리스트
            "minor_patch_data": [],
        }

        try:
            page = await self._context.new_page()

            # 성능 최적화
            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf}",
                lambda route: route.abort(),
            )
            await page.route("**/analytics**", lambda route: route.abort())
            await page.route("**/ads**", lambda route: route.abort())

            await self._load_page(page)

            # 메이저 패치 정보 추출 (모든 파트 수집)
            major_patches = await self._extract_major_patch(page)

            if major_patches:
                # 첫 번째 파트를 기준으로 기본 정보 설정
                first_part = major_patches[0]
                major_version = first_part["version"]
                major_date = first_part["date"]

                crawling_results.update(
                    {
                        "major_patch_version": major_version,
                        "major_patch_date": major_date,
                        "major_patches": major_patches,  # 모든 파트 정보
                    }
                )

                # 마이너 패치 검색
                major_urls = {p["url"] for p in major_patches}
                minor_data = await self._extract_minor_patches(
                    page, major_version, major_urls
                )
                crawling_results["minor_patch_data"] = minor_data

            await page.close()

        except Exception as e:
            print(f"크롤링 중 오류 발생: {e}")
            return None

        return crawling_results

    async def _launch_browser(self):
        """최적화된 브라우저 설정"""
        current_os = platform.system()
        print(f"운영체제 감지: {current_os}")

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
                print("리눅스 환경: Firefox 브라우저 사용")
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
                print(f"Firefox 실행 실패, Chromium으로 대체 시도: {e}")
                browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=common_args,
                )
        else:
            print(f"{current_os} 환경: Chromium 브라우저 사용")
            browser = await self._playwright.chromium.launch(
                headless=True,
                args=common_args,
            )

        return browser

    async def _load_page(self, page):
        """최적화된 페이지 로드"""
        print(f"페이지 로딩 중: {self.base_url}...")
        try:
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_selector("h4.article-title", timeout=30000)
            print("페이지 로드 완료.")
        except Exception as e:
            print(f"페이지 로드 중 타임아웃: {e}")
            # 타임아웃이어도 이미 로드된 콘텐츠로 진행

    async def _extract_major_patch(self, page) -> list:
        """메이저 패치 추출 (다중 파트 지원) - 각 파트를 리스트로 반환"""
        major_patches = []
        try:
            article_elements = await page.locator("h4.article-title").all()
            latest_version = None

            # 1. 최신 메이저 버전 번호 찾기
            for title_locator in article_elements[:10]:
                title_text = await title_locator.text_content()
                if "PATCH NOTES" in title_text or "패치노트" in title_text:
                    version_match = re.search(
                        r"(\d+\.\d+)\s*(?:PATCH NOTES|패치노트)",
                        title_text,
                        re.IGNORECASE,
                    )
                    # 마이너/핫픽스 버전(e.g., 8.0a)은 제외
                    if version_match and not re.search(
                        r"\d+\.\d+[a-z]", title_text, re.IGNORECASE
                    ):
                        latest_version = version_match.group(1)
                        print(f"최신 메이저 버전 감지: {latest_version}")
                        break

            if not latest_version:
                print("메이저 패치를 찾을 수 없습니다.")
                return []

            # 2. 최신 버전에 해당하는 모든 파트 수집
            for title_locator in article_elements[:10]:
                title_text = await title_locator.text_content()
                # 제목에 latest_version이 포함되고, '패치노트'가 있으며, 마이너가 아닌 것
                if (
                    latest_version in title_text
                    and ("PATCH NOTES" in title_text or "패치노트" in title_text)
                    and not re.search(
                        rf"{re.escape(latest_version)}[a-z]", title_text, re.IGNORECASE
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
                                "version": latest_version,
                                "date": date,
                                "url": url,
                                "title": patch_title,
                            }
                        )
                        print(f"✅ 메이저 패치 발견: {latest_version} - {patch_title}")
                        print(f"   URL: {url}")

            # 제목순으로 정렬 (Part.1 -> Part.2)
            major_patches.sort(key=lambda p: p["title"])
            return major_patches

        except Exception as e:
            print(f"메이저 패치 추출 중 오류: {e}")

        return []

    async def _extract_minor_patches(self, page, major_version, major_urls: set):
        """최���화된 마이너 패치 추출 (메이저 URL set을 받아 중복 방지)"""
        minor_patches = []
        minor_pattern = re.compile(rf"({re.escape(major_version)}[a-z])", re.IGNORECASE)

        try:
            article_elements = await page.locator("h4.article-title").all()

            tasks = []
            for title_locator in article_elements[:20]:
                tasks.append(
                    self._process_minor_patch(title_locator, minor_pattern, major_urls)
                )

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in list(reversed(results)):
                if isinstance(result, dict) and result:
                    minor_patches.append(result)
                    print(f"  - 마이너 패치 발견: {result['version']}")

        except Exception as e:
            print(f"마이너 패치 추출 중 오류: {e}")

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


async def get_patch_info():
    """패치노트 정보 반환"""
    # 새로운 크롤링 실행
    print("🔄 새로운 패치노트 정보 크롤링...")
    async with PatchNoteCrawler() as crawler:
        patch_info = await crawler.get_patch_info()

        return patch_info


async def save_patch_notes_to_db():
    """패치노트 정보를 DB에 저장하는 함수"""
    conn, c = connect_DB()
    create_patch_notes_table(c)

    try:
        patch_info = await get_patch_info()

        if not patch_info or not patch_info.get("major_patch_version"):
            print("크롤링된 패치노트 정��가 없습니다.")
            return False

        # 메이저 패치노트 처리
        major_version = patch_info["major_patch_version"]
        major_title = patch_info["major_patch_title"]
        major_url = patch_info["major_patch_url"]

        # DB에서 해당 버전의 패치노트 조회
        c.execute("SELECT title FROM patch_notes WHERE version=?", (major_version,))
        existing_patch = c.fetchone()

        # DB에 없거나 제목이 다를 경우에만 저장/업데이트
        if not existing_patch or existing_patch[0] != major_title:
            c.execute(
                "INSERT OR REPLACE INTO patch_notes (version, title, url, is_major) VALUES (?, ?, ?, ?)",
                (major_version, major_title, major_url, True),
            )
            print(
                f"패치노트 버전 {major_version}이 업데이트되었습니다. ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
            )
            print(f"  제목: {major_title}")
        else:
            print(f"패치노트 버전 {major_version}은(는) 이미 최신입니다.")

        # 마이너 패치노트 처리
        for minor_patch in patch_info.get("minor_patch_data", []):
            minor_version = minor_patch["version"]
            minor_title = minor_patch["title"]
            minor_url = minor_patch["url"]

            c.execute("SELECT title FROM patch_notes WHERE version=?", (minor_version,))
            existing_minor_patch = c.fetchone()

            if not existing_minor_patch or existing_minor_patch[0] != minor_title:
                c.execute(
                    "INSERT OR REPLACE INTO patch_notes (version, title, url, is_major) VALUES (?, ?, ?, ?)",
                    (minor_version, minor_title, minor_url, False),
                )
                print(f"  - 마이너 패치 {minor_version}이(가) 업데이트되었습니다.")
            else:
                print(f"  - 마이너 패치 {minor_version}은(는) 이미 최신입니다.")

        conn.commit()
        print("패치노트 데이터가 성공적으로 저장되었습니다.")
        return True

    except Exception as e:
        print(f"DB 저장 중 오류 발생: {e}")
        return False

    finally:
        conn.close()
