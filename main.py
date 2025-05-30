import sys

sys.dont_write_bytecode = True

import asyncio
import discord
from discord.ext import commands
import os
from config import Config
from utils.helpers import current_time


intents = discord.Intents.default()
# intents.message_content = True
# intents.guilds = True
bot = commands.Bot(command_prefix="/", intents=intents)


async def load_extensions():
    for filename in os.listdir("bot/cogs"):
        if filename.endswith(".py") and not filename.startswith("__"):
            await bot.load_extension(f"bot.cogs.{filename[:-3]}")
            print(f"[{current_time()}] {filename} was sucessfully loaded")
    print(f"[{current_time()}] All cogs successfully loaded")


@bot.event
async def on_ready():
    """봇 시작하면 로그인 로그 출력력하고 상태 띄워주는 함수"""
    print(f"[{current_time()}] Logged in as {bot.user}")
    bot.owner_id = Config.BOT_OWNER_ID
    bot.log_channel = bot.get_channel(Config.LOG_CHANNEL_ID)
    try:
        # 개발 중이라면 특정 길드에만 동기화 (빠름)
        # GUILD_ID = Config.SPECIFIC_SERVER_ID  # 테스트 서버 ID
        # synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        # print(f"[{current_time()}] Synced {len(synced)} commands to guild {GUILD_ID}")

        # 전역 동기화 (모든 서버에 적용, 최대 1시간 소요)
        synced = await bot.tree.sync()
        print(f"[{current_time()}] Synced {len(synced)} commands globally")

        # 현재 등록된 명령어 목록 출력
        commands_list = [cmd.name for cmd in bot.tree.get_commands()]
        print(f"[{current_time()}] Registered commands: {commands_list}")

    except Exception as e:
        print(f"[{current_time()}] Failed to sync commands: {e}")

    await bot.change_presence(
        activity=discord.Game(name=f"눈젖빵 {len(bot.guilds)}개째 제작")
    )


@bot.event
async def on_guild_join(guild):
    """새로운 서버에 초대받았을 때 메시지 출력"""
    await bot.change_presence(
        activity=discord.Game(name=f"눈젖빵 {len(bot.guilds)}개째 제작")
    )

    new_server = guild.system_channel
    server_info = (guild.name, guild.id)
    print(f"[{current_time()}] Bot was invited at {server_info}")
    await bot.log_channel.send(
        f"*[{current_time()}]* Bot was invited at `{server_info}`"
    )

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
    print(f"[{current_time()}] Bot was kicked out at {server_info}")
    await bot.log_channel.send(
        f"*[{current_time()}]* Bot was kicked out at `{server_info}`"
    )


async def main():
    """봇 실행 메인 함수"""
    # 설정 검증
    Config.validate()

    await load_extensions()
    await bot.start(Config.BREAD_TOKEN)
    # await bot.start(Config.INFERIORITY_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
