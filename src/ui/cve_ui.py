import discord
from discord import ui

#from omega_api import get_cve, search_cves_by_package

class MeuModal(discord.ui.Modal, title="Formulário Simples"):
    nome = discord.ui.TextInput(
        label="Qual é o seu nome?",
        placeholder="Digite seu nome aqui...",
        required=True
    )
    
    feedback = discord.ui.TextInput(
        label="Deixe seu feedback",
        style=discord.TextStyle.paragraph,
        placeholder="Escreva sua opinião...",
        max_length=300
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Obrigado, {self.nome.value}! Seu feedback foi recebido.",
            ephemeral=True
        )
