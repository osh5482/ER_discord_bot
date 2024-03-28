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


def current_time():
    """현재시간 확인함수
    반환값 : str(현재시간 Y-m-d H-M-S)"""
    current_time = datetime.now()
    # 시간을 원하는 형식으로 포맷하여 출력
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


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


@bot.event
async def on_ready():
    """봇 시작하면 로그인 로그 print하고 상태 띄워주는 함수"""
    print(f"logged in as {bot.user} at {current_time()}")
    await bot.change_presence(activity=discord.Game(name="실수로 눈젖빵 제작"))


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


@commands.cooldown(1, 10, commands.BucketType.channel)
@bot.command(aliases=["ㅍㅊ", "패치", "ㅍㄴ", "패노", "패치노트"])
async def get_recent_major_patchnote(ctx):
    """제일 최근 메이저패치 가져오는 함수"""
    if ctx.author == bot.user:
        return
    # print(f"Start getRecentPatchNote...")
    RecentMajorPatchNote = await ER.get_patchnote()
    await ctx.send(RecentMajorPatchNote)
    print(f"Success getRecentPatchNote! at {current_time()}")
    return


@commands.cooldown(1, 10, commands.BucketType.channel)
@bot.command(aliases=["ㄷㅈ", "동접"])
async def get_in_game_user(ctx):
    """동접 확인 함수"""
    if ctx.author == bot.user:
        return
    # print(f"Start getInGameUser...")
    in_game_user = await ER.get_current_player_api()
    if in_game_user >= 12000:
        icon = "god_game"
    if in_game_user >= 6000:
        icon = "plz_play_game"
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
    print(f"Success getInGameUser {in_game_user} at {current_time()}")


@commands.cooldown(1, 10, commands.BucketType.channel)
@bot.command(aliases=["ㅅㅈ", "시즌"])
async def get_season_remaining(ctx):
    """남은 시즌 확인 함수"""
    if ctx.author == bot.user:
        return
    # print(f"Start getSeasonRemaining...")
    curren_season_data, current_season_name = await ER.get_current_season_name()
    remaining_time_list = await ER.remain_time(curren_season_data)
    day = remaining_time_list[0]
    hour = remaining_time_list[1]
    minute = remaining_time_list[2]
    lastday = await ER.end_current_season(curren_season_data)

    if current_season_name == aiohttp.ClientResponseError:
        await not_my_fault(ctx)
        return
    description = f"시즌 종료일 : **{lastday}**\n시즌 종료까지 **{day}일 {hour}시간 {minute}분** 남았습니다."
    embed = discord.Embed(
        title=f"{current_season_name}",
        description=description,
        color=0x00FF00,
    )

    await ctx.channel.send(embed=embed)
    print(f"Success getSeasonRemaining at {current_time()}")


@bot.listen()
async def on_message(ctx):  #
    """특정 명령어 인식하는 함수"""
    # 봇이 보낸 메시지 무시
    if ctx.author == bot.user:
        return

    if ctx.content.startswith("?"):

        if ctx.content.startswith("?ㅈㅈ") or ctx.content.startswith("?전적"):
            argus = ctx.content[3:].strip()
            if argus == "":
                await ctx.reply("> 닉네임을 입력해주세요.")
                return
            name_list = argus.split(" ")
            files, embeds = await get_user_info(ctx.channel, name_list)
            print(f"Success get user info({name_list}) at {current_time()}")
            await ctx.reply(files=files, embeds=embeds)
            return

        if ctx.content.startswith("?ㅌㄱ") or ctx.content.startswith("?통계"):
            argus = ctx.content[3:].strip()
            weapon, character = argus.split(" ")

            try:
                file, embed = await get_character_statistics(weapon, character)
                await ctx.reply(file=file, embed=embed)
                print(
                    f"Success get character statistics {weapon} {character} at {current_time()}"
                )
                return

            except:
                print("failed making embed")

    else:
        if "끝까지 함께하겠다 이터널리턴" in ctx.content:
            try:
                await ER_forever(ctx)
            except commands.CommandOnCooldown as e:
                await on_command_error(ctx, e)
                return

        if "젠장 마커스" in ctx.content:
            try:
                await damn_it(ctx)
            except commands.CommandOnCooldown as e:
                await on_command_error(ctx, e)
                return
            return


@commands.cooldown(1, 10, commands.BucketType.channel)
async def get_character_statistics(weapon, character):
    """캐릭터 통계 가져와서 임베드로 보여주는 함수"""
    weapon_E = weapon_english[f"{weapon}"]
    character_E = char_english[f"{character}"]
    s_dict = await gg.make_character_statistics(weapon_E, character_E)

    embed = discord.Embed(
        title=f"{weapon} {character}",
        # description=f"()",
        color=0x00FF00,
        url=f"https://dak.gg/er/characters/{character_E}?weaponType={weapon_E}",
    )

    pick_percent = s_dict["pick"][0]
    win_percent = s_dict["win"][0]
    get_RP_percent = s_dict["get_RP"][0]
    pick_rank = s_dict["pick"][1][1:].replace("/", " / ")
    win_rank = s_dict["win"][1][1:].replace("/", " / ")
    get_RP_rank = s_dict["get_RP"][1][1:].replace("/", " / ")

    embed.add_field(name="픽률", value=f"{pick_percent}\n{pick_rank}", inline=True)
    embed.add_field(name="승률", value=f"{win_percent}\n{win_rank}", inline=True)
    embed.add_field(
        name="RP획득량", value=f"{get_RP_percent}\n{get_RP_rank}", inline=True
    )

    code = s_dict["code"]
    file = discord.File(
        f"./image/char_profile/{code}_{character_E}.png", filename="profile.png"
    )
    embed.set_thumbnail(url="attachment://profile.png")

    return file, embed


async def get_user_info(ctx, name_list):
    """유저 현재시즌 정보 출력해주는 함수"""
    files_and_embeds = []

    for name in name_list:
        user_tuple = await ER.get_user_num(name)
        if user_tuple == aiohttp.ClientResponseError:
            await not_my_fault(ctx)
            return
        rank_data = await ER.get_user_season_data(user_tuple)
        if rank_data == 404:
            code = 404
            char_name = "Leniticon"
            embed = discord.Embed(
                title=f"{name}",
                description="존재하지 않는 유저입니다.\n서버 점검 중일수도 있습니다.",
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
            char_name, code = ER.find_characte_name(most_character_code)

            embed = discord.Embed(
                title=f"{name}",
                description=f"랭킹 : {rank} 위\n티어 : {tier}\nMMR : {mmr}",
                color=0x00FF00,
                url=f"https://dak.gg/er/players/{name}",
            )
        file_path = f"./image/char_profile/{code}_{char_name}.png"
        embed.set_thumbnail(url=f"attachment://{char_name}.png")
        file = discord.File(file_path, filename=f"{char_name}.png")
        files_and_embeds.append((embed, file))

    files = [file for embed, file in files_and_embeds]
    embeds = [embed for embed, file in files_and_embeds]
    return files, embeds


@commands.cooldown(1, 10, commands.BucketType.channel)
@bot.command(aliases=["ㅇㅌ", "이터", "이터니티"])
async def check_iternity_rating(ctx):
    """이터 컷 보는 함수"""
    if ctx.author == bot.user:
        return
    rating = await ER.get_iternity_rating()
    await ctx.channel.send(f"> 이터니티 컷 : **{rating}** 점")
    print(f"Success checkDIternityRating {rating} at {current_time()}")


@commands.cooldown(1, 10, commands.BucketType.channel)
@bot.command(aliases=["ㄷㅁ", "데미", "데미갓", "뎀갓"])
async def check_demigod_rating(ctx):
    """데미갓 컷 보는 함수"""
    if ctx.author == bot.user:
        return
    rating = await ER.get_demigod_rating()
    await ctx.channel.send(f"> 데미갓 컷 : **{rating}** 점")
    print(f"Success checkDemigodRating {rating} at {current_time()}")


@commands.cooldown(1, 10, commands.BucketType.channel)
async def damn_it(ctx):
    """젠장 마커스"""
    cooldown_time = 10
    func_name = "damn_it"
    if await check_cooldown(func_name, cooldown_time):
        with open("./image/damn_it_markus.png", "rb") as f:
            image = discord.File(f)
        await ctx.reply(file=image)
        print(f"젠장 마커스 난 네가 좋다 / {current_time()}")
    else:
        raise commands.CommandOnCooldown(
            cooldown_time, ctx.channel.id, commands.BucketType.channel
        )
    return


async def ER_forever(ctx):
    """지옥끝까지 함께하겠다 이터널리턴!!!!"""
    cooldown_time = 10
    func_name = "ER_forever"
    if await check_cooldown(func_name, cooldown_time):
        with open("./image/ER_forever.jpg", "rb") as f:
            image = discord.File(f)
        await ctx.reply(file=image)
        print(f"지옥끝까지 함께하겠다 이터널리턴!!!! / {current_time()}")
    else:
        raise commands.CommandOnCooldown(
            cooldown_time, ctx.channel.id, commands.BucketType.channel
        )


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


bot.run(TOKEN)
