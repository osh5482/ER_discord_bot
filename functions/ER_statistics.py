import json
from functions.dict_lib import *
from bs4 import BeautifulSoup
import aiohttp
import asyncio


async def dakgg_crawler(weapon, character_name):
    """무기, 캐릭터 이름으로 닥지지 통계 크롤링해오기
    반환값 : dict(str(각 통계 html)) /
    에러시 aiohttp.ClientResponseError"""
    url = f"https://dak.gg/er/characters/{character_name}?weaponType={weapon}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                statistics_dict = {
                    "code": char_code[f"{character_name}"],
                    "character_name": char_korean[f"{character_name}"],
                    "weapon": weapon_korean[f"{weapon}"],
                }

                for div in soup.find_all("div", class_="css-n6szh2"):
                    # 통계 이름 추출
                    stat_name = div.find("div", class_="css-dy7q68").text

                    # 값 추출
                    value_div = div.find("div", class_="css-1s2413a")
                    if value_div:
                        value = value_div.text
                        value = value.replace("%", " %")
                    else:
                        # span 태그가 있는 경우
                        span_value = div.find("span")
                        if span_value:
                            value = span_value.text

                    # 순위 정보 추출
                    ranking: str = div.find("div", class_="css-1sw8f3s").text
                    ranking = ranking.replace("#", "")

                    # 딕셔너리에 저장
                    statistics_dict[stat_name] = {
                        "value": value,
                        "ranking": ranking,
                    }
                print(statistics_dict)

                return statistics_dict

            else:  # 요청에 문제가 있는듯
                print(f"Error: {response.status}")
                # 여기서 발생한 에러를 호출한 곳으로 전달
                raise aiohttp.ClientResponseError(status=response.status)


async def main():
    return


if __name__ == "__main__":
    asyncio.run(main())
