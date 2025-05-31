import asyncio
import aiohttp
import json


class DakggApi:
    """닥지지 API 클라이언트 클래스
    이 클래스는 닥지지 API를 통해 아이템, 캐릭터, 경로 데이터를 비동기적으로 가져옵니다."""

    def __init__(self):
        self.base_url = "https://er.dakgg.io/api/v1"
        self.item_url = f"{self.base_url}/data/items"
        self.char_url = f"{self.base_url}/character-stats"
        self.route_url = f"{self.base_url}/routes"

    async def fetch_data(self, url: str, params=None) -> dict:
        """주어진 URL에서 데이터를 비동기적으로 가져옵니다."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params) as response:
                    response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
                    data = await response.json()
                    return data
            except aiohttp.ClientError as e:
                print(f"Error during request: {e}")
                return None

    async def crawl_item_data(self) -> dict:
        """아이템 데이터를 비동기적으로 가져옵니다."""
        item_data = await self.fetch_data(self.item_url)
        if item_data:
            item_data = json.dumps(item_data, indent=2, ensure_ascii=False)
            print(f"Fetched {len(item_data)} items.")
        return item_data

    async def crawl_char_data(self, tier: str = None) -> dict:
        """캐릭터 데이터를 비동기적으로 가져옵니다."""
        params = {"tier": tier} if tier else {}
        char_data = await self.fetch_data(self.char_url, params=params)
        if char_data:
            char_data = char_data.get("characterStatSnapshot", [])
            char_data = char_data.get("characterStats", [])
            char_data = json.dumps(char_data, indent=2, ensure_ascii=False)
            print(f"Fetched {len(char_data)} characters.")
        return char_data

    async def crawl_route_data(self) -> dict:
        """경로 데이터를 비동기적으로 가져옵니다."""
        route_data = await self.fetch_data(self.route_url)
        if route_data:
            route_data = json.dumps(route_data, indent=2, ensure_ascii=False)
            print(f"Fetched {len(route_data)} routes.")
        return route_data


async def main():
    dakgg_api = DakggApi()
    char_data = await dakgg_api.crawl_char_data(tier="in1000")
    if char_data:
        print(char_data)


if __name__ == "__main__":
    asyncio.run(main())
