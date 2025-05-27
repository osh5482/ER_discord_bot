import re
import asyncio
import platform
import time  # 성능 측정을 위해 추가
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from functions.dict_lib import char_code, char_korean, weapon_korean
import json


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


class StatisticsCrawler(PatchNoteCrawler):
    """
    PatchNoteCrawler를 상속받아 게임 통계 크롤링 기능을 제공하는 클래스
    기존 ER_statistics.py의 dakgg_crawler 함수를 대체합니다.
    """

    def __init__(self):
        super().__init__()
        # 통계 크롤링용 기본 URL은 다름
        self.base_url = "https://dak.gg"
        # 페이지 캐싱을 위한 변수들
        self._current_page = None
        self._current_url = None
        self._page_loaded = False

    async def _get_or_create_page(self, url):
        """페이지 재사용 또는 새 페이지 생성"""
        # 같은 URL이고 페이지가 이미 로드된 경우 재사용
        if self._current_page and self._current_url == url and self._page_loaded:
            print(f"🔄 기존 페이지 재사용: {url}")
            return self._current_page

        # 기존 페이지가 있으면 닫기
        if self._current_page:
            try:
                await self._current_page.close()
            except:
                pass

        # 새 페이지 생성
        print(f"🆕 새 페이지 생성: {url}")
        self._current_page = await self._context.new_page()

        # 성능 최적화: 불필요한 리소스 차단 (더 강화)
        await self._current_page.route(
            "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,css}",
            lambda route: route.abort(),
        )
        await self._current_page.route("**/analytics**", lambda route: route.abort())
        await self._current_page.route("**/ads**", lambda route: route.abort())
        await self._current_page.route("**/tracking**", lambda route: route.abort())
        await self._current_page.route("**/gtag**", lambda route: route.abort())

        # 빠른 페이지 로드 (타임아웃 단축)
        print(f"⏳ 페이지 로딩 시작...")
        start_time = time.time()

        await self._current_page.goto(url, wait_until="domcontentloaded", timeout=8000)

        # 통계 섹션이 로드될 때까지 대기 (타임아웃 단축)
        await self._current_page.wait_for_selector("div.css-n6szh2", timeout=6000)

        load_time = time.time() - start_time
        print(f"✅ 페이지 로드 완료: {load_time:.2f}초")

        self._current_url = url
        self._page_loaded = True

        return self._current_page

    async def dakgg_crawler(self, weapon, character_name):
        """
        무기, 캐릭터 이름으로 닥지지 통계 크롤링해오기
        기존 ER_statistics.py의 dakgg_crawler 함수와 동일한 반환값 형식 유지

        반환값 : dict(str(각 통계 html)) /
        에러시 aiohttp.ClientResponseError와 유사한 예외 처리
        """
        url = f"https://dak.gg/er/characters/{character_name}?weaponType={weapon}"

        try:
            # 결과 딕셔너리 초기화 (기존 형식 유지)
            statistics_dict = {
                "code": char_code.get(character_name, 0),
                "character_name": char_korean.get(character_name, character_name),
                "weapon": weapon_korean.get(weapon, weapon),
            }

            page = await self._get_or_create_page(url)

            # 통계 데이터 추출
            start_time = time.time()
            stat_elements = await page.locator("div.css-n6szh2").all()

            for stat_block in stat_elements:
                try:
                    # 통계 이름 추출
                    stat_name_element = stat_block.locator("div.css-dy7q68")
                    stat_name = await stat_name_element.inner_text(timeout=2000)
                    stat_name = stat_name.strip()

                    if not stat_name:
                        continue

                    # 값 추출 (기존 로직과 동일)
                    value_element = stat_block.locator("div.css-1s2413a")
                    value = ""

                    try:
                        # div.css-1s2413a가 있는 경우
                        value = await value_element.inner_text(timeout=1500)
                        value = value.replace("%", " %")
                    except:
                        # span 태그가 있는 경우
                        try:
                            span_element = stat_block.locator("span")
                            value = await span_element.inner_text(timeout=1500)
                        except:
                            value = ""

                    # 순위 정보 추출
                    ranking_element = stat_block.locator("div.css-1sw8f3s")
                    ranking = ""
                    try:
                        ranking = await ranking_element.inner_text(timeout=1500)
                        ranking = ranking.replace("#", "")
                    except:
                        ranking = ""

                    # 기존 형식과 동일하게 딕셔너리에 저장
                    statistics_dict[stat_name] = {
                        "value": value.strip(),
                        "ranking": ranking.strip(),
                    }

                except Exception as e:
                    print(f"⚠️ 통계 블록 처리 중 오류: {e}")
                    continue

            extract_time = time.time() - start_time
            print(f"📊 데이터 추출 완료: {extract_time:.2f}초")
            print(f"✅ 통계 크롤링 완료: {character_name} + {weapon}")

            return statistics_dict

        except Exception as e:
            print(f"❌ dak.gg 크롤링 오류: {e}")
            # 기존 코드와의 호환성을 위해 사용자 정의 예외 발생
            from aiohttp import ClientResponseError

            raise ClientResponseError(
                request_info=None,
                history=(),
                status=500,
                message=f"크롤링 실패: {str(e)}",
            )

    async def scrape_tier_statistics(self, weapon, character_name, tier="다이아몬드+"):
        """
        특정 티어의 통계를 크롤링하는 함수 (최적화된 버전)
        기존 페이지를 재사용하여 로딩 시간 대폭 단축
        """

        url = f"https://dak.gg/er/characters/{character_name}?weaponType={weapon}"

        try:
            # 페이지 재사용 또는 생성
            page = await self._get_or_create_page(url)

            # 티어 드롭다운 클릭 (최적화된 셀렉터와 단축된 타임아웃)
            tier_change_start = time.time()

            try:
                print(f"🎯 '{tier}' 티어로 변경 시도...")

                # 더 효율적인 셀렉터 순서 (성공률 높은 것부터)
                tier_selectors = [
                    "button.css-1lyboqe",  # 가장 일반적인 형태
                    "button[class*='trigger']",
                    ".tier-selector button",
                    "button:has-text('다이아몬드+')",
                ]

                # 드롭다운 클릭
                clicked = False
                for selector in tier_selectors:
                    try:
                        await page.click(selector, timeout=2000)  # 타임아웃 단축
                        print(f"🎯 드롭다운 클릭 성공: {selector}")
                        clicked = True
                        break
                    except:
                        continue

                if not clicked:
                    print(f"⚠️ 드롭다운 버튼을 찾을 수 없음, 기본 통계 사용")
                    return await self._extract_statistics_data(
                        page, weapon, character_name
                    )

                # 드롭다운 열림 대기 (시간 단축)
                await asyncio.sleep(0.5)  # 1.5초에서 0.5초로 단축

                # 티어 옵션 클릭 (더 정확한 셀렉터)
                tier_option_selectors = [
                    f"li:has-text('{tier}')",
                    f"[role='option']:has-text('{tier}')",
                    f".option-item:has-text('{tier}')",
                    f"div[data-value='{tier}']",
                ]

                tier_selected = False
                for option_selector in tier_option_selectors:
                    try:
                        await page.click(option_selector, timeout=2000)  # 타임아웃 단축
                        print(f"✅ '{tier}' 티어 선택 성공")
                        tier_selected = True
                        break
                    except:
                        continue

                if not tier_selected:
                    print(f"⚠️ '{tier}' 티어 옵션을 찾을 수 없음")
                    return await self._extract_statistics_data(
                        page, weapon, character_name
                    )

                # 페이지 업데이트 대기 (최적화)
                print(f"⏳ 데이터 업데이트 대기...")

                # 더 효율적인 대기 방식: 특정 요소의 변경을 감지
                try:
                    # 통계 데이터가 업데이트되었는지 확인
                    await page.wait_for_function(
                        """() => {
                            const elements = document.querySelectorAll('div.css-n6szh2');
                            return elements.length > 0;
                        }""",
                        timeout=3000,  # 5초에서 3초로 단축
                    )

                    # 추가적인 작은 대기 (DOM 업데이트 완료 보장)
                    await asyncio.sleep(0.8)  # 3초에서 0.8초로 대폭 단축

                except Exception as wait_error:
                    print(f"⚠️ 페이지 업데이트 대기 중 타임아웃: {wait_error}")
                    # 타임아웃이어도 진행

                tier_change_time = time.time() - tier_change_start
                print(f"🏁 티어 변경 완료: {tier_change_time:.2f}초")

            except Exception as e:
                print(f"⚠️ 티어 선택 중 오류 (기본 통계 사용): {e}")

            # 통계 데이터 추출
            statistics_dict = await self._extract_statistics_data(
                page, weapon, character_name
            )

            print(f"🎉 티어별 통계 크롤링 완료: {character_name} + {weapon} ({tier})")

            return statistics_dict

        except Exception as e:
            print(f"❌ 티어별 통계 크롤링 오류: {e}")
            # 오류 발생 시 기본 통계로 폴백
            return await self.dakgg_crawler(weapon, character_name)

    async def _extract_statistics_data(self, page, weapon, character_name):
        """통계 데이터 추출 공통 함수 (성능 최적화)"""
        start_time = time.time()

        statistics_dict = {
            "code": char_code.get(character_name, 0),
            "character_name": char_korean.get(character_name, character_name),
            "weapon": weapon_korean.get(weapon, weapon),
        }

        try:
            # 통계 섹션 대기 (타임아웃 단축)
            await page.wait_for_selector("div.css-n6szh2", timeout=4000)

            # 통계 데이터 추출 (병렬 처리 방식으로 최적화)
            stat_elements = await page.locator("div.css-n6szh2").all()

            # 각 통계 블록을 병렬로 처리
            tasks = []
            for stat_block in stat_elements:
                tasks.append(self._extract_single_stat(stat_block))

            # 병렬 실행
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 정리
            for result in results:
                if isinstance(result, dict) and result.get("name"):
                    stat_name = result["name"]
                    statistics_dict[stat_name] = {
                        "value": result.get("value", "").strip(),
                        "ranking": result.get("ranking", "").strip(),
                    }

            extract_time = time.time() - start_time
            print(f"📊 데이터 추출 시간: {extract_time:.2f}초")

        except Exception as e:
            print(f"⚠️ 통계 데이터 추출 중 오류: {e}")

        return statistics_dict

    async def _extract_single_stat(self, stat_block):
        """단일 통계 블록에서 데이터 추출 (병렬 처리용)"""
        try:
            # 통계 이름 추출
            stat_name_element = stat_block.locator("div.css-dy7q68")
            stat_name = await stat_name_element.inner_text(timeout=1500)
            stat_name = stat_name.strip()

            if not stat_name:
                return {}

            # 값과 순위를 병렬로 추출
            value_task = self._extract_value(stat_block)
            ranking_task = self._extract_ranking(stat_block)

            value, ranking = await asyncio.gather(
                value_task, ranking_task, return_exceptions=True
            )

            return {
                "name": stat_name,
                "value": value if isinstance(value, str) else "",
                "ranking": ranking if isinstance(ranking, str) else "",
            }

        except Exception as e:
            return {}

    async def _extract_value(self, stat_block):
        """값 추출 헬퍼 함수"""
        try:
            value_element = stat_block.locator("div.css-1s2413a")
            value = await value_element.inner_text(timeout=1000)
            return value.replace("%", " %")
        except:
            try:
                span_element = stat_block.locator("span")
                return await span_element.inner_text(timeout=1000)
            except:
                return ""

    async def _extract_ranking(self, stat_block):
        """순위 추출 헬퍼 함수"""
        try:
            ranking_element = stat_block.locator("div.css-1sw8f3s")
            ranking = await ranking_element.inner_text(timeout=1000)
            return ranking.replace("#", "")
        except:
            return ""

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 시 페이지도 정리"""
        if self._current_page:
            try:
                await self._current_page.close()
            except:
                pass

        # 부모 클래스의 정리 메서드 호출
        await super().__aexit__(exc_type, exc_val, exc_tb)
