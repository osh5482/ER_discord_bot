import discord
from discord.ext import commands
from functions.utill import *


class easter_egg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.func_name = None
        self.cooldown_time = 60

    @commands.Cog.listener()
    async def on_message(self, message):  #
        """특정 명령어 인식하는 함수"""

        # 봇이 보낸 메시지 무시
        if message.author == self.bot.user:
            return

        if "끝까지 함께하겠다 이터널리턴" in message.content:
            try:
                await self.ER_forever(message)
                return
            except commands.CommandOnCooldown as e:
                await self.on_command_error(message, e)
                print_user_server(message)
                return

        if "젠장 마커스" in message.content:
            try:
                await self.damn_it(message)
                return
            except commands.CommandOnCooldown as e:
                await self.on_command_error(message, e)
                print_user_server(message)
                return

    async def damn_it(self, mesaage):
        """젠장 마커스"""

        self.func_name = "easter_egg"
        if await check_cooldown(self.func_name, self.cooldown_time):
            with open("./image/damn_it_markus.png", "rb") as f:
                image = discord.File(f)
            await mesaage.reply(file=image)
            print(f"[{current_time()}] 젠장 마커스 난 네가 좋다")

        else:
            self.func_name = "damn_it"
            raise commands.CommandOnCooldown(
                self.cooldown_time, mesaage.channel.id, commands.BucketType.channel
            )
        return

    async def ER_forever(self, message):
        """지옥끝까지 함께하겠다 이터널리턴!!!!"""

        self.func_name = "easter_egg"
        if await check_cooldown(self.func_name, self.cooldown_time):
            with open("./image/ER_forever.jpg", "rb") as f:
                image = discord.File(f)
            await message.reply(file=image)
            print(f"[{current_time()}] 지옥끝까지 함께하겠다 이터널리턴!!!!")
        else:
            self.func_name = "ER_forever"
            raise commands.CommandOnCooldown(
                self.cooldown_time,
                message.channel.id,
                commands.BucketType.channel,
            )

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """에러처리 함수"""

        # 없는 명령어
        if isinstance(error, commands.CommandNotFound):
            return

        # 명령어 쿨타임
        if isinstance(error, commands.CommandOnCooldown):
            if not hasattr(ctx, "command"):
                command_name = self.func_name
            else:
                command_name = ctx.command
            print(f"[{current_time()}] {command_name} was requested on cooldown")
            return


async def setup(bot):
    await bot.add_cog(easter_egg(bot))
