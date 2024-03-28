from datetime import datetime
import time
import aiohttp
import discord
from discord.ext import commands
import ER_API as ER
import ER_statistics as gg
import os
from dotenv import load_dotenv
from dict_lib import char_english, weapon_english

load_dotenv(verbose=True)
TOKEN = os.getenv("DISCORD_TOKEN")


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="?", intents=intents)
cooldowns = {}
import queue
import threading

bot = commands.Bot(command_prefix="?")

# 작업 큐 생성
task_queue = queue.Queue()

# 워커 쓰레드 수
num_threads = 4


# 워커 쓰레드 생성 및 시작
def worker():
    while True:
        func, args, kwargs = task_queue.get()
        try:
            func(*args, **kwargs)
        except Exception as e:
            print(f"Error executing function: {e}")
        task_queue.task_done()


for _ in range(num_threads):
    thread = threading.Thread(target=worker)
    thread.daemon = True
    thread.start()


@bot.command()
async def test(ctx, arg1, arg2, kwarg1=None):
    # 함수를 큐에 넣기
    task_queue.put((my_function, (arg1, arg2), {"kwarg1": kwarg1}))
    await ctx.send("Function added to queue")


bot.run(TOKEN)
