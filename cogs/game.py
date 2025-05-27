import aiohttp
import discord
import time  # 성능 측정을 위해 추가
from discord.ext import commands
from discord import app_commands
import functions.ER_API as ER
from functions.crawler import StatisticsCrawler  # 변경된 import
from functions.dict_lib import char_english, weapon_english, char_weapons
from functions.utill import *
from functions.manageDB import *


class game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ㅍㄴ", description="제일 최근 메이저패치와 마이너패치 정보를 불러옵니다."
    )
    async def get_recent_major_patchnote(self, interaction: discord.Interaction):
        """제일 최근 메이저패치와 마이너패치 가져오는 함수 (DB에서 조회)"""

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

        # 메이저 패치 정보 추출
        major_version = patch_info.get("major_patch_version")
        major_date = patch_info.get("major_patch_date")
        major_url = patch_info.get("major_patch_url")
        minor_patches = patch_info.get("minor_patch_data", [])
        last_updated = patch_info.get("last_updated")

        if not major_url:
            await interaction.followup.send(
                "최근 패치노트를 찾을 수 없습니다.", ephemeral=True
            )
            return

        # Discord Embed 생성
        embed = discord.Embed(title=f"🔧 최신 패치노트", color=0x00FF00)

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

        await interaction.followup.send(embed=embed)

        print(f"[{current_time()}] Success getRecentPatchNote from DB")
        print(f"Major: {major_version} ({major_date}) - {major_url}")
        print(f"Minor patches: {len(minor_patches)}개")
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
        file = discord.File(f"./image/icon/{icon}.png", filename="leniticon.png")
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

        file_path = f"./image/char_profile/{code}_{char_name}.png"
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
            # 로딩 메시지 표시
            await interaction.response.defer()

            weapon_E = weapon_english[f"{weapon}"]
            character_E = char_english[f"{character}"]

            # 기본 다이아+ 통계 가져오기
            async with StatisticsCrawler() as crawler:
                s_dict = await crawler.dakgg_crawler(weapon_E, character_E)

            # 초기 임베드 생성
            embed, file = await self._create_statistics_embed(
                s_dict, weapon, character, weapon_E, character_E, "다이아몬드+"
            )

            # 티어 선택 드롭다운 뷰 생성
            view = TierSelectionView(
                weapon, character, weapon_E, character_E, s_dict["code"]
            )

            await interaction.followup.send(file=file, embed=embed, view=view)
            print(
                f"[{current_time()}] Success get character statistics {weapon} {character}"
            )
            print_user_server(interaction)
            await logging_function(self.bot, interaction)
        except Exception as e:
            print("failed making embed: ", e)
            await interaction.followup.send(
                "통계를 가져오는 데 실패했습니다.", ephemeral=True
            )

    async def _create_statistics_embed(
        self, s_dict, weapon, character, weapon_E, character_E, tier="다이아몬드+"
    ):
        """통계 임베드를 생성하는 헬퍼 함수"""
        embed = discord.Embed(
            title=f"{weapon} {character}",
            color=0x00FF00,
            url=f"https://dak.gg/er/characters/{character_E}?weaponType={weapon_E}",
        )

        pick_percent = s_dict.get("픽률", {}).get("value", "N/A")
        win_percent = s_dict.get("승률", {}).get("value", "N/A")
        get_RP = s_dict.get("RP 획득", {}).get("value", "N/A")
        pick_rank = s_dict.get("픽률", {}).get("ranking", "N/A")
        win_rank = s_dict.get("승률", {}).get("ranking", "N/A")
        get_RP_rank = s_dict.get("RP 획득", {}).get("ranking", "N/A")

        embed.add_field(name="픽률", value=f"{pick_percent}\n#{pick_rank}", inline=True)
        embed.add_field(name="승률", value=f"{win_percent}\n#{win_rank}", inline=True)
        embed.add_field(
            name="RP획득", value=f"{get_RP} RP\n#{get_RP_rank}", inline=True
        )

        # 티어에 따른 푸터 텍스트 설정
        embed.set_footer(text=f"가장 최근 패치의 {tier} 7일 통계입니다")

        code = s_dict["code"]
        file = discord.File(
            f"./image/char_profile/{code}_{character_E}.png", filename="profile.png"
        )
        embed.set_thumbnail(url="attachment://profile.png")

        return embed, file


class TierSelectionView(discord.ui.View):
    """티어 선택 드롭다운을 포함하는 뷰"""

    def __init__(self, weapon, character, weapon_E, character_E, char_code):
        super().__init__(timeout=300)  # 5분 후 타임아웃
        self.weapon = weapon
        self.character = character
        self.weapon_E = weapon_E
        self.character_E = character_E
        self.char_code = char_code

        # 드롭다운 메뉴 추가
        self.add_item(TierDropdown(weapon, character, weapon_E, character_E, char_code))

    async def on_timeout(self):
        """타임아웃 시 버튼 비활성화"""
        for item in self.children:
            item.disabled = True


class TierDropdown(discord.ui.Select):
    """티어 선택 드롭다운 메뉴"""

    def __init__(self, weapon, character, weapon_E, character_E, char_code):
        self.weapon = weapon
        self.character = character
        self.weapon_E = weapon_E
        self.character_E = character_E
        self.char_code = char_code

        # 티어 옵션 정의 (이모지 제거)
        tier_options = [
            discord.SelectOption(
                label="In 1000", description="상위 1000명 통계", value="In 1000"
            ),
            discord.SelectOption(
                label="미스릴+", description="미스릴 이상 통계", value="미스릴+"
            ),
            discord.SelectOption(
                label="메테오라이트+",
                description="메테오라이트 이상 통계",
                value="메테오라이트+",
            ),
            discord.SelectOption(
                label="다이아몬드+",
                description="다이아몬드 이상 통계",
                value="다이아몬드+",
                default=True,  # 기본 선택
            ),
            discord.SelectOption(
                label="플래티넘+", description="플래티넘 이상 통계", value="플래티넘+"
            ),
            discord.SelectOption(
                label="플래티넘", description="플래티넘 통계", value="플래티넘"
            ),
            discord.SelectOption(label="골드", description="골드 통계", value="골드"),
            discord.SelectOption(label="실버", description="실버 통계", value="실버"),
            discord.SelectOption(
                label="브론즈", description="브론즈 통계", value="브론즈"
            ),
            discord.SelectOption(
                label="아이언", description="아이언 통계", value="아이언"
            ),
        ]

        super().__init__(
            placeholder="다른 티어의 통계를 보려면 선택하세요...",
            min_values=1,
            max_values=1,
            options=tier_options,
        )

    async def callback(self, interaction: discord.Interaction):
        """드롭다운 선택 시 호출되는 콜백 (최적화된 버전)"""
        try:
            selected_tier = self.values[0]

            # 즉시 응답으로 로딩 상태 표시 (이미지 없이)
            loading_embed = discord.Embed(
                title=f"🔄 {self.weapon} {self.character}",
                description=f"**{selected_tier}** 티어 통계를 불러오는 중...",
                color=0xFFFF00,  # 노란색으로 로딩 상태 표시
            )

            await interaction.response.edit_message(
                embed=loading_embed,
                attachments=[],  # 기존 이미지 제거
                view=None,  # 로딩 중에는 드롭다운 숨김
            )

            start_time = time.time()

            # 선택된 티어의 통계 가져오기
            async with StatisticsCrawler() as crawler:
                s_dict = await crawler.scrape_tier_statistics(
                    self.weapon_E, self.character_E, selected_tier
                )

            load_time = time.time() - start_time
            print(f"🏁 총 로딩 시간: {load_time:.2f}초")

            # 새로운 임베드 생성
            from cogs.game import game

            game_cog = game(interaction.client)
            embed, file = await game_cog._create_statistics_embed(
                s_dict,
                self.weapon,
                self.character,
                self.weapon_E,
                self.character_E,
                selected_tier,
            )

            # 드롭다운의 기본 선택값 업데이트
            for option in self.options:
                option.default = option.value == selected_tier

            # 새로운 뷰 생성 (기존 뷰 유지하되 선택값만 업데이트)
            new_view = TierSelectionView(
                self.weapon,
                self.character,
                self.weapon_E,
                self.character_E,
                self.char_code,
            )

            # 새 드롭다운의 선택값 업데이트
            for option in new_view.children[0].options:
                option.default = option.value == selected_tier

            # 메시지 업데이트 (완료된 임베드와 이미지로 교체)
            await interaction.edit_original_response(
                embed=embed, attachments=[file], view=new_view
            )

            print(
                f"[{current_time()}] Tier statistics updated: {self.weapon} {self.character} - {selected_tier} ({load_time:.2f}s)"
            )

        except Exception as e:
            print(f"❌ 티어 통계 업데이트 실패: {e}")

            # 에러 상태 표시 (이미지 없이)
            error_embed = discord.Embed(
                title=f"❌ {self.weapon} {self.character}",
                description=f"**{selected_tier}** 티어 통계를 가져오는데 실패했습니다.\n잠시 후 다시 시도해주세요.",
                color=0xFF0000,  # 빨간색으로 에러 상태 표시
            )

            # 원본 뷰로 복원
            original_view = TierSelectionView(
                self.weapon,
                self.character,
                self.weapon_E,
                self.character_E,
                self.char_code,
            )

            await interaction.edit_original_response(
                embed=error_embed,
                attachments=[],  # 에러 시에도 이미지 제거
                view=original_view,
            )


async def setup(bot):
    await bot.add_cog(game(bot))
