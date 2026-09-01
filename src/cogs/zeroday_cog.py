import discord
from discord import app_commands
from discord.ext import commands

from database import lang_db
from omega_api import search_zeroday_exploits
from translator import load_command_translation
from ui import ZeroDayPanel


class ZerodayCog(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    @app_commands.command(
        name="zerodaytoday", description="Search exploits on 0daytoday"
    )
    @app_commands.guild_only()
    @app_commands.describe(search="Search query (free text or CVE)")
    async def send_zeroday(
        self, interaction: discord.Interaction, search: str
    ) -> None:
        await interaction.response.defer(thinking=True)
        search: str = search.strip()

        lang: str = await lang_db.get_language(interaction.guild_id)

        try:
            cog_translations: dict = await load_command_translation(
                "zerodaycog", lang, "cog"
            )
            view_translations: dict = await load_command_translation(
                "zerodaycog", lang, "view"
            )
        except Exception:
            cog_translations: dict = {}
            view_translations: dict = {}

        if len(search) < 3:
            msg_short: str = cog_translations.get(
                "err_too_short",
                "❌ Search query too short (minimum 3 characters).",
            )
            await interaction.followup.send(msg_short)
            return

        try:
            result = await search_zeroday_exploits(search, page=1, limit=5)
        except Exception:
            result = None

        if not result:
            not_found_tpl: str = cog_translations.get(
                "not_found",
                "🔍 No zero-day found for `{search}`.",
            )
            await interaction.followup.send(
                not_found_tpl.format(search=search)
            )
            return

        view: ZeroDayPanel = ZeroDayPanel(
            query=search,
            initial_results=result,
            current_page=1,
            lang=lang,
            translations=view_translations,
        )

        msg: discord.WebhookMessage = await interaction.followup.send(view=view)
        view.message = msg


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ZerodayCog(bot))