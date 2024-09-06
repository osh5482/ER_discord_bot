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

        members = []
        for server in servers:
            members.extend(member.id for member in server.members)
        unique_members = set(members)

        server_list = [f"{server} / {server.member_count}" for server in servers]
        servers_str = "\n".join(server_list)
        print(servers_str)
        print(f"[{current_time()}] server cnt: {len(server_list)}")
        print(f"총 멤버 수: {len(members)}")
        print(f"중복제외 멤버 수: {len(unique_members)}")
        await interaction.response.send_message(
            f"```사용 서버 갯수 : {len(server_list)}\n서버 멤버 수: {len(members)}\n중복제외 멤버수: {len(unique_members)}```",
            ephemeral=True,
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

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """로그 채널에 로그 남기는 함수"""
        log_channel = self.bot.get_channel(self.log_channel_id)
        await log_channel.send(
            f"*[{current_time()}]* `{ctx.command}` was processed by `{ctx.author}` in `{ctx.guild}`"
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """새로운 서버에 초대받았을 때 메시지 출력"""
        new_server = guild.system_channel
        server_info = (guild.name, guild.id)
        print(f"[{current_time()}] Bot was invited at {server_info}")
        await self.log_channel.send(
            f"[{current_time()}] Bot was invited at {server_info}"
        )
        await self.bot.change_presence(
            activity=discord.Game(name=f"눈젖빵 {len(self.bot.guilds)}개째 제작")
        )

        if new_server:
            await asyncio.sleep(1)
            await new_server.send(f"눈젖빵을 {len(self.bot.guilds)}개나 만들어 버려요~")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """서버에서 봇 내보내질 때 로그 남김"""
        server_info = (guild.name, guild.id)
        print(f"[{current_time()}] Bot was kicked out at {server_info}")
        await self.log_channel.send(
            f"[{current_time()}] Bot was kicked out at {server_info}"
        )

        await self.bot.change_presence(
            activity=discord.Game(name=f"눈젖빵 {len(self.bot.guilds)}개째 제작")
        )


async def setup(bot):
    await bot.add_cog(bot_manage(bot))
