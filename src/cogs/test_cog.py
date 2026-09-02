import io
import json
import discord
from discord.ext import commands

from graph import CVSSRadarChartGenerator


class CVSSChartCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.generator = None

    async def cog_load(self):
        # Inicializa o gerador junto com o pool de processos
        self.generator = CVSSRadarChartGenerator()

    async def cog_unload(self):
        # Encerra o executor e libera os recursos dos workers
        if self.generator:
            self.generator.close()

    @commands.command(name="cvss")
    async def render_cvss_chart(self, ctx: commands.Context):
        raw_json = """{
            "id": "CVE-2026-1444",
            "sourceIdentifier": "cna@vuldb.com",
            "published": "2026-01-26T22:15:54.377",
            "lastModified": "2026-06-17T10:15:48.133",
            "vulnStatus": "Deferred",
            "cveTags": [],
            "descriptions": [
                {
                    "lang": "en",
                    "value": "A vulnerability has been found in iJason-Liu Books_Manager..."
                }
            ],
            "metrics": {
                "cvssMetricV31": [
                    {
                        "source": "cna@vuldb.com",
                        "type": "Secondary",
                        "cvssData": {
                            "version": "3.1",
                            "vectorString": "CVSS:3.1/AV:N/AC:L/PR:H/UI:R/S:U/C:N/I:L/A:N",
                            "baseScore": 2.4,
                            "baseSeverity": "LOW",
                            "attackVector": "NETWORK",
                            "attackComplexity": "LOW",
                            "privilegesRequired": "HIGH",
                            "userInteraction": "REQUIRED",
                            "scope": "UNCHANGED",
                            "confidentialityImpact": "NONE",
                            "integrityImpact": "LOW",
                            "availabilityImpact": "NONE"
                        }
                    }
                ]
            }
        }"""

        try:
            # Converte e valida a entrada de dados
            data = json.loads(raw_json)

            # Executa a geração no pool de processos sem bloquear o loop do bot
            cve_id, img_bytes = await self.generator.generate_chart(data)

            # Prepara o arquivo para o envio via Discord
            with io.BytesIO(img_bytes) as image_binary:
                file = discord.File(
                    fp=image_binary, filename=f"{cve_id}_radar.png"
                )

                embed = discord.Embed(
                    title=f"Relatório de Métricas — {cve_id}",
                    color=discord.Color.red(),
                )
                embed.set_image(url=f"attachment://{cve_id}_radar.png")

                await ctx.send(embed=embed, file=file)

        except Exception as err:
            await ctx.send(f"Erro ao processar o gráfico CVSS: `{err}`")


async def setup(bot: commands.Bot):
    await bot.add_cog(CVSSChartCog(bot))