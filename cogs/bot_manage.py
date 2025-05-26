import asyncio
import os
import discord
from discord.ext import commands
from discord import app_commands
from functions.manageDB import save_patch_notes_to_db
from functions.utill import current_time, print_user_server, logging_function

BOT_OWNER_ID = 393987987005767690
SPECIFIC_SERVER_ID = 1156212577202872351


def is_owner(interaction: discord.Interaction):
    return interaction.user.id == BOT_OWNER_ID


class bot_manage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.check(is_owner)
    @app_commands.command(name="관리", description="봇 관리 명령어 (관리자 전용)")
    async def manage(self, interaction: discord.Interaction):
        """Displays the management panel with buttons."""
        view = ManageView(self)
        try:
            await interaction.response.send_message(
                "봇 관리 패널입니다. 아래 버튼을 클릭하여 원하는 작업을 수행하세요.",
                view=view,
                ephemeral=True,
            )
        except Exception as e:
            print(f"ERROR: {e}")
            await interaction.response.send_message(
                f"명령어 실행 중 오류가 발생했습니다.\n{e}", ephemeral=True
            )

    @app_commands.check(is_owner)
    @app_commands.command(
        name="ㅍㄴ새로고침",
        description="패치노트를 즉시 새로 크롤링합니다. (관리자 전용)",
    )
    async def refresh_patchnote(self, interaction: discord.Interaction):
        """패치노트를 즉시 새로고침하는 함수 (관리자 전용)"""

        # 관리자 권한 확인 (필요에 따라 수정)
        if interaction.user.id != 393987987005767690:  # BOT_OWNER_ID
            await interaction.response.send_message(
                "이 명령어는 봇 관리자만 사용할 수 있습니다.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        print(f"[{current_time()}] 관리자가 패치노트 새로고침을 요청했습니다.")

        try:
            success = await save_patch_notes_to_db()

            if success:
                await interaction.followup.send(
                    "✅ 패치노트가 성공적으로 새로고침되었습니다.", ephemeral=True
                )
                print(f"[{current_time()}] 패치노트 수동 새로고침 완료")
            else:
                await interaction.followup.send(
                    "❌ 패치노트 새로고침에 실패했습니다.", ephemeral=True
                )
                print(f"[{current_time()}] 패치노트 수동 새로고침 실패")

        except Exception as e:
            await interaction.followup.send(
                f"❌ 패치노트 새로고침 중 오류가 발생했습니다: {e}", ephemeral=True
            )
            print(f"[{current_time()}] 패치노트 수동 새로고침 오류: {e}")

        print_user_server(interaction)
        await logging_function(self.bot, interaction)

    async def list_servers(self, interaction: discord.Interaction):
        """현재 봇이 속한 서버 확인"""
        servers = self.bot.guilds
        server_list = [f"{server} / {server.member_count}" for server in servers]
        server_list = sorted(server_list)
        total_members = sum(server.member_count for server in servers)

        print("\n".join(server_list))
        print(f"[{current_time()}] server count: {len(server_list)}")
        print(f"Total members: {total_members}")

        await interaction.followup.send(
            f"```사용 서버 갯수 : {len(server_list)}\n서버 멤버 수: {total_members}```",
            ephemeral=True,
        )

    async def leave_server(self, interaction: discord.Interaction):
        """특정서버에서 봇 강퇴"""
        await interaction.followup.send(
            "퇴출할 서버의 이름을 입력하세요:", ephemeral=True
        )

        def check(m):
            return (
                m.author.id == interaction.user.id
                and m.channel.id == interaction.channel.id
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=30)
            server_name = msg.content.strip()

            if not server_name:
                await interaction.followup.send(
                    "서버 이름을 입력하지 않았습니다.", ephemeral=True
                )
                return

            server = None
            for guild in self.bot.guilds:
                if guild.name == server_name:
                    server = guild
                    break

            if server:
                await server.leave()
                await interaction.followup.send(
                    f"{server.name}에서 봇을 내보냈습니다. (ID: {server.id})",
                    ephemeral=True,
                )

            else:
                await interaction.followup.send(
                    f"봇이 해당 서버에 존재하지 않습니다. (서버 이름: {server_name})",
                    ephemeral=True,
                )

        except asyncio.TimeoutError:
            await interaction.followup.send(
                "서버 이름 입력 시간이 초과되었습니다.", ephemeral=True
            )

    async def reload_cogs(self, interaction: discord.Interaction):
        """Reload all cogs."""
        await interaction.followup.send("모든 cog를 리로드합니다...", ephemeral=True)

        for extension in list(self.bot.extensions):
            try:
                await self.bot.unload_extension(extension)  # Unload the cog
                await self.bot.load_extension(extension)  # Load it again
                print(f"[{current_time()}] Reloading Success: `{extension}`")
            except Exception as e:
                print(f"[{current_time()}] Reloading Fail: `{extension}`\n{e}")

        await logging_function(self.bot, interaction)


class ManageView(discord.ui.View):
    """Custom view that displays the management buttons."""

    def __init__(self, cog: bot_manage):
        super().__init__(timeout=None)
        self.cog = cog

    @discord.ui.button(label="서버 확인", style=discord.ButtonStyle.primary)
    async def servers_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handles the server check button click."""
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message(
                "이 명령어는 봇 소유자만 사용할 수 있습니다.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        await self.cog.list_servers(interaction)

    @discord.ui.button(label="서버 퇴출", style=discord.ButtonStyle.danger)
    async def leave_server_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handles the leave server button click."""
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message(
                "이 명령어는 봇 소유자만 사용할 수 있습니다.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        await self.cog.leave_server(interaction)

    @discord.ui.button(label="Cog 리로드", style=discord.ButtonStyle.secondary)
    async def reload_cogs_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        """Handles the reload cogs button click."""
        if interaction.user.id != BOT_OWNER_ID:
            await interaction.response.send_message(
                "이 명령어는 봇 소유자만 사용할 수 있습니다.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        await self.cog.reload_cogs(interaction)


async def setup(bot):
    await bot.add_cog(bot_manage(bot))
