import re
import traceback
import discord
from discord import ui

from omega_api import get_cve, search_cves_by_package
from translator import cvecog_translate

from .cve_view import CVEDetailView, CVEPanel

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)


# ==========================
# MODAL FOR PACKAGE SEARCH
# ==========================


class CVEPackageSearchModal(ui.Modal):

    def __init__(self, guild_id: int | None, texts: dict) -> None:
        self.guild_id = guild_id
        self.texts = texts
        super().__init__(title=texts["title"])

        self.score = ui.Label(
            text=texts["lbl_score"],
            description=texts["desc_score"],
            component=ui.Select(
                custom_id="score_select",
                placeholder=texts["ph_score"],
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(label=texts["opt_low"], value="low"),
                    discord.SelectOption(label=texts["opt_medium"], value="medium"),
                    discord.SelectOption(label=texts["opt_high"], value="high"),
                    discord.SelectOption(
                        label=texts["opt_critical"], value="critical"
                    ),
                ],
            ),
        )

        self.year = ui.Label(
            text=texts["lbl_year"],
            description=texts["desc_year"],
            component=ui.Select(
                custom_id="year_select",
                placeholder=texts["ph_year"],
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(label=str(y), value=str(y))
                    for y in range(2026, 2001, -1)
                ],
            ),
        )

        self.package_name = ui.Label(
            text=texts["lbl_package"],
            description=texts["desc_package"],
            component=ui.TextInput(
                style=discord.TextStyle.short,
                placeholder=texts["ph_package"],
                max_length=100,
                required=True,
            ),
        )

        self.add_item(self.score)
        self.add_item(self.year)
        self.add_item(self.package_name)

    @classmethod
    async def create(cls, guild_id: int | None = None) -> "CVEPackageSearchModal":
        """Busca as strings traduzidas e só então monta o modal.

        __init__ não pode ser async, então a tradução precisa acontecer
        antes, aqui na factory.
        """
        texts = {
            key: await cvecog_translate(guild_id, "pkg_modal", key)
            for key in (
                "title",
                "lbl_score",
                "desc_score",
                "ph_score",
                "opt_low",
                "opt_medium",
                "opt_high",
                "opt_critical",
                "lbl_year",
                "desc_year",
                "ph_year",
                "lbl_package",
                "desc_package",
                "ph_package",
            )
        }
        return cls(guild_id, texts)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        package = self.package_name.component.value
        score_range = self.score.component.values[0]
        selected_year = self.year.component.values[0]

        results = await search_cves_by_package(
            package_name=package,
            year=selected_year,
            severity=score_range,
            page=1,
            limit=5,
        )

        if not results:
            not_found_msg = await cvecog_translate(
                interaction.guild_id,
                "pkg_modal",
                "not_found",
                package=package,
                year=selected_year,
                severity=score_range,
            )
            await interaction.followup.send(
                f"❌ {not_found_msg}",
                ephemeral=True,
            )
            return

        panel_view = CVEPanel(
            guild_id=interaction.guild_id,
            package_name=package,
            year=selected_year,
            severity=score_range,
            initial_results=results,
            current_page=1,
        )
        await panel_view.init_ui()

        msg = await interaction.followup.send(
            view=panel_view,
            wait=True,
        )
        panel_view.message = msg

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        err_msg = await cvecog_translate(interaction.guild_id, "pkg_modal", "error")
        if interaction.response.is_done():
            await interaction.followup.send(err_msg, ephemeral=True)
        else:
            await interaction.response.send_message(err_msg, ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)


# ==========================
# MODAL FOR ID SEARCH ONLY
# ==========================


class CVEIdSearchModal(ui.Modal):

    def __init__(self, guild_id: int | None, texts: dict) -> None:
        self.guild_id = guild_id
        self.texts = texts
        super().__init__(title=texts["title"])

        self.cve_id = ui.TextInput(
            label=texts["lbl_id"],
            placeholder=texts["ph_id"],
            style=discord.TextStyle.short,
            min_length=13,
            max_length=20,
            required=True,
        )

        self.add_item(self.cve_id)

    @classmethod
    async def create(cls, guild_id: int | None = None) -> "CVEIdSearchModal":
        texts = {
            key: await cvecog_translate(guild_id, "id_modal", key)
            for key in ("title", "lbl_id", "ph_id")
        }
        return cls(guild_id, texts)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        cve_code = self.cve_id.value.strip().upper()

        if not CVE_PATTERN.match(cve_code):
            invalid_msg = await cvecog_translate(
                interaction.guild_id, "id_modal", "invalid_format"
            )
            await interaction.response.send_message(
                f"❌ {invalid_msg}",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        data = await get_cve(cve_code)

        if not data:
            not_found_msg = await cvecog_translate(
                interaction.guild_id,
                "id_modal",
                "not_found",
                cve_code=cve_code,
            )
            await interaction.followup.send(
                f"❌ {not_found_msg}",
                ephemeral=True,
            )
            return

        detail_view = CVEDetailView(
            cve_data=data,
            guild_id=interaction.guild_id,
        )
        await detail_view.init_ui()

        attachments = [detail_view.chart_file] if detail_view.chart_file else []

        msg = await interaction.followup.send(
            view=detail_view,
            files=attachments,
            wait=True,
        )
        detail_view.message = msg

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        err_msg = await cvecog_translate(interaction.guild_id, "id_modal", "error")
        if interaction.response.is_done():
            await interaction.followup.send(err_msg, ephemeral=True)
        else:
            await interaction.response.send_message(err_msg, ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)