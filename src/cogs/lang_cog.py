import discord
from discord import app_commands
from discord.ext import commands

from database import lang_db
from translator import langcog_translate

LANGUAGE_CHOICES = [
    app_commands.Choice(name="Português (Brasil)", value="PTBR"),
    app_commands.Choice(name="English (US)", value="EN"),
    app_commands.Choice(name="Español", value="ES"),
]


class LanguageConfigCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    lang = app_commands.Group(
        name="language",
        description="Sets up the bot's language for this server.",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @lang.command(
        name="set",
        description="Sets the default language for this server's messages.",
    )
    @app_commands.describe(idioma="Choose the new server language.")
    @app_commands.choices(idioma=LANGUAGE_CHOICES)
    @app_commands.guild_only()
    async def definir(
        self,
        interaction: discord.Interaction,
        idioma: app_commands.Choice[str],
    ) -> None:
        await lang_db.set_language(
            guild_id=interaction.guild_id,
            language=idioma.value,
        )

        msg = await langcog_translate(
            interaction.guild_id,
            "success",
            "changed",
            nome=idioma.name,
            codigo=idioma.value,
        )

        await interaction.response.send_message(msg, ephemeral=True)

    @lang.command(
        name="current",
        description="Displays the language currently set up for the server.",
    )
    @app_commands.guild_only()
    async def atual(self, interaction: discord.Interaction) -> None:
        current_lang = await lang_db.get_language(interaction.guild_id)

        nome_idioma = next(
            (c.name for c in LANGUAGE_CHOICES if c.value == current_lang),
            current_lang,
        )

        msg = await langcog_translate(
            interaction.guild_id,
            "success",
            "current",
            nome=nome_idioma,
            codigo=current_lang,
        )

        await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LanguageConfigCog(bot))