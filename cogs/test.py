from discord.ext import tasks, commands


class test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.index = 0
        self.printer.start()

    def cog_unload(self):
        self.printer.cancel()

    @tasks.loop(seconds=2.0)
    async def printer(self):
        print(self.index)
        self.index += 1


async def setup(bot):
    await bot.add_cog(test(bot))
