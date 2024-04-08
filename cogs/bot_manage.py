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
            await new_server.send("아 ㅁㅊ 눈젖빵 만들었어")
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
        print(f"[{current_time()}] cnt: {len(server_list)}")
        await ctx.channel.send(servers_str)


async def setup(bot):
    await bot.add_cog(bot_manage(bot))
