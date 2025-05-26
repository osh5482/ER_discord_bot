import asyncio
from datetime import datetime, time
from discord.ext import tasks, commands
from functions.manageDB import save_patch_notes_to_db
from functions.utill import current_time


class patch_scheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.patch_crawler.start()

    def cog_unload(self):
        self.patch_crawler.cancel()

    @tasks.loop(minutes=1)  # 1분마다 체크
    async def patch_crawler(self):
        """특정 시간에 패치노트 크롤링 및 DB 저장 실행하는 함수"""
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute

        # 매일 7시, 17시 1분, 17시 30분에 실행
        target_times = [
            (7, 0),  # 7시 정각
            (17, 1),  # 17시 1분
            (17, 30),  # 17시 30분
        ]

        # 현재 시간이 목표 시간과 일치하는지 확인
        if (current_hour, current_minute) in target_times:
            print(
                f"[{current_time()}] 예정된 시간 도래 - 패치노트 크롤링을 시작합니다..."
            )

            try:
                success = await save_patch_notes_to_db()

                if success:
                    print(f"[{current_time()}] 패치노트 크롤링 및 저장 완료")
                else:
                    print(f"[{current_time()}] 패치노트 크롤링 실패")

            except Exception as e:
                print(f"[{current_time()}] 패치노트 스케줄러 오류: {e}")

    @patch_crawler.before_loop
    async def before_patch_crawler(self):
        """봇이 준비될 때까지 대기"""
        await self.bot.wait_until_ready()
        # 봇 시작 시 한 번 실행
        print(f"[{current_time()}] 봇 시작 시 패치노트 초기 크롤링 실행")
        await save_patch_notes_to_db()


async def setup(bot):
    await bot.add_cog(patch_scheduler(bot))
