import aiohttp
import discord
from discord.ext import commands
import functions.ER_API as ER
import functions.ER_statistics as gg
from functions.dict_lib import char_english, weapon_english, char_weapons
from functions.utill import *
from functions.manageDB import *


class game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.command(aliases=["ㅍㅊ", "패치", "ㅍㄴ", "패노", "패치노트", "vs"])
    async def get_recent_major_patchnote(self, ctx):
        """제일 최근 메이저패치 가져오는 함수"""
        if ctx.author == self.bot.user:
            return
        # print(f"Start getRecentPatchNote...")
        RecentMajorPatchNote = await ER.get_patchnote()
        await ctx.send(RecentMajorPatchNote)
        print(
            f"[{current_time()}] Success getRecentPatchNote\nPatchNote url: {RecentMajorPatchNote}"
        )
        print_user_server(ctx)
        return

    # @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.command(aliases=["ㄷㅈ", "동접", "ew"])
    async def get_in_game_user(self, ctx):
        """동접 확인 함수"""
        if ctx.author == self.bot.user:
            return

        current_unix_time = int(time.time())
        now = current_time()
        in_game_user = await ER.get_current_player_api()

        conn, c = connect_DB()
        create_table(c)
        insert_data(c, current_unix_time, now, in_game_user)

        c.close()
        conn.close()

        most_24h = await load_24h()

        if in_game_user >= 20000:
            icon = "god_game"

        elif in_game_user >= 10000:
            icon = "plz_play_game"

        elif in_game_user >= 4000:
            icon = "mang_game"

        else:
            icon = "chobisang"

        in_game_user = format(in_game_user, ",")
        most_24h = format(most_24h, ",")

        embed = discord.Embed(
            title="현재 동시 접속자",
            description=f"**{in_game_user}** 명",
            color=0x00FF00,
        )

        embed.add_field(name="24h 최고 동접", value=f"{most_24h} 명", inline=False)
        file = discord.File(f"./image/icon/{icon}.png", filename="leniticon.png")
        embed.set_thumbnail(url="attachment://leniticon.png")
        await ctx.send(file=file, embed=embed)

        print(f"[{current_time()}] Success getInGameUser {in_game_user} and save on DB")
        print_user_server(ctx)

    # @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.command(aliases=["ㅅㅈ", "시즌", "tw"])
    async def get_season_remaining(self, ctx):
        """남은 시즌 확인 함수"""
        if ctx.author == self.bot.user:
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
        print(f"[{current_time()}] Success getSeasonRemaining")
        print_user_server(ctx)

    # @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.command(aliases=["ㄷㅁ", "ㄷㅁㄱ", "데미", "데미갓", "뎀갓", "ea"])
    async def check_demigod_rating(self, ctx):
        """데미갓 컷 보는 함수"""
        if ctx.author == self.bot.user:
            return
        rating = await ER.get_demigod_rating()
        await ctx.channel.send(f"> 데미갓 컷 : **{rating}** 점")
        print(f"[{current_time()}] Success check_demigod_rating {rating}")
        print_user_server(ctx)

    # @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.command(aliases=["ㅇㅌ", "ㅇㅌㄴㅌ", "이터", "이터니티", "dx"])
    async def check_iternity_rating(self, ctx):
        """이터 컷 보는 함수"""
        if ctx.author == self.bot.user:
            return
        rating = await ER.get_iternity_rating()
        await ctx.channel.send(f"> 이터니티 컷 : **{rating}** 점")
        print(f"[{current_time()}] Success check_iternity_rating {rating}")
        print_user_server(ctx)

    @commands.Cog.listener()
    async def on_message(self, ctx):
        """특정 명령어 인식하는 함수"""
        # 봇이 보낸 메시지 무시
        if ctx.author == self.bot.user:
            return

        if ctx.content.startswith("?"):

            if (
                ctx.content.startswith("?ㅈㅈ")
                or ctx.content.startswith("?전적")
                or ctx.content.startswith("?ww")
            ):
                argus = ctx.content[3:].strip()
                if argus == "":
                    await ctx.reply(
                        "> 닉네임을 입력해주세요.\n> 띄어쓰기로 멀티서치가 가능합니다."
                    )
                    return
                name_list = argus.split(" ")
                files, embeds = await self.get_user_info(ctx.channel, name_list)
                print(f"[{current_time()}] Success get user info {name_list}")
                print_user_server(ctx)
                await ctx.reply(files=files, embeds=embeds)
                await logging_function(self.bot, ctx, function_name="get_user_info")
                return

            if (
                ctx.content.startswith("?ㅌㄱ")
                or ctx.content.startswith("?통계")
                or ctx.content.startswith("?xr")
            ):
                argus = ctx.content[3:].strip()

                if argus == "":
                    await ctx.reply("?ㅌㄱ<무기> <캐릭터>로 입력해주세요.")
                    return

                weapon_character = argus.split(" ")

                if len(weapon_character) == 1:
                    word = weapon_character[0]
                    finish = False

                    for name in char_weapons.keys():
                        if word.endswith(name):
                            character = name
                            weapon = word[: -len(name)]
                            finish = True
                            break

                    if finish == False:
                        await ctx.reply("무기 혹은 캐릭터 이름을 확인해주세요.")
                        return

                if len(weapon_character) > 2:
                    await ctx.reply("?ㅌㄱ<무기> <캐릭터>로 입력해주세요.")
                    return

                if len(weapon_character) == 2:
                    weapon = weapon_character[0]
                    character = weapon_character[1]

                if (
                    weapon not in weapon_english.keys()
                    or character not in char_weapons.keys()
                ):
                    await ctx.reply("무기 혹은 캐릭터 이름을 확인해주세요.")
                    return

                if weapon not in char_weapons[character]:
                    await ctx.reply("해당 캐릭터가 사용하지 않는 무기입니다.")
                    return

                try:
                    file, embed = await self.get_character_statistics(weapon, character)
                    await ctx.reply(file=file, embed=embed)
                    print(
                        f"[{current_time()}] Success get character statistics {weapon} {character}"
                    )
                    print_user_server(ctx)
                    await logging_function(
                        self.bot, ctx, function_name="get_character_statistics"
                    )
                    return

                except:
                    print("failed making embed")

    async def get_user_info(self, ctx, name_list):
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
                rank = format(rank, ",")
                tier = rank_data["tier"]
                mmr = rank_data["mmr"]

                win_rate = (rank_data["totalWins"] / rank_data["totalGames"]) * 100
                win_rate = round(win_rate, 2)
                average_TK = round(
                    rank_data["totalTeamKills"] / rank_data["totalGames"], 2
                )
                average_rank = rank_data["averageRank"]
                most_character_code = rank_data["characterStats"][0]["characterCode"]
                char_name, code = ER.find_characte_name(most_character_code)

                embed = discord.Embed(
                    title=f"{name}",
                    # description=f"랭킹 : {rank} 위\n티어 : {tier}\nMMR : {mmr}",
                    color=0x00FF00,
                    url=f"https://dak.gg/er/players/{name}",
                )
                embed.add_field(name="랭킹", value=f"{rank}위", inline=True)
                embed.add_field(name="티어", value=f"{tier}", inline=True)
                embed.add_field(name="mmr", value=f"{mmr}", inline=True)
                embed.add_field(name="승률", value=f"{win_rate}%", inline=True)
                embed.add_field(name="평균순위", value=f"{average_rank}위", inline=True)
                embed.add_field(name="평균TK", value=f"{average_TK}", inline=True)

            if user_tuple[0] == 640415:
                file_path = "./image/icon/rakkun.jpg"
            else:
                file_path = f"./image/char_profile/{code}_{char_name}.png"

            embed.set_thumbnail(url=f"attachment://{char_name}.png")
            file = discord.File(file_path, filename=f"{char_name}.png")
            files_and_embeds.append((embed, file))

        files = [file for embed, file in files_and_embeds]
        embeds = [embed for embed, file in files_and_embeds]
        return files, embeds

    # @commands.cooldown(1, 10, commands.BucketType.channel)
    @commands.command()
    async def get_character_statistics(self, weapon, character):
        """캐릭터 통계 가져와서 임베드로 보여주는 함수"""
        weapon_E = weapon_english[f"{weapon}"]
        character_E = char_english[f"{character}"]
        s_dict = await gg.make_character_statistics(weapon_E, character_E)

        embed = discord.Embed(
            title=f"{weapon} {character}",
            # description=f"다이아+ 통계",
            color=0x00FF00,
            url=f"https://dak.gg/er/characters/{character_E}?weaponType={weapon_E}",
        )

        pick_percent = s_dict["pick"][0]
        win_percent = s_dict["win"][0]
        get_RP = s_dict["get_RP"][0]
        pick_rank = s_dict["pick"][1][1:].replace("/", " / ")
        win_rank = s_dict["win"][1][1:].replace("/", " / ")
        get_RP_rank = s_dict["get_RP"][1][1:].replace("/", " / ")

        embed.add_field(name="픽률", value=f"{pick_percent}\n{pick_rank}", inline=True)
        embed.add_field(name="승률", value=f"{win_percent}\n{win_rank}", inline=True)
        embed.add_field(
            name="RP획득량", value=f"{get_RP} RP\n{get_RP_rank}", inline=True
        )
        embed.set_footer(text="가장 최근 패치의 다이아+ 3일 통계입니다")

        code = s_dict["code"]
        file = discord.File(
            f"./image/char_profile/{code}_{character_E}.png", filename="profile.png"
        )
        embed.set_thumbnail(url="attachment://profile.png")

        return file, embed


async def setup(bot):
    await bot.add_cog(game(bot))
