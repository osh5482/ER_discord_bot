import asyncio
import time as time_module
from datetime import datetime
import discord
from discord.ext import tasks, commands
from config import Config
from database.connection import (
    get_pool,
    create_table,
    insert_data,
    delete_old_data,
    sort_by_time,
    save_patch_notes_to_db,
)
from core.api.eternal_return import get_current_player_api
from utils.logger import logger


# 패치노트 메시지 트리거 디바운스 대기 시간 (초). 마지막 메시지 이후 이 시간 동안 추가 메시지가 없으면 크롤링 실행.
PATCH_DEBOUNCE_SECONDS = 30


class tasks_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 현재 대기 중인 패치노트 디바운스 태스크 핸들. 대기 중인 작업이 없으면 None.
        self._patch_debounce_task: asyncio.Task | None = None

        self.save_data.start()
        # 시간 기반 스케줄러는 메시지 트리거 방식(on_message)으로 대체됨. 코드 보존을 위해 주석만 처리.
        # self.patch_crawler.start()

    def cog_unload(self):
        self.save_data.cancel()
        # self.patch_crawler.cancel()  # 시간 기반 스케줄러 비활성화에 따른 동반 주석 처리

        # 대기 중인 디바운스 태스크가 있으면 cog 언로드 시 함께 취소하여 좀비 태스크 방지
        if self._patch_debounce_task and not self._patch_debounce_task.done():
            self._patch_debounce_task.cancel()

    @tasks.loop(minutes=15.0)
    async def save_data(self):
        """15분마다 동접 데이터 저장 및 삭제 실행하는 함수"""
        current_unix_time = int(time_module.time())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_player = await get_current_player_api()

        async with get_pool().acquire() as conn:
            await insert_data(conn, current_unix_time, now, current_player)
            await delete_old_data(conn)

        current_player = format(current_player, ",")
        logger.info(f"Save player {current_player}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """공지 채널(follow된 채널)에 메시지가 올라올 때마다 호출되어 디바운스 타이머를 재설정한다.

        Discord follow 기능으로 미러링된 메시지는 webhook 형식으로 도착하며,
        webhook의 author는 봇 자신이 아니므로 정상적으로 통과된다.
        """
        # 타겟 채널이 아니면 무시 (다른 서버/채널의 모든 메시지 이벤트가 들어오므로 빠르게 필터링)
        if message.channel.id != Config.PATCH_NOTIFY_CHANNEL_ID:
            return

        # 봇 자신의 메시지는 무시 (안전장치)
        if message.author.id == self.bot.user.id:
            return

        logger.info(
            f"공지 채널 메시지 감지 (작성자: {message.author}). "
            f"디바운스 타이머 재설정 ({PATCH_DEBOUNCE_SECONDS}초)"
        )

        # 기존 대기 태스크가 있으면 취소하고 새 태스크 생성 (trailing debounce 패턴)
        if self._patch_debounce_task and not self._patch_debounce_task.done():
            self._patch_debounce_task.cancel()

        self._patch_debounce_task = asyncio.create_task(self._debounced_patch_crawl())

    async def _debounced_patch_crawl(self):
        """디바운스 시간 동안 대기 후 패치노트 크롤링을 실행한다.

        대기 중에 새 메시지가 도착하면 on_message에서 이 태스크를 취소하므로,
        CancelledError는 정상 흐름의 일부로 silent하게 처리한다.
        """
        try:
            await asyncio.sleep(PATCH_DEBOUNCE_SECONDS)
        except asyncio.CancelledError:
            # 새 메시지가 와서 취소된 정상 흐름 — 다음 태스크가 이미 스케줄됨
            return

        logger.info("디바운스 완료 - 패치노트 크롤링 시작 (메시지 트리거)")
        try:
            success = await save_patch_notes_to_db()
            if success:
                logger.info("패치노트 크롤링 및 저장 완료 (메시지 트리거)")
            else:
                logger.warning("패치노트 크롤링 실패 (메시지 트리거)")
        except Exception as e:
            logger.error(f"패치노트 메시지 트리거 크롤링 오류: {e}")

    # ========================================================================
    # [DEPRECATED] 시간 기반 패치노트 스케줄러.
    # 메시지 트리거 방식(on_message + 디바운싱)으로 대체되었으나, 롤백 대비 보존.
    # ========================================================================
    # @tasks.loop(minutes=1)  # 1분마다 체크
    # async def patch_crawler(self):
    #     """특정 시간에 패치노트 크롤링 및 DB 저장 실행하는 함수"""
    #     now = datetime.now()
    #     current_hour = now.hour
    #     current_minute = now.minute
    #
    #     # 매일 7시, 17시 1분, 17시 30분에 실행
    #     target_times = [
    #         (7, 0),  # 7시 정각
    #         (17, 1),  # 17시 1분
    #         (17, 30),  # 17시 30분
    #     ]
    #
    #     # 현재 시간이 목표 시간과 일치하는지 확인
    #     if (current_hour, current_minute) in target_times:
    #         logger.info("예정된 시간 도래 - 패치노트 크롤링을 시작합니다...")
    #
    #         try:
    #             success = await save_patch_notes_to_db()
    #
    #             if success:
    #                 logger.info("패치노트 크롤링 및 저장 완료")
    #             else:
    #                 logger.warning("패치노트 크롤링 실패")
    #
    #         except Exception as e:
    #             logger.error(f"패치노트 스케줄러 오류: {e}")
    #
    # @patch_crawler.before_loop
    # async def before_patch_crawler(self):
    #     """봇이 준비될 때까지 대기"""
    #     await self.bot.wait_until_ready()
    #     # 봇 시작 시 한 번 실행
    #     logger.info("봇 시작 시 패치노트 초기 크롤링 실행")
    #     await save_patch_notes_to_db()


async def setup(bot):
    await bot.add_cog(tasks_cog(bot))
