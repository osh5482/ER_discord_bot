import asyncio
import discord
from discord.ext import commands
from functions.utill import current_time


class bot_manage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """새로운 서버에 초대받았을 때 메시지 출력"""
        new_server = guild.system_channel
        server_info = (guild.name, guild.id)
        if new_server:
            await asyncio.sleep(1)
            await new_server.send("아 또 눈젖빵 만들었어")
        print(f"[{current_time()}] Bot was invited at {server_info}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """서버에서 봇 내보내질 때 로그 남김"""
        server_info = (guild.name, guild.id)
        print(f"[{current_time()}] Bot was kicked out at {server_info}")

    @commands.command(hidden=True, name="서버")
    @commands.is_owner()
    async def servers(self, ctx):
        servers = self.bot.guilds
        server_list = [f"{server.name} (ID: {server.id})" for server in servers]
        servers_str = "\n".join(server_list)
        print(servers_str)
        print(f"[{current_time()}] server cnt: {len(server_list)}")
        # await ctx.channel.send(servers_str)

    @commands.command(aliases=["ㅁㅇ", "문의"])
    async def QnA(self, ctx):
        user_id = self.bot.owner_id  # 봇 주인의 ID를 가져옵니다.
        user = await self.bot.fetch_user(user_id)  # 사용자 정보를 가져옵니다.
        owner_name = user.name  # 사용자의 이름을 가져옵니다.
        await ctx.reply(f"ㄴ문의는 {owner_name}에게 DM해주세요.")

        questioner = ctx.author.name
        server = ctx.guild.name
        print(f"[{current_time()}] QnA was used by {questioner} in {server}")


async def setup(bot):
    await bot.add_cog(bot_manage(bot))
