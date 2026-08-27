from discord import app_commands
from discord.ext import commands

from omega_api import search_zeroday_exploits


class ZerodayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="zeroday", description="Pesquisar exploits zero-day")
    @app_commands.guild_only()
    @app_commands.describe(search="O que pesquisar")
    async def send_zeroday(self, interaction, search: str):
        await interaction.response.defer(thinking=True)
        search = search.strip()

        if len(search) < 3:
            await interaction.followup.send("❌ Termo muito curto (mínimo 3 caracteres).")
            return

        try:
            result = await search_zeroday_exploits(search, limit=10)
        except Exception:
            result = None

        if not result:
            await interaction.followup.send(f"🔍 Nenhum zero-day encontrado para `{search}`.")
            return

        text = str(result)
        if len(text) > 1900:
            text = text[:1900] + "\n... (truncado)"
        await interaction.followup.send(f"```json\n{text}\n```")


async def setup(bot):
    await bot.add_cog(ZerodayCog(bot))