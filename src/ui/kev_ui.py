import discord
from discord import ui

from parser import KevParser, KevNew

PAGE_SIZE = 5

# Global parser instance (loads the SHA-256 state file once)
kev_parser = KevParser()


class KevView(ui.LayoutView):
    def __init__(self, kev: KevNew, colour: discord.Colour | int | None = None):
        super().__init__(timeout=None)

        cwes = ", ".join(kev.cwes) if isinstance(kev.cwes, list) else kev.cwes

        container = ui.Container(
            ui.TextDisplay(f"## {kev.cve_id}\n**{kev.vulnerability_name}**"),
            ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            ui.TextDisplay(
                f"**Vendor:** {kev.vendor_project} **|** "
                f"**Product:** {kev.product} **|** "
                f"**CWE:** {cwes}"
            ),
            ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            ui.TextDisplay(f"**Description**\n{kev.short_description[:1000]}"),
            ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small),
            ui.TextDisplay(f"**Required Action**\n{kev.required_action[:1000]}"),
            ui.Separator(visible=True, spacing=discord.SeparatorSpacing.large),
            ui.TextDisplay(
                f"**Add:** {kev.date_added} **|** "
                f"**Deadline:** {kev.due_date} **|** "
                f"**Ransomware:** {kev.known_ransomware}"
            ),
            accent_colour=colour,
        )

        self.add_item(container)


def kev_colour(kev: KevNew) -> discord.Colour | None:
    return discord.Colour.red() if kev.known_ransomware == "Known" else None


class KevButton(ui.Button):
    def __init__(self, cve_id: str, label_text: str = "View Details") -> None:
        super().__init__(
            label=label_text,
            style=discord.ButtonStyle.secondary,
            custom_id=f"kev_view_{cve_id}",
        )
        self.cve_id = cve_id

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        kev = await kev_parser.parse_entry(self.cve_id)
        if not kev:
            await interaction.followup.send(
                f"❌ Could not load details for `{self.cve_id}`.",
                ephemeral=True,
            )
            return

        detail_view = KevView(kev, colour=kev_colour(kev))

        # Reuse the same detail message if one is already open
        if getattr(self.view, "detail_message", None):
            try:
                await self.view.detail_message.edit(view=detail_view)
                return
            except (discord.NotFound, discord.HTTPException):
                self.view.detail_message = None

        msg = await interaction.followup.send(view=detail_view, wait=True)
        if hasattr(self.view, "detail_message"):
            self.view.detail_message = msg


class KevPanel(ui.LayoutView):
    def __init__(
        self,
        query: str,
        initial_results: list[KevNew],
        current_page: int = 1,
    ) -> None:
        super().__init__(timeout=180)
        self.query = query
        self.current_page = current_page
        self.initial_results = initial_results
        self.message = None
        self.detail_message = None

    async def init_ui(self) -> None:
        await self.build_ui(self.initial_results)

    async def on_timeout(self) -> None:
        def disable_all(items) -> None:
            for item in items:
                if hasattr(item, "disabled"):
                    item.disabled = True
                if hasattr(item, "children"):
                    disable_all(item.children)

        disable_all(self.children)

        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: ui.Item,
    ) -> None:
        err_msg = "❌ An error occurred while updating the results."
        if interaction.response.is_done():
            await interaction.followup.send(err_msg, ephemeral=True)
        else:
            await interaction.response.send_message(err_msg, ephemeral=True)

    async def build_ui(self, results: list[KevNew]) -> None:
        self.clear_items()

        for kev in results:
            desc = kev.short_description
            container = ui.Container(
                ui.TextDisplay(
                    f"**{kev.cve_id}** — {kev.vendor_project} {kev.product}"
                ),
                ui.TextDisplay(
                    f"**Added:** `{kev.date_added}` **|** "
                    f"**Ransomware:** `{kev.known_ransomware}`\n"
                    f"**Description:** {desc[:150]}{'...' if len(desc) > 150 else ''}"
                ),
                accent_colour=kev_colour(kev),
            )

            btn_row = ui.ActionRow()
            btn_row.add_item(KevButton(cve_id=kev.cve_id))
            container.add_item(btn_row)

            self.add_item(container)

        has_more_pages = len(results) == PAGE_SIZE
        self.add_pagination_controls(has_more_pages=has_more_pages)

    def add_pagination_controls(self, has_more_pages: bool) -> None:
        nav_row = ui.ActionRow()

        prev_button = ui.Button(
            label="Previous",
            style=discord.ButtonStyle.primary,
            disabled=self.current_page <= 1,
        )
        prev_button.callback = self.prev_page
        nav_row.add_item(prev_button)

        nav_row.add_item(
            ui.Button(
                label=f"Page {self.current_page}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
            )
        )

        next_button = ui.Button(
            label="Next",
            style=discord.ButtonStyle.primary,
            disabled=not has_more_pages,
        )
        next_button.callback = self.next_page
        nav_row.add_item(next_button)

        self.add_item(nav_row)

    async def prev_page(self, interaction: discord.Interaction) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            await self.update_page(interaction)

    async def next_page(self, interaction: discord.Interaction) -> None:
        self.current_page += 1
        await self.update_page(interaction)

    async def update_page(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        results = await kev_parser.parse_search(self.query, page=self.current_page)

        if not results:
            if self.current_page > 1:
                self.current_page -= 1
            return

        await self.build_ui(results)
        await interaction.edit_original_response(view=self)