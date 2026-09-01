import discord
from discord import app_commands
from discord.ext import commands

from translator import feedcog_translate
from database import feed_db 
from feeds import process_feeds_once

SEVERITY_CHOICES = [
    app_commands.Choice(name="Critical (9.0+)", value=9.0),
    app_commands.Choice(name="High (7.0+)", value=7.0),
    app_commands.Choice(name="Medium (4.0+)", value=4.0),
    app_commands.Choice(name="All (includes unknown severity)", value=0.0),
]

class FeedConfigCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    feeds = app_commands.Group(
        name="feeds",
        description="Configures vulnerability feed delivery on this server.",
        default_permissions=discord.Permissions(manage_guild=True, manage_webhooks=True),
        guild_only=True,
    )

    @feeds.command(name="register", description="Registers a channel to receive vulnerability feeds.")
    @app_commands.describe(
        channel="Channel where feeds will be sent.",
        severity="Minimum severity to be sent to this channel.",
        include_unknown="Also send items without identified severity?",
    )
    @app_commands.choices(severity=SEVERITY_CHOICES)
    @app_commands.guild_only()
    async def register(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        severity: app_commands.Choice[float],
        include_unknown: bool = True,
    ):
        try:
            avatar_bytes = await self.bot.user.display_avatar.read()
            webhook = await channel.create_webhook(
                name="Enchiridion",
                avatar=avatar_bytes,
                reason="Vulnerability feed registration via /feeds register",
            )
        except discord.Forbidden:
            message = await feedcog_translate(
                interaction.guild_id,
                "errors",
                "no_webhook_permission",
                channel=channel.mention,
            )
            await interaction.response.send_message(message, ephemeral=True)
            return
        except discord.HTTPException as error:
            message = await feedcog_translate(
                interaction.guild_id,
                "errors",
                "webhook_creation_failed",
                channel=channel.mention,
                error=error,
            )
            await interaction.response.send_message(message, ephemeral=True)
            return

        await feed_db.add_subscription(
            guild_id=interaction.guild_id,
            channel_id=channel.id,
            min_severity=severity.value,
            allow_unknown=include_unknown,
            webhook_url=webhook.url,
        )

        message = await feedcog_translate(
            interaction.guild_id,
            "success",
            "registered",
            channel=channel.mention,
            severity=severity.name,
        )
        await interaction.response.send_message(message, ephemeral=True)

    @feeds.command(name="severity", description="Changes the severity filter for an already registered channel.")
    @app_commands.describe(
        channel="Channel whose severity filter will be changed.",
        severity="New minimum severity for this channel.",
        include_unknown="Also send items without identified severity?",
    )
    @app_commands.choices(severity=SEVERITY_CHOICES)
    @app_commands.guild_only()
    async def severity(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        severity: app_commands.Choice[float],
        include_unknown: bool = True,
    ):
        subscriptions = await feed_db.list_subscriptions_for_guild(interaction.guild_id)
        if not any(sub.channel_id == channel.id for sub in subscriptions):
            message = await feedcog_translate(
                interaction.guild_id,
                "errors",
                "channel_not_registered",
                channel=channel.mention,
            )
            await interaction.response.send_message(message, ephemeral=True)
            return

        await feed_db.update_severity_filter(
            guild_id=interaction.guild_id,
            channel_id=channel.id,
            min_severity=severity.value,
            allow_unknown=include_unknown,
        )

        message = await feedcog_translate(
            interaction.guild_id,
            "success",
            "severity_updated",
            channel=channel.mention,
            severity=severity.name,
        )
        await interaction.response.send_message(message, ephemeral=True)

    @feeds.command(name="remove", description="Removes feed registration from a channel.")
    @app_commands.describe(channel="Channel that will stop receiving feeds.")
    @app_commands.guild_only()
    async def remove(self, interaction: discord.Interaction, channel: discord.TextChannel):
        subscriptions = await feed_db.list_subscriptions_for_guild(interaction.guild_id)
        subscription = next((sub for sub in subscriptions if sub.channel_id == channel.id), None)

        if subscription and subscription.webhook_url:
            try:
                webhook = discord.Webhook.from_url(subscription.webhook_url, session=self.bot.webhook_session)
                await webhook.delete(reason="Removed via /feeds remove")
            except discord.HTTPException:
                pass 

        await feed_db.remove_subscription(
            guild_id=interaction.guild_id,
            channel_id=channel.id,
        )

        message = await feedcog_translate(
            interaction.guild_id,
            "success",
            "removed",
            channel=channel.mention,
        )
        await interaction.response.send_message(message, ephemeral=True)

    @feeds.command(name="list", description="Lists the channels on this server registered to receive feeds.")
    @app_commands.guild_only()
    async def list(self, interaction: discord.Interaction):
        subscriptions = await feed_db.list_subscriptions_for_guild(interaction.guild_id)

        if not subscriptions:
            message = await feedcog_translate(interaction.guild_id, "errors", "no_channels_registered")
            await interaction.response.send_message(message, ephemeral=True)
            return

        lines = []
        text_yes = await feedcog_translate(interaction.guild_id, "ui", "yes")
        text_no = await feedcog_translate(interaction.guild_id, "ui", "no")

        for subscription in subscriptions:
            channel = interaction.guild.get_channel(subscription.channel_id)
            if channel:
                channel_name = channel.mention
            else:
                channel_name = await feedcog_translate(
                    interaction.guild_id,
                    "errors",
                    "channel_not_found",
                    channel_id=subscription.channel_id,
                )

            unknown_status = text_yes if subscription.allow_unknown else text_no
            
            line = await feedcog_translate(
                interaction.guild_id,
                "ui",
                "list_line",
                channel=channel_name,
                min_severity=subscription.min_severity,
                unknown=unknown_status,
            )
            lines.append(line)

        is_first_chunk = True
        current_chunk = ""
        for line in lines:
            candidate = f"{current_chunk}\n{line}" if current_chunk else line
            if len(candidate) > 1900:
                await self._send_chunk(interaction, current_chunk, is_first_chunk)
                is_first_chunk = False
                current_chunk = line
            else:
                current_chunk = candidate

        if current_chunk:
            await self._send_chunk(interaction, current_chunk, is_first_chunk)


async def setup(bot):
    await bot.add_cog(FeedConfigCog(bot))