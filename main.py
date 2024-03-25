import discord
from discord.ext import commands
import ER_API as ER
import steam_API as steam
import os
from dotenv import load_dotenv

load_dotenv(verbose=True)
TOKEN = os.getenv("DISCORD_TOKEN")


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def insert_comma(data, unit=3):  # 숫자 단위 끊어주는 함수
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


@bot.event
async def on_command_error(ctx, error):  # 없는 명령어 무시하는 함수
    if isinstance(error, commands.CommandNotFound):
        return
    raise error


@bot.event
async def on_ready():  # 봇 로그인 로그 print하고 상태 띄워주는 함수
    print(f"logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(name="실수로 눈젖빵 제작"))


@bot.command(aliases=["ㄷㅈ", "동접"])  # 동접 확인 함수
async def getInGameUser2(ctx):
    if ctx.author == bot.user:
        return
    print(f"Start getInGameUser...")
    inGameUser = steam.getCurrentPlayer()
    if inGameUser >= 10000:
        icon = "god_game"
    else:
        icon = "mang_game"
    inGameUser = insert_comma(str(inGameUser))
    embed = discord.Embed(
        # title="현재 동시 접속자",
        description="**현재 동시 접속자**",
        color=0x00FF00,
    )
    embed.add_field(name="\u200b", value=f"**{inGameUser}** 명", inline=False)
    file = discord.File(f"emoticon/{icon}.png", filename="leniticon.png")
    embed.set_thumbnail(url="attachment://leniticon.png")
    await ctx.send(file=file, embed=embed)
    print(f"Success getInGameUser {inGameUser} now")


@bot.command(aliases=["ㅅㅈ", "시즌"])
async def getSeasonRemaining(ctx):  # 남은 시즌 확인 함수
    if ctx.author == bot.user:
        return
    print(f"Start getSeasonRemaining...")
    remaining_time_list = ER.remainTime()
    day = remaining_time_list[0]
    hour = remaining_time_list[1]
    minute = remaining_time_list[2]
    lastday = ER.endCurrentSeason()
    currentSeasonName = ER.getCurrentSeasonName()
    description = f"시즌 종료일 : **{lastday}**\n시즌 종료까지 **{day}일 {hour}시간 {minute}분** 남았습니다."
    embed = discord.Embed(
        title=f"{currentSeasonName}",
        description=description,
        color=0x00FF00,
    )

    await ctx.channel.send(embed=embed)
    print(f"Success getSeasonRemaining")


@bot.listen()
async def on_message(message):  # 전적 검색 함수, 멀티서치 가능
    # 봇이 보낸 메시지 무시
    if message.author == bot.user:
        return

    if message.content.startswith("!ㅈㅈ") or message.content.startswith("!전적"):
        argus = message.content[len("!ㅈㅈ") :]
        argu_list = argus.split(" ")
        if argu_list[0] == "":
            del argu_list[0]
        for argu in argu_list:
            await getUserInfo(message.channel, argu)


async def getUserInfo(ctx, player_name):  # 유저정보 확인 함수
    print(f"Start getUserInfo({player_name})...")
    userNum = ER.getUserNum(player_name)
    rankData = ER.getSeasonData(userNum)
    if rankData is None:
        await ctx.send(f"> '{player_name}'는 존재하지 않는 닉네임입니다.")
    elif rankData == 0:
        await ctx.send(f"> '{player_name}' 의 현재시즌 정보가 없습니다.")
    else:
        rank = rankData["rank"]
        rank = insert_comma(rank)
        tier = rankData["tier"]
        mmr = rankData["mmr"]

        embed = discord.Embed(
            title=f"{player_name}",
            description=f"랭킹 : {rank} 위\n티어 : {tier}\nMMR : {mmr}",
            color=0x00FF00,
            url=f"https://dak.gg/er/players/{player_name}",
        )
        mostChar = ER.getMostCharacterCode(player_name)
        charName, code = ER.find_name(mostChar)
        file = discord.File(
            f"charProfile/{code}_{charName}.png",
            filename="profile.png",
        )
        embed.set_thumbnail(url="attachment://profile.png")
        await ctx.send(file=file, embed=embed)
        print(f"Success getUserInfo({player_name})!")


@bot.command(aliases=["ㅇㅌ", "이터", "이터니티"])
async def checkIternityRating(ctx):  # 이터 컷 보는 함수
    if ctx.author == bot.user:
        return
    print(f"Start checkIternityRating...")
    rating = ER.iternityRating()
    await ctx.channel.send(f"> 이터니티 컷 : **{rating}** 점")
    print(f"Success checkDIternityRating...{rating} now")


@bot.command(aliases=["ㄷㅁ", "데미", "데미갓", "뎀갓"])
async def checkDemigodRating(ctx):  # 데미갓 컷 보는 함수
    if ctx.author == bot.user:
        return
    print(f"Start checkDemigodRating...")
    rating = ER.demigodRating()
    await ctx.channel.send(f"> 데미갓 컷 : **{rating}** 점")
    print(f"Success checkDemigodRating...{rating} now")


@bot.listen()
async def on_message(ctx):  # 전적 검색 함수, 멀티서치 가능
    # 봇이 보낸 메시지 무시
    if ctx.author == bot.user:
        return

    if ctx.content == "젠장":
        embed = discord.Embed(title="젠장 마커스!!!!", description="난 네가 좋다!!!!")
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/1221830644775129138/1221830793500954784/image.png?ex=66140199&is=66018c99&hm=ae4f543270cd4d60f8a39424842f753206af4f9b1cf402b23e0b8f920eea92cb&"
        )
        await ctx.channel.send(embed=embed)
        print("젠장 마커스 난 네가 좋다")


bot.run(TOKEN)
