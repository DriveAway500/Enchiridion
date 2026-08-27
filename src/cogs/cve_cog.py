import re
from discord import app_commands
from discord.ext import commands

from ui import CVEPanel
from omega_api import get_cve, search_cves_by_package

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)
PACKAGE_PATTERN = re.compile(r"^[a-zA-Z0-9._+-]+$")

AVAILABLE_YEARS = [2026, 2025, 2024, 2023, 2022, 2021, 2020]


class CveCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="cve", description="Pesquisar CVE ou pacote afetado")
    @app_commands.guild_only()
    @app_commands.describe(
        method="O método de pesquisa",
        search="O que pesquisar",
        year="Ano do CVE (obrigatório para pesquisa por pacote)",
    )
    @app_commands.choices(
        method=[
            app_commands.Choice(name="CVE ID", value="cve"),
            app_commands.Choice(name="Nome do pacote", value="package"),
        ],
        year=[
            app_commands.Choice(name=str(year), value=str(year))
            for year in AVAILABLE_YEARS
        ],
    )
    async def send_cve(
        self,
        interaction,
        method: app_commands.Choice[str],
        search: str,
        year: app_commands.Choice[str] = None,
    ):
        await interaction.response.defer(thinking=True)
        method_value = method.value
        search = search.strip()

        if method_value == "cve":
            if not CVE_PATTERN.match(search):
                await interaction.followup.send(
                    "❌ Use `CVE-AAAA-NNNNN` (ex: `CVE-2021-44228`)."
                )
                return
            search = search.upper()
        else:
            if not year:
                await interaction.followup.send(
                    "❌ Selecione o **ano** ao pesquisar por nome de pacote."
                )
                return
            if len(search) < 2 or not PACKAGE_PATTERN.match(search):
                await interaction.followup.send("❌ Nome de pacote inválido.")
                return

        try:
            if method_value == "cve":
                result = await get_cve(search)
                if not result:
                    await interaction.followup.send(
                        f"🔍 Nenhum resultado encontrado para `{search}`."
                    )
                    return

                text = str(result)
                if len(text) > 1900:
                    text = text[:1900] + "\n... (truncado)"
                await interaction.followup.send(f"```json\n{text}\n```")

            else:
                results = await search_cves_by_package(
                    search, year=year.value, page=1, limit=5
                )

                if not results:
                    await interaction.followup.send(
                        f"🔍 Nenhum resultado encontrado para o pacote `{search}` no ano `{year.value}`."
                    )
                    return

                view = CVEPanel(
                    package_name=search,
                    year=year.value,
                    initial_results=results,
                    current_page=1,
                )

                msg = await interaction.followup.send(view=view)
                view.message = msg

        except Exception as e:
            print(e)
            await interaction.followup.send(
                "❌ Ocorreu um erro ao consultar os dados da API."
            )


async def setup(bot):
    await bot.add_cog(CveCog(bot))
