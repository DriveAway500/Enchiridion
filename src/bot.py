import discord
from discord.ext import commands, tasks

from database import FeedDatabase
from feeds import process_feeds_once, CVEClassifier


class EnchiridionBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix="__ENCHIRIDION_UNUSED_PREFIX_9f3a7c__",
            intents=intents
        )
        self.database: FeedDatabase | None = None
        self.classifier: CVEClassifier | None = None

    async def setup_hook(self):
        try:
            await self.load_extension("cogs.exploit_cog")
            await self.load_extension("cogs.cve_cog")
            await self.load_extension("cogs.zeroday_cog")
            await self.load_extension("cogs.help_cog")
            await self.load_extension("cogs.feed_cog")

            synced = await self.tree.sync()
            print(f"SYNCHRONIZED {len(synced)} GLOBAL TREE COMMANDS.")

            self.database = FeedDatabase("feeds.db")
            await self.database.init()
            self.classifier = CVEClassifier(is_sent_checker=self.database.is_sent)

            self.feed_task.start()
        except Exception as e:
            print(f"SETUP HOOK ERROR: {e}")

    @tasks.loop(seconds=300)
    async def feed_task(self):
        try:
            await process_feeds_once(self, self.database, self.classifier)
        except Exception as e:
            print(f"ERRO NA TASK DE FEEDS: {e}")

    @feed_task.before_loop
    async def before_feed_task(self):
        await self.wait_until_ready()

    @feed_task.error
    async def feed_task_error(self, error: BaseException):
        print(f"FEED TASK CRASHOU: {error}")

    async def close(self):
        self.feed_task.cancel()
        await super().close()

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