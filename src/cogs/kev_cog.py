import discord
from discord import app_commands
from discord.ext import commands

from ui import KevPanel, kev_parser

class KevCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="active_cve",
        description="Search CVE currently being explored",
    )
    @app_commands.guild_only()
    @app_commands.describe(query="Keyword to search (e.g. Windows, Microsoft, Chrome)")
    async def search_kev(
        self,
        interaction: discord.Interaction,
        query: str,
    ) -> None:
        await interaction.response.defer()

        query = query.strip()
        if not query:
            await interaction.followup.send(
                "❌ Please provide a search term.",
                ephemeral=True,
            )
            return

        results = await kev_parser.parse_search(query, page=1)
        if not results:
            await interaction.followup.send(
                f"❌ No KEV entries found for `{query}`.",
                ephemeral=True,
            )
            return

        panel = KevPanel(query=query, initial_results=results)
        await panel.init_ui()
        panel.message = await interaction.followup.send(view=panel, wait=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(KevCog(bot))
    
