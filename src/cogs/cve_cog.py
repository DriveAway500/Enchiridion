import re
from discord import app_commands
from discord.ext import commands

from omega_api import get_cve, search_cves_by_package

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)
PACKAGE_PATTERN = re.compile(r"^[a-zA-Z0-9._+-]+$")


class CveCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="cve", description="Pesquisar CVE ou pacote afetado")
    @app_commands.guild_only()
    @app_commands.describe(method="O método de pesquisa", search="O que pesquisar")
    @app_commands.choices(method=[
        app_commands.Choice(name="CVE ID", value="cve"),
        app_commands.Choice(name="Nome do pacote", value="package"),
    ])
    async def send_cve(self, interaction, method: app_commands.Choice[str], search: str):
        await interaction.response.defer(thinking=True)
        method_value = method.value
        search = search.strip()

        if method_value == "cve":
            if not CVE_PATTERN.match(search):
                await interaction.followup.send("❌ Use `CVE-AAAA-NNNNN` (ex: `CVE-2021-44228`).")
                return
            search = search.upper()
        else:
            if len(search) < 2 or not PACKAGE_PATTERN.match(search):
                await interaction.followup.send("❌ Nome de pacote inválido.")
                return

        try:
            if method_value == "cve":
                result = await get_cve(search)
            else:
                result = await search_cves_by_package(search, limit=10)
        except Exception:
            result = None

        if not result:
            await interaction.followup.send(f"🔍 Nenhum resultado encontrado para `{search}`.")
            return

        text = str(result)
        if len(text) > 1900:
            text = text[:1900] + "\n... (truncado)"
        await interaction.followup.send(f"```json\n{text}\n```")


async def setup(bot):
    await bot.add_cog(CveCog(bot))
