import discord
from discord import app_commands
from discord.ext import commands

from translations import helpcog_translate


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Displays help information about the search tools.",
    )
    @app_commands.guild_only()
    @app_commands.choices(
        opcao=[
            app_commands.Choice(name="exploitdb", value="exploitdb"),
            app_commands.Choice(name="cve", value="cve"),
            app_commands.Choice(name="zerodaytoday", value="zerodaytoday"),
        ]
    )
    async def help(self, interaction: discord.Interaction, opcao: app_commands.Choice[str]):
        try:
            description = await helpcog_translate(interaction.guild_id, "docs", opcao.value)
        except (KeyError, TypeError):
            error_message = await helpcog_translate(interaction.guild_id, "errors", "not_found")
            await interaction.response.send_message(error_message, ephemeral=True)
            return

        embed = discord.Embed(
            title=f"/{opcao.name}",
            description=description,
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))