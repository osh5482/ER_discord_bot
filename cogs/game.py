import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
import functions.ER_API as ER
import functions.ER_statistics as gg
from functions.dict_lib import char_english, weapon_english, char_weapons
from functions.utill import *
from functions.manageDB import *


class game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ㅍㄴ", description="제일 최근 메이저패치를 불러옵니다.")
    async def get_recent_major_patchnote(self, interaction: discord.Interaction):
        """제일 최근 메이저패치 가져오는 함수"""
        RecentMajorPatchNote = await ER.get_patchnote()
        await interaction.response.send_message(RecentMajorPatchNote)
        print(
            f"[{current_time()}] Success getRecentPatchNote\nPatchNote url: {RecentMajorPatchNote}"
        )
        print_user_server(interaction)
        return

    @app_commands.command(name="ㄷㅈ", description="현재 스팀 동접자 수를 확인합니다.")
    async def get_in_game_user(self, interaction: discord.Interaction):
        """동접 확인 함수"""

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
            # url=f"https://steamdb.info/app/1049590/charts/",
            description=f"**{in_game_user}** 명",
            color=0x00FF00,
        )

        embed.add_field(name="24h 최고 동접", value=f"{most_24h} 명", inline=False)
        file = discord.File(f"./image/icon/{icon}.png", filename="leniticon.png")
        embed.set_thumbnail(url="attachment://leniticon.png")
        await interaction.response.send_message(file=file, embed=embed)

        print(f"[{current_time()}] Success getInGameUser {in_game_user} and save on DB")
        print_user_server(interaction)

    @app_commands.command(
        name="ㅅㅈ", description="현재 시즌의 남은 기한을 확인합니다."
    )
    async def get_season_remaining(self, interaction: discord.Interaction):
        """남은 시즌 확인 함수"""

        curren_season_data, current_season_name = await ER.get_current_season_name()
        remaining_time_list = await ER.remain_time(curren_season_data)
        day = remaining_time_list[0]
        hour = remaining_time_list[1]
        minute = remaining_time_list[2]
        lastday = await ER.end_current_season(curren_season_data)

        if current_season_name == aiohttp.ClientResponseError:
            await not_my_fault(interaction)
            return
        description = f"시즌 종료일 : **{lastday}**\n시즌 종료까지 **{day}일 {hour}시간 {minute}분** 남았습니다."
        embed = discord.Embed(
            title=f"{current_season_name}",
            description=description,
            color=0x00FF00,
        )

        await interaction.response.send_message(embed=embed)
        print(f"[{current_time()}] Success getSeasonRemaining")
        print_user_server(interaction)

    @app_commands.command(name="ㄷㅁ", description="현재 데미갓 MMR 컷을 확인합니다.")
    async def check_demigod_rating(self, interaction: discord.Interaction):
        """데미갓 컷 보는 함수"""

        rating = await ER.get_demigod_rating()
        await interaction.response.send_message(f"> 데미갓 컷 : **{rating}** 점")
        print(f"[{current_time()}] Success check_demigod_rating {rating}")
        print_user_server(interaction)

    @app_commands.command(name="ㅇㅌ", description="현재 이터니티 MMR 컷을 확인합니다.")
    async def check_iternity_rating(self, interaction: discord.Interaction):
        """이터 컷 보는 함수"""

        rating = await ER.get_iternity_rating()
        await interaction.response.send_message(f"> 이터니티 컷 : **{rating}** 점")
        print(f"[{current_time()}] Success check_iternity_rating {rating}")
        print_user_server(interaction)

    @app_commands.command(
        name="ㅈㅈ", description="유저의 현재 시즌 정보를 가져옵니다."
    )
    @app_commands.describe(name="닉네임")
    async def user_info(self, interaction: discord.Interaction, name: str):
        files_and_embeds = []

        user_tuple = await ER.get_user_num(name)
        if user_tuple == aiohttp.ClientResponseError:
            await interaction.response.send_message(
                "서버 오류로 인해 유저 정보를 가져올 수 없습니다.", ephemeral=True
            )
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
        elif rank_data == 0:
            code = rank_data
            char_name = "Nadja"
            embed = discord.Embed(
                title=f"{name}",
                description="현재시즌 정보가 없습니다.",
                color=0x00FF00,
                url=f"https://dak.gg/er/players/{name}",
            )
        else:
            rank = format(rank_data["rank"], ",")
            tier = rank_data["tier"]
            mmr = rank_data["mmr"]

            win_rate = round(
                (rank_data["totalWins"] / rank_data["totalGames"]) * 100, 2
            )
            average_TK = round(rank_data["totalTeamKills"] / rank_data["totalGames"], 2)
            average_rank = rank_data["averageRank"]
            most_character_code = rank_data["characterStats"][0]["characterCode"]
            char_name, code = ER.find_characte_name(most_character_code)

            embed = discord.Embed(
                title=f"{name}",
                color=0x00FF00,
                url=f"https://dak.gg/er/players/{name}",
            )
            embed.add_field(name="랭킹", value=f"{rank}위", inline=True)
            embed.add_field(name="티어", value=f"{tier}", inline=True)
            embed.add_field(name="mmr", value=f"{mmr}", inline=True)
            embed.add_field(name="승률", value=f"{win_rate}%", inline=True)
            embed.add_field(name="평균순위", value=f"{average_rank}위", inline=True)
            embed.add_field(name="평균TK", value=f"{average_TK}", inline=True)
            file_path = f"./image/char_profile/{code}_{char_name}.png"

        embed.set_thumbnail(url=f"attachment://{char_name}.png")
        file = discord.File(file_path, filename=f"{char_name}.png")
        files_and_embeds.append((embed, file))

        files = [file for embed, file in files_and_embeds]
        embeds = [embed for embed, file in files_and_embeds]
        await interaction.response.send_message(files=files, embeds=embeds)

        print(f"[{current_time()}] Success get user info {name}")
        print_user_server(interaction)
        await logging_function(self.bot, interaction, function_name="get_user_info")

    @app_commands.command(name="ㅌㄱ", description="캐릭터 통계를 가져옵니다.")
    @app_commands.describe(weapon="무기 이름", character="캐릭터 이름")
    async def character_statistics(
        self, interaction: discord.Interaction, weapon: str, character: str
    ):
        try:
            weapon_E = weapon_english[f"{weapon}"]
            character_E = char_english[f"{character}"]
            s_dict = await gg.make_character_statistics(weapon_E, character_E)

            embed = discord.Embed(
                title=f"{weapon} {character}",
                color=0x00FF00,
                url=f"https://dak.gg/er/characters/{character_E}?weaponType={weapon_E}",
            )

            pick_percent = s_dict["pick"][0]
            win_percent = s_dict["win"][0]
            get_RP = s_dict["get_RP"][0]
            pick_rank = s_dict["pick"][1][1:].replace("/", " / ")
            win_rank = s_dict["win"][1][1:].replace("/", " / ")
            get_RP_rank = s_dict["get_RP"][1][1:].replace("/", " / ")

            embed.add_field(
                name="픽률", value=f"{pick_percent}\n{pick_rank}", inline=True
            )
            embed.add_field(
                name="승률", value=f"{win_percent}\n{win_rank}", inline=True
            )
            embed.add_field(
                name="RP획득량", value=f"{get_RP} RP\n{get_RP_rank}", inline=True
            )
            embed.set_footer(text="가장 최근 패치의 다이아+ 3일 통계입니다")

            code = s_dict["code"]
            file = discord.File(
                f"./image/char_profile/{code}_{character_E}.png", filename="profile.png"
            )
            embed.set_thumbnail(url="attachment://profile.png")

            await interaction.response.send_message(file=file, embed=embed)
            print(
                f"[{current_time()}] Success get character statistics {weapon} {character}"
            )
            print_user_server(interaction)
            await logging_function(
                self.bot, interaction, function_name="get_character_statistics"
            )
        except Exception as e:
            print("failed making embed", e)
            await interaction.response.send_message(
                "통계를 가져오는 데 실패했습니다.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(game(bot))
