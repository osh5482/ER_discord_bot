import discord
from discord.ext import commands
from utils.helpers import current_time, print_user_server


class events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """에러처리 함수"""

        # 없는 명령어
        if isinstance(error, commands.CommandNotFound):
            return

        # 명령어 쿨타임
        if isinstance(error, commands.CommandOnCooldown):
            print(f"[{current_time()}] {ctx.command} was requested on cooldown")
            print_user_server(ctx)
            return

        # 기타 에러 로깅
        print(f"[{current_time()}] Unhandled error: {error}")


async def setup(bot):
    await bot.add_cog(events(bot))
