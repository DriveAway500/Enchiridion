import asyncio
import discord
import aiohttp

from parser import KevParser
from ui import KevView
#from database import feed_db


async def send_feed() -> None:
    kev_task = KevParser()
    data = await kev_task.parse_kev_new()
    if not data:
        return

    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)

        for d in data:
            view = KevView(d, discord.Colour.red())
            await webhook.send(view=view)

if __name__ == "__main__":
    asyncio.run(send_feed())

