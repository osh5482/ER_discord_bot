import json
from dict_lib import *
from bs4 import BeautifulSoup
import aiohttp

import asyncio


async def make_character_statistics(weapon, character):
    statistics_dict = await dakgg_crawler(weapon, character)
    statistics_dict["win"] = await get_statistics(statistics_dict["win"])
    statistics_dict["top3"] = await get_statistics(statistics_dict["top3"])
    statistics_dict["get_RP"] = await get_statistics_RP(statistics_dict["get_RP"])
    statistics_dict["pick"] = await get_statistics(statistics_dict["pick"])
    statistics_dict["avg_rank"] = await get_statistics(statistics_dict["avg_rank"])
    statistics_dict["avg_kills"] = await get_statistics(statistics_dict["avg_kills"])
    return statistics_dict


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
                dl_tag = soup.find("dl")

                statistics_list = str(dl_tag).split(
                    '<div class="border border-r-0 border-[#e6e6e6]">'
                )

                statistics_dict = {
                    "code": char_code[f"{character_name}"],
                    "character_name": char_korean[f"{character_name}"],
                    "weapon": weapon_korean[f"{weapon}"],
                    "win": statistics_list[1],
                    "top3": statistics_list[2],
                    "get_RP": statistics_list[3],
                    "pick": statistics_list[4],
                    "avg_rank": statistics_list[5],
                    "avg_kills": statistics_list[6],
                }
                return statistics_dict

            else:  # 요청에 문제가 있는듯
                print(f"Error: {response.status}")
                # 여기서 발생한 에러를 호출한 곳으로 전달
                raise aiohttp.ClientResponseError(status=response.status)


async def get_statistics(dl):
    """dl[0]으로 통계+순위 구해오는 함수
    반환값 : list(str(퍼센트), str(순위))"""
    try:
        soup = BeautifulSoup(dl, "html.parser")
        dd = soup.find("dd")
        statistics = dd.contents[0].strip()
        rank = dd.contents[1].get_text(strip=True)  # str(#순위/전체) 가져옴
        return statistics, rank

    except Exception as e:
        print(e)


async def get_statistics_RP(dl):
    """dl[0]으로 통계+순위 구해오는 함수 (RP항목 전용)
    반환값 : list(str(퍼센트), str(순위))"""
    try:
        soup = BeautifulSoup(dl, "html.parser")
        dd = soup.find("dd")
        image_and_number = dd.find("span", class_="flex").get_text(strip=True)
        span_tags = dd.find_all("span")[1]
        get_RP = image_and_number.split()[0]  # RP획득량 가져옴
        rank = span_tags.get_text(strip=True)  # str(#순위/전체) 가져옴
        return get_RP, rank

    except Exception as e:
        print(e)


async def main():
    s = await make_character_statistics("Rapier", "Chiara")
    print(s)


if __name__ == "__main__":
    asyncio.run(main())
