import asyncio
import logging

import discord
from discord.ext import tasks

from .cve_spider import CVEClassifier
from database import feed_db

logger = logging.getLogger(__name__)

MAX_CONCURRENT_SENDS = 20


def _build_embed(item):
    return discord.Embed(
        title=f"{item.severity_label} {item.title}"[:256],
        url=item.link,
        description=item.summary[:4000],
        color=discord.Color(int(item.color_hex.lstrip("#"), 16)),
    )


def _matches_filter(item, sub):
    if item.severity_score == -1.0:
        return sub.allow_unknown
    return item.severity_score >= sub.min_severity


async def _send_to_subscription(session, sub, item):
    """Send via webhook. Returns (sent_successfully, webhook_gone)."""
    if not sub.webhook_url:
        return False, False

    webhook = discord.Webhook.from_url(sub.webhook_url, session=session)
    embed = _build_embed(item)
    try:
        await asyncio.wait_for(webhook.send(embed=embed), timeout=10)
        return True, False
    except asyncio.TimeoutError:
        logger.warning("Timeout sending item %s to channel %s", item.id, sub.channel_id)
        return False, False
    except discord.NotFound:
        logger.warning(
            "Webhook for channel %s (guild %s) no longer exists - removing subscription",
            sub.channel_id,
            sub.guild_id,
        )
        return False, True
    except discord.DiscordException:
        logger.warning(
            "Failed to send item %s to channel %s", item.id, sub.channel_id, exc_info=True
        )
        return False, False


async def process_feeds_once(bot, classifier):
    stats = {
        "items_found": 0,
        "subscriptions": 0,
        "matched": 0,
        "sent_ok": 0,
        "sent_failed": 0,
    }

    items = await classifier.fetch_and_classify()
    stats["items_found"] = len(items)
    logger.info("Feed cycle: %d new item(s) found in total", len(items))
    if not items:
        return stats

    subscriptions = await feed_db.list_subscriptions()
    stats["subscriptions"] = len(subscriptions)
    logger.info(
        "Feed cycle: %d subscription(s) registered (across all guilds)", len(subscriptions)
    )

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SENDS)

    async def _send_with_limit(sub, item):
        async with semaphore:
            return await _send_to_subscription(bot.webhook_session, sub, item)

    for item in items:
        matching_subs = [s for s in subscriptions if _matches_filter(item, s)]
        stats["matched"] += len(matching_subs)
        logger.debug(
            "Item %s (%s, score=%s) -> %d matching channel(s)",
            item.id,
            item.severity_label,
            item.severity_score,
            len(matching_subs),
        )

        if not matching_subs:
            continue

        results = await asyncio.gather(*(_send_with_limit(sub, item) for sub in matching_subs))

        for sub, (ok, webhook_gone) in zip(matching_subs, results):
            if ok:
                stats["sent_ok"] += 1
            else:
                stats["sent_failed"] += 1
                if webhook_gone:
                    await feed_db.remove_subscription(sub.guild_id, sub.channel_id)

        await feed_db.mark_sent(item.id)

    logger.info("Feed cycle finished: %s", stats)
    return stats


def setup_feed_task(bot, interval_seconds=7200):
    classifier = CVEClassifier(is_sent_checker=feed_db.is_sent)
    bot.feed_classifier = classifier

    @tasks.loop(seconds=interval_seconds)
    async def feed_task():
        try:
            await process_feeds_once(bot, classifier)
        except Exception:
            logger.exception("Error while processing feed cycle")

    @feed_task.before_loop
    async def before_feed_task():
        await bot.wait_until_ready()

    @feed_task.error
    async def feed_task_error(error):
        logger.critical(
            "Feed task crashed: %s", error, exc_info=(type(error), error, error.__traceback__)
        )

    return feed_task