import discord
from discord import ui

from omega_api import get_cve, search_cves_by_package
from translator import load_command_translation

PAGE_SIZE = 5


class CVEDetailView(ui.LayoutView):

    def __init__(
        self,
        cve_data: dict,
        lang: str = "EN",
        translations: dict = None,
    ) -> None:
        super().__init__(timeout=180)
        self.cve_data = cve_data
        self.lang = lang
        self.translations = translations or {}
        self.message = None
        self.build_ui()

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

    def build_ui(self) -> None:
        self.clear_items()
        data = self.cve_data

        cve_id = data.get("id", "N/A")
        status = data.get("vulnStatus", "N/A")
        published = data.get("published", "N/A").split("T")[0]
        last_modified = data.get("lastModified", "N/A").split("T")[0]

        descriptions = data.get("descriptions", [])
        no_desc_text = self.translations.get(
            "no_description", "No description available."
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

        title_tpl = self.translations.get(
            "details_title", "🛡️ **Details for {cve_id}**"
        )
        container.add_item(ui.TextDisplay(title_tpl.format(cve_id=cve_id)))

        lbl_status = self.translations.get("status", "Status")
        lbl_published = self.translations.get("published", "Published on")
        lbl_updated = self.translations.get("updated", "Updated")
        lbl_score = self.translations.get("score", "Score")
        lbl_vector = self.translations.get("vector", "Vector")

        info_text = (
            f"**{lbl_status}:** `{status}`\n"
            f"**{lbl_published}:** `{published}` | **{lbl_updated}:** `{last_modified}`\n"
            f"**{lbl_score}:** {score_info}\n"
            f"**{lbl_vector}:** `{vector_str}`"
        )
        container.add_item(ui.TextDisplay(info_text))

        lbl_desc = self.translations.get("description", "Description")
        container.add_item(ui.TextDisplay(f"**{lbl_desc}:**\n{desc_text}"))

        references = data.get("references", [])
        if references:
            btn_row = ui.ActionRow()
            ref_single_tpl = self.translations.get("ref_single", "Source Link")
            ref_multi_tpl = self.translations.get(
                "ref_multiple", "Source Link {idx}"
            )

            for idx, ref in enumerate(references[:3], start=1):
                url = ref.get("url")
                if url:
                    label_str = (
                        ref_multi_tpl.format(idx=idx)
                        if len(references) > 1
                        else ref_single_tpl
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
        lang: str = "EN",
    ) -> None:
        super().__init__(
            label=label_text,
            style=discord.ButtonStyle.secondary,
            custom_id=f"cve_view_{cve_id}",
        )
        self.cve_id = cve_id
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        data = await get_cve(self.cve_id)
        if not data:
            try:
                detail_trans = await load_command_translation(
                    "cvecog", self.lang, "detail_view"
                )
            except Exception:
                detail_trans = {}

            err_tpl = detail_trans.get(
                "load_error", "Could not load details for `{cve_id}`."
            )
            msg_text = err_tpl.format(cve_id=self.cve_id)

            await interaction.followup.send(
                f"❌ {msg_text}",
                ephemeral=True,
            )
            return

        try:
            detail_translations = await load_command_translation(
                "cvecog", self.lang, "detail_view"
            )
        except Exception:
            detail_translations = {}

        detail_view = CVEDetailView(
            cve_data=data,
            lang=self.lang,
            translations=detail_translations,
        )

        if hasattr(self.view, "detail_message") and self.view.detail_message:
            try:
                await self.view.detail_message.edit(view=detail_view)
                detail_view.message = self.view.detail_message
                return
            except (discord.NotFound, discord.HTTPException):
                self.view.detail_message = None

        msg = await interaction.followup.send(
            view=detail_view, wait=True
        )
        detail_view.message = msg
        if hasattr(self.view, "detail_message"):
            self.view.detail_message = msg


class CVEPanel(ui.LayoutView):

    def __init__(
        self,
        package_name: str,
        year: str,
        severity: str,
        initial_results: list,
        current_page: int = 1,
        lang: str = "EN",
        translations: dict = None,
    ) -> None:
        super().__init__(timeout=180)
        self.package_name = package_name
        self.year = year
        self.severity = severity
        self.current_page = current_page
        self.lang = lang
        self.translations = translations or {}
        self.message = None
        self.detail_message = None
        self.build_ui(initial_results)

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
        err_msg = self.translations.get(
            "error_update", "Something went wrong while updating the panel!"
        )
        if interaction.response.is_done():
            await interaction.followup.send(err_msg, ephemeral=True)
        else:
            await interaction.response.send_message(err_msg, ephemeral=True)

    def build_ui(self, cves: list) -> None:
        self.clear_items()

        btn_details_label = self.translations.get(
            "btn_details", "View Details"
        )
        lbl_score = self.translations.get("score", "Score")
        lbl_published = self.translations.get("published", "Published on")
        lbl_desc = self.translations.get("description", "Description")
        no_desc_text = self.translations.get(
            "no_description", "No description available."
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
                    lang=self.lang,
                )
            )
            container.add_item(btn_row)

            self.add_item(container)

        has_more_pages = len(cves) == PAGE_SIZE
        self.add_pagination_controls(has_more_pages=has_more_pages)

    def add_pagination_controls(self, has_more_pages: bool) -> None:
        nav_row = ui.ActionRow()

        lbl_prev = self.translations.get("btn_prev", "◀ Previous")
        lbl_next = self.translations.get("btn_next", "Next ▶")
        page_indicator_tpl = self.translations.get(
            "page_indicator", "Page {page}"
        )

        prev_button = ui.Button(
            label=lbl_prev,
            style=discord.ButtonStyle.primary,
            disabled=self.current_page <= 1,
        )
        prev_button.callback = self.prev_page
        nav_row.add_item(prev_button)

        page_indicator = ui.Button(
            label=page_indicator_tpl.format(page=self.current_page),
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

        self.build_ui(results)
        await interaction.edit_original_response(view=self)