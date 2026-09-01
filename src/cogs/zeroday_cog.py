import discord
from discord import app_commands
from discord.ext import commands

from omega_api import search_zeroday_exploits
from translator import zerodaycog_translate
from ui import ZeroDayPanel


class ZerodayCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="zerodaytoday", description="Search exploits on 0daytoday"
    )
    @app_commands.guild_only()
    @app_commands.describe(search="Search query (free text or CVE)")
    async def send_zeroday(
        self, interaction: discord.Interaction, search: str
    ) -> None:
        await interaction.response.defer(thinking=True)
        search = search.strip()

        if len(search) < 3:
            msg_text = await zerodaycog_translate(
                interaction.guild_id, "errors", "too_short"
            )
            await interaction.followup.send(msg_text)
            return

        try:
            result = await search_zeroday_exploits(search, page=1, limit=5)
        except Exception:
            result = None

        if not result:
            msg_text = await zerodaycog_translate(
                interaction.guild_id, "errors", "not_found", search=search
            )
            await interaction.followup.send(msg_text)
            return

        view = ZeroDayPanel(
            guild_id=interaction.guild_id,
            query=search,
            initial_results=result,
            current_page=1,
        )
        await view.init_ui()

        msg = await interaction.followup.send(view=view)
        view.message = msg


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ZerodayCog(bot))