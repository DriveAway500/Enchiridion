import aiohttp
import discord
from discord.ext import commands

from feeds import setup_feed_task

EXTENSIONS = (
    "cogs.exploit_cog",
    "cogs.cve_cog",
    "cogs.zeroday_cog",
    "cogs.help_cog",
    "cogs.feed_cog",
    "cogs.lang_cog",
)

class EnchiridionBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix="__ENCHIRIDION_UNUSED_PREFIX_9f3a7c__",
            intents=intents,
        )
        self.feed_task = None
        self.webhook_session = None

    async def setup_hook(self):
        self.webhook_session = aiohttp.ClientSession()

        for extension in EXTENSIONS:
            await self.load_extension(extension)

        synced = await self.tree.sync()
        print(f"SYNCHRONIZED {len(synced)} GLOBAL TREE COMMANDS.")

        self.feed_task = setup_feed_task(self)
        self.feed_task.start()

    async def close(self):
        if self.feed_task and self.feed_task.is_running():
            self.feed_task.cancel()
        if self.webhook_session:
            await self.webhook_session.close()
        await super().close()

    async def on_ready(self):
        activity = discord.CustomActivity(name="Procurando Exploits...")
        await self.change_presence(status=discord.Status.online, activity=activity)
        print(f"BOT CONNECTED AS: {self.user}")


def enchiridion_run(token):
    bot = EnchiridionBot()
    bot.run(token)