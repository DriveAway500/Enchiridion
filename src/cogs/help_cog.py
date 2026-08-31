import discord
from discord import app_commands
from discord.ext import commands

from database import lang_db
from translator import load_command_translation


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Exibe informações de ajuda sobre as ferramentas de pesquisa.",
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
        lang = "EN"
        if interaction.guild_id:
            lang = await lang_db.get_language(interaction.guild_id, default="EN")

        data = await load_command_translation("help", lang)

        tool_info = data.get(opcao.value)

        if not tool_info:
            error_message = (
                "No information found for the selected option."
                if lang == "EN"
                else "Nenhuma informação encontrada para a opção selecionada."
            )
            await interaction.response.send_message(error_message, ephemeral=True)
            return

        description = tool_info["documentation"]

        embed = discord.Embed(
            title=f"/{opcao.name}",
            description=description,
            color=discord.Color.blue(),
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))