import discord
from discord import ui

from omega_api import get_cve, search_cves_by_package

PAGE_SIZE = 5


class CVEDetailView(ui.LayoutView):
    def __init__(self, cve_data):
        super().__init__(timeout=180)
        self.cve_data = cve_data
        self.message = None
        self.build_ui()

    async def on_timeout(self):
        def disable_all(items):
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

    def build_ui(self):
        self.clear_items()
        data = self.cve_data

        cve_id = data.get("id", "N/A")
        status = data.get("vulnStatus", "N/A")
        published = data.get("published", "N/A").split("T")[0]
        last_modified = data.get("lastModified", "N/A").split("T")[0]

        descriptions = data.get("descriptions", [])
        desc_text = next(
            (d["value"] for d in descriptions if d.get("lang") == "en"),
            "Sem descrição disponível.",
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

        container.add_item(ui.TextDisplay(f"🛡️ **Detalhes da {cve_id}**"))

        info_text = (
            f"**Status:** `{status}`\n"
            f"**Publicado em:** `{published}` | **Atualizado:** `{last_modified}`\n"
            f"**Pontuação:** {score_info}\n"
            f"**Vetor:** `{vector_str}`"
        )
        container.add_item(ui.TextDisplay(info_text))

        container.add_item(ui.TextDisplay(f"**Descrição:**\n{desc_text}"))

        references = data.get("references", [])
        if references:
            btn_row = ui.ActionRow()
            for idx, ref in enumerate(references[:3], start=1):
                url = ref.get("url")
                if url:
                    btn_row.add_item(
                        ui.Button(
                            label=f"Link de Origem {idx}"
                            if len(references) > 1
                            else "Link de Origem",
                            style=discord.ButtonStyle.link,
                            url=url,
                        )
                    )
            container.add_item(btn_row)

        self.add_item(container)


class CVEButton(ui.Button):
    def __init__(self, cve_id):
        super().__init__(
            label="Ver Detalhes",
            style=discord.ButtonStyle.secondary,
            custom_id=f"cve_view_{cve_id}",
        )
        self.cve_id = cve_id

    async def callback(self, interaction):
        await interaction.response.defer(ephemeral=True)

        data = await get_cve(self.cve_id)
        if not data:
            await interaction.followup.send(
                f"❌ Não foi possível carregar os detalhes da `{self.cve_id}`.",
                ephemeral=True,
            )
            return

        detail_view = CVEDetailView(cve_data=data)

        # Se já existir um painel enviado no container pai (CVEPanel), apenas edita
        if self.view.detail_message:
            try:
                await self.view.detail_message.edit(view=detail_view)
                detail_view.message = self.view.detail_message
                return
            except (discord.NotFound, discord.HTTPException):
                # Caso a mensagem antiga tenha sido apagada, gera uma nova
                self.view.detail_message = None

        msg = await interaction.followup.send(
            view=detail_view, wait=True
        )
        detail_view.message = msg
        self.view.detail_message = msg


class CVEPanel(ui.LayoutView):
    def __init__(self, package_name, year, severity, initial_results, current_page=1):
        super().__init__(timeout=180)
        self.package_name = package_name
        self.year = year
        self.severity = severity
        self.current_page = current_page
        self.message = None
        self.detail_message = None  # Armazena a referência da mensagem de detalhes
        self.build_ui(initial_results)

    async def on_timeout(self):
        def disable_all(items):
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

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: ui.Item):
        if interaction.response.is_done():
            await interaction.followup.send("Algo deu errado ao atualizar o painel!", ephemeral=True)
        else:
            await interaction.response.send_message("Algo deu errado ao atualizar o painel!", ephemeral=True)

    def build_ui(self, cves):
        self.clear_items()

        for cve in cves:
            cve_id = cve.get("cve_id", "N/A")
            cve_data = cve.get("data", {})

            descriptions = cve_data.get("descriptions", [])
            desc_text = next(
                (d["value"] for d in descriptions if d.get("lang") == "en"),
                "Sem descrição disponível.",
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

            # Extraindo os nomes dos softwares prejudicados (limitando para evitar estouro)
            affected_items = cve_data.get("affected", [])
            products = []
            for item in affected_items:
                for data in item.get("affectedData", []):
                    product = data.get("product")
                    if product and product not in products:
                        products.append(product)
            
            # Se houver muitos produtos, limita a 2 para não estourar a linha
            if len(products) > 2:
                software_names = f"{products[0]}, {products[1]}..."
            elif products:
                software_names = ", ".join(products)
            else:
                software_names = self.package_name.capitalize()

            container = ui.Container()

            # Título focado apenas na CVE e nos softwares
            container.add_item(
                ui.TextDisplay(f"**{cve_id}** — {software_names}")
            )

            # Score movido para junto dos detalhes
            details_text = (
                f"**Score:** {score_info}\n"
                f"**Publicado em:** `{published}`\n"
                f"**Descrição:** {desc_text[:150]}{'...' if len(desc_text) > 150 else ''}"
            )
            container.add_item(ui.TextDisplay(details_text))

            btn_row = ui.ActionRow()
            btn_row.add_item(CVEButton(cve_id=cve_id))
            container.add_item(btn_row)

            self.add_item(container)

        has_more_pages = len(cves) == PAGE_SIZE
        self.add_pagination_controls(has_more_pages=has_more_pages)

    def add_pagination_controls(self, has_more_pages):
        nav_row = ui.ActionRow()

        prev_button = ui.Button(
            label="◀ Anteriores",
            style=discord.ButtonStyle.primary,
            disabled=self.current_page <= 1,
        )
        prev_button.callback = self.prev_page
        nav_row.add_item(prev_button)

        page_indicator = ui.Button(
            label=f"Página {self.current_page}",
            style=discord.ButtonStyle.secondary,
            disabled=True,
        )
        nav_row.add_item(page_indicator)

        next_button = ui.Button(
            label="Próximos ▶",
            style=discord.ButtonStyle.primary,
            disabled=not has_more_pages,
        )
        next_button.callback = self.next_page
        nav_row.add_item(next_button)

        self.add_item(nav_row)

    async def prev_page(self, interaction):
        if self.current_page > 1:
            self.current_page -= 1
            await self.update_page(interaction)

    async def next_page(self, interaction):
        self.current_page += 1
        await self.update_page(interaction)

    async def update_page(self, interaction):
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