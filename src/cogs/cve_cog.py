from discord import app_commands
from discord.ext import commands

from ui import CVEPackageSearchModal, CVEIdSearchModal


class CveCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="cve", description="Pesquisar CVE ou pacote afetado")
    @app_commands.guild_only()
    @app_commands.describe(method="O método de pesquisa")
    @app_commands.choices(
        method=[
            app_commands.Choice(name="CVE ID", value="cve"),
            app_commands.Choice(name="Nome do pacote", value="package"),
        ]
    )
    async def send_cve(
        self,
        interaction,
        method: app_commands.Choice[str],
    ):
        if method.value == "cve":
            await interaction.response.send_modal(CVEIdSearchModal())
        else:
            await interaction.response.send_modal(CVEPackageSearchModal())


async def setup(bot):
    await bot.add_cog(CveCog(bot))
