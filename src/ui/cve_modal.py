import re
import traceback
import discord
from discord import ui

#==========================
#MODAL FOR PACKAGE SEARCH
#==========================

class CVEPackageSearchModal(ui.Modal, title='Pesquisar CVEs'):
    score = ui.Label(
        text='Score CVSS',
        description='Filtre por severidade / pontuação',
        component=ui.Select(
            custom_id="score_select",
            placeholder="Selecione a faixa de score",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Baixo (0.1 - 3.9)", value="low"),
                discord.SelectOption(label="Médio (4.0 - 6.9)", value="medium"),
                discord.SelectOption(label="Alto (7.0 - 8.9)", value="high"),
                discord.SelectOption(label="Crítico (9.0 - 10.0)", value="critical"),
            ]
        )
    )

    year = ui.Label(
        text='Intervalo de Tempo',
        description='Escolha o ano de publicação',
        component=ui.Select(
            custom_id="year_select",
            placeholder="Selecione o ano",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="2026", value="2026"),
                discord.SelectOption(label="2025", value="2025"),
                discord.SelectOption(label="2024", value="2024"),
                discord.SelectOption(label="2023", value="2023"),
            ]
        )
    )

    package_name = ui.Label(
        text='Pacote ou Termo',
        description='Insira o nome do pacote ou palavra-chave',
        component=ui.TextInput(
            style=discord.TextStyle.short,
            placeholder="Ex: linux, openssl, sudo...",
            max_length=100,
            required=True
        )
    )

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)

        search_query = {
            "package": self.package_name.component.value,
            "score_range": self.score.component.values[0],
            "year": self.year.component.values[0]
        }

        # TODO: Chame seu método de busca passando 'search_query'
        # exemplo: results = await seu_metodo_de_busca(search_query)

        await interaction.followup.send(
            f"Pesquisa iniciada para o pacote `{search_query['package']}` (Ano: {search_query['year']}, Score: {search_query['score_range']}).",
            ephemeral=True
        )

    async def on_error(self, interaction, error):
        await interaction.response.send_message('Algo deu errado na consulta!', ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)


#==========================
#MODAL FOR ID SEARCH ONLY
#==========================

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)

class CVEIdSearchModal(ui.Modal, title="Pesquisar CVE"):
    cve_id = ui.TextInput(
        label="ID da CVE",
        placeholder="Ex: CVE-2021-44228",
        style=discord.TextStyle.short,
        min_length=13,
        max_length=20,
        required=True,
    )

    async def on_submit(self, interaction):
        cve_code = self.cve_id.value.strip().upper()

        if not CVE_PATTERN.match(cve_code):
            await interaction.response.send_message(
                "❌ Formato de CVE inválido! Use o formato `CVE-AAAA-NNNN` (ex: `CVE-2021-44228`).",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        # TODO: Chame o método de busca passando o ID validado
        # result = await get_cve(cve_code)

        await interaction.followup.send(
            f"Pesquisa iniciada para a CVE `{cve_code}`.",
            ephemeral=True,
        )

    async def on_error(self, interaction, error):
        await interaction.response.send_message(
            "Algo deu errado na consulta!", ephemeral=True
        )
        traceback.print_exception(type(error), error, error.__traceback__)