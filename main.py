import sys

sys.dont_write_bytecode = True

# logger를 가장 먼저 import하여 discord.py 인터셉트가 봇 시작 전부터 동작하도록 함
from utils.logger import logger

import asyncio
import discord
from discord.ext import commands
import os
from config import Config
from datetime import datetime
from database.connection import init_pool, close_pool, create_table, create_patch_table


intents = discord.Intents.default()
# intents.message_content = True
# intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)


async def load_extensions():
    for filename in os.listdir("bot/cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            await bot.load_extension(f"bot.cogs.{filename[:-3]}")
            logger.info(f"{filename} was successfully loaded")
    logger.info("All cogs successfully loaded")


@bot.event
async def on_ready():
    """봇 시작하면 로그인 로그 출력하고 상태 띄워주는 함수"""
    logger.info(f"Logged in as {bot.user}")
    bot.owner_id = Config.BOT_OWNER_ID
    bot.log_channel = bot.get_channel(Config.LOG_CHANNEL_ID)
    try:
        # 봇이 참여 중인 모든 길드에 명령어 동기화 (즉시 반영)
        commands_list = [cmd.name for cmd in bot.tree.get_commands()]
        logger.debug(f"Registered commands: {commands_list}")

        # 글로벌 명령어를 모두 제거 (길드 명령어만 사용)
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        logger.info("Cleared all global commands")

        # 글로벌 명령어를 트리에 다시 등록 (길드 sync용)
        # clear_commands는 트리에서만 제거하므로, cog의 명령어를 다시 로드
        for cog_name, cog in bot.cogs.items():
            for cmd in cog.get_app_commands():
                bot.tree.add_command(cmd)

        # 각 길드에 즉시 반영 (세마포어로 동시 요청 수 제한하여 rate limit 방지)
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)

        sem = asyncio.Semaphore(5)

        async def sync_guild(guild):
            async with sem:
                try:
                    synced = await bot.tree.sync(guild=guild)
                    logger.debug(
                        f"Synced {len(synced)} commands to {guild.name} ({guild.id})"
                    )
                    return True
                except Exception as e:
                    logger.warning(f"Failed to sync to {guild.name} ({guild.id}): {e}")
                    return False

        results = await asyncio.gather(*(sync_guild(guild) for guild in bot.guilds))
        synced_count = sum(1 for r in results if r)

        logger.info(f"Synced commands to {synced_count}/{len(bot.guilds)} guilds")

    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

    await bot.change_presence(
        activity=discord.Game(name=f"눈젖빵 {len(bot.guilds)}개째 제작")
    )


@bot.event
async def on_guild_join(guild):
    """새로운 서버에 초대받았을 때 메시지 출력"""
    await bot.change_presence(
        activity=discord.Game(name=f"눈젖빵 {len(bot.guilds)}개째 제작")
    )

    # 새 서버에 명령어 즉시 동기화
    try:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        logger.info(f"Synced commands to new guild {guild.name} ({guild.id})")
    except Exception as e:
        logger.warning(f"Failed to sync to new guild {guild.name}: {e}")

    new_server = guild.system_channel
    server_info = (guild.name, guild.id)
    logger.info(f"Bot was invited at {server_info}")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await bot.log_channel.send(f"*[{now}]* Bot was invited at `{server_info}`")

    if new_server:
        await asyncio.sleep(1)
        await new_server.send(f"눈젖빵을 {len(bot.guilds)}개나 만들어 버려요~")


@bot.event
async def on_guild_remove(guild):
    """서버에서 봇 내보내질 때 로그 남김"""
    await bot.change_presence(
        activity=discord.Game(name=f"눈젖빵 {len(bot.guilds)}개째 제작")
    )

    server_info = (guild.name, guild.id)
    logger.info(f"Bot was kicked out at {server_info}")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await bot.log_channel.send(f"*[{now}]* Bot was kicked out at `{server_info}`")


async def main():
    """봇 실행 메인 함수"""
    # 설정 검증
    Config.validate()

    # PostgreSQL 커넥션 풀 초기화 및 테이블 생성
    await init_pool()
    await create_table()
    await create_patch_table()

    await load_extensions()
    try:
        await bot.start(Config.BREAD_TOKEN)  # 서비스용 봇
        # await bot.start(Config.INFERIORITY_TOKEN)  # 개발용 테스트 봇
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
