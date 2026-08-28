import datetime
import traceback
import discord
from discord import app_commands
from discord.ext import commands
from discord import ui

class Questionnaire(ui.Modal, title='Questionnaire Response'):
    distro = ui.Label(
        text='Arch Based Distros',
        description='Selecione a sua distribuição preferida',
        component=ui.Select(
            custom_id="arch_distro_select",
            placeholder="Escolha uma distro...",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Arch", value="1417721225840693259"),
                discord.SelectOption(label="Manjaro", value="1417721263136309309"),
                discord.SelectOption(label="Garuda", value="1417721297592385628"),
                discord.SelectOption(label="EndeavourOS", value="1417721370200244284"),
                discord.SelectOption(label="BlackArch", value="1417721409022459904"),
                discord.SelectOption(label="Artix", value="1417721462445445261"),
                discord.SelectOption(label="ArchCraft", value="1417721500038987937"),
            ]
        )
    )

    name = ui.Label(
        text='Name',
        description='Digite seu nome',
        component=ui.TextInput(
            style=discord.TextStyle.short,
            max_length=100
        )
    )

    answer = ui.Label(
        text='Answer',
        description='Digite sua resposta',
        component=ui.TextInput(
            style=discord.TextStyle.paragraph,
            max_length=1000
        )
    )

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)

        selected_role_id = int(self.distro.component.values[0])
        role = interaction.guild.get_role(selected_role_id)

        all_distro_ids = [int(opt.value) for opt in self.distro.component.options]
        roles_to_remove = [r for r in interaction.user.roles if r.id in all_distro_ids]

        if roles_to_remove:
            await interaction.user.remove_roles(*roles_to_remove)

        if role:
            if role in interaction.user.roles:
                await interaction.followup.send(
                    f"Você já possui o cargo {role.name}!", 
                    ephemeral=True
                )
            else:
                await interaction.user.add_roles(role)
                await interaction.followup.send(
                    f"Obrigado {self.name.component.value}! Cargo {role.name} adicionado!", 
                    ephemeral=True
                )

    async def on_error(self, interaction, error):
        await interaction.response.send_message('Algo deu errado!', ephemeral=True)
        traceback.print_exception(type(error), error, error.__traceback__)

class ModalTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="modal", description="Abre o modal")
    async def abrir_modal(self, interaction):
        await interaction.response.send_modal(Questionnaire())

async def setup(bot):
    await bot.add_cog(ModalTestCog(bot))