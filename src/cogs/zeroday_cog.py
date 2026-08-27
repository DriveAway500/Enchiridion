from discord import app_commands
from discord.ext import commands

from ui import ZeroDayPanel
from omega_api import search_zeroday_exploits


class ZerodayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="zerodaytoday", description="Pesquisar exploits no 0daytoday")
    @app_commands.guild_only()
    @app_commands.describe(search="O que pesquisar (termo livre ou CVE)")
    async def send_zeroday(self, interaction, search: str):
        await interaction.response.defer(thinking=True)
        search = search.strip()

        if len(search) < 3:
            await interaction.followup.send(
                "❌ Termo muito curto (mínimo 3 caracteres)."
            )
            return

        try:
            result = await search_zeroday_exploits(search, page=1, limit=5)
        except Exception:
            result = None

        if not result:
            await interaction.followup.send(
                f"🔍 Nenhum zero-day encontrado para `{search}`."
            )
            return

        view = ZeroDayPanel(
            query=search, initial_results=result, current_page=1
        )

        msg = await interaction.followup.send(view=view)
        view.message = msg


async def setup(bot):
    await bot.add_cog(ZerodayCog(bot))