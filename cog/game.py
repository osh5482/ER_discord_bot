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

class game(commands.Cog):
    def __init__(self, bot)
        self.bot = bot

    @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.command(aliases=["ㅍㅊ", "패치", "ㅍㄴ", "패노", "패치노트"])
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
    @commands.command(aliases=["ㄷㅈ", "동접"])
    async def get_in_game_user(ctx):
        """동접 확인 함수"""
        if ctx.author == bot.user:
            return
        # print(f"Start getInGameUser...")
        in_game_user = await ER.get_current_player_api()
        if in_game_user >= 12000:
            icon = "god_game"
        elif in_game_user >= 6000:
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
    @commands.command(aliases=["ㅅㅈ", "시즌"])
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
