import io

import discord
from discord import ui

from omega_api import get_zeroday_exploit, search_zeroday_exploits

PAGE_SIZE = 5


class ExploitButton(ui.Button):

    def __init__(self, exploit_id, title, translations=None):
        self.translations = translations or {}
        label_text = self.translations.get("btn_view_exploit", "View Exploit")

        super().__init__(
            label=label_text,
            style=discord.ButtonStyle.secondary,
            custom_id=f"exploit_view_{exploit_id}",
        )
        self.exploit_id = exploit_id
        self.title = title

    async def callback(self, interaction):
        await interaction.response.defer()

        data = await get_zeroday_exploit(self.exploit_id)
        if not data or "code" not in data:
            err_msg = self.translations.get(
                "err_code_fetch",
                "❌ Could not load code for this exploit.",
            )
            await interaction.followup.send(
                err_msg,
                ephemeral=True,
            )
            return

        metadata = data.get("metadata", {})
        file_path = metadata.get("file", f"{self.exploit_id}.txt")
        file_name = file_path.split("/")[-1]
        code = data.get("code", "")
        file_extension = file_name.split(".")[-1] if "." in file_name else ""

        title_header = f"📌 **{self.title}**\n"
        code_block = f"```{file_extension}\n{code}\n```"
        message_content = f"{title_header}{code_block}"

        panel_view = self.view
        file_obj = None

        if len(message_content) > 2000:
            message_content = f"{title_header}"
            file_bytes = io.BytesIO(code.encode("utf-8"))
            file_obj = discord.File(fp=file_bytes, filename=file_name)

        if panel_view.active_code_message:
            try:
                if file_obj:
                    panel_view.active_code_message = (
                        await panel_view.active_code_message.edit(
                            content=message_content,
                            attachments=[file_obj],
                        )
                    )
                else:
                    panel_view.active_code_message = (
                        await panel_view.active_code_message.edit(
                            content=message_content,
                            attachments=[],
                        )
                    )
                return
            except discord.NotFound:
                panel_view.active_code_message = None

        if file_obj:
            msg = await interaction.channel.send(
                content=message_content,
                file=file_obj,
                reference=interaction.message,
            )
        else:
            msg = await interaction.channel.send(
                content=message_content,
                reference=interaction.message,
            )

        panel_view.active_code_message = msg


class ZeroDayPanel(ui.LayoutView):

    def __init__(
        self,
        query,
        initial_results,
        current_page=1,
        lang="EN",
        translations=None,
    ):
        super().__init__(timeout=180)
        self.query = query
        self.current_page = current_page
        self.lang = lang
        self.translations = translations or {}
        self.active_code_message = None
        self.message = None
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

    def build_ui(self, exploits):
        self.clear_items()

        lbl_category = self.translations.get("lbl_category", "Category")
        lbl_platform = self.translations.get("lbl_platform", "Platform")
        lbl_date = self.translations.get("lbl_date", "Date")
        lbl_author = self.translations.get("lbl_author", "Author")

        for exploit in exploits:
            cves = exploit.get("cve")
            cves_line = f"**CVEs:** `{', '.join(cves)}`\n" if cves else ""

            container = ui.Container()
            container.add_item(
                ui.TextDisplay(f"**{exploit.get('title', '')}**")
            )

            details_text = (
                f"**{lbl_category}:** `{exploit.get('category', 'N/A')}`\n"
                f"**{lbl_platform}:** `{exploit.get('platform', 'N/A')}`\n"
                f"**{lbl_date}:** {exploit.get('date', 'N/A')}\n"
                f"**{lbl_author}:** {exploit.get('author', 'N/A')}\n"
                f"{cves_line}"
            )
            container.add_item(ui.TextDisplay(details_text))

            btn_row = ui.ActionRow()
            btn_row.add_item(
                ExploitButton(
                    exploit_id=exploit["exploit_id"],
                    title=exploit.get("title", ""),
                    translations=self.translations,
                )
            )
            container.add_item(btn_row)

            self.add_item(container)

        has_more_pages = len(exploits) == PAGE_SIZE
        self.add_pagination_controls(has_more_pages=has_more_pages)

    def add_pagination_controls(self, has_more_pages):
        nav_row = ui.ActionRow()

        lbl_prev = self.translations.get("btn_prev", "◀ Previous")
        lbl_next = self.translations.get("btn_next", "Next ▶")
        page_tpl = self.translations.get("btn_page", "Page {page}")

        prev_button = ui.Button(
            label=lbl_prev,
            style=discord.ButtonStyle.primary,
            disabled=self.current_page <= 1,
        )
        prev_button.callback = self.prev_page
        nav_row.add_item(prev_button)

        page_indicator = ui.Button(
            label=page_tpl.format(page=self.current_page),
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

    async def prev_page(self, interaction):
        if self.current_page > 1:
            self.current_page -= 1
            await self.update_page(interaction)

    async def next_page(self, interaction):
        self.current_page += 1
        await self.update_page(interaction)

    async def update_page(self, interaction):
        await interaction.response.defer()
        results = await search_zeroday_exploits(
            self.query, page=self.current_page, limit=PAGE_SIZE
        )

        if not results and self.current_page > 1:
            self.current_page -= 1
            return

        self.build_ui(results)
        await interaction.edit_original_response(view=self)