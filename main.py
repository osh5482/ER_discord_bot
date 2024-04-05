import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from functions.utill import *
import manageDB as DB


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="?", intents=intents)


async def load_extensions():
    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"{filename} cogs load success")


@bot.event
async def on_ready():
    """봇 시작하면 로그인 로그 print하고 상태 띄워주는 함수"""
    print(f"logged in as {bot.user} at {current_time()}")
    await bot.change_presence(activity=discord.Game(name="실수로 눈젖빵 제작"))


@bot.event
async def on_command_error(ctx, error):
    """에러처리 함수"""

    # 없는 명령어
    if isinstance(error, commands.CommandNotFound):
        return

    # 명령어 쿨타임
    if isinstance(error, commands.CommandOnCooldown):
        if not hasattr(ctx, "command"):
            command_name = "Easter Egg"
        else:
            command_name = ctx.command
        print(f"{command_name} was requested on cooldown at {current_time()}")
        return


async def main():
    await load_extensions()
    load_dotenv(verbose=True)
    TOKEN = os.getenv("DISCORD_TOKEN")
    await bot.start(TOKEN)


asyncio.run(main())
