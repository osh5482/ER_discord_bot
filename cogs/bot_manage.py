import asyncio
import discord
from discord.ext import commands
from functions.utill import current_time, print_user_server


class bot_manage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel_id = 1227163092719374366

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """새로운 서버에 초대받았을 때 메시지 출력"""
        new_server = guild.system_channel
        server_info = (guild.name, guild.id)
        if new_server:
            await asyncio.sleep(1)
            await new_server.send(f"눈젖빵을 {len(self.bot.guilds)}개나 만들어 버려요~")
            print(f"[{current_time()}] Bot was invited at {server_info}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        """서버에서 봇 내보내질 때 로그 남김"""
        server_info = (guild.name, guild.id)
        print(f"[{current_time()}] Bot was kicked out at {server_info}")

    @commands.command(hidden=True, name="서버")
    @commands.is_owner()
    async def servers(self, ctx):
        """봇이 있는 서버 리스트 출력"""
        servers = self.bot.guilds
        server_list = [
            f"server: {server}, members: {server.member_count}" for server in servers
        ]
        servers_str = "\n".join(server_list)
        print(servers_str)
        print(f"[{current_time()}] server cnt: {len(server_list)}")
        await ctx.channel.send(servers_str)

    # @commands.command(aliases=["ㅁㅇ", "문의"])
    # async def QnA(self, ctx):
    #     user_id = self.bot.owner_id  # 봇 주인의 ID를 가져옵니다.
    #     user = await self.bot.fetch_user(user_id)  # 사용자 정보를 가져옵니다.
    #     owner_name = user.name  # 사용자의 이름을 가져옵니다.
    #     await ctx.reply(
    #         f"문의는 {owner_name}에게 DM, 혹은 osh5482@naver.com로 메일을 보내주세요."
    #     )

    #     questioner = ctx.author.name
    #     server = ctx.guild.name
    #     print(f"[{current_time()}] QnA was used by {questioner} in {server}")
    #     print_user_server(ctx)

    @commands.cooldown(1, 1800, commands.BucketType.user)
    @commands.command(aliases=["ㅁㅇ", "문의"])
    async def send_question(self, ctx, question):
        """나한테 문의사항 보내주는 함수"""
        owner = await self.bot.fetch_user(self.bot.owner_id)  # 393987987005767690
        await owner.send(
            f"[{current_time()}]\n{ctx.guild.name}에서 {ctx.author}님이 문의를 등록했습니다\n> {question}"
        )
        await ctx.reply("문의사항이 전송되었습니다. 쿨타임은 30분입니다.")
        print(f"[{current_time()}] Questioned by {ctx.author} in {ctx.guild.name}")
        print_user_server(ctx)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """로그 채널에 로그 남기는 함수"""
        log_channel = self.bot.get_channel(self.log_channel_id)
        await log_channel.send(
            f"*[{current_time()}]* `{ctx.command}` was processed by `{ctx.author}` in `{ctx.guild}`"
        )


async def setup(bot):
    await bot.add_cog(bot_manage(bot))
