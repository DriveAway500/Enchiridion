from discord import app_commands
from discord.ext import commands

from ui import CVEPackageSearchModal, CVEIdSearchModal


class CveCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="cve", description="Search by CVE or affected package")
    @app_commands.guild_only()
    @app_commands.describe(method="Search method")
    @app_commands.choices(
        method=[
            app_commands.Choice(name="CVE ID", value="cve"),
            app_commands.Choice(name="Package Name", value="package"),
        ]
    )
    async def send_cve(
        self,
        interaction,
        method: app_commands.Choice[str],
    ):
        if method.value == "cve":
            modal = await CVEIdSearchModal.create(interaction.guild_id)
        else:
            modal = await CVEPackageSearchModal.create(interaction.guild_id)

        await interaction.response.send_modal(modal)


async def setup(bot):
    await bot.add_cog(CveCog(bot))
