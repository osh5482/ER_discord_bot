import urllib.request
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv(verbose=True)
API_key = os.getenv("STEAM_API_KEY")
# http://api.steampowered.com/<인터페이스 이름>/<메서드 이름>/v<버전>/?key=<api 키>&format=<형식>


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


def current_time():
    # 현재 시간을 가져옵니다.
    current_time = datetime.now()

    # 시간을 분 단위로 변환합니다.
    current_time_minutes = current_time.strftime("%Y-%m-%d %H:%M")

    # 문자열을 datetime 객체로 변환합니다.
    current_time_datetime = datetime.strptime(current_time_minutes, "%Y-%m-%d %H:%M")

    return current_time_datetime


def getCurrentPlayer():
    url = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?&appid=1049590"
    responseDecode = getRequestUrl(url)
    jsonResponse = json.loads(responseDecode)
    response = jsonResponse["response"]
    player_count = response["player_count"]
    # currentTime = current_time()
    return player_count
