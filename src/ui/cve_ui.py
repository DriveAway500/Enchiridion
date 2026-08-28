import discord
import aiohttp

# ---------------------------------------------------------------------------
# CONFIGURAÇÃO CENTRAL: adicionar/alterar um método de pesquisa é só mexer
# aqui. Cada método define seus campos (e se são obrigatórios) e como a
# URL da API deve ser montada a partir dos valores digitados.
# ---------------------------------------------------------------------------
METODOS_PESQUISA = {
    "cve": {
        "label": "Nome da CVE",
        "campos": {
            "termo": {"label": "CVE (ex: CVE-2024-12345)", "obrigatorio": True},
            "ano": {"label": "Ano (opcional)", "obrigatorio": False},
        },
        "montar_url": lambda v: f"https://api.exemplo.com/cve/{v['termo']}",
    },
    "produto": {
        "label": "Nome do produto",
        "campos": {
            "termo": {"label": "Nome do produto", "obrigatorio": True},
            "ano": {"label": "Ano", "obrigatorio": True},
        },
        "montar_url": lambda v: f"https://api.exemplo.com/produto/{v['termo']}/{v['ano']}",
    },
}


# ---------------------------------------------------------------------------
# Modal gerado dinamicamente: os campos (e se são obrigatórios) vêm direto
# da configuração do método escolhido. Não é preciso criar uma classe de
# modal por método.
# ---------------------------------------------------------------------------
class PesquisaModal(discord.ui.Modal):
    def __init__(self, metodo_key: str):
        config = METODOS_PESQUISA[metodo_key]
        super().__init__(title=f"Pesquisar por {config['label']}")
        self.metodo_key = metodo_key
        self.campos_input: dict[str, discord.ui.TextInput] = {}

        for chave, campo_cfg in config["campos"].items():
            campo = discord.ui.TextInput(
                label=campo_cfg["label"],
                required=campo_cfg["obrigatorio"],
                max_length=100,
            )
            self.campos_input[chave] = campo
            self.add_item(campo)

    async def on_submit(self, interaction: discord.Interaction):
        config = METODOS_PESQUISA[self.metodo_key]
        valores = {chave: campo.value for chave, campo in self.campos_input.items()}

        url = config["montar_url"](valores)

        await interaction.response.defer(ephemeral=True)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    dados = await resp.json()
        except Exception as e:
            await interaction.followup.send(
                f"Erro ao consultar a API: `{e}`", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Resultado da Pesquisa",
            description=f"URL consultada:\n`{url}`",
            color=discord.Color.blurple(),
        )
        # TODO: adaptar os campos do embed conforme o formato real da resposta da API
        embed.add_field(name="Resposta bruta", value=f"```json\n{dados}\n```"[:1024])

        await interaction.followup.send(embed=embed, ephemeral=True)


# ---------------------------------------------------------------------------
# Select que escolhe o método e abre o modal correspondente
# ---------------------------------------------------------------------------
class MetodoSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cfg["label"], value=chave)
            for chave, cfg in METODOS_PESQUISA.items()
        ]
        super().__init__(placeholder="Selecione o método de pesquisa...", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PesquisaModal(self.values[0]))


class PainelPesquisa(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MetodoSelect())