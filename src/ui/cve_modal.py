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

    def __init__(self, guild_id: int | None = None) -> None:
        self.guild_id = guild_id
        super().__init__(title="Search CVEs")

        self.score = ui.Label(
            text="CVSS Score",
            description="Filter by severity / score",
            component=ui.Select(
                custom_id="score_select",
                placeholder="Select score range",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(label="Low (0.1 - 3.9)", value="low"),
                    discord.SelectOption(label="Medium (4.0 - 6.9)", value="medium"),
                    discord.SelectOption(label="High (7.0 - 8.9)", value="high"),
                    discord.SelectOption(
                        label="Critical (9.0 - 10.0)", value="critical"
                    ),
                ],
            ),
        )

        self.year = ui.Label(
            text="Time Range",
            description="Choose publication year",
            component=ui.Select(
                custom_id="year_select",
                placeholder="Select year",
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

        self.package_name = ui.Label(
            text="Package or Term",
            description="Enter package name or keyword",
            component=ui.TextInput(
                style=discord.TextStyle.short,
                placeholder="e.g., linux, openssl, sudo...",
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
            not_found_msg = await cvecog_translate(
                interaction.guild_id,
                "modal",
                "not_found_package",
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
        err_msg = await cvecog_translate(
            interaction.guild_id, "modal", "error_generic"
        )
        if interaction.response.is_done():
            await interaction.followup.send(err_msg, ephemeral=True)
        else:
            await interaction.response.send_message(err_msg, ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)


# ==========================
# MODAL FOR ID SEARCH ONLY
# ==========================


class CVEIdSearchModal(ui.Modal):

    def __init__(self, guild_id: int | None = None) -> None:
        self.guild_id = guild_id
        super().__init__(title="Search CVE")

        self.cve_id = ui.TextInput(
            label="CVE ID",
            placeholder="e.g., CVE-2021-44228",
            style=discord.TextStyle.short,
            min_length=13,
            max_length=20,
            required=True,
        )

        self.add_item(self.cve_id)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        cve_code = self.cve_id.value.strip().upper()

        if not CVE_PATTERN.match(cve_code):
            invalid_msg = await cvecog_translate(
                interaction.guild_id, "modal", "invalid_format"
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
                "modal",
                "not_found_id",
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

        msg = await interaction.followup.send(
            view=detail_view,
            wait=True,
        )
        detail_view.message = msg

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        err_msg = await cvecog_translate(
            interaction.guild_id, "modal", "error_generic"
        )
        if interaction.response.is_done():
            await interaction.followup.send(err_msg, ephemeral=True)
        else:
            await interaction.response.send_message(err_msg, ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)