import discord
from discord import app_commands
from discord.ext import commands

# Opções de severidade mostradas no slash command.
# O valor numérico é o "min_severity" salvo na FeedDatabase e usado
# pelo feed_task para filtrar o que é enviado em cada canal.
SEVERITY_CHOICES = [
    app_commands.Choice(name="Crítico (9.0+)", value=9.0),
    app_commands.Choice(name="Alto (7.0+)", value=7.0),
    app_commands.Choice(name="Médio (4.0+)", value=4.0),
    app_commands.Choice(name="Baixo (qualquer severidade conhecida)", value=0.1),
    app_commands.Choice(name="Tudo (inclui severidade desconhecida)", value=0.0),
]


class FeedConfigCog(commands.Cog):
    """Comandos para configurar em quais canais os feeds de vulnerabilidades são enviados."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    feeds = app_commands.Group(
        name="feeds",
        description="Configura o envio de feeds de vulnerabilidades neste servidor.",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @feeds.command(name="registrar", description="Registra um canal para receber os feeds de vulnerabilidades.")
    @app_commands.describe(
        canal="Canal onde os feeds serão enviados.",
        severidade="Severidade mínima que será enviada para este canal.",
        incluir_desconhecidas="Enviar também itens sem severidade identificada?",
        canal_crosspost="Canal opcional para republicar automaticamente vulnerabilidades críticas.",
    )
    @app_commands.choices(severidade=SEVERITY_CHOICES)
    async def registrar(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        severidade: app_commands.Choice[float],
        incluir_desconhecidas: bool = True,
        canal_crosspost: discord.TextChannel | None = None,
    ):
        await self.bot.database.add_subscription(
            guild_id=interaction.guild_id,
            channel_id=canal.id,
            min_severity=severidade.value,
            allow_unknown=incluir_desconhecidas,
            crosspost_channel_id=canal_crosspost.id if canal_crosspost else None,
        )

        await interaction.response.send_message(
            f"✅ Feeds registrados em {canal.mention} com severidade mínima **{severidade.name}**."
            + (f"\nCrosspost habilitado em {canal_crosspost.mention} para itens críticos."
               if canal_crosspost else ""),
            ephemeral=True,
        )

    @feeds.command(name="severidade", description="Altera o filtro de severidade de um canal já registrado.")
    @app_commands.describe(
        canal="Canal cuja severidade será alterada.",
        severidade="Nova severidade mínima para este canal.",
        incluir_desconhecidas="Enviar também itens sem severidade identificada?",
    )
    @app_commands.choices(severidade=SEVERITY_CHOICES)
    async def severidade(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        severidade: app_commands.Choice[float],
        incluir_desconhecidas: bool = True,
    ):
        subs = await self.bot.database.list_subscriptions_for_guild(interaction.guild_id)
        if not any(s.channel_id == canal.id for s in subs):
            await interaction.response.send_message(
                f"⚠️ {canal.mention} não está registrado. Use `/feeds registrar` primeiro.",
                ephemeral=True,
            )
            return

        await self.bot.database.update_severity_filter(
            guild_id=interaction.guild_id,
            channel_id=canal.id,
            min_severity=severidade.value,
            allow_unknown=incluir_desconhecidas,
        )

        await interaction.response.send_message(
            f"🔧 Filtro de {canal.mention} atualizado para **{severidade.name}**.",
            ephemeral=True,
        )

    @feeds.command(name="remover", description="Remove o registro de feeds de um canal.")
    @app_commands.describe(canal="Canal que deixará de receber feeds.")
    async def remover(self, interaction: discord.Interaction, canal: discord.TextChannel):
        await self.bot.database.remove_subscription(
            guild_id=interaction.guild_id,
            channel_id=canal.id,
        )
        await interaction.response.send_message(
            f"🗑️ {canal.mention} removido dos feeds de vulnerabilidades.",
            ephemeral=True,
        )

    @feeds.command(name="listar", description="Lista os canais deste servidor registrados para receber feeds.")
    async def listar(self, interaction: discord.Interaction):
        subs = await self.bot.database.list_subscriptions_for_guild(interaction.guild_id)

        if not subs:
            await interaction.response.send_message(
                "Nenhum canal registrado neste servidor ainda.", ephemeral=True
            )
            return

        linhas = []
        for sub in subs:
            canal = interaction.guild.get_channel(sub.channel_id)
            nome_canal = canal.mention if canal else f"`{sub.channel_id}` (canal não encontrado)"
            desconhecidas = "sim" if sub.allow_unknown else "não"
            linha = f"{nome_canal} — severidade mínima **{sub.min_severity}** (inclui desconhecidas: {desconhecidas})"
            if sub.crosspost_channel_id:
                crosspost_canal = interaction.guild.get_channel(sub.crosspost_channel_id)
                nome_crosspost = crosspost_canal.mention if crosspost_canal else f"`{sub.crosspost_channel_id}`"
                linha += f" — crosspost em {nome_crosspost}"
            linhas.append(linha)

        await interaction.response.send_message("\n".join(linhas), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(FeedConfigCog(bot))