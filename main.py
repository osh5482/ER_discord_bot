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


@bot.event
async def on_guild_join(guild):
    """새로운 서버 들어갔을때 로그띄워주는 함수"""
    print(f"{bot.user} was invited at {guild.name}")


@bot.event
async def on_guild_remove(guild):
    """서버에서 봇이 나갈 때 실행되는 코드"""
    print(f"{bot.user} was kicked out at {guild.name}")


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
    try:
        await bot.unload_extension(f"cogs.{module}")
        print(f"[{current_time()}] {module} was sucessfully unloaded")
    except commands.ExtensionError as e:
        await ctx.send(f"{e.__class__.__name__}: {e}")


@bot.command(hidden=True)
@commands.is_owner()
async def reload(ctx: commands.Context, *, module: str):
    try:
        await bot.reload_extension(f"cogs.{module}")
        print(f"[{current_time()}] {module} was sucessfully reloaded")
    except commands.ExtensionError as e:
        await ctx.send(f"{e.__class__.__name__}: {e}")


@bot.command(hidden=True)
@commands.is_owner()
async def all_reload(ctx: commands.Context):
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


@bot.command(hidden=True)
@commands.is_owner()
async def stop(ctx):
    await ctx.send("봇을 종료합니다.")
    print(f"[{current_time()}]Bot was stopped")
    await bot.close()


@bot.command(hidden=True, name="서버")
@commands.is_owner()
async def servers(ctx):
    servers = bot.guilds
    server_list = [f"{server.name} (ID: {server.id})" for server in servers]
    for i in server_list:
        print(server_list[i])
    print(f"cnt: {len(server_list)}")


if __name__ == "__main__":
    asyncio.run(main())
