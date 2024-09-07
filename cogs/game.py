import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from bs4 import BeautifulSoup  # Install BeautifulSoup for web scraping
import functions.ER_API as ER
import functions.ER_statistics as gg
from functions.dict_lib import char_english, weapon_english, char_weapons
from functions.utill import *
from functions.manageDB import *


class game(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_bintum_image(self):
        """Fetch image from the specified link for 'bintum'."""
        url = "https://gall.dcinside.com/mgallery/board/lists/?id=bser"  # The URL you want to scrape

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Find the <span> with the class "cover" and extract the background-image URL
                    cover_span = soup.find("span", class_="cover")
                    if cover_span and "background-image" in cover_span["style"]:
                        # Extract the image URL from the style attribute
                        style_attr = cover_span["style"]
                        start = style_attr.find("url(") + 4
                        end = style_attr.find(")", start)
                        img_url = style_attr[start:end].strip("'\"")
                        return img_url
                    else:
                        return None
                else:
                    return None

    async def send_bintum_image(self, interaction: discord.Interaction):
        """Send the image fetched from the website to the interaction."""
        img_url = await self.fetch_bintum_image()
        if img_url:
            embed = discord.Embed(
                title="bintum's Special Command",
                description="Here is the image:",
                color=0x00FF00,
            )
            embed.set_image(url=img_url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "Failed to fetch image.", ephemeral=True
            )

    async def check_bintum(self, interaction: discord.Interaction):
        """Check if the user is 'bintum' and redirect to alternative command if true."""
        if interaction.user.name == "bintum":  # Check if the user is 'bintum'
            await self.send_bintum_image(interaction)
            return True
        return False

    @app_commands.command(name="ㅍㄴ", description="제일 최근 메이저패치를 불러옵니다.")
    async def get_recent_major_patchnote(self, interaction: discord.Interaction):
        if await self.check_bintum(interaction):
            return

        RecentMajorPatchNote = await ER.get_patchnote()
        await interaction.response.send_message(RecentMajorPatchNote)
        print(
            f"[{current_time()}] Success getRecentPatchNote\nPatchNote url: {RecentMajorPatchNote}"
        )
        print_user_server(interaction)
        await logging_function(self.bot, interaction)

    @app_commands.command(name="ㄷㅈ", description="현재 스팀 동접자 수를 확인합니다.")
    async def get_in_game_user(self, interaction: discord.Interaction):
        if await self.check_bintum(interaction):
            return

        current_unix_time = int(time.time())
        now = current_time()
        in_game_user = await ER.get_current_player_api()

        conn, c = connect_DB()
        create_table(c)
        insert_data(c, current_unix_time, now, in_game_user)

        c.close()
        conn.close()

        most_24h = await load_24h()

        if in_game_user >= 20000:
            icon = "god_game"
        elif in_game_user >= 10000:
            icon = "plz_play_game"
        elif in_game_user >= 4000:
            icon = "mang_game"
        else:
            icon = "chobisang"

        in_game_user = format(in_game_user, ",")
        most_24h = format(most_24h, ",")

        embed = discord.Embed(
            title="현재 동시 접속자",
            description=f"**{in_game_user}** 명",
            color=0x00FF00,
        )

        embed.add_field(name="24h 최고 동접", value=f"{most_24h} 명", inline=False)
        file = discord.File(f"./image/icon/{icon}.png", filename="leniticon.png")
        embed.set_thumbnail(url="attachment://leniticon.png")
        await interaction.response.send_message(file=file, embed=embed)

        print(f"[{current_time()}] Success getInGameUser {in_game_user} and save on DB")
        print_user_server(interaction)
        await logging_function(self.bot, interaction)

    @app_commands.command(
        name="ㅅㅈ", description="현재 시즌의 남은 기한을 확인합니다."
    )
    async def get_season_remaining(self, interaction: discord.Interaction):
        if await self.check_bintum(interaction):
            return

        curren_season_data, current_season_name = await ER.get_current_season_name()
        remaining_time_list = await ER.remain_time(curren_season_data)
        day = remaining_time_list[0]
        hour = remaining_time_list[1]
        minute = remaining_time_list[2]
        lastday = await ER.end_current_season(curren_season_data)

        if current_season_name == aiohttp.ClientResponseError:
            await not_my_fault(interaction)
            return
        description = f"시즌 종료일 : **{lastday}**\n시즌 종료까지 **{day}일 {hour}시간 {minute}분** 남았습니다."
        embed = discord.Embed(
            title=f"{current_season_name}",
            description=description,
            color=0x00FF00,
        )

        await interaction.response.send_message(embed=embed)
        print(f"[{current_time()}] Success getSeasonRemaining")
        print_user_server(interaction)
        await logging_function(self.bot, interaction)

    # Continue modifying other commands similarly...


async def setup(bot):
    await bot.add_cog(game(bot))
