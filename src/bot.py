import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="__ENCHIRIDION_UNUSED_PREFIX_9f3a7c__", intents=intents)

@bot.event
async def setup_hook():
    try:
        #await bot.load_extension("cogs.ping_cog")
        await bot.load_extension("cogs.exploit_cog")
        await bot.load_extension("cogs.cve_cog")
        await bot.load_extension("cogs.zeroday_cog")
        await bot.load_extension("cogs.help_cog")

    except Exception as e:
        print(f"SETUP HOOK ERROR: {e}")

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()

        activity = discord.CustomActivity(name="Procurando Exploits...")
        await bot.change_presence(status=discord.Status.online, activity=activity)

        print(f"SYNCHRONIZED {len(synced)} GLOBAL TREE COMMANDS.")
        print(f"BOT CONNECTED AS: {bot.user}")

    except Exception as e:
        print(f"ON READY ERROR: {e}")


def enchiridion_run(token):
    try:
        bot.run(token)
    except Exception as e:
        print(f"ERROR WHILE TRYING TO RUN: {e}")