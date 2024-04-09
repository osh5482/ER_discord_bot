import asyncio
import discord
from discord.ext import commands
from functions.utill import current_time, print_user_server


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
    async def send_question(self, ctx):
        sent_message = await ctx.reply(
            "문의사항을 이 메세지에 **답장**으로 1분안에 입력해주세요.\n쿨타임은 **30분**입니다."
        )

        def check(message):
            return (
                message.author == ctx.author
                and message.reference
                and message.reference.message_id == sent_message.id
            )

        try:
            reply_message = await self.bot.wait_for(
                "message", check=check, timeout=60
            )  # 사용자의 답장을 기다립니다. 60초 동안 대기합니다.
        except asyncio.TimeoutError:
            await sent_message.reply("1분이 초과되었습니다.")
            return

        # 사용자의 답장을 나에게 DM으로 보냅니다.
        owner = await self.bot.fetch_user(self.bot.owner_id)  # 393987987005767690
        await owner.send(
            f"{ctx.guild.name}에서 {ctx.author}님이 문의를 등록했습니다\n> {reply_message.content}"
        )
        await reply_message.reply("문의사항이 전송되었습니다.")
        print(f"[{current_time()}] Questioned by {ctx.author} in {ctx.guild.name}")


async def setup(bot):
    await bot.add_cog(bot_manage(bot))
