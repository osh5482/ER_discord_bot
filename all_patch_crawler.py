import asyncio
import platform
from playwright.async_api import async_playwright
import re
from collections import defaultdict
from urllib.parse import urljoin
import sqlite3
import json
from datetime import datetime
from config import Config


class AllPatchCrawler:
    """전체 Eternal Return 패치노트 크롤링 클래스"""

    def __init__(self):
        self.base_url = (
            "https://playeternalreturn.com/posts/news?categoryPath=patchnote"
        )
        self._browser = None
        self._context = None

    async def __aenter__(self):
        """컨텍스트 매니저 진입 - 브라우저 초기화"""
        self._playwright = await async_playwright().start()
        self._browser = await self._launch_browser()
        self._context = await self._browser.new_context(
            locale="ko-KR",
            viewport={"width": 1280, "height": 720},
            ignore_https_errors=True,
            java_script_enabled=True,
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
            "--single-process",
            "--memory-pressure-off",
        ]

        if current_os == "Linux":
            try:
                print("리눅스 환경: Firefox 브라우저 사용")
                browser = await self._playwright.firefox.launch(
                    headless=True,  # 콘솔 출력을 위해 headless 모드 유지
                    firefox_user_prefs={
                        "dom.webnotifications.enabled": False,
                        "dom.push.enabled": False,
                        "media.autoplay.enabled": False,
                        "permissions.default.image": 2,
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
                headless=False,  # 디버깅을 위해 headless 모드 해제
                args=common_args,
            )

        return browser

    def _connect_db(self):
        """데이터베이스 연결 함수"""
        conn = sqlite3.connect(Config.DATABASE_PATH, isolation_level=None)
        c = conn.cursor()
        return conn, c

    def _recreate_patch_notes_table(self, c):
        """기존 patch_notes 테이블을 삭제하고 새로운 구조로 재생성"""
        # 기존 patch_notes 테이블 삭제
        c.execute("DROP TABLE IF EXISTS patch_notes")
        print("기존 patch_notes 테이블을 삭제했습니다.")

        # 새로운 구조로 patch_notes 테이블 생성
        c.execute(
            """CREATE TABLE patch_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                major_version TEXT NOT NULL,
                major_date TEXT,
                major_patches TEXT,
                minor_patches TEXT,
                updated_at INTEGER NOT NULL,
                str_updated_at TEXT NOT NULL
            )"""
        )
        print("새로운 구조로 patch_notes 테이블이 생성되었습니다.")

        # 인덱스 생성
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_patch_notes_version ON patch_notes (major_version)"
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_patch_notes_updated_at ON patch_notes (updated_at)"
        )

    def _insert_patch_data(self, c, patch_data_list):
        """패치노트 데이터 저장 함수 - 전체 버전 관리"""
        current_unix_time = int(datetime.now().timestamp())
        current_str_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 기존 데이터 모두 삭제 (전체 재작성 방식)
        c.execute("DELETE FROM patch_notes")
        print("기존 patch_notes 데이터를 삭제했습니다.")

        # 새로운 데이터 삽입
        inserted_count = 0
        for patch_data in patch_data_list:
            c.execute(
                """INSERT INTO patch_notes 
                   (major_version, major_date, major_patches, minor_patches, updated_at, str_updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    patch_data["major_version"],
                    patch_data["major_date"],
                    patch_data["major_patches"],
                    patch_data["minor_patches"],
                    current_unix_time,
                    current_str_time,
                ),
            )
            inserted_count += 1

        print(f"✅ 총 {inserted_count}개의 패치 버전이 데이터베이스에 저장되었습니다.")
        return inserted_count

    def _get_all_patches_from_db(self, c):
        """데이터베이스에서 모든 패치노트 데이터 조회 함수"""
        c.execute(
            """SELECT id, major_version, major_date, major_patches, minor_patches, str_updated_at 
               FROM patch_notes 
               ORDER BY major_version DESC"""
        )
        rows = c.fetchall()

        patches = []
        for row in rows:
            (
                patch_id,
                major_version,
                major_date,
                major_patches_json,
                minor_patches_json,
                str_updated_at,
            ) = row

            # JSON 문자열을 파이썬 객체로 변환
            try:
                major_patches = (
                    json.loads(major_patches_json) if major_patches_json else []
                )
                minor_patches = (
                    json.loads(minor_patches_json) if minor_patches_json else []
                )
            except json.JSONDecodeError:
                major_patches = []
                minor_patches = []

            patches.append(
                {
                    "id": patch_id,
                    "major_version": major_version,
                    "major_date": major_date,
                    "major_patches": major_patches,
                    "minor_patches": minor_patches,
                    "last_updated": str_updated_at,
                }
            )

        return patches

    async def crawl_all_patches(self):
        """모든 패치노트를 크롤링하여 정리된 데이터 반환"""
        try:
            page = await self._context.new_page()

            # 성능 최적화: 불필요한 리소스 차단
            await page.route(
                "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf}",
                lambda route: route.abort(),
            )
            await page.route("**/analytics**", lambda route: route.abort())
            await page.route("**/ads**", lambda route: route.abort())

            print(f"'{self.base_url}' 페이지로 이동 중...")
            await page.goto(self.base_url, wait_until="domcontentloaded", timeout=30000)
            print("페이지 로드 완료.")

            # 모든 패치노트 로드
            await self._load_all_patches(page)

            # 패치노트 제목과 링크 수집
            patch_data = await self._collect_patch_data(page)

            await page.close()
            return patch_data

        except Exception as e:
            print(f"크롤링 중 오류 발생: {e}")
            return None

    async def _load_all_patches(self, page):
        """모든 More 버튼을 클릭하여 모든 패치노트 로드"""
        print("\n모든 'More' 버튼을 클릭하여 모든 패치 노트를 로드합니다...")

        click_count = 0
        # max_clicks = 50  # 무한 루프 방지

        while True:  # click_count < max_clicks:
            try:
                more_button = page.locator(".more-button")
                is_visible = await more_button.is_visible()
                is_enabled = await more_button.is_enabled() if is_visible else False

                if is_visible and is_enabled:
                    print(f"More 버튼 클릭 중... ({click_count + 1})")
                    await more_button.click()
                    await asyncio.sleep(1)  # 로딩 시간 확보
                    click_count += 1
                else:
                    print("더 이상 'More' 버튼이 없거나 비활성화되어 있습니다.")
                    break

            except Exception as e:
                print(f"More 버튼 클릭 중 오류: {e}")
                break

        print(f"총 {click_count}번의 More 버튼을 클릭했습니다.")

    async def _collect_patch_data(self, page):
        """패치노트 제목과 링크를 수집하여 정리"""
        print("\nh4.article-title 셀렉터로 모든 패치 노트 제목과 링크를 수집합니다...")

        # 모든 제목 요소 가져오기
        article_elements = await page.locator("h4.article-title").all()
        print(f"총 {len(article_elements)}개의 패치 노트를 수집했습니다.")

        # 패치 노트 데이터 수집
        patch_list = []

        for element in article_elements:
            try:
                title_text = await element.text_content()
                if not title_text or not title_text.strip():
                    continue

                # 링크 추출
                parent_a = element.locator("xpath=ancestor::a[1]")
                relative_url = await parent_a.get_attribute("href")

                if relative_url:
                    full_url = urljoin(self.base_url, relative_url)
                    patch_list.append({"title": title_text.strip(), "url": full_url})

            except Exception as e:
                print(f"패치 데이터 수집 중 오류: {e}")
                continue

        # 패치 데이터 분석 및 그룹화
        return self._analyze_and_group_patches(patch_list)

    def _analyze_and_group_patches(self, patch_list):
        """패치 데이터를 분석하고 버전별로 그룹화"""
        print("\n패치 노트 데이터를 분석하고 그룹화합니다...")

        # 패치 노트를 버전별로 그룹화할 딕셔너리 초기화
        grouped_patches = defaultdict(
            lambda: {"major": {"titles": [], "dates": [], "urls": []}, "minor": []}
        )

        # 정규식 패턴들
        date_pattern = r"(\d{4}\.\d{2}\.\d{2})"
        # 개선된 버전 추출 패턴: x.y, x.yy, x.y.z, x.yy.z 형태를 정확히 캡처
        version_extract_pattern = r"(\d+\.\d+(?:\.\d+)?)\s*([a-zA-Z]*)"

        for patch_data in patch_list:
            title_text = patch_data["title"]
            url = patch_data["url"]

            # 날짜 추출
            date_match = re.search(date_pattern, title_text)
            extracted_date = date_match.group(1) if date_match else None

            # 날짜 부분을 제거하여 버전 매칭
            title_text_no_date = re.sub(date_pattern, "", title_text).strip()

            # 버전 정보 찾기
            match = re.search(version_extract_pattern, title_text_no_date)

            if match:
                full_version = match.group(1)  # 전체 버전 (예: "1.36", "1.36.1")
                alpha_part = match.group(2).strip()  # 알파벳 부분 (예: "a", "b")

                # 그룹화 키는 전체 버전을 사용 (더 이상 x.y로 자르지 않음)
                grouping_key = full_version

                # 0.x 버전 체크 (처리 중단)
                if grouping_key.startswith("0."):
                    major_version_num = int(grouping_key.split(".")[0])
                    if major_version_num == 0:
                        print(
                            f"\n[알림] 0.x 이하 버전 ({grouping_key})이 감지되어 패치 노트 처리를 중단합니다."
                        )
                        break

                # 메이저/마이너 패치 구분
                version_type = "major" if not alpha_part else "minor"

                if version_type == "major":
                    grouped_patches[grouping_key]["major"]["titles"].append(title_text)
                    grouped_patches[grouping_key]["major"]["urls"].append(url)
                    if extracted_date:
                        grouped_patches[grouping_key]["major"]["dates"].append(
                            extracted_date
                        )
                else:  # minor patch
                    grouped_patches[grouping_key]["minor"].append(
                        {
                            "title": title_text,
                            "url": url,
                            "date": extracted_date,
                            "alpha_part": alpha_part,
                        }
                    )
            else:
                print(f"경고: 버전 정보를 찾을 수 없는 패치 노트: {title_text}")

        return grouped_patches

    def _print_grouped_patches(self, grouped_patches):
        """그룹화된 패치 데이터를 콘솔에 출력"""

        def sort_version_keys(key):
            """버전 키를 올바르게 정렬하는 함수"""
            # 버전을 점으로 분리하여 숫자로 변환
            parts = key.split(".")
            # 각 부분을 정수로 변환하여 튜플로 반환
            try:
                return tuple(int(part) for part in parts)
            except ValueError:
                # 숫자가 아닌 경우 문자열 그대로 반환
                return tuple(parts)

        sorted_versions = sorted(
            grouped_patches.keys(), key=sort_version_keys, reverse=True
        )

        print("\n--- 패치 노트 분류 결과 ---")
        for version_key in sorted_versions:
            patches = grouped_patches[version_key]
            major_info = patches["major"]
            minor_patches = patches["minor"]

            if major_info["titles"] or minor_patches:
                # 메이저 패치 날짜 표시 (첫 번째 날짜 사용)
                major_date_str = (
                    f" ({major_info['dates'][0]})" if major_info["dates"] else ""
                )
                print(f"\n== 버전 {version_key}{major_date_str} ==")

                if major_info["titles"]:
                    print("  [메이저 패치 노트]")
                    for i, title in enumerate(major_info["titles"]):
                        url = (
                            major_info["urls"][i]
                            if i < len(major_info["urls"])
                            else "URL 없음"
                        )
                        print(f"    - {title}")
                        print(f"      링크: {url}")

                if minor_patches:
                    print("  [마이너 패치 노트]")
                    # 마이너 패치 정렬 (날짜 및 알파벳 순)
                    sorted_minor_patches = sorted(
                        minor_patches,
                        key=lambda x: (
                            x["date"] if x["date"] else "",
                            x["alpha_part"],
                        ),
                    )
                    for patch_detail in sorted_minor_patches:
                        minor_date_str = (
                            f" ({patch_detail['date']})" if patch_detail["date"] else ""
                        )
                        print(f"    - {patch_detail['title']}{minor_date_str}")
                        print(f"      링크: {patch_detail['url']}")
            else:
                print(f"버전 {version_key}: 해당 버전의 패치 노트가 없습니다.")

        print("\n--- 패치 노트 분류 완료 ---")

    def _save_to_database(self, grouped_patches):
        """그룹화된 패치 데이터를 SQLite 데이터베이스에 저장"""
        print("\nSQLite 데이터베이스에 저장 중...")

        # 데이터베이스 연결 및 테이블 재생성
        conn, c = self._connect_db()
        self._recreate_patch_notes_table(c)

        # 데이터베이스 저장용 데이터 준비
        db_data = []

        def sort_version_keys(key):
            """버전 키를 올바르게 정렬하는 함수"""
            # 버전을 점으로 분리하여 숫자로 변환
            parts = key.split(".")
            # 각 부분을 정수로 변환하여 튜플로 반환
            try:
                return tuple(int(part) for part in parts)
            except ValueError:
                # 숫자가 아닌 경우 문자열 그대로 반환
                return tuple(parts)

        sorted_versions = sorted(
            grouped_patches.keys(), key=sort_version_keys, reverse=True
        )

        for version_key in sorted_versions:
            patches = grouped_patches[version_key]
            major_info = patches["major"]
            minor_patches = patches["minor"]

            # 메이저 패치 처리 - major_patches로 마이너와 동일한 구조 생성
            if major_info["titles"]:
                # 메이저 패치들을 리스트 형태로 구성
                major_patches_list = []
                for i, title in enumerate(major_info["titles"]):
                    url = major_info["urls"][i] if i < len(major_info["urls"]) else ""
                    date = (
                        major_info["dates"][i] if i < len(major_info["dates"]) else ""
                    )

                    major_patches_list.append(
                        {
                            "version": version_key,
                            "url": url,
                            "title": title,
                            "date": date,
                        }
                    )

                # 메이저 패치 데이터를 JSON 문자열로 변환 (마이너와 동일한 구조)
                major_patches_json = json.dumps(major_patches_list, ensure_ascii=False)

                # 첫 번째 메이저 패치의 정보를 대표값으로 사용
                first_major = major_patches_list[0] if major_patches_list else {}

                db_data.append(
                    {
                        "major_version": version_key,
                        "major_date": first_major.get("date", ""),
                        "major_patches": major_patches_json,  # 마이너와 동일한 구조
                        "minor_patches": (
                            json.dumps(minor_patches, ensure_ascii=False)
                            if minor_patches
                            else "[]"
                        ),
                    }
                )

            # 메이저 패치가 없지만 마이너 패치가 있는 경우도 처리
            elif minor_patches:
                db_data.append(
                    {
                        "major_version": version_key,
                        "major_date": "",
                        "major_patches": "[]",  # 빈 배열
                        "minor_patches": json.dumps(minor_patches, ensure_ascii=False),
                    }
                )

        # 데이터베이스에 저장
        if db_data:
            inserted_count = self._insert_patch_data(c, db_data)

            # 저장된 데이터 요약 출력
            total_major_patches = sum(
                len(json.loads(row["major_patches"]))
                for row in db_data
                if row["major_patches"] != "[]"
            )
            total_minor_patches = sum(
                len(json.loads(row["minor_patches"]))
                for row in db_data
                if row["minor_patches"] != "[]"
            )
            print(
                f"메이저 패치: {total_major_patches}개, 마이너 패치: {total_minor_patches}개"
            )

            # 연결 종료
            c.close()
            conn.close()

            return inserted_count
        else:
            print("❌ 저장할 데이터가 없습니다.")
            # 연결 종료
            c.close()
            conn.close()
            return 0

    def get_all_patches_summary(self):
        """데이터베이스에서 전체 패치노트 요약 정보 조회"""
        conn, c = self._connect_db()

        # 테이블이 존재하는지 확인
        c.execute(
            """SELECT count(name) FROM sqlite_master WHERE type='table' AND name='patch_notes' """
        )
        if c.fetchone()[0] == 0:
            print("patch_notes 테이블이 존재하지 않습니다.")
            c.close()
            conn.close()
            return []

        patches = self._get_all_patches_from_db(c)

        c.close()
        conn.close()

        if patches:
            print(f"\n=== 데이터베이스 저장된 패치노트 요약 ===")
            print(f"총 {len(patches)}개의 패치 버전이 저장되어 있습니다.")

            # 최신 5개 버전 출력
            print("\n최신 5개 패치 버전:")
            for i, patch in enumerate(patches[:5]):
                major_patches_count = len(patch["major_patches"])
                minor_patches_count = len(patch["minor_patches"])
                print(
                    f"  {i+1}. 버전 {patch['major_version']} (메이저: {major_patches_count}개, 마이너: {minor_patches_count}개)"
                )

            return patches
        else:
            print("데이터베이스에 저장된 패치노트가 없습니다.")
            return []


async def main():
    """메인 실행 함수"""
    print("=== Eternal Return 전체 패치노트 크롤러 시작 ===")

    async with AllPatchCrawler() as crawler:
        # 모든 패치노트 크롤링
        grouped_patches = await crawler.crawl_all_patches()

        if grouped_patches:
            # 콘솔에 결과 출력
            crawler._print_grouped_patches(grouped_patches)

            # SQLite 데이터베이스에 저장
            saved_count = crawler._save_to_database(grouped_patches)

            if saved_count > 0:
                print(f"\n=== 크롤링 완료 ===")
                print(f"데이터베이스에 {saved_count}개 버전 저장 완료")

                # 저장된 데이터 요약 확인
                crawler.get_all_patches_summary()
            else:
                print("\n=== 크롤링 완료 (저장 실패) ===")
        else:
            print("\n=== 크롤링 실패 ===")


if __name__ == "__main__":
    asyncio.run(main())
