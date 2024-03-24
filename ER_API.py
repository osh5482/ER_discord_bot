from bs4 import BeautifulSoup
import urllib.request
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv(verbose=True)
API_key = os.getenv("ER_API_KEY")
charCode = {
    "jackie": 1,
    "aya": 2,
    "hyunwoo": 3,
    "magnus": 4,
    "fiora": 5,
    "nadine": 6,
    "zahir": 7,
    "hart": 8,
    "isol": 9,
    "lidailin": 10,
    "yuki": 11,
    "hyejin": 12,
    "xiukai": 13,
    "sissela": 14,
    "chiara": 15,
    "adriana": 16,
    "silvia": 17,
    "shoichi": 18,
    "emma": 19,
    "lenox": 20,
    "rozzi": 21,
    "luke": 22,
    "cathy": 23,
    "adela": 24,
    "bernice": 25,
    "barbara": 26,
    "alex": 27,
    "sua": 28,
    "leon": 29,
    "eleven": 30,
    "rio": 31,
    "william": 32,
    "nicky": 33,
    "nathapon": 34,
    "jan": 35,
    "eva": 36,
    "daniel": 37,
    "jenny": 38,
    "camilo": 39,
    "chloe": 40,
    "johann": 41,
    "bianca": 42,
    "celine": 43,
    "echion": 44,
    "mai": 45,
    "aiden": 46,
    "laura": 47,
    "tia": 48,
    "felix": 49,
    "elena": 50,
    "priya": 51,
    "adina": 52,
    "markus": 53,
    "karla": 54,
    "estelle": 55,
    "piolo": 56,
    "martina": 57,
    "haze": 58,
    "issac": 59,
    "tazia": 60,
    "irem": 61,
    "theodore": 62,
    "lyanh": 63,
    "vanya": 64,
    "debimariene": 65,
    "arda": 66,
    "abigail": 67,
    "alonso": 68,
    "leni": 69,
    "tsubame": 70,
    "kenneth": 71,
    "katja": 72,
}


# def getInGameUser():  # 동접 가져오는 함수
#     steam_url = "https://steamcommunity.com/app/1049590"
#     html = urllib.request.urlopen(steam_url)
#     soupER = BeautifulSoup(html, "html.parser")
#     find_tag = soupER.find_all("span", class_="apphub_NumInApp")
#     in_span = str(find_tag[0].string)
#     str_list = in_span.split(" ")
#     inGameUser = str_list[0]
#     return inGameUser


def getRequestUrl(url):  # API url 접근 함수
    req = urllib.request.Request(url)
    req.add_header("x-api-key", API_key)

    try:
        reponse = urllib.request.urlopen(req)

        if reponse.getcode() == 200:
            return reponse.read().decode("utf-8")  # 디코딩된 url 반환
    except Exception as e:
        # print(e)
        return None  # url 접근 실패시 None 반환


def currentSeason():  # 현재 시즌 정보 가져오는 함수
    url = "https://open-api.bser.io/v2/data/Season"
    responseDecode = getRequestUrl(url)
    allSeasonData = json.loads(responseDecode)
    seasonList = allSeasonData["data"]
    currentSeasonData = seasonList[-1]
    return currentSeasonData


def getCurrentSeasonName():
    currentSeasonData = currentSeason()
    seasonID = currentSeasonData["seasonID"]
    if (seasonID - 17) % 2 == 0:
        front = "정규 시즌"
        now = (seasonID - 17) // 2
        return f"{front} {now}"
    else:
        front = "프리 시즌"
        now = ((seasonID - 17) // 2) + 1
        return f"{front} {now}"


def endCurrentSeason():
    currentSeasonData = currentSeason()
    seasonEnd = currentSeasonData["seasonEnd"]
    endDate = seasonEnd.split(" ")[0]
    endTime = seasonEnd.split(" ")[1]
    endYear = endDate.split("-")[0]
    endMonth = endDate.split("-")[1]
    endDay = endDate.split("-")[2]
    endHour = endTime.split(":")[0]
    lastday = f"{endYear}년 {endMonth}월 {endDay}일 {endHour}시"
    return lastday


def remainTime():
    currentSeasonData = currentSeason()
    seasonEnd = currentSeasonData["seasonEnd"]
    target_time = datetime.strptime(seasonEnd, "%Y-%m-%d %H:%M:%S")
    current_time = datetime.now()

    time_difference = target_time - current_time  # 차이 계산

    remaining_seconds = time_difference.total_seconds()  # 남은 시간을 초 단위로 변환

    remaining_days, remaining_seconds = divmod(remaining_seconds, 86400)
    remaining_hours, remaining_seconds = divmod(remaining_seconds, 3600)
    remaining_minutes, _ = divmod(remaining_seconds, 60)  # 남은 일, 시간, 분 계산

    remaining_time_list = [
        int(remaining_days),
        int(remaining_hours),
        int(remaining_minutes),
    ]  # 반환값 리스트 생성

    return remaining_time_list


def getUserNum(nickname):  # 닉네임으로 유저id 가져오는 함수
    base = "https://open-api.bser.io/v1/user/nickname"
    parameters = f"?query={urllib.parse.quote(nickname)}"
    url = base + parameters
    responseDecode = getRequestUrl(url)

    if responseDecode == None:
        return None  # url에서 가져온 json이 None이면 None 반환
    else:
        jsonResponse = json.loads(responseDecode)
        try:
            user = jsonResponse["user"]
            userNum = user["userNum"]
            return userNum  # 검색된 유저의 유저id 반환
        except:
            return None


def getSeasonData(user_num):  # 유저 id로 시즌랭크 데이터 가져오는 함수
    if user_num == None:
        return None
    base = "https://open-api.bser.io/v1/user/stats"
    currentSeasonData = currentSeason()
    seasonID = currentSeasonData["seasonID"]
    para = f"/{user_num}/{seasonID}"  # 3시즌 랭쿼드 데이터
    url = base + para
    responseDecode = getRequestUrl(url)
    # print("url : " + url)
    if responseDecode == None:  # 가져온 데이터 없으면 None 반환
        return None  # 해당 유저가 존재하지 않음
    else:
        allData = json.loads(responseDecode)
        if allData["code"] != 200:
            return 0  # 현재시즌 기록 없음
        userStats = allData["userStats"][0]
        tier = detectTier(userStats)
        userStats["tier"] = tier
        return userStats  # 유저의 랭크 데이터를 딕셔너리로 반환


tiers = {
    "다이아몬드": [(4800, 5150), (5150, 5500), (5500, 5850), (5850, 6200)],
    "플레티넘": [(3600, 3900), (3900, 4200), (4200, 4500), (4500, 4800)],
    "골드": [(2600, 2850), (2850, 3100), (3100, 3350), (3350, 3600)],
    "실버": [(1600, 1850), (1850, 2100), (2100, 2350), (2350, 2600)],
    "브론즈": [(800, 1000), (1000, 1200), (1200, 1300), (1300, 1600)],
    "아이언": [(0, 200), (200, 400), (400, 600), (600, 800)],
}


def detectTier(userStats, tiers=tiers):
    mmr = userStats["mmr"]
    division = 5
    if mmr >= 6200:
        rank = userStats["rank"]
        userTier = isRanker(rank)
        return userTier
    else:
        for tier, ranges in tiers.items():
            division = 5
            for low, high in ranges:
                division -= 1
                if low <= mmr < high:
                    userTier = tier
                    return f"{userTier} {division}"


# def detectTier(userStats):
#     mmr = userStats["mmr"]
#     if mmr in range(0, 800):
#         if mmr < 200:
#             tier = "아이언4"
#         elif mmr < 400:
#             tier = "아이언3"
#         elif mmr < 600:
#             tier = "아이언2"
#         else:
#             tier = "아이언1"
#     elif mmr in range(800, 1600):
#         if mmr < 1000:
#             tier = "브론즈 4"
#         elif mmr < 1200:
#             tier = "브론즈 3"
#         elif mmr < 1300:
#             tier = "브론즈 2"
#         else:
#             tier = "브론즈 1"
#     elif mmr in range(1600, 2600):
#         if mmr < 1850:
#             tier = "실버 4"
#         elif mmr < 2100:
#             tier = "실버 3"
#         elif mmr < 2350:
#             tier = "실버 2"
#         else:
#             tier = "실버 1"
#     elif mmr in range(2600, 3600):
#         if mmr < 2850:
#             tier = "골드 4"
#         elif mmr < 3100:
#             tier = "골드 3"
#         elif mmr < 3350:
#             tier = "골드 2"
#         else:
#             tier = "골드 1"
#     elif mmr in range(3600, 4800):
#         if mmr < 3900:
#             tier = "플레티넘 4"
#         elif mmr < 4200:
#             tier = "플레티넘 3"
#         elif mmr < 4500:
#             tier = "플레티넘 2"
#         else:
#             tier = "플레티넘 1"
#     elif mmr in range(4800, 6201):
#         if mmr < 5150:
#             tier = "다이아몬드 4"
#         elif mmr < 5500:
#             tier = "다이아몬드 3"
#         elif mmr < 5850:
#             tier = "다이아몬드 2"
#         else:
#             tier = "다이아몬드 1"
#     else:
#         rank = userStats["rank"]
#         tier = isRanker(rank)
#     return tier


def isRanker(rank):
    if rank < 200:
        tier = "이터니티"
    elif rank < 700:
        tier = "데미갓"
    else:
        tier = "미스릴"
    return tier


def getMostCharacterCode(userName):
    userNum = getUserNum(userName)
    userStats = getSeasonData(userNum)
    characterStats = userStats["characterStats"]
    mostCharacterCode = characterStats[0]["characterCode"]
    return mostCharacterCode


def find_name(user_code, name_dict=charCode):
    for name, code in name_dict.items():
        if code == user_code:
            return name, code
    return None


def demigodRating():
    base = "https://open-api.bser.io/v1"
    currentSeasonData = currentSeason()
    seasonID = currentSeasonData["seasonID"]
    para = f"/rank/top/{seasonID}/3"  # 3시즌 랭쿼드 데이터
    url = base + para
    responseDecode = getRequestUrl(url)
    # print("url : " + url)
    if responseDecode == None:  # 가져온 데이터 없으면 None 반환
        return None  # 해당 유저가 존재하지 않음
    else:
        allData = json.loads(responseDecode)
        topRanks = allData["topRanks"]
        lastDemigod = topRanks[699]
        demigod_cut = lastDemigod["mmr"]
        return demigod_cut


def iternityRating():
    base = "https://open-api.bser.io/v1"
    currentSeasonData = currentSeason()
    seasonID = currentSeasonData["seasonID"]
    para = f"/rank/top/{seasonID}/3"  # 3시즌 랭쿼드 데이터
    url = base + para
    responseDecode = getRequestUrl(url)
    # print("url : " + url)
    if responseDecode == None:  # 가져온 데이터 없으면 None 반환
        return None  # 해당 유저가 존재하지 않음
    else:
        allData = json.loads(responseDecode)
        topRanks = allData["topRanks"]
        lastIternity = topRanks[199]
        # lastUser = lastIternity["nickname"]
        iternity_cut = lastIternity["mmr"]
        return iternity_cut  # lastUser
