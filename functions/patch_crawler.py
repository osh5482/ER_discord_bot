import re
import platform
from urllib.parse import urljoin
from playwright.async_api import async_playwright


class PatchNoteCrawler:
    """Eternal Return 패치노트 크롤링 클래스"""

    def __init__(self):
        self.base_url = (
            "https://playeternalreturn.com/posts/news?categoryPath=patchnote"
        )

    async def get_patch_info(self) -> dict:
        """
        최신 메이저 패치노트와 관련 마이너 패치노트 정보를 가져오는 함수

        Returns:
            dict: {
                "major_patch_version": str,  # 메이저 패치 버전
                "major_patch_date": str,     # 메이저 패치 날짜
                "major_patch_url": str,      # 메이저 패치 URL
                "minor_patch_data": list     # 마이너 패치 리스트
            }
            에러시 None
        """
        browser = None
        crawling_results = {
            "major_patch_version": None,
            "major_patch_date": None,
            "major_patch_url": None,
            "minor_patch_data": [],
        }

        try:
            async with async_playwright() as p:
                browser = await self._launch_browser(p)
                context = await browser.new_context(locale="ko-KR")
                page = await context.new_page()

                await self._load_page(page)

                # 메이저 패치 정보 추출
                major_version, major_date, major_url = await self._extract_major_patch(
                    page
                )
                crawling_results.update(
                    {
                        "major_patch_version": major_version,
                        "major_patch_date": major_date,
                        "major_patch_url": major_url,
                    }
                )

                # 마이너 패치 정보 추출
                if major_version and major_url:
                    minor_data = await self._extract_minor_patches(
                        page, major_version, major_url
                    )
                    crawling_results["minor_patch_data"] = minor_data

        except Exception as e:
            print(f"크롤링 중 오류 발생: {e}")
            return None
        finally:
            if browser:
                await browser.close()

        return crawling_results

    async def _launch_browser(self, playwright):
        """OS에 따른 브라우저 설정 및 실행"""
        current_os = platform.system()
        print(f"운영체제 감지: {current_os}")

        if current_os == "Windows":
            # 윈도우: Chromium 사용 (기본 설정)
            print("윈도우 환경: Chromium 브라우저 사용")
            browser = await playwright.chromium.launch(headless=True)

        elif current_os == "Linux":
            # 리눅스: Firefox 사용 (더 안정적)
            print("리눅스 환경: Firefox 브라우저 사용")
            try:
                browser = await playwright.firefox.launch(
                    headless=True,
                    firefox_user_prefs={
                        "dom.webnotifications.enabled": False,
                        "dom.push.enabled": False,
                    },
                )
            except Exception as e:
                print(f"Firefox 실행 실패, Chromium으로 대체 시도: {e}")
                # Firefox 실패시 Chromium으로 대체 (리눅스 안전 옵션)
                browser = await playwright.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-setuid-sandbox",
                        "--no-first-run",
                        "--no-zygote",
                        "--single-process",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                    ],
                )

        elif current_os == "Darwin":  # macOS
            # macOS: Chromium 사용 (기본 설정)
            print("macOS 환경: Chromium 브라우저 사용")
            browser = await playwright.chromium.launch(headless=True)

        else:
            # 기타 OS: 기본 Chromium 사용
            print(f"알 수 없는 운영체제 ({current_os}): 기본 Chromium 사용")
            browser = await playwright.chromium.launch(headless=True)

        return browser

    async def _load_page(self, page):
        """페이지 로드 및 대기"""
        print(f"페이지 로딩 중: {self.base_url}...")
        await page.goto(self.base_url)
        await page.wait_for_selector("h4.article-title", timeout=10000)
        print("페이지 로드 완료.")

    async def _extract_major_patch(self, page):
        """메이저 패치노트 정보 추출"""
        article_elements = await page.locator("h4.article-title").all()

        for title_locator in article_elements:
            title_text = await title_locator.text_content()

            if "PATCH NOTES" in title_text or "패치노트" in title_text:
                version_match = re.search(
                    r"(\d+\.\d+)\s*(?:PATCH NOTES|패치노트)", title_text, re.IGNORECASE
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

        return None, None, None

    async def _extract_minor_patches(self, page, major_version, major_url):
        """마이너 패치노트 정보 추출"""
        minor_patches = []
        minor_pattern = re.compile(rf"({re.escape(major_version)}[a-z])", re.IGNORECASE)

        article_elements = await page.locator("h4.article-title").all()

        for title_locator in article_elements:
            title_text = await title_locator.text_content()
            minor_match = minor_pattern.search(title_text)

            if minor_match:
                minor_version = minor_match.group(1)
                parent_a = title_locator.locator("xpath=ancestor::a[1]")
                relative_url = await parent_a.get_attribute("href")

                if relative_url:
                    url = urljoin(self.base_url, relative_url)
                    if url != major_url:  # 중복 방지
                        minor_patches.append({"version": minor_version, "url": url})
                        print(f"  - 마이너 패치 발견: {minor_version}")

        return list(reversed(minor_patches))  # 최신순 정렬
