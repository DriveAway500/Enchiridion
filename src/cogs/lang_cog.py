import discord
from discord import app_commands
from discord.ext import commands

from database import lang_db
from translator import load_command_translation

LANGUAGE_CHOICES = [
    app_commands.Choice(name="Português (Brasil)", value="PTBR"),
    app_commands.Choice(name="English (US)", value="EN"),
    app_commands.Choice(name="Español", value="ES"),
]


class LanguageConfigCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    lang = app_commands.Group(
        name="idioma",
        description="Configura o idioma do bot neste servidor.",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @lang.command(
        name="definir",
        description="Define o idioma padrão para as mensagens deste servidor.",
    )
    @app_commands.describe(idioma="Escolha o novo idioma do servidor.")
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

        translation_data = await load_command_translation(
            "langcog", idioma.value, "when_change"
        )
        base_message = translation_data.get(
            "response", "Server language changed to: "
        )

        await interaction.response.send_message(
            f"🌐 {base_message} **{idioma.name}** (`{idioma.value}`).",
            ephemeral=True,
        )

    @lang.command(
        name="atual",
        description="Exibe o idioma atualmente configurado no servidor.",
    )
    @app_commands.guild_only()
    async def atual(self, interaction: discord.Interaction) -> None:
        current_lang = await lang_db.get_language(interaction.guild_id)

        nome_idioma = next(
            (c.name for c in LANGUAGE_CHOICES if c.value == current_lang),
            current_lang,
        )

        translation_data = await load_command_translation(
            "langcog", current_lang, "when_check"
        )
        base_message = translation_data.get(
            "response", "Current server language is: "
        )

        await interaction.response.send_message(
            f"🌐 {base_message} **{nome_idioma}** (`{current_lang}`).",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LanguageConfigCog(bot))