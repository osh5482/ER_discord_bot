import re
import aiohttp
from datetime import datetime
from utils.logger import logger


# 패치노트 카테고리 ID (Eternal Return 공식 사이트 API 기준)
PATCH_NOTE_CATEGORY_ID = 28

# API 엔드포인트
API_URL = "https://playeternalreturn.com/api/v1/posts/news"


class PatchNoteCrawler:
    """Eternal Return 패치노트 크롤링 클래스 (REST API 기반)

    공식 사이트의 내부 REST API를 직접 호출하여 패치노트 데이터를 수집한다.
    Playwright(헤드리스 브라우저) 대비 메모리 사용량과 속도가 대폭 개선됨.
    """

    def __init__(self):
        self._session = None

    async def __aenter__(self):
        """컨텍스트 매니저 진입 - HTTP 세션 생성"""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료 - HTTP 세션 정리"""
        if self._session:
            await self._session.close()

    async def get_patch_info(
        self, load_all: bool = False, until_version: str = None
    ) -> dict:
        """패치노트 정보를 API에서 수집하여 반환

        Args:
            load_all: True이면 전체 히스토리를 수집한다.
                      False이면 until_version이 나타날 때까지만 수집한다.
            until_version: 증분 크롤링 시 기준이 되는 버전 문자열 (예: "10.1").
                           이 버전이 수집되면 이후 페이지 요청을 중단한다.
                           load_all=True이면 무시된다.

        Returns:
            dict: {"versions": [...]} 형식의 패치노트 데이터.
                  각 버전은 major_version, major_date, major_patches, minor_patch_data를 포함한다.
        """
        try:
            # API에서 패치노트 아티클 수집
            articles = await self._fetch_all_patch_articles(
                load_all=load_all, until_version=until_version
            )

            if not articles:
                logger.warning("수집된 패치노트 아티클이 없습니다.")
                return {"versions": []}

            # 아티클을 버전별로 그룹화하여 반환
            versions = self._group_articles_by_version(articles)
            return {"versions": versions}

        except Exception as e:
            logger.error(f"크롤링 중 오류 발생: {e}")
            return None

    async def _fetch_page(self, page_num: int) -> dict:
        """API에서 한 페이지의 아티클을 가져온다.

        Args:
            page_num: 페이지 번호 (1부터 시작)

        Returns:
            dict: API 응답 JSON. 실패 시 None.
        """
        params = {"categoryPath": "patchnote", "page": page_num, "hl": "ko"}
        try:
            async with self._session.get(API_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"API 요청 실패 (page={page_num}): HTTP {resp.status}")
                    return None
        except Exception as e:
            logger.warning(f"API 요청 중 오류 (page={page_num}): {e}")
            return None

    async def _fetch_all_patch_articles(
        self, load_all: bool = False, until_version: str = None
    ) -> list:
        """전체 또는 증분으로 패치노트 아티클을 수집한다.

        Args:
            load_all: True이면 모든 페이지를 순회한다.
            until_version: 이 버전이 수집되면 순회를 중단한다.

        Returns:
            list: 패치노트 아티클 딕셔너리 리스트 (최신순).
        """
        articles = []
        found_versions = set()
        page_num = 1

        while True:
            data = await self._fetch_page(page_num)
            if not data:
                break

            page_articles = data.get("articles", [])
            if not page_articles:
                logger.debug(f"page={page_num}: 아티클 없음. 순회 종료.")
                break

            total_page = data.get("total_page", 1)

            # 패치노트 카테고리(category_id=28)만 필터링
            for article in page_articles:
                if article.get("category_id") != PATCH_NOTE_CATEGORY_ID:
                    continue

                parsed = self._parse_article(article)
                if parsed:
                    articles.append(parsed)
                    if parsed.get("major_version"):
                        found_versions.add(parsed["major_version"])

            logger.debug(
                f"page={page_num}/{total_page}: "
                f"패치노트 {len(articles)}개 수집됨"
            )

            # 증분/최근 모드 중단 조건
            if not load_all:
                if until_version:
                    # 증분 모드: until_version이 수집되었고, 그보다 오래된 버전도 발견되면 중단
                    # (until_version의 모든 파트가 로드됐음을 보장하기 위함)
                    if until_version in found_versions and self._has_older_version(found_versions, until_version):
                        logger.info(
                            f"기준 버전 {until_version}보다 오래된 버전 발견 — 수집 중단 (page={page_num})."
                        )
                        break
                else:
                    # 최근 모드 (until_version 없음): 메이저 버전 2개 이상 발견되면 중단
                    # (최신 메이저 버전의 모든 파트+마이너가 수집되었음을 보장)
                    major_versions_found = {
                        a["major_version"] for a in articles if not a["is_minor"]
                    }
                    if len(major_versions_found) >= 2:
                        logger.debug(
                            f"최근 모드: 메이저 버전 {len(major_versions_found)}개 발견 — 수집 중단."
                        )
                        break

            # 마지막 페이지 도달 시 종료
            if page_num >= total_page:
                logger.debug(f"마지막 페이지 도달 (page={page_num}/{total_page}).")
                break

            page_num += 1

        logger.info(f"총 {len(articles)}개의 패치노트 아티클 수집 완료.")
        return articles

    def _parse_article(self, article: dict) -> dict:
        """API 아티클 객체를 파싱하여 필요한 정보를 추출한다.

        Args:
            article: API 응답의 단일 아티클 객체

        Returns:
            dict: 파싱된 아티클 정보. 파싱 실패 시 None.
                - title: 원본 제목
                - url: 아티클 URL
                - date: 날짜 문자열 (YYYY.MM.DD)
                - version: 버전 문자열 (예: "10.4" 또는 "10.4a")
                - is_minor: 마이너 패치 여부
                - major_version: 메이저 버전 (예: "10.4")
        """
        # 제목 추출 (i18ns에서 사용 가능한 로케일 선택)
        i18ns = article.get("i18ns", {})
        locale_data = i18ns.get("ko_KR") or i18ns.get("en_US")
        if not locale_data:
            # 아무 로케일이나 사용
            locale_data = next(iter(i18ns.values()), None)
        if not locale_data:
            return None

        title = locale_data.get("title", "").strip()
        if not title:
            return None

        url = article.get("url", "")

        # 날짜 추출: API의 created_at(ISO 8601) → YYYY.MM.DD 형식
        created_at = article.get("created_at", "")
        date = None
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                date = dt.strftime("%Y.%m.%d")
            except (ValueError, AttributeError):
                pass

        # 제목에서도 날짜 추출 시도 (제목에 날짜가 있는 경우 우선 사용)
        title_date_match = re.search(r"(\d{4}\.\d{2}\.\d{2})", title)
        if title_date_match:
            date = title_date_match.group(1)

        # 날짜 부분을 제거한 제목으로 버전 매칭 (날짜 숫자가 버전으로 오탐되는 것 방지)
        title_no_date = re.sub(r"\d{4}\.\d{2}\.\d{2}", "", title).strip()

        # 버전 추출
        # 마이너 패치: "10.4a", "1.1.0b" 등 (버전+알파벳 접미사)
        minor_match = re.search(
            r"(?<!\d)(\d+\.\d+(?:\.\d+)?)([a-z])\b", title_no_date, re.IGNORECASE
        )
        if minor_match:
            version = minor_match.group(1) + minor_match.group(2).lower()
            major_version = self._normalize_version(minor_match.group(1))
            return {
                "title": title,
                "url": url,
                "date": date,
                "version": version,
                "is_minor": True,
                "major_version": major_version,
            }

        # 메이저 패치: "10.4 패치노트", "PATCH NOTES 10.4" 등
        major_match = re.search(
            r"(?<!\d)(\d+\.\d+(?:\.\d+)?)\s*(?:PATCH NOTES|패치노트)",
            title_no_date,
            re.IGNORECASE,
        )
        if not major_match:
            major_match = re.search(
                r"(?:PATCH NOTES|패치노트)\s*(\d+\.\d+(?:\.\d+)?)",
                title_no_date,
                re.IGNORECASE,
            )
        if major_match:
            version = self._normalize_version(major_match.group(1))
            return {
                "title": title,
                "url": url,
                "date": date,
                "version": version,
                "is_minor": False,
                "major_version": version,
            }

        # 패치노트 키워드 없이 버전만 있는 제목 (예: "1.0.0 실험체", "1.0.0 전술 스킬")
        # category_id=28로 이미 필터링됐으므로 패치노트 관련 게시글 확정
        fallback_match = re.search(
            r"(?<!\d)(\d+\.\d+(?:\.\d+)?)(?!\d)", title_no_date
        )
        if fallback_match:
            version = self._normalize_version(fallback_match.group(1))
            return {
                "title": title,
                "url": url,
                "date": date,
                "version": version,
                "is_minor": False,
                "major_version": version,
            }

        return None

    @staticmethod
    def _normalize_version(version: str) -> str:
        """버전 문자열을 정규화한다.

        trailing '.0'을 제거하여 "1.1.0" → "1.1", "1.0.0" → "1.0" 형태로 통일한다.
        단, "10.4" 같은 2자리 버전은 그대로 유지한다.

        Args:
            version: 원본 버전 문자열

        Returns:
            str: 정규화된 버전 문자열
        """
        # X.Y.0 형태에서 trailing .0 제거 → X.Y
        normalized = re.sub(r"\.0$", "", version)
        # 최소 X.Y 형태는 유지 (예: "1.0" → "1.0", "0" 같은 건 안 됨)
        if "." not in normalized:
            return version
        return normalized

    def _group_articles_by_version(self, articles: list) -> list:
        """파싱된 아티클 리스트를 버전별로 그룹화한다.

        기존 Playwright 크롤러와 동일한 반환 형식을 유지한다:
        [
            {
                "major_version": "10.4",
                "major_date": "2024.03.12",
                "major_patches": [{"version", "date", "url", "title"}, ...],
                "minor_patch_data": [{"version", "url", "title"}, ...]
            },
            ...
        ]

        Args:
            articles: _parse_article()로 파싱된 아티클 리스트 (최신순)

        Returns:
            list: 버전별 그룹화된 패치 데이터 리스트 (최신순)
        """
        # 버전별로 분류
        version_map = {}  # major_version -> {"major": [], "minor": []}

        for article in articles:
            mv = article["major_version"]
            if mv not in version_map:
                version_map[mv] = {"major": [], "minor": []}

            if article["is_minor"]:
                version_map[mv]["minor"].append(article)
            else:
                version_map[mv]["major"].append(article)

        # 버전 순서 유지 (아티클이 최신순으로 들어왔으므로, 처음 등장 순서가 최신순)
        seen_order = []
        for article in articles:
            mv = article["major_version"]
            if mv not in seen_order:
                seen_order.append(mv)

        results = []
        for mv in seen_order:
            data = version_map[mv]

            # 메이저 패치 정리 (제목순 정렬: Part.1 → Part.2)
            major_patches = [
                {
                    "version": a["major_version"],
                    "date": a["date"],
                    "url": a["url"],
                    "title": a["title"],
                }
                for a in sorted(data["major"], key=lambda x: x["title"])
            ]

            major_date = major_patches[0]["date"] if major_patches else None

            # 마이너 패치 정리 (오래된 순: a → b → c)
            minor_patch_data = [
                {
                    "version": a["version"],
                    "url": a["url"],
                    "title": a["title"],
                }
                for a in reversed(data["minor"])
            ]

            results.append(
                {
                    "major_version": mv,
                    "major_date": major_date,
                    "major_patches": major_patches,
                    "minor_patch_data": minor_patch_data,
                }
            )

        logger.info(f"총 {len(results)}개의 메이저 버전으로 그룹화 완료.")
        return results

    @staticmethod
    def _has_older_version(found_versions: set, target_version: str) -> bool:
        """수집된 버전 중 target_version보다 오래된 것이 있는지 확인한다.

        Args:
            found_versions: 지금까지 수집된 메이저 버전 집합
            target_version: 기준 버전

        Returns:
            bool: 기준 버전보다 오래된 버전이 존재하면 True
        """
        def version_key(v):
            try:
                return tuple(int(x) for x in v.split("."))
            except (ValueError, AttributeError):
                return (0, 0)

        target_key = version_key(target_version)
        for v in found_versions:
            if version_key(v) < target_key:
                return True
        return False


async def get_patch_info(load_all: bool = False, until_version: str = None):
    """패치노트 정보 반환

    Args:
        load_all: True이면 전체 패치 히스토리를 수집한다.
        until_version: 증분 크롤링 시 기준 버전. 이 버전이 보이면 수집 중단.
                       load_all=True이거나 None이면 무시된다.
    """
    mode_label = (
        "[전체 히스토리]"
        if load_all
        else f"[증분: {until_version}까지]" if until_version else "[최근]"
    )
    logger.info(f"패치노트 크롤링 시작... {mode_label}")
    async with PatchNoteCrawler() as crawler:
        return await crawler.get_patch_info(
            load_all=load_all, until_version=until_version
        )
