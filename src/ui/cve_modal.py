import re
import traceback
import discord
from discord import ui

from omega_api import get_cve, search_cves_by_package
from translator import load_command_translation

from .cve_view import CVEDetailView, CVEPanel

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)


# ==========================
# MODAL FOR PACKAGE SEARCH
# ==========================


class CVEPackageSearchModal(ui.Modal):

    def __init__(
        self, lang: str = "EN", translations: dict = None
    ) -> None:
        self.lang = lang
        self.translations = translations or {}

        modal_title = self.translations.get("title", "Search CVEs")
        super().__init__(title=modal_title)

        lbl_score = self.translations.get("lbl_score", "CVSS Score")
        desc_score = self.translations.get(
            "desc_score", "Filter by severity / score"
        )
        ph_score = self.translations.get("ph_score", "Select score range")

        opt_low = self.translations.get("opt_low", "Low (0.1 - 3.9)")
        opt_medium = self.translations.get("opt_medium", "Medium (4.0 - 6.9)")
        opt_high = self.translations.get("opt_high", "High (7.0 - 8.9)")
        opt_critical = self.translations.get(
            "opt_critical", "Critical (9.0 - 10.0)"
        )

        self.score = ui.Label(
            text=lbl_score,
            description=desc_score,
            component=ui.Select(
                custom_id="score_select",
                placeholder=ph_score,
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(label=opt_low, value="low"),
                    discord.SelectOption(label=opt_medium, value="medium"),
                    discord.SelectOption(label=opt_high, value="high"),
                    discord.SelectOption(
                        label=opt_critical, value="critical"
                    ),
                ],
            ),
        )

        lbl_year = self.translations.get("lbl_year", "Time Range")
        desc_year = self.translations.get(
            "desc_year", "Choose publication year"
        )
        ph_year = self.translations.get("ph_year", "Select year")

        self.year = ui.Label(
            text=lbl_year,
            description=desc_year,
            component=ui.Select(
                custom_id="year_select",
                placeholder=ph_year,
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(
                        label=str(y), value=str(y)
                    )
                    for y in range(2026, 2001, -1)
                ],
            ),
        )

        lbl_package = self.translations.get("lbl_package", "Package or Term")
        desc_package = self.translations.get(
            "desc_package", "Enter package name or keyword"
        )
        ph_package = self.translations.get(
            "ph_package", "e.g., linux, openssl, sudo..."
        )

        self.package_name = ui.Label(
            text=lbl_package,
            description=desc_package,
            component=ui.TextInput(
                style=discord.TextStyle.short,
                placeholder=ph_package,
                max_length=100,
                required=True,
            ),
        )

        self.add_item(self.score)
        self.add_item(self.year)
        self.add_item(self.package_name)

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
            not_found_tpl = self.translations.get(
                "not_found",
                "No CVE found for package `{package}` in {year} with severity `{severity}`.",
            )
            msg_text = not_found_tpl.format(
                package=package, year=selected_year, severity=score_range
            )
            await interaction.followup.send(
                f"❌ {msg_text}",
                ephemeral=True,
            )
            return

        try:
            view_translations = await load_command_translation(
                "cvecog", self.lang, "panel_view"
            )
        except Exception:
            view_translations = {}

        panel_view = CVEPanel(
            package_name=package,
            year=selected_year,
            severity=score_range,
            initial_results=results,
            current_page=1,
            lang=self.lang,
            translations=view_translations,
        )

        msg = await interaction.followup.send(
            view=panel_view,
            wait=True,
        )
        panel_view.message = msg

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        err_msg = self.translations.get(
            "error", "Something went wrong with the query!"
        )
        await interaction.response.send_message(err_msg, ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)


# ==========================
# MODAL FOR ID SEARCH ONLY
# ==========================


class CVEIdSearchModal(ui.Modal):

    def __init__(
        self, lang: str = "EN", translations: dict = None
    ) -> None:
        self.lang = lang
        self.translations = translations or {}

        modal_title = self.translations.get("title", "Search CVE")
        super().__init__(title=modal_title)

        lbl_id = self.translations.get("lbl_id", "CVE ID")
        ph_id = self.translations.get("ph_id", "e.g., CVE-2021-44228")

        self.cve_id = ui.TextInput(
            label=lbl_id,
            placeholder=ph_id,
            style=discord.TextStyle.short,
            min_length=13,
            max_length=20,
            required=True,
        )

        self.add_item(self.cve_id)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        cve_code = self.cve_id.value.strip().upper()

        if not CVE_PATTERN.match(cve_code):
            invalid_msg = self.translations.get(
                "invalid_format",
                "Invalid CVE format! Use the format `CVE-YYYY-NNNN` (e.g., `CVE-2021-44228`).",
            )
            await interaction.response.send_message(
                f"❌ {invalid_msg}",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        data = await get_cve(cve_code)

        if not data:
            not_found_tpl = self.translations.get(
                "not_found", "No record found for CVE `{cve_code}`."
            )
            msg_text = not_found_tpl.format(cve_code=cve_code)
            await interaction.followup.send(
                f"❌ {msg_text}",
                ephemeral=True,
            )
            return

        try:
            view_translations = await load_command_translation(
                "cvecog", self.lang, "detail_view"
            )
        except Exception:
            view_translations = {}

        detail_view = CVEDetailView(
            cve_data=data,
            lang=self.lang,
            translations=view_translations,
        )

        msg = await interaction.followup.send(
            view=detail_view,
            wait=True,
        )
        detail_view.message = msg

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        err_msg = self.translations.get(
            "error", "Something went wrong with the query!"
        )
        await interaction.response.send_message(err_msg, ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)