import io
import discord
from discord import ui

from omega_api import get_cve, search_cves_by_package
from translator import cvecog_translate
# Assuming CVSSRadarChartGenerator is saved in chart_generator.py
from graph import CVSSRadarChartGenerator

PAGE_SIZE = 5

# Global chart generator instance to reuse worker processes efficiently
chart_generator = CVSSRadarChartGenerator()


class CVEDetailView(ui.LayoutView):

    def __init__(
        self,
        cve_data: dict,
        chart_file: discord.File | None = None,
        guild_id: int | None = None,
    ) -> None:
        super().__init__(timeout=180)
        self.cve_data = cve_data
        self.chart_file = chart_file
        self.guild_id = guild_id
        self.message = None

    async def init_ui(self) -> None:
        await self.build_ui()

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

    async def build_ui(self) -> None:
        self.clear_items()
        data = self.cve_data

        cve_id = data.get("id", "N/A")
        status = data.get("vulnStatus", "N/A")
        published = data.get("published", "N/A").split("T")[0]
        last_modified = data.get("lastModified", "N/A").split("T")[0]

        descriptions = data.get("descriptions", [])
        no_desc_text = await cvecog_translate(
            self.guild_id, "detail_view", "no_description"
        )
        desc_text = next(
            (d["value"] for d in descriptions if d.get("lang") == "en"),
            no_desc_text,
        )

        metrics = data.get("metrics", {})
        score_info = "N/A"
        vector_str = "N/A"

        if metrics.get("cvssMetricV40"):
            cvss = metrics["cvssMetricV40"][0].get("cvssData", {})
            score_info = f"`{cvss.get('baseScore', 'N/A')}` (**{cvss.get('baseSeverity', 'N/A')}** - CVSS v4.0)"
            vector_str = cvss.get("vectorString", "N/A")
        elif metrics.get("cvssMetricV31"):
            cvss = metrics["cvssMetricV31"][0].get("cvssData", {})
            score_info = f"`{cvss.get('baseScore', 'N/A')}` (**{cvss.get('baseSeverity', 'N/A')}** - CVSS v3.1)"
            vector_str = cvss.get("vectorString", "N/A")

        container = ui.Container()

        title_text = await cvecog_translate(
            self.guild_id, "detail_view", "details_title", cve_id=cve_id
        )
        container.add_item(ui.TextDisplay(title_text))

        # Add the radar chart attachment to Media Gallery if available
        if self.chart_file:
            media_gallery = ui.MediaGallery(
                discord.MediaGalleryItem(self.chart_file)
            )
            container.add_item(media_gallery)

        lbl_status = await cvecog_translate(self.guild_id, "detail_view", "status")
        lbl_published = await cvecog_translate(
            self.guild_id, "detail_view", "published"
        )
        lbl_updated = await cvecog_translate(self.guild_id, "detail_view", "updated")
        lbl_score = await cvecog_translate(self.guild_id, "detail_view", "score")
        lbl_vector = await cvecog_translate(self.guild_id, "detail_view", "vector")

        info_text = (
            f"**{lbl_status}:** `{status}`\n"
            f"**{lbl_published}:** `{published}` | **{lbl_updated}:** `{last_modified}`\n"
            f"**{lbl_score}:** {score_info}\n"
            f"**{lbl_vector}:** `{vector_str}`"
        )
        container.add_item(ui.TextDisplay(info_text))

        lbl_desc = await cvecog_translate(
            self.guild_id, "detail_view", "description"
        )
        container.add_item(ui.TextDisplay(f"**{lbl_desc}:**\n{desc_text}"))

        references = data.get("references", [])
        if references:
            btn_row = ui.ActionRow()

            for idx, ref in enumerate(references[:3], start=1):
                url = ref.get("url")
                if url:
                    if len(references) > 1:
                        label_str = await cvecog_translate(
                            self.guild_id, "detail_view", "ref_multiple", idx=idx
                        )
                    else:
                        label_str = await cvecog_translate(
                            self.guild_id, "detail_view", "ref_single"
                        )

                    btn_row.add_item(
                        ui.Button(
                            label=label_str,
                            style=discord.ButtonStyle.link,
                            url=url,
                        )
                    )
            container.add_item(btn_row)

        self.add_item(container)


class CVEButton(ui.Button):

    def __init__(
        self,
        cve_id: str,
        label_text: str = "View Details",
        guild_id: int | None = None,
    ) -> None:
        super().__init__(
            label=label_text,
            style=discord.ButtonStyle.secondary,
            custom_id=f"cve_view_{cve_id}",
        )
        self.cve_id = cve_id
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        data = await get_cve(self.cve_id)
        if not data:
            msg_text = await cvecog_translate(
                interaction.guild_id,
                "detail_view",
                "load_error",
                cve_id=self.cve_id,
            )

            await interaction.followup.send(
                f"❌ {msg_text}",
                ephemeral=True,
            )
            return

        # Generate the radar chart using the generator
        chart_file = None
        try:
            _, image_bytes = await chart_generator.generate_chart(data)
            chart_file = discord.File(
                fp=io.BytesIO(image_bytes),
                filename=f"cvss_{self.cve_id}.png"
            )
        except Exception as err:
            print(f"Failed to generate CVSS radar chart for {self.cve_id}: {err}")

        detail_view = CVEDetailView(
            cve_data=data,
            chart_file=chart_file,
            guild_id=interaction.guild_id,
        )
        await detail_view.init_ui()

        # Build attachments list for discord API call
        attachments = [chart_file] if chart_file else []

        if hasattr(self.view, "detail_message") and self.view.detail_message:
            try:
                await self.view.detail_message.edit(view=detail_view, attachments=attachments)
                detail_view.message = self.view.detail_message
                return
            except (discord.NotFound, discord.HTTPException):
                self.view.detail_message = None

        msg = await interaction.followup.send(
            view=detail_view,
            files=attachments,
            wait=True
        )
        detail_view.message = msg
        if hasattr(self.view, "detail_message"):
            self.view.detail_message = msg


class CVEPanel(ui.LayoutView):

    def __init__(
        self,
        guild_id: int | None,
        package_name: str,
        year: str,
        severity: str,
        initial_results: list,
        current_page: int = 1,
    ) -> None:
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.package_name = package_name
        self.year = year
        self.severity = severity
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
        err_msg = await cvecog_translate(
            interaction.guild_id, "panel_view", "error_update"
        )
        if interaction.response.is_done():
            await interaction.followup.send(err_msg, ephemeral=True)
        else:
            await interaction.response.send_message(err_msg, ephemeral=True)

    async def build_ui(self, cves: list) -> None:
        self.clear_items()

        btn_details_label = await cvecog_translate(
            self.guild_id, "panel_view", "btn_details"
        )
        lbl_score = await cvecog_translate(self.guild_id, "panel_view", "score")
        lbl_published = await cvecog_translate(
            self.guild_id, "panel_view", "published"
        )
        lbl_desc = await cvecog_translate(
            self.guild_id, "panel_view", "description"
        )
        no_desc_text = await cvecog_translate(
            self.guild_id, "panel_view", "no_description"
        )

        for cve in cves:
            cve_id = cve.get("cve_id", "N/A")
            cve_data = cve.get("data", {})

            descriptions = cve_data.get("descriptions", [])
            desc_text = next(
                (d["value"] for d in descriptions if d.get("lang") == "en"),
                no_desc_text,
            )

            metrics = cve_data.get("metrics", {})
            cvss_list = metrics.get("cvssMetricV31", [])
            score_info = "N/A"
            if cvss_list:
                primary_cvss = next(
                    (c for c in cvss_list if c.get("type") == "Primary"),
                    cvss_list[0],
                )
                cvss_data = primary_cvss.get("cvssData", {})
                base_score = cvss_data.get("baseScore", "N/A")
                base_severity = cvss_data.get("baseSeverity", "N/A")
                score_info = f"`{base_score}` (**{base_severity}**)"

            published = cve_data.get("published", "N/A").split("T")[0]

            affected_items = cve_data.get("affected", [])
            products = []
            for item in affected_items:
                for data in item.get("affectedData", []):
                    product = data.get("product")
                    if product and product not in products:
                        products.append(product)

            if len(products) > 2:
                software_names = f"{products[0]}, {products[1]}..."
            elif products:
                software_names = ", ".join(products)
            else:
                software_names = self.package_name.capitalize()

            container = ui.Container()

            container.add_item(
                ui.TextDisplay(f"**{cve_id}** — {software_names}")
            )

            details_text = (
                f"**{lbl_score}:** {score_info}\n"
                f"**{lbl_published}:** `{published}`\n"
                f"**{lbl_desc}:** {desc_text[:150]}{'...' if len(desc_text) > 150 else ''}"
            )
            container.add_item(ui.TextDisplay(details_text))

            btn_row = ui.ActionRow()
            btn_row.add_item(
                CVEButton(
                    cve_id=cve_id,
                    label_text=btn_details_label,
                    guild_id=self.guild_id,
                )
            )
            container.add_item(btn_row)

            self.add_item(container)

        has_more_pages = len(cves) == PAGE_SIZE
        await self.add_pagination_controls(has_more_pages=has_more_pages)

    async def add_pagination_controls(self, has_more_pages: bool) -> None:
        nav_row = ui.ActionRow()

        lbl_prev = await cvecog_translate(self.guild_id, "panel_view", "btn_prev")
        lbl_next = await cvecog_translate(self.guild_id, "panel_view", "btn_next")
        page_indicator_label = await cvecog_translate(
            self.guild_id, "panel_view", "page_indicator", page=self.current_page
        )

        prev_button = ui.Button(
            label=lbl_prev,
            style=discord.ButtonStyle.primary,
            disabled=self.current_page <= 1,
        )
        prev_button.callback = self.prev_page
        nav_row.add_item(prev_button)

        page_indicator = ui.Button(
            label=page_indicator_label,
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )
        nav_row.add_item(page_indicator)

        next_button = ui.Button(
            label=lbl_next,
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
        results = await search_cves_by_package(
            package_name=self.package_name,
            year=self.year,
            severity=self.severity,
            page=self.current_page,
            limit=PAGE_SIZE,
        )

        if not results and self.current_page > 1:
            self.current_page -= 1
            return

        await self.build_ui(results)
        await interaction.edit_original_response(view=self)