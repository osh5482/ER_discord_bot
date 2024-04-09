import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from functions.utill import *


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="?", intents=intents)


async def load_extensions():
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            if filename == "test.py":
                pass
            else:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"[{current_time()}] {filename} was sucessfully loaded")
    print("All cogs successfully loaded")


@bot.event
async def on_ready():
    """봇 시작하면 로그인 로그 print하고 상태 띄워주는 함수"""
    print(f"[{current_time()}] Logged in as {bot.user}")
    bot.owner_id = 393987987005767690
    count = len(bot.guilds)
    await bot.change_presence(activity=discord.Game(name=f"눈젖빵 {count}개째 제작"))


@bot.command(hidden=True)
@commands.is_owner()
async def load(ctx: commands.Context, *, module: str):
    try:
        await bot.load_extension(f"cogs.{module}")
        print(f"[{current_time()}] {module} was sucessfully loaded")
    except commands.ExtensionError as e:
        await ctx.send(f"{e.__class__.__name__}: {e}")


@bot.command(hidden=True)
@commands.is_owner()
async def unload(ctx: commands.Context, *, module: str):
    """특정 cog 언로드"""
    try:
        await bot.unload_extension(f"cogs.{module}")
        print(f"[{current_time()}] {module} was sucessfully unloaded")
    except commands.ExtensionError as e:
        await ctx.send(f"{e.__class__.__name__}: {e}")


@bot.command(hidden=True)
@commands.is_owner()
async def reload(ctx: commands.Context, *, module: str):
    """특정 cog 리로드"""
    try:
        await bot.reload_extension(f"cogs.{module}")
        print(f"[{current_time()}] {module} was sucessfully reloaded")
    except commands.ExtensionError as e:
        await ctx.send(f"{e.__class__.__name__}: {e}")


@bot.command(hidden=True)
@commands.is_owner()
async def all_reload(ctx: commands.Context):
    """모든 cog 리로드"""
    for filename in os.listdir("cogs"):
        try:
            if filename.endswith(".py"):
                if filename == "test.py":
                    pass
                else:
                    await bot.reload_extension(f"cogs.{filename[:-3]}")
                    print(f"[{current_time()}] {filename} was sucessfully reloaded")
        except commands.ExtensionError as e:
            await ctx.send(f"{e.__class__.__name__}: {e}")
    print("All cogs successfully reloaded")


@bot.command(aliases=["ㄷㅇ", "도움", "도움말"])
async def command_list(ctx):
    msg = """```명령어 접두어: ?
    ㄷㅈ : 스팀 동시 접속자를 확인합니다.
    ㅍㄴ : 가장 최근 메이저패치의 패치노트를 가져옵니다.
    ㅅㅈ : 현재 시즌의 기한을 확인합니다.
    ㄷㅁ : 현재 데미캇 레이팅 컷을 확인합니다.
    ㅇㅌ : 현재 이터니티 레이팅 컷을 확인합니다.
    ㅈㅈ <닉네임> : 유저의 랭겜 전적을 가져옵니다. 띄어쓰기로 멀티서치가 가능합니다.
    ㅌㄱ <무기> <캐릭터> : 캐릭터의 통계를 가져옵니다.
    ==========================================================
    ㅁㅇ <문의내용> : 문의사항을 보낼수있습니다. (쿨타임 30분)```"""

    await ctx.channel.send(msg)
    print(f"[{current_time()}] Success command_list")
    print_user_server(ctx)
    return


async def main():
    """봇 실행 메인 함수"""
    await load_extensions()
    load_dotenv(verbose=True)
    TOKEN = os.getenv("DISCORD_TOKEN")
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
