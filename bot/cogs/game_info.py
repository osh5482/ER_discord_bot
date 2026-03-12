import aiohttp
import discord
from datetime import datetime
from discord.ext import commands
from discord import app_commands
import core.api.eternal_return as ER
import core.crawlers.statistics as gg
from utils.constants import char_english, weapon_english, char_weapons
from utils.helpers import *
from utils.logger import logger
from database.connection import *
from config import Config


class PatchNoteSelectView(discord.ui.View):
    """패치노트 버전 선택을 위한 드롭다운 메뉴 뷰 - 페이지네이션 지원"""

    def __init__(self, all_patches, current_patch_info, page=0):
        super().__init__(timeout=300)  # 5분 타임아웃
        self.all_patches = all_patches
        self.current_patch_info = current_patch_info
        self.page = page
        self.items_per_page = 23  # 네비게이션 버튼을 위해 2개 여유 공간 확보

        # 페이지 계산
        self.total_pages = (
            len(all_patches) + self.items_per_page - 1
        ) // self.items_per_page
        start_idx = page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(all_patches))
        current_page_patches = all_patches[start_idx:end_idx]

        # 드롭다운 메뉴 옵션 생성
        options = []
        for i, patch in enumerate(current_page_patches):
            global_idx = start_idx + i  # 전체 리스트에서의 인덱스
            # 현재 선택된 패치인지 확인
            is_current = (
                patch["major_version"] == current_patch_info["major_patch_version"]
            )

            # 라벨 생성 (최신 버전인지 확인)
            label = f"버전 {patch['major_version']}"
            if global_idx == 0:  # 가장 최신 버전
                label += " (최신)"

            options.append(
                discord.SelectOption(
                    label=label,
                    description=(
                        patch["major_date"] if patch["major_date"] else "날짜 정보 없음"
                    ),
                    value=patch["major_version"],
                    default=is_current,
                )
            )

        if options:
            self.select_menu = PatchVersionSelect(options, self.all_patches)
            self.add_item(self.select_menu)

        # 페이지네이션 버튼 추가 (2페이지 이상일 때만)
        if self.total_pages > 1:
            # 이전 페이지 버튼
            prev_button = discord.ui.Button(
                label="◀ 이전",
                style=discord.ButtonStyle.secondary,
                disabled=(page == 0),
                row=1,
            )
            prev_button.callback = self.previous_page
            self.add_item(prev_button)

            # 페이지 정보 버튼 (비활성화)
            page_info_button = discord.ui.Button(
                label=f"{page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                row=1,
            )
            self.add_item(page_info_button)

            # 다음 페이지 버튼
            next_button = discord.ui.Button(
                label="다음 ▶",
                style=discord.ButtonStyle.secondary,
                disabled=(page >= self.total_pages - 1),
                row=1,
            )
            next_button.callback = self.next_page
            self.add_item(next_button)

    async def previous_page(self, interaction: discord.Interaction):
        """이전 페이지로 이동"""
        if self.page > 0:
            new_page = self.page - 1
            new_view = PatchNoteSelectView(
                self.all_patches, self.current_patch_info, new_page
            )

            # 현재 선택된 패치의 임베드 유지
            current_patch = None
            for patch in self.all_patches:
                if (
                    patch["major_version"]
                    == self.current_patch_info["major_patch_version"]
                ):
                    current_patch = patch
                    break

            if current_patch:
                embed = create_patch_embed(current_patch)
                await interaction.response.edit_message(embed=embed, view=new_view)
            else:
                await interaction.response.edit_message(view=new_view)

    async def next_page(self, interaction: discord.Interaction):
        """다음 페이지로 이동"""
        if self.page < self.total_pages - 1:
            new_page = self.page + 1
            new_view = PatchNoteSelectView(
                self.all_patches, self.current_patch_info, new_page
            )

            # 현재 선택된 패치의 임베드 유지
            current_patch = None
            for patch in self.all_patches:
                if (
                    patch["major_version"]
                    == self.current_patch_info["major_patch_version"]
                ):
                    current_patch = patch
                    break

            if current_patch:
                embed = create_patch_embed(current_patch)
                await interaction.response.edit_message(embed=embed, view=new_view)
            else:
                await interaction.response.edit_message(view=new_view)

    async def on_timeout(self):
        """타임아웃 시 모든 컴포넌트 비활성화"""
        for item in self.children:
            item.disabled = True

        # 메시지 편집은 여기서 하지 않음 (interaction이 없어서 에러 발생 가능)


class PatchVersionSelect(discord.ui.Select):
    """패치 버전 선택 드롭다운 메뉴"""

    def __init__(self, options, all_patches):
        super().__init__(
            placeholder="다른 패치 버전을 선택하세요...",
            options=options,
            min_values=1,
            max_values=1,
        )
        self.all_patches = all_patches

    async def callback(self, interaction: discord.Interaction):
        """드롭다운 메뉴에서 패치 버전 선택 시 호출"""
        selected_version = self.values[0]

        # 선택된 버전의 패치 정보 찾기
        selected_patch = None
        for patch in self.all_patches:
            if patch["major_version"] == selected_version:
                selected_patch = patch
                break

        if not selected_patch:
            await interaction.response.send_message(
                "선택한 패치 버전의 정보를 찾을 수 없습니다.", ephemeral=True
            )
            return

        # 새로운 임베드 생성
        embed = create_patch_embed(selected_patch)

        # 드롭다운 메뉴의 기본 선택값 업데이트
        for i, option in enumerate(self.options):
            option.default = option.value == selected_version

        # 새로운 뷰 생성 (업데이트된 기본값 반영) - 현재 페이지 유지
        current_page = 0
        # 선택된 버전이 몇 페이지에 있는지 찾기
        for i, patch in enumerate(self.all_patches):
            if patch["major_version"] == selected_version:
                current_page = i // 23  # items_per_page와 동일
                break

        new_view = PatchNoteSelectView(
            self.all_patches,
            {"major_patch_version": selected_patch["major_version"]},
            current_page,
        )

        await interaction.response.edit_message(embed=embed, view=new_view)


def create_patch_embed(patch_info):
    """패치 정보로부터 Discord 임베드 생성"""
    major_version = patch_info.get("major_version", "알 수 없음")
    major_date = patch_info.get("major_date", "")
    major_patches = patch_info.get("major_patches", [])
    minor_patches = patch_info.get("minor_patches", [])
    last_updated = patch_info.get("last_updated", "")

    # Discord Embed 생성
    embed = discord.Embed(title=f"🔧 패치노트 - {major_version}", color=0x00FF00)

    # 메이저 패치 정보 (날짜를 필드명에 포함)
    if major_patches:
        # 날짜 정보를 필드명에 추가
        field_name = f"📋 메이저 패치"
        if major_date:
            field_name += f" ({major_date})"

        # 메이저 패치들을 오래된 순으로 정렬하여 제목으로 표시
        try:
            sorted_major_patches = sorted(
                major_patches,
                key=lambda x: x.get("date", "") if x.get("date") else "",
                reverse=False,  # 오래된 순으로 정렬
            )
        except:
            sorted_major_patches = major_patches

        major_info = ""
        for patch in sorted_major_patches:
            # 제목에서 버전 정보 추출하여 기본값으로 사용
            title = patch.get("title", "")
            if not title:
                title = f"{major_version} PATCH NOTES"

            url = patch.get("url", "")

            if url:
                if major_info:  # 이미 내용이 있으면 줄바꿈 추가
                    major_info += "\n"
                major_info += f"[**{title}**]({url})"
            else:
                if major_info:
                    major_info += "\n"
                major_info += f"**{title}**"

        if not major_info:  # major_patches가 있지만 내용이 없는 경우
            major_info = f"**{major_version}**"

        embed.add_field(name=field_name, value=major_info, inline=False)
    else:
        # major_patches가 없는 경우
        field_name = f"📋 메이저 패치"
        if major_date:
            field_name += f" ({major_date})"

        major_info = f"**{major_version}**"
        embed.add_field(name=field_name, value=major_info, inline=False)

    # 마이너 패치 정보
    if minor_patches:
        # 마이너 패치를 오래된 순으로 정렬 (날짜 및 알파벳 순)
        try:
            sorted_minor_patches = sorted(
                minor_patches,
                key=lambda x: (
                    x.get("date", "") if x.get("date") else "",
                    x.get("alpha_part", "") if x.get("alpha_part") else "",
                ),
                reverse=False,  # 오래된 순으로 변경
            )
        except:
            sorted_minor_patches = minor_patches

        minor_info = ""
        displayed_count = 0
        max_display = 15  # 최대 표시할 마이너 패치 수

        for patch in sorted_minor_patches:
            if displayed_count >= max_display:
                remaining_count = len(sorted_minor_patches) - displayed_count
                minor_info += f"\n... 외 {remaining_count}개 더"
                break

            # 새로운 구조와 기존 구조 모두 지원
            if isinstance(patch, dict):
                # 딕셔너리 형태의 패치 정보
                if "alpha_part" in patch:
                    # 새로운 구조 (alpha_part 포함)
                    version = f"{major_version}{patch.get('alpha_part', '')}"
                    url = patch.get("url", "")
                else:
                    # 기존 구조
                    version = patch.get("version", "")
                    url = patch.get("url", "")

                if version and url:
                    minor_info += f"[{version}]({url})  "
                    displayed_count += 1
            else:
                # 기존 구조 지원 (문자열인 경우)
                minor_info += f"{patch}  "
                displayed_count += 1

        minor_info = minor_info.strip()
        embed.add_field(name="🔨 마이너 패치", value=minor_info, inline=False)
    else:
        embed.add_field(
            name="🔨 마이너 패치",
            value="해당 버전의 마이너 패치가 없습니다.",
            inline=False,
        )

    # 마지막 업데이트 시간 추가
    if last_updated:
        embed.set_footer(text=f"마지막 업데이트: {last_updated}")

    return embed


class game_info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ㅍㄴ", description="제일 최근 메이저패치와 마이너패치 정보를 불러옵니다."
    )
    async def get_recent_major_patchnote(self, interaction: discord.Interaction):
        """제일 최근 메이저패치와 마이너패치 가져오는 함수 (DB에서 조회) - 드롭다운 메뉴 지원"""

        # 로딩 메시지 표시 (ephemeral로 설정)
        await interaction.response.defer(ephemeral=True)

        # DB에서 모든 패치노트 정보 조회
        try:
            conn, c = connect_DB()
            create_patch_table(c)  # 테이블이 없으면 생성

            # 모든 패치 데이터 조회 (버전 순으로 정렬)
            c.execute(
                """SELECT major_version, major_date, major_patches, minor_patches, str_updated_at 
                   FROM patch_notes 
                   ORDER BY major_version DESC"""
            )
            rows = c.fetchall()

            c.close()
            conn.close()

        except Exception as e:
            await interaction.followup.send(
                f"데이터베이스 조회 중 오류가 발생했습니다: {e}", ephemeral=True
            )
            return

        if not rows:
            await interaction.followup.send(
                "저장된 패치노트 정보가 없습니다. 잠시 후 다시 시도해주세요.",
                ephemeral=True,
            )
            return

        # 버전 정렬을 위한 함수
        def sort_version_key(version_str):
            try:
                parts = version_str.split(".")
                return tuple(int(part) for part in parts)
            except (ValueError, AttributeError):
                return (0, 0)

        # 패치 데이터 처리 및 정렬
        all_patches = []
        for row in rows:
            (
                major_version,
                major_date,
                major_patches_json,
                minor_patches_json,
                str_updated_at,
            ) = row

            # JSON 파싱
            try:
                major_patches = (
                    json.loads(major_patches_json) if major_patches_json else []
                )
                minor_patches = (
                    json.loads(minor_patches_json) if minor_patches_json else []
                )
            except json.JSONDecodeError:
                major_patches = []
                minor_patches = []

            all_patches.append(
                {
                    "major_version": major_version,
                    "major_date": major_date,
                    "major_patches": major_patches,
                    "minor_patches": minor_patches,
                    "last_updated": str_updated_at,
                }
            )

        # 버전별로 정렬 (최신순)
        all_patches.sort(
            key=lambda x: sort_version_key(x["major_version"]), reverse=True
        )

        if not all_patches:
            await interaction.followup.send(
                "최근 패치노트를 찾을 수 없습니다.", ephemeral=True
            )
            return

        # 최신 패치 정보
        latest_patch = all_patches[0]

        # 첫 번째 임베드 생성 (최신 패치)
        embed = create_patch_embed(latest_patch)

        # 드롭다운 메뉴 뷰 생성 (2개 이상의 패치가 있을 때만)
        view = None
        if len(all_patches) > 1:
            # 현재 선택된 패치가 몇 페이지에 있는지 계산
            current_page = 0
            for i, patch in enumerate(all_patches):
                if patch["major_version"] == latest_patch["major_version"]:
                    current_page = i // 23  # items_per_page와 동일
                    break

            view = PatchNoteSelectView(
                all_patches,
                {"major_patch_version": latest_patch["major_version"]},
                current_page,
            )

        await interaction.followup.send(embed=embed, view=view)

        logger.debug(f"Total patches available: {len(all_patches)}")
        logger.debug(f"Latest: {latest_patch['major_version']} ({latest_patch['major_date']})")
        print_user_server(interaction, "Success getRecentPatchNote from DB with dropdown")
        await logging_function(self.bot, interaction)

    @app_commands.command(name="ㄷㅈ", description="현재 스팀 동접자 수를 확인합니다.")
    async def get_in_game_user(self, interaction: discord.Interaction):
        """동접 확인 함수"""

        current_unix_time = int(time.time())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

        print_user_server(interaction, f"Success getInGameUser {in_game_user} and save on DB")
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
        print_user_server(interaction, "Success getSeasonRemaining")
        await logging_function(self.bot, interaction)

    @app_commands.command(name="ㄷㅁ", description="현재 데미갓 MMR 컷을 확인합니다.")
    async def check_demigod_rating(self, interaction: discord.Interaction):
        """데미갓 컷 보는 함수"""

        rating = await ER.get_demigod_rating()
        if rating:
            await interaction.response.send_message(f"> 데미갓 컷 : **{rating}** 점")
        else:
            await interaction.response.send_message(f"> 아직 데미갓 유저가 없습니다.")

        print_user_server(interaction, f"Success check_demigod_rating {rating}")
        await logging_function(self.bot, interaction)

    @app_commands.command(name="ㅇㅌ", description="현재 이터니티 MMR 컷을 확인합니다.")
    async def check_iternity_rating(self, interaction: discord.Interaction):
        """이터 컷 보는 함수"""

        rating = await ER.get_iternity_rating()
        if rating:
            await interaction.response.send_message(f"> 이터니티 컷 : **{rating}** 점")
        else:
            await interaction.response.send_message(f"> 아직 이터니티 유저가 없습니다.")
        print_user_server(interaction, f"Success check_iternity_rating {rating}")
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

        print_user_server(interaction, f"Success get user info {name}")
        await logging_function(self.bot, interaction)

    @app_commands.command(name="ㅌㄱ", description="캐릭터 통계를 가져옵니다.")
    @app_commands.describe(weapon="무기 이름", character="캐릭터 이름")
    async def character_statistics(
        self, interaction: discord.Interaction, weapon: str, character: str
    ):
        # 먼저 defer()로 "로딩 중..." 상태 표시 (3초 타임아웃 방지)
        await interaction.response.defer()

        try:
            # 무기/캐릭터 이름 검증
            if weapon not in weapon_english:
                await interaction.followup.send(
                    f"❌ '{weapon}'은(는) 올바른 무기 이름이 아닙니다.", ephemeral=True
                )
                return

            if character not in char_english:
                await interaction.followup.send(
                    f"❌ '{character}'은(는) 올바른 캐릭터 이름이 아닙니다.",
                    ephemeral=True,
                )
                return

            weapon_E = weapon_english[weapon]
            character_E = char_english[character]

            # 캐릭터가 해당 무기를 사용할 수 있는지 검증
            if weapon not in char_weapons.get(character, []):
                await interaction.followup.send(
                    f"❌ {character}은(는) {weapon}을(를) 사용할 수 없습니다.\n"
                    f"사용 가능한 무기: {', '.join(char_weapons[character])}",
                    ephemeral=True,
                )
                return

            logger.info(f"통계 크롤링 시작: {weapon} {character}")

            # 크롤링 수행 (시간이 오래 걸림)
            s_dict = await gg.dakgg_crawler(weapon_E, character_E)

            # Embed 생성
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

            # defer() 사용 후에는 followup.send()로 응답
            await interaction.followup.send(file=file, embed=embed)

            print_user_server(interaction, f"Success get character statistics {weapon} {character}")
            await logging_function(self.bot, interaction)

        except KeyError as e:
            logger.error(f"KeyError in character_statistics: {e}")
            await interaction.followup.send(
                f"❌ 통계 데이터를 찾을 수 없습니다. 필수 통계 항목이 누락되었습니다: {e}",
                ephemeral=True,
            )
        except FileNotFoundError as e:
            logger.error(f"FileNotFoundError in character_statistics: {e}")
            await interaction.followup.send(
                f"❌ 캐릭터 이미지 파일을 찾을 수 없습니다.", ephemeral=True
            )
        except Exception as e:
            logger.exception(f"Error in character_statistics: {e}")
            await interaction.followup.send(
                f"❌ 통계를 가져오는 데 실패했습니다.\n오류: {str(e)}", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(game_info(bot))
