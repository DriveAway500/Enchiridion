import discord
from discord import app_commands
from discord.ext import commands

from database import feed_db 
from feeds import process_feeds_once

SEVERITY_CHOICES = [
    app_commands.Choice(name="Crítico (9.0+)", value=9.0),
    app_commands.Choice(name="Alto (7.0+)", value=7.0),
    app_commands.Choice(name="Médio (4.0+)", value=4.0),
    app_commands.Choice(name="Tudo (inclui severidade desconhecida)", value=0.0),
]


class FeedConfigCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    feeds = app_commands.Group(
        name="feeds",
        description="Configura o envio de feeds de vulnerabilidades neste servidor.",
        default_permissions=discord.Permissions(manage_guild=True, manage_webhooks=True),
        guild_only=True,
    )

    @feeds.command(name="registrar", description="Registra um canal para receber os feeds de vulnerabilidades.")
    @app_commands.describe(
        canal="Canal onde os feeds serão enviados.",
        severidade="Severidade mínima que será enviada para este canal.",
        incluir_desconhecidas="Enviar também itens sem severidade identificada?",
    )
    @app_commands.choices(severidade=SEVERITY_CHOICES)
    @app_commands.guild_only()
    async def registrar(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        severidade: app_commands.Choice[float],
        incluir_desconhecidas: bool = True,
    ):
        try:
            avatar_bytes = await self.bot.user.display_avatar.read()
            webhook = await canal.create_webhook(
                name="Enchiridion",
                avatar=avatar_bytes,
                reason="Registro de feed de vulnerabilidades via /feeds registrar",
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"⚠️ Não tenho permissão de **Gerenciar Webhooks** em {canal.mention}. "
                "Dê essa permissão ao bot nesse canal e tente novamente.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"⚠️ Não consegui criar o webhook em {canal.mention}: {e}",
                ephemeral=True,
            )
            return

        await feed_db.add_subscription(
            guild_id=interaction.guild_id,
            channel_id=canal.id,
            min_severity=severidade.value,
            allow_unknown=incluir_desconhecidas,
            webhook_url=webhook.url,
        )

        await interaction.response.send_message(
            f"✅ Feeds registrados em {canal.mention} com severidade mínima **{severidade.name}**.",
            ephemeral=True,
        )

    @feeds.command(name="severidade", description="Altera o filtro de severidade de um canal já registrado.")
    @app_commands.describe(
        canal="Canal cuja severidade será alterada.",
        severidade="Nova severidade mínima para este canal.",
        incluir_desconhecidas="Enviar também itens sem severidade identificada?",
    )
    @app_commands.choices(severidade=SEVERITY_CHOICES)
    @app_commands.guild_only()
    async def severidade(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        severidade: app_commands.Choice[float],
        incluir_desconhecidas: bool = True,
    ):
        subs = await feed_db.list_subscriptions_for_guild(interaction.guild_id)
        if not any(s.channel_id == canal.id for s in subs):
            await interaction.response.send_message(
                f"⚠️ {canal.mention} não está registrado. Use `/feeds registrar` primeiro.",
                ephemeral=True,
            )
            return

        await feed_db.update_severity_filter(
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
    @app_commands.guild_only()
    async def remover(self, interaction: discord.Interaction, canal: discord.TextChannel):
        subs = await feed_db.list_subscriptions_for_guild(interaction.guild_id)
        sub = next((s for s in subs if s.channel_id == canal.id), None)

        if sub and sub.webhook_url:
            try:
                webhook = discord.Webhook.from_url(sub.webhook_url, session=self.bot.webhook_session)
                await webhook.delete(reason="Removido via /feeds remover")
            except discord.HTTPException:
                pass  # Já não existe mais - sem problema.

        await feed_db.remove_subscription(
            guild_id=interaction.guild_id,
            channel_id=canal.id,
        )
        await interaction.response.send_message(
            f"🗑️ {canal.mention} removido dos feeds de vulnerabilidades.",
            ephemeral=True,
        )

    @feeds.command(name="listar", description="Lista os canais deste servidor registrados para receber feeds.")
    @app_commands.guild_only()
    async def listar(self, interaction: discord.Interaction):
        subs = await feed_db.list_subscriptions_for_guild(interaction.guild_id)

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
            linhas.append(linha)

        primeiro_bloco = True
        bloco_atual = ""
        for linha in linhas:
            candidato = f"{bloco_atual}\n{linha}" if bloco_atual else linha
            if len(candidato) > 1900:
                await self._enviar_bloco(interaction, bloco_atual, primeiro_bloco)
                primeiro_bloco = False
                bloco_atual = linha
            else:
                bloco_atual = candidato

        if bloco_atual:
            await self._enviar_bloco(interaction, bloco_atual, primeiro_bloco)


async def setup(bot):
    await bot.add_cog(FeedConfigCog(bot))