import discord
from discord import app_commands
from discord.ext import commands

from database import lang_db

LANGUAGE_CHOICES = [
    app_commands.Choice(name="Português (Brasil)", value="pt_BR"),
    app_commands.Choice(name="English (US)", value="en_US"),
    app_commands.Choice(name="Español", value="es_ES"),
]


class LanguageConfigCog(commands.Cog):
    """Comandos para configurar o idioma do bot no servidor."""

    def __init__(self, bot):
        self.bot = bot

    lang = app_commands.Group(
        name="idioma",
        description="Configura o idioma do bot neste servidor.",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @lang.command(name="definir", description="Define o idioma padrão para as mensagens deste servidor.")
    @app_commands.describe(idioma="Escolha o novo idioma do servidor.")
    @app_commands.choices(idioma=LANGUAGE_CHOICES)
    @app_commands.guild_only()
    async def definir(
        self,
        interaction: discord.Interaction,
        idioma: app_commands.Choice[str],
    ):
        await lang_db.set_language(
            guild_id=interaction.guild_id,
            language=idioma.value,
        )

        await interaction.response.send_message(
            f"🌐 Idioma do servidor alterado para **{idioma.name}** (`{idioma.value}`).",
            ephemeral=True,
        )

    @lang.command(name="atual", description="Exibe o idioma atualmente configurado no servidor.")
    @app_commands.guild_only()
    async def atual(self, interaction: discord.Interaction):
        current_lang = await lang_db.get_language(interaction.guild_id)

        # Mapeia a string para o nome amigável da escolha
        nome_idioma = next(
            (c.name for c in LANGUAGE_CHOICES if c.value == current_lang),
            current_lang,
        )

        await interaction.response.send_message(
            f"🌐 O idioma atual deste servidor é **{nome_idioma}** (`{current_lang}`).",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(LanguageConfigCog(bot))