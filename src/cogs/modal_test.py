import datetime
import traceback
import discord
from discord import app_commands
from discord.ext import commands
from discord import ui

class CVESearchModal(ui.Modal, title='Pesquisar CVEs'):
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
        description='Nome do pacote ou palavra-chave',
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

class ModalTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="modal", description="Abre o modal")
    async def abrir_modal(self, interaction):
        await interaction.response.send_modal(CVESearchModal())

async def setup(bot):
    await bot.add_cog(ModalTestCog(bot))