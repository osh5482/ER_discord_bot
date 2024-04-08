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
    await bot.change_presence(activity=discord.Game(name="실수로 눈젖빵 제작"))


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
    TOKEN = os.getenv("DISCORD_TOKEN")
    await bot.start(TOKEN)


@bot.event
async def on_guild_join(guild):
    """새로운 서버에 초대받았을때 메세지 출력"""
    new_server = guild.sysyem_channel
    server_info = (guild.name, guild.id)
    await new_server.send("아 ㅁㅊ 눈젖빵 만들었어")
    print(f"Bot was invites at {server_info}")


@bot.event
async def on_guild_remove(guild):
    """서버에서 봇 내보내질때 로그 남김"""
    server_info = (guild.name, guild.id)
    print(f"Bot was kicked out at {server_info}")


@bot.command(hidden=True, name="서버")
@commands.is_owner()
async def servers(ctx):
    servers = bot.guilds
    server_list = [(server.name, server.id) for server in servers]
    for server_info in server_list:
        print(server_info)
    print(f"cnt: {len(server_list)}")


if __name__ == "__main__":
    asyncio.run(main())
