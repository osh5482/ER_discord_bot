import aiohttp
import urllib.parse
from bs4 import BeautifulSoup
from datetime import datetime
import os
from dotenv import load_dotenv

from functions.dict_lib import *

# from dict_lib import *

import asyncio
import json
import time


load_dotenv(verbose=True)
ER_key = os.getenv("ER")
steam_key = os.getenv("steam")

# async def getCurrentPlayer_crawl():  # 웹 크롤링해서 동접 가져오는 함수
#     url = "https://steamcommunity.com/app/1049590"
#     async with aiohttp.ClientSession() as session:
#         async with session.get(url) as response:
#             if response.status == 200:
#                 html = await response.text()
#                 soup = BeautifulSoup(html, "html.parser")
#                 span = soup.find("span", class_="apphub_NumInApp")
#                 currentPlayer, _ = span.text.split(" ")
#                 currentPlayer = currentPlayer.replace(",", "")
#                 return int(currentPlayer)
#             else:
#                 print(f"Error: Failed to fetch URL, status code {response.status}")
#                 return None


async def get_current_player_api():
    """스팀 api로 이리 동접 가져오는 함수
    반환값 : int(동접자수) / 에러시 None"""
    url = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?&appid=1049590"
    headers = {"x-api-key": steam_key}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                response_json = await response.json()
                response = response_json["response"]
                player_count = response["player_count"]
                return player_count

            else:
                print(f"Error: {response.status}")
                return None  # URL 접근 실패시 None 반환


async def add_header(url):
    """
    url에 헤더 추가해주는 함수
    반환값 : dict(파이썬 객체) /
    에러시 aiohttp.ClientResponseError
    """
    headers = {"x-api-key": ER_key}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                response_json = await response.json()
                # print(json.dumps(response_json, ensure_ascii=False, indent=2))
                return response_json  # 디코딩된 URL 반환

            else:  # 보통 네트워크 에러임
                print(f"Error: {response.status}")
                # 여기서 발생한 에러를 호출한 곳으로 전달하고 함
                raise aiohttp.ClientResponseError(status=response.status)


async def get_user_num(nickname):
    """
    닉네임으로 유저id를 가져오는 함수
    반환값 : tuple(유저id,유저 닉네임) /
    없는유저일 경우 int(404) /
    통신에러인 경우 에러값
    """
    base = "https://open-api.bser.io/v1/user/nickname"
    parameters = f"?query={urllib.parse.quote(nickname)}"
    url = base + parameters
    response_json = await add_header(url)

    try:
        # print(response_json)
        if response_json["code"] == 200:
            user = response_json["user"]
            user_num = user["userNum"]
            user_name = user["nickname"]
            return user_num, user_name  # 유저정보가 있으면 id랑 닉네임 반환

        if response_json["code"] == 404:
            return 404  # 없는 유저임

    except aiohttp.ClientResponseError as e:
        print(f"Error: code: {e.status}, {e.message}")
        return e  # 네트워크 에러처리


async def get_current_season():
    """현재 진행중인 시즌의 정보를 가져오는 함수
    반환값 : dict(현재시즌 정보) /
    통신에러인 경우 에러값"""
    url = "https://open-api.bser.io/v2/data/Season"
    response_json = await add_header(url)

    if response_json != aiohttp.ClientResponseError:
        all_season_data = response_json["data"]

        if all_season_data:
            current_season_data = all_season_data[-1]
            return current_season_data

        else:
            print("Error: 'data' key not found in JSON response")
            return None

    else:
        print("Error: Failed to fetch response from the API")
        return response_json


async def get_current_season_name():
    """현재시즌의 이름을 확인하는 함수
    반환값 : tuple(현재 시즌 데이터, 현재 시즌 이름) /
    에러시 None"""
    try:
        current_season_data = await get_current_season()

        if current_season_data:
            season_id = current_season_data["seasonID"]

            if (season_id - 17) % 2 == 0:
                front = "정규 시즌"
                now = (season_id - 17) // 2

            else:
                front = "프리 시즌"
                now = ((season_id - 17) // 2) + 1
            current_season_name = f"{front} {now}"
            return current_season_data, current_season_name

        else:
            print("Error: Failed to get current season data")
            return None

    except Exception as e:
        print(e)
        return None


async def end_current_season(current_season_data):
    """현재시즌 끝나는 날짜와 시간 가져오는 함수
    반환값 : str(끝나는 날짜) /
    에러시 None"""
    if current_season_data:
        season_end = current_season_data["seasonEnd"]
        # print("Success: take end time of current season")
        end_date, end_time = season_end.split(" ")
        end_year, end_month, end_day = end_date.split("-")
        end_hour = end_time.split(":")[0]
        last_day = f"{end_year}년 {end_month}월 {end_day}일 {end_hour}시"
        return last_day

    else:
        print("Error: Failed to get current season data")
        return None


async def remain_time(current_season_data):
    """특정시즌 끝날때까지 남은 시간 계산하는 함수
    반환값 : list(남은시간 d,H,M) /
    에러시 None"""
    try:

        if current_season_data:
            season_end = current_season_data["seasonEnd"]
            target_time = datetime.strptime(season_end, "%Y-%m-%d %H:%M:%S")
            current_time = datetime.now()

            time_difference = target_time - current_time  # 차이 계산

            remaining_seconds = (
                time_difference.total_seconds()
            )  # 남은 시간을 초 단위로 변환

            remaining_days, remaining_seconds = divmod(remaining_seconds, 86400)
            remaining_hours, remaining_seconds = divmod(remaining_seconds, 3600)
            remaining_minutes, _ = divmod(
                remaining_seconds, 60
            )  # 남은 일, 시간, 분 계산

            remaining_time_list = [
                int(remaining_days),
                int(remaining_hours),
                int(remaining_minutes),
            ]  # 반환값 리스트 생성

            # print("Success: creating remain time list [d,h,m]")
            return remaining_time_list

        else:
            print("Error: Failed to get current season data")
            return None

    except Exception as e:
        print(f"Error: {e}")
        return None


async def get_user_season_data(user_tuple):
    """
    유저 정보 튜플로 시즌 랭크 데이터 가져오는 함수
    반환값 : dict(유저 현재시즌 랭크 데이터) /
    유저가 없는경우 int(404) /
    유저가 랭을 안돌린 경우 int(0)"""
    if user_tuple == 404:  # 없는유저인경우
        return 404

    else:
        user_num = user_tuple[0]
        # user_name = user_tuple[1]
        base = "https://open-api.bser.io/v1/user/stats"
        current_season_data = await get_current_season()
        season_id = current_season_data["seasonID"]
        para = f"/{user_num}/{season_id}"  # 3시즌 랭쿼드 데이터
        url = base + para
        response_json = await add_header(url)

        if response_json["code"] == 404:  # 시즌데이터가 없는경우
            return 0

        else:
            user_stats = response_json["userStats"][0]
            tier = detect_tier(user_stats)
            user_stats["tier"] = tier
            # print(f"Success: creating user's season data")
            # print(json.dumps(user_stats, ensure_ascii=False, indent=2))
            return user_stats  # 유저의 랭크 데이터를 딕셔너리로 반환


# async def getSimpleData(user_num):  # 유저 id로 기본 데이터 가져오는 함수
#     if user_num is None:
#         return None
#     base = "https://open-api.bser.io/v1/"
#     current_season_data = await getCurrentSeason()
#     season_id = current_season_data["seasonID"]
#     para = f"/{user_num}/{season_id}"  # 3시즌 랭쿼드 데이터
#     url = base + para
#     async with aiohttp.ClientSession() as session:
#         async with session.get(url) as response:
#             if response.status != 200:  # 데이터를 가져오지 못한 경우 None 반환
#                 print("존재하지 않는 유저")
#                 return None
#             else:
#                 data = await response.json()
#                 return data["message"]


def detect_tier(userStats):
    """
    mmr에 따른 티어 탐지하는 함수
    반환값 : str(티어)"""
    mmr = userStats["mmr"]

    if mmr >= 6400:
        rank = userStats["rank"]
        userTier = is_ranker(rank, mmr)
        # print("Success: detecting user tier")
        return userTier

    else:
        userTier = is_not_ranker(mmr)
        return userTier


def is_not_ranker(mmr, tiers=tiers):
    for tier, ranges in tiers.items():
        division = 4
        for low, high in ranges:
            if low <= mmr < high:
                userTier = tier
                return f"{userTier} {division}"
            division -= 1


def is_ranker(rank, mmr):
    """다이아 이상 티어 구분 함수
    반환값 : str(티어)"""
    if rank < 200 and mmr > 7000:
        tier = "이터니티"
    elif rank < 700 and mmr > 7000:
        tier = "데미갓"
    elif mmr > 6800:
        tier = "미스릴"
    else:
        tier = "메테오라이트"
    return tier


# async def getMostCharacterCode(user_num):  # 유저 id로 모스트 캐릭터 코드 찾는 함수
#     try:
#         user_stats = await getUserSeasonData(user_num)
#         if user_stats:
#             character_stats = user_stats["characterStats"]
#             most_character_code = character_stats[0]["characterCode"]
#             print(most_character_code)
#             return most_character_code
#         else:
#             print("Error: Failed to get user stats")
#             return None
#     except Exception as e:
#         print(f"Error: {e}")
#         return None


def find_characte_name(most_character_code, char_code=char_code):
    """캐릭터 코드로 캐릭터 이름 찾는 함수
    반환값 : tuple(캐릭이름, 캐릭코드) /
    에러시 None"""
    for name, code in char_code.items():
        if code == most_character_code:
            # print("Success: find user most character with code")
            return name, code
    return None


async def get_demigod_rating() -> int:
    """데미갓 컷 알려주는 함수
    반환값 : int(데미갓 컷 점수) /
    에러시 None"""
    try:
        base = "https://open-api.bser.io/v1"
        current_season_data = await get_current_season()
        season_id = current_season_data["seasonID"]
        para = f"/rank/top/{season_id}/3"  # 3시즌 랭쿼드 데이터
        url = base + para
        response_json = await add_header(url)

        top_ranks = response_json["topRanks"]
        last_demigod = top_ranks[699]
        demigod_cut = last_demigod["mmr"]
        return demigod_cut

    except Exception as e:
        print(f"Error: {e}")
        return None


async def get_iternity_rating() -> int:
    """이터니티 컷 알려주는 함수
    반환값 : int(이터니티 컷 점수) /
    에러시 None"""
    try:
        base = "https://open-api.bser.io/v1"
        current_season_data = await get_current_season()
        season_id = current_season_data["seasonID"]
        para = f"/rank/top/{season_id}/3"  # 3시즌 랭쿼드 데이터
        url = base + para
        response_json = await add_header(url)

        top_ranks = response_json["topRanks"]
        last_iternity = top_ranks[199]
        iternity_cut = last_iternity["mmr"]
        return iternity_cut

    except Exception as e:
        print(f"Error: {e}")
        return None


async def get_patchnote() -> str:
    """공홈에서 제일 최근 메이저 패치노트 링크 가져오는 함수
    반환값 : str(최근 메이저 패치노트 url) /
    에러시 None"""
    try:
        patch_note_list_url = (
            "https://playeternalreturn.com/posts/news?categoryPath=patchnote"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(patch_note_list_url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    tag_div = soup.find("ul", class_="er-articles")
                    for li in tag_div.find_all("li"):
                        h4 = li.find("h4", class_="er-article__title")
                        if h4 and "PATCH NOTES" in h4.text:
                            a = li.find("a", class_="er-article-link")
                            if a:
                                recent_patch_note = a["href"]
                                return recent_patch_note
                    print("Error: Failed to find patch note")
                    return None
                else:
                    print(
                        f"Error: Failed to fetch HTML, status code: {response.status}"
                    )
                    return None
    except Exception as e:
        print(f"Error: {e}")
        return None


async def get_routh(id):
    url = f"https://open-api.bser.io/v1/weaponRoutes/recommend/{id}"
    response_json = await add_header(url)
    print(json.dumps(response_json, ensure_ascii=False, indent=2))
    return response_json


async def get_meta_data(meta):
    url = f"https://open-api.bser.io/v1/data/{meta}"
    response_json = await add_header(url)
    return response_json


async def get_user_recent_games_10(user_num, next=None):
    """유저의 최근 10게임 반환
    반환값 : dict"""
    url = f"https://open-api.bser.io/v1/user/games/{user_num}"
    if next is not None:
        url += f"?next={next}"
    response_json = await add_header(url)

    return response_json


async def get_user_recent_games_90d(user_num):
    games = []
    next = None

    while True:
        result = await get_user_recent_games_10(user_num, next=next)
        games.append(result)
        if "next" not in result.keys():
            break
        next = result["next"]

    return games


async def main():
    start_time = time.perf_counter()

    tuples = await get_user_num("아니tlqk내솔로가")
    a = await get_user_season_data(tuples)
    print(json.dumps(a, ensure_ascii=False, indent=2))

    end_time = time.perf_counter()  # 종료 시간 기록
    total_time = end_time - start_time  # 전체 작업 시간 계산
    rounded_time = round(total_time, 3)
    print(f"Total time taken: {rounded_time} seconds")  # 전체 작업 시간 출력


if __name__ == "__main__":
    asyncio.run(main())
