from datetime import datetime
import discord
import inspect
from config import Config
from utils.logger import logger


async def not_my_fault(ctx):
    """서버에 문제 생겼을때 출력하는 함수"""
    logger.error("Network error occurred")
    embed = discord.Embed(
        title=f"정보 불러오기 실패",
        description=f"Api 네트워크 오류",
        color=0x00FF00,
    )
    file_path = f"./assets/images/icons/not_my_fault.png"
    embed.set_thumbnail(url="attachment://Error.png")
    file = discord.File(file_path, filename="Error.png")
    await ctx.channel.send(file=file, embed=embed)


def print_user_server(interaction: discord.Interaction, message: str = ""):
    """
    명령어 실행 결과와 실행자 정보를 한 줄의 로그로 출력한다.

    Args:
        interaction: Discord Interaction 객체 (사용자 및 서버 정보 추출용)
        message: 앞에 붙일 로그 메시지. 없으면 실행자 정보만 출력.
    """
    user_name = interaction.user
    server_name = interaction.guild
    if message:
        logger.info(f"{message} | by {user_name} in {server_name}")
    else:
        logger.info(f"Processed by {user_name} in {server_name}")


async def logging_function(bot, interaction: discord.Interaction):
    """명령어 아니어도 로그 남기는 함수"""

    log_channel = bot.get_channel(Config.LOG_CHANNEL_ID)
    function_name = inspect.stack()[1].function  # 호출한 함수의 이름을 자동으로 가져옴
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    await log_channel.send(
        f"*[{now}]* `{function_name}` was processed by `{interaction.user}` in `{interaction.guild}`"
    )
