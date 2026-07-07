import asyncio
import json
import aiohttp
from bs4 import BeautifulSoup
from utils.constants import *
from utils.logger import logger


# aiohttp 요청에 사용할 헤더 (봇 탐지 우회)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://dak.gg/",
}


async def _fetch_character_stats(session, weapon, character_name, tier=None):
    """
    dak.gg에서 캐릭터 통계를 HTTP 요청으로 가져와 파싱한다.
    Playwright 없이 __NEXT_DATA__ JSON을 직접 추출하여 속도를 대폭 향상시킨다.

    Args:
        session: aiohttp.ClientSession 인스턴스
        weapon: 무기 타입 (영문, 예: "Glove")
        character_name: 캐릭터 이름 (영문, 예: "Hyunwoo")
        tier: 티어 필터 (dak.gg URL 파라미터, 예: "diamond_plus")
              None이면 기본값(다이아몬드+)

    Returns:
        dict: 통계 정보 딕셔너리 (기존 Playwright 방식과 동일한 형식)

    Raises:
        Exception: 요청 실패 또는 데이터 파싱 실패 시
    """
    url = f"https://dak.gg/er/characters/{character_name}?weaponType={weapon}"
    if tier:
        url += f"&tier={tier}"

    logger.info(f"통계 요청 중: {url}")

    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        if resp.status != 200:
            raise Exception(f"HTTP {resp.status} 응답: {url}")
        html = await resp.text()

    # __NEXT_DATA__ JSON 태그에서 통계 데이터 추출
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        raise Exception(
            "__NEXT_DATA__ 태그를 찾을 수 없습니다. dak.gg 구조가 변경되었을 수 있습니다."
        )

    next_data = json.loads(script.text)
    queries = next_data["props"]["pageProps"]["dehydratedState"]["queries"]

    # getCharacterStatistics 쿼리 찾기
    stats_data = None
    for q in queries:
        query_key = q.get("queryKey", [])
        if "getCharacterStatistics" in query_key:
            stats_data = q["state"]["data"]
            break

    if not stats_data:
        raise Exception("통계 쿼리 데이터를 찾을 수 없습니다.")

    snapshot = stats_data["characterDetailStatSnapshot"]
    detail = snapshot["characterDetailStat"]
    tier_count = snapshot["tierCount"]

    # 해당 무기의 통계 찾기 (weaponStats 배열에서 가장 count가 큰 항목 = 요청한 무기)
    weapon_stats = detail.get("weaponStats", [])
    if not weapon_stats:
        raise Exception("무기 통계 데이터가 없습니다.")

    # count가 가장 큰 무기 통계 선택 (URL에서 지정한 무기)
    ws = max(weapon_stats, key=lambda x: x["count"])

    count = ws["count"]
    win = ws["win"]
    mmr_gain = ws["mmrGain"]
    rank_data = ws.get("rank", {})
    rank_size = rank_data.get("size", "")

    # 픽률, 승률, RP 획득 계산 (dak.gg 표시 형식에 맞춤)
    # 픽률 = 이 무기의 픽 수 / 티어 전체 픽 슬롯 수(tierCount).
    # tierGameCount(게임 수)가 아니라 tierCount로 나눠야 dak.gg 표시값과 일치한다.
    pick_rate = (count / tier_count * 100) if tier_count > 0 else 0
    win_rate = (win / count * 100) if count > 0 else 0
    rp_gain = (mmr_gain / count) if count > 0 else 0

    def _fmt_rank(key):
        r = rank_data.get(key)
        if r is None:
            return "-"
        return f"{r} / {rank_size}" if rank_size else str(r)

    # 기존 Playwright 방식과 동일한 출력 형식
    statistics_dict = {
        "code": char_code[character_name],
        "character_name": char_korean[character_name],
        "weapon": weapon_korean[weapon],
        "픽률": {
            "value": f"{pick_rate:.2f} %",
            "ranking": _fmt_rank("count"),
        },
        "승률": {
            "value": f"{win_rate:.2f} %",
            "ranking": _fmt_rank("win"),
        },
        "RP 획득": {
            "value": f"{rp_gain:.1f}",
            "ranking": _fmt_rank("mmrGain"),
        },
    }

    logger.info(f"통계 파싱 완료: {character_name}/{weapon} (tier={tier})")
    return statistics_dict


async def _fetch_page_data(session, character_name, tier=None):
    """
    dak.gg 캐릭터 페이지를 요청하고 __NEXT_DATA__ JSON을 파싱하여 반환한다.
    weaponType 파라미터 없이 요청하여 모든 무기 통계를 포함시킨다.

    Returns:
        tuple: (stats_data, mastery_map) - 통계 쿼리 데이터, mastery ID→무기영문명 매핑
    """
    url = f"https://dak.gg/er/characters/{character_name}"
    if tier:
        url += f"?tier={tier}"

    logger.info(f"페이지 요청 중: {url}")

    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        if resp.status != 200:
            raise Exception(f"HTTP {resp.status} 응답: {url}")
        html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script:
        raise Exception("__NEXT_DATA__ 태그를 찾을 수 없습니다.")

    next_data = json.loads(script.text)
    queries = next_data["props"]["pageProps"]["dehydratedState"]["queries"]

    # mastery ID → 무기 영문명 매핑 구축
    mastery_map = {}
    for q in queries:
        qk = q.get("queryKey", [])
        if any("MASTERI" in str(k).upper() for k in qk):
            for m in q["state"]["data"]["masteries"]:
                mastery_map[m["id"]] = m["key"]
            break

    # 통계 쿼리 찾기
    stats_data = None
    for q in queries:
        query_key = q.get("queryKey", [])
        if "getCharacterStatistics" in query_key:
            stats_data = q["state"]["data"]
            break

    if not stats_data:
        raise Exception("통계 쿼리 데이터를 찾을 수 없습니다.")

    return stats_data, mastery_map


def _build_weapon_stats_dict(ws, character_name, weapon_key, tier_count):
    """weaponStats 항목 하나를 기존 형식의 stats_dict로 변환한다."""
    count = ws["count"]
    win = ws["win"]
    mmr_gain = ws["mmrGain"]
    rank_data = ws.get("rank", {})
    rank_size = rank_data.get("size", "")

    # 픽률 = 이 무기의 픽 수 / 티어 전체 픽 슬롯 수(tierCount).
    # tierGameCount(게임 수)가 아니라 tierCount로 나눠야 dak.gg 표시값과 일치한다.
    pick_rate = (count / tier_count * 100) if tier_count > 0 else 0
    win_rate = (win / count * 100) if count > 0 else 0
    rp_gain = (mmr_gain / count) if count > 0 else 0

    def _fmt_rank(key):
        r = rank_data.get(key)
        if r is None:
            return "-"
        return f"{r} / {rank_size}" if rank_size else str(r)

    return {
        "code": char_code[character_name],
        "character_name": char_korean[character_name],
        "weapon": weapon_korean.get(weapon_key, weapon_key),
        "픽률": {
            "value": f"{pick_rate:.2f} %",
            "ranking": _fmt_rank("count"),
        },
        "승률": {
            "value": f"{win_rate:.2f} %",
            "ranking": _fmt_rank("win"),
        },
        "RP 획득": {
            "value": f"{rp_gain:.1f}",
            "ranking": _fmt_rank("mmrGain"),
        },
    }


async def _fetch_all_weapon_stats(session, character_name, tier=None):
    """
    한 번의 HTTP 요청으로 캐릭터의 모든 무기 통계를 가져온다.

    Args:
        session: aiohttp.ClientSession 인스턴스
        character_name: 캐릭터 이름 (영문)
        tier: 티어 필터 (None이면 기본값 다이아몬드+)

    Returns:
        dict: 무기 영문명을 키로 하는 stats_dict 딕셔너리 (count 내림차순 정렬)
              예: {"Glove": {...}, "Tonfa": {...}}
    """
    stats_data, mastery_map = await _fetch_page_data(session, character_name, tier)

    snapshot = stats_data["characterDetailStatSnapshot"]
    detail = snapshot["characterDetailStat"]
    tier_count = snapshot["tierCount"]

    weapon_stats = detail.get("weaponStats", [])
    if not weapon_stats:
        raise Exception("무기 통계 데이터가 없습니다.")

    # count 내림차순 정렬 (첫 번째 = 가장 인기 무기)
    weapon_stats_sorted = sorted(weapon_stats, key=lambda x: x["count"], reverse=True)

    result = {}
    for ws in weapon_stats_sorted:
        weapon_key = mastery_map.get(ws["key"])
        if not weapon_key:
            logger.warning(f"알 수 없는 mastery ID: {ws['key']}, 건너뜀")
            continue
        result[weapon_key] = _build_weapon_stats_dict(
            ws, character_name, weapon_key, tier_count
        )

    logger.info(
        f"전체 무기 통계 파싱 완료: {character_name} (tier={tier}, 무기 {len(result)}개)"
    )
    return result


async def dakgg_crawler_all_weapons(character_name, tier=None):
    """
    캐릭터의 모든 무기 통계를 한 번의 요청으로 가져온다.

    Args:
        character_name: 캐릭터 이름 (영문)
        tier: 티어 필터 (None이면 기본값 다이아몬드+)

    Returns:
        dict: 무기 영문명을 키로 하는 stats_dict (count 내림차순)
    """
    async with aiohttp.ClientSession(headers=_HEADERS) as session:
        return await _fetch_all_weapon_stats(session, character_name, tier)


async def dakgg_crawler_all_weapons_all_tiers(character_name, tier_data):
    """
    모든 티어의 전체 무기 통계를 병렬로 크롤링하여 tier_data에 저장한다.

    Args:
        character_name: 캐릭터 이름 (영문)
        tier_data: 크롤링 결과를 저장할 딕셔너리 (공유 참조)
                   키: 티어값, 값: {무기영문명: stats_dict} 형태
    """
    remaining_tiers = [
        tier_value for tier_value in tier_filter.values() if tier_value not in tier_data
    ]

    if not remaining_tiers:
        return

    async with aiohttp.ClientSession(headers=_HEADERS) as session:

        async def _crawl_tier(tier_value):
            try:
                data = await _fetch_all_weapon_stats(
                    session, character_name, tier_value
                )
                tier_data[tier_value] = data
                logger.info(f"백그라운드 전체 무기 크롤링 완료: {tier_value}")
            except Exception as e:
                tier_data[tier_value] = None
                logger.warning(f"백그라운드 전체 무기 크롤링 실패 ({tier_value}): {e}")

        await asyncio.gather(*[_crawl_tier(t) for t in remaining_tiers])


async def dakgg_crawler(weapon, character_name, tier=None):
    """
    무기, 캐릭터 이름으로 닥지지 통계 크롤링해오기 (aiohttp 방식)

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
    async with aiohttp.ClientSession(headers=_HEADERS) as session:
        return await _fetch_character_stats(session, weapon, character_name, tier)


async def dakgg_crawler_all_tiers(weapon, character_name, tier_data):
    """
    모든 티어의 통계를 병렬로 크롤링하여 tier_data에 저장한다.
    asyncio.gather를 사용해 모든 티어를 동시에 요청하여 속도를 대폭 향상시킨다.

    Args:
        weapon: 무기 타입 (영문)
        character_name: 캐릭터 이름 (영문)
        tier_data: 크롤링 결과를 저장할 딕셔너리 (공유 참조)
                   이미 크롤링된 티어는 건너뜀
    """
    # 아직 크롤링되지 않은 티어만 수집
    remaining_tiers = [
        tier_value for tier_value in tier_filter.values() if tier_value not in tier_data
    ]

    if not remaining_tiers:
        return

    async with aiohttp.ClientSession(headers=_HEADERS) as session:

        async def _crawl_tier(tier_value):
            try:
                data = await _fetch_character_stats(
                    session, weapon, character_name, tier_value
                )
                tier_data[tier_value] = data
                logger.info(f"백그라운드 크롤링 완료: {tier_value}")
            except Exception as e:
                tier_data[tier_value] = None
                logger.warning(f"백그라운드 크롤링 실패 ({tier_value}): {e}")

        # 모든 남은 티어를 동시에 요청
        await asyncio.gather(*[_crawl_tier(t) for t in remaining_tiers])


async def main():
    """테스트용 메인 함수"""
    try:
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
