import discord
from discord import app_commands
from discord.ext import commands

from database import lang_db
from omega_api import search_zeroday_exploits
from translator import load_command_translation
from ui import ZeroDayPanel


class ZerodayCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="zerodaytoday", description="Search exploits on 0daytoday"
    )
    @app_commands.guild_only()
    @app_commands.describe(search="Search query (free text or CVE)")
    async def send_zeroday(self, interaction, search):
        await interaction.response.defer(thinking=True)
        search = search.strip()

        lang = await lang_db.get_language(interaction.guild_id)

        try:
            cog_translations = await load_command_translation(
                "zerodaycog", lang, "cog"
            )
            view_translations = await load_command_translation(
                "zerodaycog", lang, "view"
            )
        except Exception:
            cog_translations = {}
            view_translations = {}

        if len(search) < 3:
            msg_short = cog_translations.get(
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
            not_found_tpl = cog_translations.get(
                "not_found",
                "🔍 No zero-day found for `{search}`.",
            )
            await interaction.followup.send(
                not_found_tpl.format(search=search)
            )
            return

        view = ZeroDayPanel(
            query=search,
            initial_results=result,
            current_page=1,
            lang=lang,
            translations=view_translations,
        )

        msg = await interaction.followup.send(view=view)
        view.message = msg


async def setup(bot):
    await bot.add_cog(ZerodayCog(bot))