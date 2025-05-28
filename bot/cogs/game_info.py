import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
import core.api.eternal_return as ER
import core.crawlers.statistics as gg
from utils.constants import char_english, weapon_english, char_weapons
from utils.helpers import *
from database.connection import *
from config import Config


class PatchVersionSelect(discord.ui.Select):
    """패치 버전 선택을 위한 드롭다운 메뉴"""

    def __init__(self, versions):
        options = []

        # 최대 25개 옵션까지만 표시 (Discord 제한)
        for i, version_info in enumerate(versions[:25]):
            version = version_info["version"]
            patch_date = version_info["patch_date"]

            # 첫 번째 항목(최신)은 기본 선택으로 표시
            is_default = i == 0

            # 최신 버전에는 (최신) 표시 추가
            if i == 0:
                label = f"버전 {version} (최신)"
            else:
                label = f"버전 {version}"

            # 패치 날짜가 있으면 표시, 없으면 "날짜 정보 없음"으로 표시
            description = (
                f"패치 날짜: {patch_date}" if patch_date else "패치 날짜: 정보 없음"
            )

            options.append(
                discord.SelectOption(
                    label=label,
                    description=description,
                    value=version,
                    default=is_default,
                )
            )

        super().__init__(
            placeholder="다른 패치 버전을 선택하세요...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        """드롭다운에서 버전을 선택했을 때 실행되는 콜백"""
        await interaction.response.defer()

        selected_version = self.values[0]

        # DB에서 선택된 버전의 패치 데이터 조회
        patch_info = await get_patch_data_by_version_async(selected_version)

        if patch_info is None:
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content="선택한 버전의 패치노트 정보를 찾을 수 없습니다.",
                embed=None,
                view=None,
            )
            return

        # 새로운 임베드 생성
        embed = create_patch_embed(patch_info)

        # 현재 뷰 업데이트 (선택된 버전을 기본값으로 설정)
        view = PatchVersionView(await get_all_patch_versions_async())

        # 드롭다운에서 선택된 항목 업데이트
        for option in view.select.options:
            option.default = option.value == selected_version

        await interaction.followup.edit_message(
            message_id=interaction.message.id, embed=embed, view=view
        )

        print(f"[{current_time()}] 패치노트 버전 변경: {selected_version}")


class PatchVersionView(discord.ui.View):
    """패치 버전 선택 뷰"""

    def __init__(self, versions):
        super().__init__(timeout=300)  # 5분 후 타임아웃
        self.select = PatchVersionSelect(versions)
        self.add_item(self.select)

    async def on_timeout(self):
        """타임아웃 시 뷰 비활성화"""
        for item in self.children:
            item.disabled = True


def create_patch_embed(patch_info):
    """패치 정보로 임베드 생성하는 헬퍼 함수"""
    major_version = patch_info.get("major_patch_version")
    major_date = patch_info.get("major_patch_date")
    major_url = patch_info.get("major_patch_url")
    minor_patches = patch_info.get("minor_patch_data", [])
    last_updated = patch_info.get("last_updated")

    embed = discord.Embed(title=f"🔧 패치노트 v{major_version}", color=0x00FF00)

    # 메이저 패치 정보
    major_info = f"**버전:** [**{major_version}**]({major_url})"
    if major_date:
        major_info += f"\n**날짜:** {major_date}"

    embed.add_field(name="📋 메이저 패치", value=major_info, inline=False)

    # 마이너 패치 정보
    if minor_patches:
        minor_patches = list(reversed(minor_patches))  # 최신순으로 정렬
        minor_info = ""
        for i, patch in enumerate(minor_patches):
            if i == len(minor_patches) - 1:
                minor_info += f"[**{patch['version']}**]({patch['url']})  "
            else:
                minor_info += f"[{patch['version']}]({patch['url']})  "
        minor_info = minor_info.strip()
        embed.add_field(name="🔨 마이너 패치", value=minor_info, inline=False)
    else:
        embed.add_field(
            name="🔨 마이너 패치",
            value="해당 버전의 마이너 패치가 없습니다.",
            inline=False,
        )

    # 마지막 업데이트 시간 추가
    embed.set_footer(text=f"마지막 업데이트: {last_updated}")

    return embed


async def get_all_patch_versions_async():
    """비동기적으로 모든 패치 버전 목록을 가져오는 함수 (패치 날짜 포함)"""
    conn, c = connect_DB()
    create_patch_table(c)

    # 패치 날짜도 함께 조회하도록 수정
    c.execute(
        """SELECT major_version, major_date, str_updated_at 
           FROM patch_notes 
           ORDER BY updated_at DESC"""
    )
    rows = c.fetchall()

    versions = []
    for row in rows:
        major_version, major_date, str_updated_at = row
        versions.append(
            {
                "version": major_version,
                "patch_date": major_date,
                "updated_at": str_updated_at,
            }
        )

    c.close()
    conn.close()
    return versions


async def get_patch_data_by_version_async(version):
    """비동기적으로 특정 버전의 패치 데이터를 가져오는 함수"""
    conn, c = connect_DB()
    create_patch_table(c)
    patch_data = get_patch_data_by_version(c, version)
    c.close()
    conn.close()
    return patch_data


class game_info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ㅍㄴ", description="제일 최근 메이저패치와 마이너패치 정보를 불러옵니다."
    )
    async def get_recent_major_patchnote(self, interaction: discord.Interaction):
        """제일 최근 메이저패치와 마이너패치 가져오는 함수 (DB에서 조회, 버전 선택 가능)"""

        # 로딩 메시지 표시
        await interaction.response.defer()

        # DB에서 패치노트 정보 조회
        patch_info = await get_patch_notes_from_db()

        if patch_info is None:
            await interaction.followup.send(
                "저장된 패치노트 정보가 없습니다. 잠시 후 다시 시도해주세요.",
                ephemeral=True,
            )
            return

        # 모든 패치 버전 목록 가져오기
        all_versions = await get_all_patch_versions_async()

        if not all_versions:
            await interaction.followup.send(
                "저장된 패치 버전이 없습니다.",
                ephemeral=True,
            )
            return

        # 메인 임베드 생성
        embed = create_patch_embed(patch_info)

        # 버전이 2개 이상일 때만 드롭다운 메뉴 표시
        if len(all_versions) > 1:
            view = PatchVersionView(all_versions)
            await interaction.followup.send(embed=embed, view=view)
        else:
            # 버전이 1개뿐이면 드롭다운 없이 임베드만 표시
            await interaction.followup.send(embed=embed)

        # 로깅
        major_version = patch_info.get("major_patch_version")
        major_date = patch_info.get("major_patch_date")
        major_url = patch_info.get("major_patch_url")
        minor_patches = patch_info.get("minor_patch_data", [])
        last_updated = patch_info.get("last_updated")

        print(f"[{current_time()}] Success getRecentPatchNote from DB")
        print(f"Major: {major_version} ({major_date}) - {major_url}")
        print(f"Minor patches: {len(minor_patches)}개")
        print(f"Available versions: {len(all_versions)}개")
        print(f"Last updated: {last_updated}")
        print_user_server(interaction)
        await logging_function(self.bot, interaction)

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
        file = discord.File(
            f"./assets/images/icons/{icon}.png", filename="leniticon.png"
        )
        embed.set_thumbnail(url="attachment://leniticon.png")
        await interaction.response.send_message(file=file, embed=embed)

        print(f"[{current_time()}] Success getInGameUser {in_game_user} and save on DB")
        print_user_server(interaction)
        await logging_function(self.bot, interaction)

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
        await logging_function(self.bot, interaction)

    @app_commands.command(name="ㄷㅁ", description="현재 데미갓 MMR 컷을 확인합니다.")
    async def check_demigod_rating(self, interaction: discord.Interaction):
        """데미갓 컷 보는 함수"""

        rating = await ER.get_demigod_rating()
        if rating:
            await interaction.response.send_message(f"> 데미갓 컷 : **{rating}** 점")
        else:
            await interaction.response.send_message(f"> 아직 데미갓 유저가 없습니다.")

        print(f"[{current_time()}] Success check_demigod_rating {rating}")
        print_user_server(interaction)
        await logging_function(self.bot, interaction)

    @app_commands.command(name="ㅇㅌ", description="현재 이터니티 MMR 컷을 확인합니다.")
    async def check_iternity_rating(self, interaction: discord.Interaction):
        """이터 컷 보는 함수"""

        rating = await ER.get_iternity_rating()
        if rating:
            await interaction.response.send_message(f"> 이터니티 컷 : **{rating}** 점")
        else:
            await interaction.response.send_message(f"> 아직 이터니티 유저가 없습니다.")
        print(f"[{current_time()}] Success check_iternity_rating {rating}")
        print_user_server(interaction)
        await logging_function(self.bot, interaction)

    @app_commands.command(
        name="ㅈㅈ", description="유저의 현재 시즌 정보를 가져옵니다."
    )
    @app_commands.describe(name="닉네임")
    async def get_user_info(self, interaction: discord.Interaction, name: str):
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

        file_path = f"./assets/images/characters/{code}_{char_name}.png"
        embed.set_thumbnail(url=f"attachment://{char_name}.png")
        file = discord.File(file_path, filename=f"{char_name}.png")
        files_and_embeds.append((embed, file))

        files = [file for embed, file in files_and_embeds]
        embeds = [embed for embed, file in files_and_embeds]
        await interaction.response.send_message(files=files, embeds=embeds)

        print(f"[{current_time()}] Success get user info {name}")
        print_user_server(interaction)
        await logging_function(self.bot, interaction)

    @app_commands.command(name="ㅌㄱ", description="캐릭터 통계를 가져옵니다.")
    @app_commands.describe(weapon="무기 이름", character="캐릭터 이름")
    async def character_statistics(
        self, interaction: discord.Interaction, weapon: str, character: str
    ):
        try:
            weapon_E = weapon_english[f"{weapon}"]
            character_E = char_english[f"{character}"]
            s_dict = await gg.dakgg_crawler(weapon_E, character_E)
            # print(s_dict)

            embed = discord.Embed(
                title=f"{weapon} {character}",
                color=0x00FF00,
                url=f"https://dak.gg/er/characters/{character_E}?weaponType={weapon_E}",
            )

            pick_percent = s_dict["픽률"]["value"]
            win_percent = s_dict["승률"]["value"]
            get_RP = s_dict["RP 획득"]["value"]
            pick_rank = s_dict["픽률"]["ranking"]
            win_rank = s_dict["승률"]["ranking"]
            get_RP_rank = s_dict["RP 획득"]["ranking"]

            embed.add_field(
                name="픽률", value=f"{pick_percent}\n{pick_rank}", inline=True
            )
            embed.add_field(
                name="승률", value=f"{win_percent}\n{win_rank}", inline=True
            )
            embed.add_field(
                name="RP획득", value=f"{get_RP} RP\n{get_RP_rank}", inline=True
            )
            embed.set_footer(text="가장 최근 패치의 다이아+ 7일 통계입니다")

            code = s_dict["code"]
            file = discord.File(
                f"./assets/images/characters/{code}_{character_E}.png",
                filename="profile.png",
            )
            embed.set_thumbnail(url="attachment://profile.png")

            await interaction.response.send_message(file=file, embed=embed)
            print(
                f"[{current_time()}] Success get character statistics {weapon} {character}"
            )
            print_user_server(interaction)
            await logging_function(self.bot, interaction)
        except Exception as e:
            print("failed making embed: ", e)
            await interaction.response.send_message(
                "통계를 가져오는 데 실패했습니다.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(game_info(bot))
