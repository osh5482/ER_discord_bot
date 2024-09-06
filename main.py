import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from functions.utill import *


intents = discord.Intents.default()
# intents.message_content = True
# intents.guilds = True
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
    bot.log_channel = bot.get_channel(1227163092719374366)
    await bot.tree.sync()
    await bot.change_presence(
        activity=discord.Game(name=f"눈젖빵 {len(bot.guilds)}개째 제작")
    )


@bot.event
async def on_guild_join(guild):
    """10명이하 서버 자동퇴장"""
    await guild.fetch_members()
    member_count = guild.member_count
    owner_in_guild = any(member.id == bot.owner_id for member in guild.members)
    if member_count < 10 or not owner_in_guild:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(
                    f"눈젖빵을 제작하기 위해서는 최소 10명의 멤버가 필요합니다."
                )
                break
        await guild.leave()
        print(f"Left guild {guild.name} because it has only {member_count} members.")


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


async def main():
    """봇 실행 메인 함수"""
    await load_extensions()
    load_dotenv(verbose=True)
    BREAD_TOKEN = os.getenv("BREAD_TOKEN")
    INFERIORITY_TOKEN = os.getenv("INFERIORITY_TOKEN")
    await bot.start(BREAD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
