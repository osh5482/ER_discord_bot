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
        최적화된 패치노트 정보 수집 (기존 함수명 유지)
        """
        crawling_results = {
            "major_patch_version": None,
            "major_patch_date": None,
            "major_patch_url": None,
            "minor_patch_data": [],
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

            # 빠른 페이지 로드
            await self._load_page(page)

            # 메이저 패치 정보 추출
            major_version, major_date, major_url = await self._extract_major_patch(page)
            crawling_results.update(
                {
                    "major_patch_version": major_version,
                    "major_patch_date": major_date,
                    "major_patch_url": major_url,
                }
            )

            # 메이저 패치를 찾았다면 마이너 패치도 검색
            if major_version and major_url:
                minor_data = await self._extract_minor_patches(
                    page, major_version, major_url
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
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=8000)
            await page.wait_for_selector("h4.article-title", timeout=5000)
            print("페이지 로드 완료.")
        except Exception as e:
            print(f"페이지 로드 중 타임아웃: {e}")
            # 타임아웃이어도 이미 로드된 콘텐츠로 진행

    async def _extract_major_patch(self, page):
        """최적화된 메이저 패치 추출"""
        try:
            article_elements = await page.locator("h4.article-title").all()

            # 상위 10개만 검색하여 속도 향상
            for title_locator in article_elements[:10]:
                title_text = await title_locator.text_content()

                if "PATCH NOTES" in title_text or "패치노트" in title_text:
                    version_match = re.search(
                        r"(\d+\.\d+)\s*(?:PATCH NOTES|패치노트)",
                        title_text,
                        re.IGNORECASE,
                    )
                    date_match = re.search(r"(\d{4}\.\d{2}\.\d{2})", title_text)

                    if version_match:
                        version = version_match.group(1)
                        date = date_match.group(1) if date_match else None

                        parent_a = title_locator.locator("xpath=ancestor::a[1]")
                        relative_url = await parent_a.get_attribute("href")

                        if relative_url:
                            url = urljoin(self.base_url, relative_url)
                            print(f"✅ 메이저 패치 발견: {version} - {url}")
                            return version, date, url

        except Exception as e:
            print(f"메이저 패치 추출 중 오류: {e}")

        return None, None, None

    async def _extract_minor_patches(self, page, major_version, major_url):
        """최적화된 마이너 패치 추출"""
        minor_patches = []
        minor_pattern = re.compile(rf"({re.escape(major_version)}[a-z])", re.IGNORECASE)

        try:
            article_elements = await page.locator("h4.article-title").all()

            # 병렬 처리를 위한 작업 리스트
            tasks = []
            for title_locator in article_elements[:20]:  # 상위 20개만 검색
                tasks.append(
                    self._process_minor_patch(title_locator, minor_pattern, major_url)
                )

            # 병렬 처리 실행
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 수집
            for result in list(reversed(results)):
                if isinstance(result, dict) and result:
                    minor_patches.append(result)
                    print(f"  - 마이너 패치 발견: {result['version']}")

        except Exception as e:
            print(f"마이너 패치 추출 중 오류: {e}")

        return list(reversed(minor_patches))  # 최신순 정렬

    async def _process_minor_patch(self, title_locator, minor_pattern, major_url):
        """개별 마이너 패치 처리"""
        try:
            title_text = await title_locator.text_content()
            minor_match = minor_pattern.search(title_text)

            if minor_match:
                minor_version = minor_match.group(1)
                parent_a = title_locator.locator("xpath=ancestor::a[1]")
                relative_url = await parent_a.get_attribute("href")

                if relative_url:
                    url = urljoin(self.base_url, relative_url)
                    if url != major_url:  # 중복 방지
                        return {"version": minor_version, "url": url}
        except Exception:
            pass
        return None
