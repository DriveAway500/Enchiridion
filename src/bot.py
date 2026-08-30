import discord
from discord.ext import commands

class EnchiridionBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix="__ENCHIRIDION_UNUSED_PREFIX_9f3a7c__",
            intents=intents
        )

    async def setup_hook(self):
        try:
            # await self.load_extension("cogs.ping_cog")
            await self.load_extension("cogs.exploit_cog")
            await self.load_extension("cogs.cve_cog")
            await self.load_extension("cogs.zeroday_cog")
            await self.load_extension("cogs.help_cog")

            synced = await self.tree.sync()
            print(f"SYNCHRONIZED {len(synced)} GLOBAL TREE COMMANDS.")
        except Exception as e:
            print(f"SETUP HOOK ERROR: {e}")

    async def on_ready(self):
        try:
            activity = discord.CustomActivity(name="Procurando Exploits...")
            await self.change_presence(status=discord.Status.online, activity=activity)
            print(f"BOT CONNECTED AS: {self.user}")
        except Exception as e:
            print(f"ON READY ERROR: {e}")


def enchiridion_run(token):
    try:
        bot = EnchiridionBot()
        bot.run(token)
    except Exception as e:
        print(f"ERROR WHILE TRYING TO RUN: {e}")