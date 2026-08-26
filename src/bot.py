import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="", intents=intents)

@bot.event
async def setup_hook():
    try:
        await bot.load_extension("cogs.ping")
    except Exception as e:
        print(f"SETUP HOOK ERROR: {e}")

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"SYNCHRONIZED {len(synced)} GLOBAL TREE COMMANDS.")
        print(f"BOT CONNECTED AS: {bot.user}")
    except Exception as e:
        print(f"ON READY ERROR: {e}")


def enchiridion_run(token):
    try:
        bot.run(token)
    except Exception as e:
        print(f"ERROR WHILE TRYING TO RUN: {e}")