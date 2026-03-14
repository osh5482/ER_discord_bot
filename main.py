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

        synced_count = 0
        for guild in bot.guilds:
            try:
                synced = await bot.tree.sync(guild=guild)
                synced_count += 1
                logger.debug(
                    f"Synced {len(synced)} commands to {guild.name} ({guild.id})"
                )
            except Exception as e:
                logger.warning(f"Failed to sync to {guild.name} ({guild.id}): {e}")

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

    await load_extensions()
    await bot.start(Config.BREAD_TOKEN)
    # await bot.start(Config.INFERIORITY_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
