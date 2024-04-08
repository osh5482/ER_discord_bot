from discord.ext import tasks, commands
from functions.manageDB import *
from functions.utill import insert_comma
from functions.ER_API import get_current_player_api
from functions.utill import current_time


class save_data(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.save.start()

    def cog_unload(self):
        self.save.cancel()

    @tasks.loop(minutes=5.0)
    async def save(self):
        """1분마다 동접 데이터 저장 및 삭제 실행하는 함수"""
        conn, c = connect_DB()
        create_table(c)
        current_unix_time = int(time.time())
        now = current_time()
        current_player = await get_current_player_api()
        insert_data(c, current_unix_time, now, current_player)
        delete_old_data(c)
        sort_by_time(c)
        current_player = insert_comma(current_player)
        # print(f"24시간 동안 최고 동접: {most_play}")
        print(f"[{now}] Save player {current_player}")

        c.close()
        conn.close()

    # @commands.command(aliases=["그래프"])
    # async def print_graph(ctx):
    #     data_list = await get_data()
    #     await creat_graph(data_list)
    #     return


async def setup(bot):
    await bot.add_cog(save_data(bot))
