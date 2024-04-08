from datetime import datetime
import time
import discord


def current_time():
    """현재시간 확인함수
    반환값 : str(현재시간 Y-m-d H-M-S)"""
    current_time = datetime.now()
    # 시간을 원하는 형식으로 포맷하여 출력
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


def insert_comma(data, unit=3):
    """세 자릿수마다 콤마 넣어주는 함수
    반환값 : str(숫자)"""
    data = str(data)
    result = []
    start = len(data) % unit

    # 처음 남은 부분을 result에 추가
    if start:
        result.append(data[:start])

    # unit 단위로 콤마 추가
    for i in range(start, len(data), unit):
        result.append(data[i : i + unit])

    return ",".join(result)


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
    file_path = f"./image/icon/not_mt_fault.png"
    embed.set_thumbnail(url="attachment://Error.png")
    file = discord.File(file_path, filename="Error.png")
    await ctx.channel.send(file=file, embed=embed)


def print_user_server(ctx):
    user_name = ctx.author.name
    server_name = ctx.guild.name
    print(f"└Process by {user_name} in {server_name}")
