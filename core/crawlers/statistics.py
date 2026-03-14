import asyncio
import platform
from playwright.async_api import async_playwright
from utils.constants import *
from utils.logger import logger


class DakggCrawler:
    """닥지지 통계 크롤링 클래스 (Playwright + Stealth 사용)"""

    def __init__(self):
        self._browser = None
        self._context = None
        self._playwright = None

    async def _apply_stealth(self, page):
        """
        봇 탐지 우회를 위한 JavaScript 패치 적용
        playwright-stealth의 핵심 기능을 직접 구현
        """
        # WebDriver 속성 제거
        await page.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        )

        # Chrome Runtime 속성 추가
        await page.add_init_script(
            """
            window.navigator.chrome = {
                runtime: {},
            };
        """
        )

        # Permissions API 위장
        await page.add_init_script(
            """
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """
        )

        # Plugin 정보 위장
        await page.add_init_script(
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """
        )

        # Languages 설정
        await page.add_init_script(
            """
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ko-KR', 'ko', 'en-US', 'en'],
            });
        """
        )

        logger.debug("Stealth 패치 적용 완료")

    """닥지지 통계 크롤링 클래스 (Playwright 사용)"""

    def __init__(self):
        self._browser = None
        self._context = None
        self._playwright = None

    async def __aenter__(self):
        """컨텍스트 매니저 진입 - 브라우저 초기화"""
        self._playwright = await async_playwright().start()
        self._browser = await self._launch_browser()
        self._context = await self._browser.new_context(
            locale="ko-KR",
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            java_script_enabled=True,
            bypass_csp=True,
            # 봇 탐지 우회를 위한 User Agent 설정
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # 추가 헤더 설정
            extra_http_headers={
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "Referer": "https://dak.gg/",
            },
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
            "--single-process",
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
                        "permissions.default.image": 2,
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

    async def crawl_character_stats(self, weapon, character_name, tier=None):
        """
        무기, 캐릭터 이름으로 닥지지 통계 크롤링

        Args:
            weapon: 무기 타입 (영문)
            character_name: 캐릭터 이름 (영문)
            tier: 티어 필터 (dak.gg URL 파라미터, 예: "gold", "diamond_plus")
                  None이면 기본값(다이아몬드+)

        Returns:
            dict: 통계 정보 딕셔너리

        Raises:
            Exception: 크롤링 실패 시
        """
        url = f"https://dak.gg/er/characters/{character_name}?weaponType={weapon}"
        if tier:
            url += f"&tier={tier}"

        try:
            page = await self._context.new_page()

            # Stealth 패치 적용 (봇 탐지 우회)
            await self._apply_stealth(page)

            # 성능 최적화: 불필요한 리소스 차단
            await page.route("**/analytics**", lambda route: route.abort())
            await page.route("**/ads**", lambda route: route.abort())
            # 이미지는 로드하지 않아도 통계는 가져올 수 있음 (속도 향상)
            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf}",
                lambda route: route.abort(),
            )

            logger.info(f"페이지 로딩 중: {url}")

            # 페이지 이동 전 짧은 지연 (봇처럼 보이지 않도록)
            await asyncio.sleep(0.5)

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # 통계 요소가 로드될 때까지 대기
            await page.wait_for_selector("div.css-n6szh2", timeout=30000)

            # 페이지 로드 후 짧은 대기 (DOM 안정화)
            await asyncio.sleep(0.5)

            logger.debug("통계 데이터 로딩 완료")

            # 기본 정보 설정
            statistics_dict = {
                "code": char_code[character_name],
                "character_name": char_korean[character_name],
                "weapon": weapon_korean[weapon],
            }

            # 모든 통계 div 요소 가져오기
            stat_elements = await page.locator("div.css-n6szh2").all()

            if not stat_elements:
                raise Exception("통계 요소를 찾을 수 없습니다.")

            for div in stat_elements:
                # 통계 이름 추출
                stat_name_element = div.locator("div.css-dy7q68")
                stat_name = await stat_name_element.text_content()

                if not stat_name:
                    continue

                # 값 추출
                value = None
                value_div = div.locator("div.css-1s2413a")

                if await value_div.count() > 0:
                    value = await value_div.text_content()
                    if value:
                        value = value.replace("%", " %")
                else:
                    # span 태그가 있는 경우
                    span_value = div.locator("span")
                    if await span_value.count() > 0:
                        value = await span_value.text_content()

                # 순위 정보 추출
                ranking_element = div.locator("div.css-1sw8f3s")
                ranking = await ranking_element.text_content()
                if ranking:
                    ranking = ranking.replace("#", "")

                # 딕셔너리에 저장
                if value and ranking:
                    statistics_dict[stat_name] = {
                        "value": value,
                        "ranking": ranking,
                    }

            await page.close()

            # 필수 통계 항목 확인
            required_stats = ["픽률", "승률", "RP 획득"]
            missing_stats = [
                stat for stat in required_stats if stat not in statistics_dict
            ]

            if missing_stats:
                raise Exception(
                    f"필수 통계 항목이 누락되었습니다: {', '.join(missing_stats)}"
                )

            logger.info(f"통계 크롤링 완료: {statistics_dict}")

            return statistics_dict

        except Exception as e:
            logger.error(f"크롤링 중 오류 발생: {e}")
            if page:
                await page.close()
            raise


async def dakgg_crawler(weapon, character_name, tier=None):
    """
    무기, 캐릭터 이름으로 닥지지 통계 크롤링해오기

    Args:
        weapon: 무기 타입 (영문)
        character_name: 캐릭터 이름 (영문)
        tier: 티어 필터 (dak.gg URL 파라미터, 예: "gold", "diamond_plus")
              None이면 기본값(다이아몬드+)

    Returns:
        dict: 통계 정보 딕셔너리 (각 통계의 value와 ranking 포함)

    Raises:
        Exception: 크롤링 실패 시
    """
    async with DakggCrawler() as crawler:
        return await crawler.crawl_character_stats(weapon, character_name, tier)


async def dakgg_crawler_all_tiers(weapon, character_name, tier_data):
    """
    모든 티어의 통계를 백그라운드로 크롤링하여 tier_data에 저장

    Args:
        weapon: 무기 타입 (영문)
        character_name: 캐릭터 이름 (영문)
        tier_data: 크롤링 결과를 저장할 딕셔너리 (공유 참조)
                   이미 크롤링된 티어는 건너뜀
    """
    async with DakggCrawler() as crawler:
        for tier_value in tier_filter.values():
            if tier_value in tier_data:
                continue
            try:
                data = await crawler.crawl_character_stats(
                    weapon, character_name, tier_value
                )
                tier_data[tier_value] = data
                logger.info(f"백그라운드 크롤링 완료: {tier_value}")
            except Exception as e:
                tier_data[tier_value] = None
                logger.warning(f"백그라운드 크롤링 실패 ({tier_value}): {e}")


async def main():
    """테스트용 메인 함수"""
    try:
        # 예시: 글러브 현우 통계 크롤링
        stats = await dakgg_crawler("Glove", "Hyunwoo")
        logger.debug("=== 크롤링 결과 ===")
        for key, value in stats.items():
            if isinstance(value, dict):
                logger.debug(f"{key}: {value['value']} (순위: {value['ranking']})")
            else:
                logger.debug(f"{key}: {value}")

    except Exception as e:
        logger.error(f"에러 발생: {e}")


if __name__ == "__main__":
    asyncio.run(main())
