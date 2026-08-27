import discord
from discord import app_commands
from discord.ext import commands

from ui import MeuModal

class ModalTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="modal", description="Abre o formulário modal")
    async def abrir_modal(self, interaction: discord.Interaction):
        await interaction.response.send_modal(MeuModal())

async def setup(bot):
    await bot.add_cog(ModalTestCog(bot))