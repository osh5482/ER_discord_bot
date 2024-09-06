import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from functions.utill import current_time, print_user_server

BOT_OWNER_ID = 393987987005767690


def is_owner(interaction: discord.Interaction):
    return interaction.user.id == BOT_OWNER_ID


class bot_manage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channel_id = 1227163092719374366
        self.log_channel = self.bot.get_channel(self.log_channel_id)

    @app_commands.check(is_owner)
    @app_commands.command(name="서버", description="봇을 사용 중인 서버 갯수 확인")
    async def servers(self, interaction: discord.Interaction):
        """봇이 있는 서버 리스트 출력"""
        servers = self.bot.guilds

        server_list = [f"{server} / {server.member_count}" for server in servers]
        servers_str = "\n".join(server_list)

        # 총 멤버 수를 계산
        total_members = sum(server.member_count for server in servers)

        print(servers_str)
        print(f"[{current_time()}] server cnt: {len(server_list)}")
        print(f"총 멤버 수: {total_members}")

        await interaction.response.send_message(
            f"```사용 서버 갯수 : {len(server_list)}\n서버 멤버 수: {total_members}```"
        )

    @commands.command(aliases=["퇴출", "내보내기"])
    @commands.is_owner()
    async def leave_server(self, ctx: commands.Context, *, server_name: str):
        """특정 서버에서 봇을 내보내는 함수"""
        server = None

        for guild in self.bot.guilds:
            if guild.name == server_name:
                server = guild
                break

        if server:
            await server.leave()
            await ctx.send(f"{server.name}에서 봇을 내보냈습니다. (ID: {server.id})")
            print(f"[{current_time()}] Bot left the server: {server.name}")
            print_user_server(ctx)

        else:
            await ctx.send(
                f"봇이 해당 서버에 존재하지 않습니다. (서버 이름: {server_name})"
            )
        return


async def setup(bot):
    await bot.add_cog(bot_manage(bot))
