import discord
from discord.ext import commands
from functions.utill import *


class easter_egg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
                # await on_command_error(ctx, e)
                return

        if "젠장 마커스" in message.content:
            try:
                await self.damn_it(message)
                return
            except commands.CommandOnCooldown as e:
                # await on_command_error(ctx, e)
                return

    async def damn_it(self, ctx):
        """젠장 마커스"""
        cooldown_time = 60
        func_name = "damn_it"
        if await check_cooldown(func_name, cooldown_time):
            with open("./image/damn_it_markus.png", "rb") as f:
                image = discord.File(f)
            await ctx.reply(file=image)
            print(f"젠장 마커스 난 네가 좋다 / {current_time()}")
        else:
            raise commands.CommandOnCooldown(
                cooldown_time, ctx.channel.id, commands.BucketType.channel
            )
        return

    async def ER_forever(self, ctx):
        """지옥끝까지 함께하겠다 이터널리턴!!!!"""
        cooldown_time = 60
        func_name = "ER_forever"
        if await check_cooldown(func_name, cooldown_time):
            with open("./image/ER_forever.jpg", "rb") as f:
                image = discord.File(f)
            await ctx.reply(file=image)
            print(f"지옥끝까지 함께하겠다 이터널리턴!!!! / {current_time()}")
        else:
            raise commands.CommandOnCooldown(
                cooldown_time, ctx.channel.id, commands.BucketType.channel
            )


async def setup(bot):
    await bot.add_cog(easter_egg(bot))
