<<<<<<< HEAD
import discord
from discord.ext import commands
import ER_API as ER
import steam_API as steam
=======
from datetime import datetime
import aiohttp
import discord
from discord.ext import commands
import async_API as ER
>>>>>>> c3294e3bdc1f6043a1ae832cc18b23ce7b9829cf
import os
from dotenv import load_dotenv

load_dotenv(verbose=True)
TOKEN = os.getenv("DISCORD_TOKEN")


intents = discord.Intents.default()
intents.message_content = True
<<<<<<< HEAD
bot = commands.Bot(command_prefix="!", intents=intents)
=======
bot = commands.Bot(command_prefix="?", intents=intents)


def currentTime():  # 현재시간 확인 함수
    current_time = datetime.now()
    # 시간을 원하는 형식으로 포맷하여 출력
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


@bot.event
async def on_command_error(ctx, error):  # 없는 명령어 무시하는 함수
    if isinstance(error, commands.CommandNotFound):
        return
    raise error


@bot.event
async def on_ready():  # 봇 로그인 로그 print하고 상태 띄워주는 함수
    print(f"logged in as {bot.user} at {currentTime()}")
    await bot.change_presence(activity=discord.Game(name="실수로 눈젖빵 제작"))


async def notMyfault(ctx):  # 서버에 문제 생겼을때 출력하는 함수
    print("Error: almost Network error")
    embed = discord.Embed(
        title=f"정보 불러오기 실패",
        description=f"ER 서버 점검 혹은 네트워크 오류",
        color=0x00FF00,
    )
    file_path = f"./image/icon/not_mt_fault.png"
    embed.set_thumbnail(url="attachment://Error.png")
    file = discord.File(file_path, filename="Error.png")
    await ctx.channel.send(file=file, embed=embed)


@bot.command(aliases=["ㅍㅊ", "패치", "ㅍㄴ", "패노", "패치노트"])
async def getRecentMajorPatchNote(ctx):  # 제일 최근 메이저패치 가져오는 함수
    if ctx.author == bot.user:
        return
    # print(f"Start getRecentPatchNote...")
    RecentMajorPatchNote = await ER.getPatchNote()
    await ctx.send(RecentMajorPatchNote)
    print(f"Success getRecentPatchNote! at {currentTime()}")
    return


@bot.command(aliases=["ㄷㅈ", "동접"])
async def getInGameUser(ctx):  # 동접 확인 함수
    if ctx.author == bot.user:
        return
    # print(f"Start getInGameUser...")
    in_game_user = await ER.getCurrentPlayer_api()
    if in_game_user >= 10000:
        icon = "god_game"
    else:
        icon = "mang_game"
    in_game_user = insert_comma(str(in_game_user))
    embed = discord.Embed(
        # title="현재 동시 접속자",
        description="**현재 동시 접속자**",
        color=0x00FF00,
    )
    embed.add_field(name="\u200b", value=f"**{in_game_user}** 명", inline=False)
    file = discord.File(f"./image/icon/{icon}.png", filename="leniticon.png")
    embed.set_thumbnail(url="attachment://leniticon.png")
    await ctx.send(file=file, embed=embed)
    print(f"Success getInGameUser {in_game_user} at {currentTime()}")


@bot.command(aliases=["ㅅㅈ", "시즌"])
async def getSeasonRemaining(ctx):  # 남은 시즌 확인 함수
    if ctx.author == bot.user:
        return
    # print(f"Start getSeasonRemaining...")
    curren_season_data, current_season_name = await ER.getCurrentSeasonName()
    remaining_time_list = await ER.remainTime(curren_season_data)
    day = remaining_time_list[0]
    hour = remaining_time_list[1]
    minute = remaining_time_list[2]
    lastday = await ER.endCurrentSeason(curren_season_data)

    if current_season_name == aiohttp.ClientResponseError:
        await notMyfault(ctx)
        return
    description = f"시즌 종료일 : **{lastday}**\n시즌 종료까지 **{day}일 {hour}시간 {minute}분** 남았습니다."
    embed = discord.Embed(
        title=f"{current_season_name}",
        description=description,
        color=0x00FF00,
    )

    await ctx.channel.send(embed=embed)
    print(f"Success getSeasonRemaining at {currentTime()}")


@bot.listen()
async def on_message(ctx):  # 전적 검색 함수, 멀티서치 가능
    # 봇이 보낸 메시지 무시
    if ctx.author == bot.user:
        return

    if ctx.content.startswith("?ㅈㅈ") or ctx.content.startswith("?전적"):
        argus = ctx.content[3:]
        name_list = argus.split(" ")
        if name_list[0] == "":
            del name_list[0]
        files, embeds = await getUserInfo(ctx.channel, name_list)
        print(f"Success getUserInfo({name_list}) at {currentTime()}")
        await ctx.reply(files=files, embeds=embeds)


async def getUserInfo(ctx, name_list):
    files_and_embeds = []

    for name in name_list:
        user_tuple = await ER.getUserNum(name)
        if user_tuple == aiohttp.ClientResponseError:
            await notMyfault(ctx)
            return
        rank_data = await ER.getUserSeasonData(user_tuple)
        if rank_data == 404:
            code = 0
            char_name = "Nadja"
            embed = discord.Embed(
                title=f"{name}",
                description="존재하지 않는 유저입니다.",
                color=0x00FF00,
                url=f"https://dak.gg/er/players/{name}",
            )
            # await ctx.send(f"> '{name}'는 존재하지 않는 닉네임입니다.")
        elif rank_data == 0:
            code = rank_data
            char_name = "Nadja"
            embed = discord.Embed(
                title=f"{name}",
                description="현재시즌 정보가 없습니다.",
                color=0x00FF00,
                url=f"https://dak.gg/er/players/{name}",
            )
            # await ctx.send(f"> '{name}' 의 현재시즌 정보가 없습니다.")
        else:
            rank = rank_data["rank"]
            rank = insert_comma(rank)
            tier = rank_data["tier"]
            mmr = rank_data["mmr"]
            most_character_code = rank_data["characterStats"][0]["characterCode"]
            char_name, code = ER.findCharacterName(most_character_code)

            embed = discord.Embed(
                title=f"{name}",
                description=f"랭킹 : {rank} 위\n티어 : {tier}\nMMR : {mmr}",
                color=0x00FF00,
                url=f"https://dak.gg/er/players/{name}",
            )
        file_path = f"./image/charProfile/{code}_{char_name}.png"
        embed.set_thumbnail(url=f"attachment://{char_name}.png")
        file = discord.File(file_path, filename=f"{char_name}.png")
        files_and_embeds.append((embed, file))

    files = [file for embed, file in files_and_embeds]
    embeds = [embed for embed, file in files_and_embeds]
    return files, embeds


@bot.command(aliases=["ㅇㅌ", "이터", "이터니티"])
async def checkIternityRating(ctx):  # 이터 컷 보는 함수
    if ctx.author == bot.user:
        return
    rating = await ER.getIternityRating()
    await ctx.channel.send(f"> 이터니티 컷 : **{rating}** 점")
    print(f"Success checkDIternityRating {rating} at {currentTime()}")


@bot.command(aliases=["ㄷㅁ", "데미", "데미갓", "뎀갓"])
async def checkDemigodRating(ctx):  # 데미갓 컷 보는 함수
    if ctx.author == bot.user:
        return
    rating = await ER.getDemigodRating()
    await ctx.channel.send(f"> 데미갓 컷 : **{rating}** 점")
    print(f"Success checkDemigodRating {rating} at {currentTime()}")


@bot.listen()
async def on_message(ctx):
    # 봇이 보낸 메시지 무시
    if ctx.author == bot.user:
        return

    if ctx.content == "젠장 마커스":
        await Damnit(ctx)


async def Damnit(ctx):  # 이스터 에그
    with open("./image/damnitMarkus.png", "rb") as f:
        image = discord.File(f)
    await ctx.reply(file=image)
    print(f"젠장 마커스 난 네가 좋다 / {currentTime()}")
    return
>>>>>>> c3294e3bdc1f6043a1ae832cc18b23ce7b9829cf


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


<<<<<<< HEAD
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


=======
>>>>>>> c3294e3bdc1f6043a1ae832cc18b23ce7b9829cf
bot.run(TOKEN)
