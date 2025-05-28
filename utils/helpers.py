from datetime import datetime
import time
import discord
import inspect


def current_time():
    """현재시간 확인함수
    반환값 : str(현재시간 Y-m-d H-M-S)"""
    current_time = datetime.now()
    # 시간을 원하는 형식으로 포맷하여 출력
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


cooldowns = {}


async def check_cooldown(func_name, cooldown_time):
    """함수 쿨다운 체크"""
    now = time.time()
    if func_name in cooldowns:
        last_call, cooldown = cooldowns[func_name]
        if now - last_call < cooldown:
            # remaining = cooldown - (now - last_call)
            # print(f"Function {func_name} is on cooldown for {remaining:.2f} seconds.")
            return False
    cooldowns[func_name] = (now, cooldown_time)
    return True


async def not_my_fault(ctx):
    """서버에 문제 생겼을때 출력하는 함수"""
    print("Error: almost Network error")
    embed = discord.Embed(
        title=f"정보 불러오기 실패",
        description=f"Api 네트워크 오류",
        color=0x00FF00,
    )
    file_path = f"./assets/images/icons/not_my_fault.png"
    embed.set_thumbnail(url="attachment://Error.png")
    file = discord.File(file_path, filename="Error.png")
    await ctx.channel.send(file=file, embed=embed)


def print_user_server(interaction: discord.Interaction):
    user_name = interaction.user
    server_name = interaction.guild
    print(f"└Processed by {user_name} in {server_name}")


async def logging_function(bot, interaction: discord.Interaction):
    """명령어 아니어도 로그 남기는 함수"""
    from config import Config

    log_channel = bot.get_channel(Config.LOG_CHANNEL_ID)
    function_name = inspect.stack()[1].function  # 호출한 함수의 이름을 자동으로 가져옴

    await log_channel.send(
        f"*[{current_time()}]* `{function_name}` was processed by `{interaction.user}` in `{interaction.guild}`"
    )
