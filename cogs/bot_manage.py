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
        print(f"[{current_time()}] Bot was invited at {server_info}")
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

        await self.bot.change_presence(
            activity=discord.Game(name=f"눈젖빵 {len(self.bot.guilds)}개째 제작")
        )

    @commands.command(hidden=True, aliases=["ㅅㅂ", "서버"])
    @commands.is_owner()
    async def servers(self, ctx):
        """봇이 있는 서버 리스트 출력"""
        servers = self.bot.guilds
        total_members = sum(server.member_count for server in servers)
        server_list = [
            f"server: {server}, members: {server.member_count}" for server in servers
        ]
        servers_str = "\n".join(server_list)
        print(servers_str)
        print(f"[{current_time()}] server cnt: {len(server_list)}")
        await ctx.channel.send(
            f"```{servers_str}\n 총 서버 갯수 : {len(server_list)}\n 총 멤버 수: {total_members}```"
        )

    @commands.cooldown(1, 1800, commands.BucketType.user)
    @commands.command(aliases=["ㅁㅇ", "문의"])
    async def send_question(self, ctx: commands.Context, *, question):
        """나한테 문의사항 보내주는 함수"""
        owner = await self.bot.fetch_user(self.bot.owner_id)  # 393987987005767690
        msg_id = ctx.message.id
        await owner.send(
            f"*[{current_time()}] 문의사항 등록*\n보낸 이: `{ctx.guild.name}`의 `{ctx.author}`님(`{ctx.author.id}`)\n>>> {question}"
        )
        await ctx.reply(
            "문의사항이 전송되었습니다. 쿨타임은 30분입니다.\n답변을 받기 위해 DM을 허용해주세요."
        )
        print(f"[{current_time()}] Questioned by {ctx.author} in {ctx.guild.name}")
        print_user_server(ctx)

    @commands.command(aliases=["ㄷㅂ", "답변"])
    @commands.is_owner()
    async def question_reply(self, ctx: commands.Context, msg_id: int, *, answer):
        """문의에 대한 답변을 보내는 함수"""
        question = await self.bot.fetch_user(msg_id)
        answer = f"*[{current_time()}]* 문의 답변이 도착했습니다.\n>>> {answer}"
        try:
            await question.reply(answer)
            await ctx.send(f"{question.author}에게 답변을 성공적으로 보냈습니다.")
        except:
            await ctx.send("개인DM이 닫혀있는듯...")
        return

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """로그 채널에 로그 남기는 함수"""
        log_channel = self.bot.get_channel(self.log_channel_id)
        await log_channel.send(
            f"*[{current_time()}]* `{ctx.command}` was processed by `{ctx.author}` in `{ctx.guild}`"
        )


async def setup(bot):
    await bot.add_cog(bot_manage(bot))
