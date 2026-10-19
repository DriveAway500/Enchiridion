"""Periodic feed task.

Orchestrates the whole pipeline and delivers results to Discord:

    FeedFetcher (HTTP) -> CVEFeedParser (parsing) -> dedup (database)
        -> subscription filter -> Discord webhook delivery
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

import aiohttp
import discord
from discord.ext import tasks

from database import feed_db
from httpx_client import get_http_client

from parser import CVEFeedParser, VulnerabilityData
from .engine import FeedFetcher, FeedFetchFailure, FeedSource

logger = logging.getLogger(__name__)

MAX_CONCURRENT_SENDS: int = 20
WEBHOOK_SEND_TIMEOUT_SECONDS: float = 10.0
DEFAULT_FEED_URLS: tuple[str, ...] = ("https://cvefeed.io/rssfeed/latest.atom",)


# --------------------------------------------------------------------------- #
# Types
# --------------------------------------------------------------------------- #


class FeedSubscription(Protocol):
    """Structural type of a subscription row returned by ``feed_db``."""

    @property
    def guild_id(self) -> int: ...

    @property
    def channel_id(self) -> int: ...

    @property
    def webhook_url(self) -> str | None: ...

    @property
    def min_severity(self) -> float: ...

    @property
    def allow_unknown(self) -> bool: ...


class FeedBot(Protocol):
    """The subset of the bot this task depends on."""

    webhook_session: aiohttp.ClientSession

    async def wait_until_ready(self) -> None: ...


class DeliveryStatus(Enum):
    """Outcome of sending one item to one subscription."""

    SENT = "sent"
    FAILED = "failed"
    WEBHOOK_GONE = "webhook_gone"
    """The webhook no longer exists; the subscription should be removed."""


@dataclass(slots=True)
class CycleStats:
    """Counters for one feed cycle."""

    items_found: int = 0
    subscriptions: int = 0
    matched: int = 0
    sent_ok: int = 0
    sent_failed: int = 0


# --------------------------------------------------------------------------- #
# Delivery
# --------------------------------------------------------------------------- #


def _build_embed(item: VulnerabilityData) -> discord.Embed:
    """Build the Discord embed for a vulnerability."""
    return discord.Embed(
        title=f"{item.severity.label} {item.title}"[:256],
        url=item.link,
        description=item.summary[:4000],
        color=discord.Color(int(item.severity.color_hex.lstrip("#"), 16)),
    )


def _matches_filter(item: VulnerabilityData, sub: FeedSubscription) -> bool:
    """Check whether an item passes a subscription's severity filter."""
    score = item.severity.score
    if score is None:
        return sub.allow_unknown
    return score >= sub.min_severity


async def _send_to_subscription(
    session: aiohttp.ClientSession,
    sub: FeedSubscription,
    item: VulnerabilityData,
) -> DeliveryStatus:
    """Send an item to a subscription's webhook."""
    if not sub.webhook_url:
        return DeliveryStatus.FAILED

    webhook = discord.Webhook.from_url(sub.webhook_url, session=session)
    embed = _build_embed(item)
    try:
        await asyncio.wait_for(
            webhook.send(embed=embed), timeout=WEBHOOK_SEND_TIMEOUT_SECONDS
        )
        return DeliveryStatus.SENT
    except asyncio.TimeoutError:
        logger.warning("Timeout sending item %s to channel %s", item.id, sub.channel_id)
        return DeliveryStatus.FAILED
    except discord.NotFound:
        logger.warning(
            "Webhook for channel %s (guild %s) no longer exists - removing subscription",
            sub.channel_id,
            sub.guild_id,
        )
        return DeliveryStatus.WEBHOOK_GONE
    except discord.DiscordException:
        logger.warning(
            "Failed to send item %s to channel %s",
            item.id,
            sub.channel_id,
            exc_info=True,
        )
        return DeliveryStatus.FAILED


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #


async def collect_new_items(
    fetcher: FeedFetcher,
    parser: CVEFeedParser,
    sources: Sequence[FeedSource],
) -> list[VulnerabilityData]:
    """Fetch, parse and deduplicate items from all sources.

    Items already marked as sent in the database are dropped, as are
    duplicates appearing in more than one feed during the same cycle.

    Args:
        fetcher: Engine used to download the feeds.
        parser: Parser used to interpret each feed.
        sources: Feeds to process.

    Returns:
        New items, oldest first within each feed.
    """
    items: list[VulnerabilityData] = []
    seen_ids: set[str] = set()

    for result in await fetcher.fetch_many(sources):
        if isinstance(result, FeedFetchFailure):
            continue  # already logged by the fetcher

        parsed = parser.parse(result.response)
        already_sent = 0
        new_items = 0

        for vulnerability in parsed.vulnerabilities:
            if vulnerability.id in seen_ids:
                continue
            if await feed_db.is_sent(vulnerability.id):
                already_sent += 1
                continue
            seen_ids.add(vulnerability.id)
            items.append(vulnerability)
            new_items += 1

        logger.info(
            "%s: %d entry(ies), %d already sent, %d without classifiable severity, "
            "%d invalid, %d new item(s) ready to send",
            parsed.source.label,
            parsed.total_entries,
            already_sent,
            parsed.discarded_unclassified,
            parsed.discarded_invalid,
            new_items,
        )

    return items


async def process_feeds_once(
    session: aiohttp.ClientSession,
    fetcher: FeedFetcher,
    parser: CVEFeedParser,
    sources: Sequence[FeedSource],
) -> CycleStats:
    """Run one full feed cycle.

    Args:
        session: HTTP session used for Discord webhook delivery.
        fetcher: Engine used to download the feeds.
        parser: Parser used to interpret each feed.
        sources: Feeds to process.

    Returns:
        Counters describing what happened during the cycle.
    """
    stats = CycleStats()

    items = await collect_new_items(fetcher, parser, sources)
    stats.items_found = len(items)
    logger.info("Feed cycle: %d new item(s) found in total", len(items))
    if not items:
        return stats

    subscriptions: Sequence[FeedSubscription] = await feed_db.list_subscriptions()
    stats.subscriptions = len(subscriptions)
    logger.info(
        "Feed cycle: %d subscription(s) registered (across all guilds)",
        len(subscriptions),
    )

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SENDS)

    async def send_with_limit(
        sub: FeedSubscription, item: VulnerabilityData
    ) -> DeliveryStatus:
        async with semaphore:
            return await _send_to_subscription(session, sub, item)

    for item in items:
        matching_subs = [s for s in subscriptions if _matches_filter(item, s)]
        stats.matched += len(matching_subs)
        logger.debug(
            "Item %s (%s, score=%s) -> %d matching channel(s)",
            item.id,
            item.severity.label,
            item.severity.score,
            len(matching_subs),
        )

        if not matching_subs:
            continue

        statuses = await asyncio.gather(
            *(send_with_limit(sub, item) for sub in matching_subs)
        )

        for sub, status in zip(matching_subs, statuses):
            if status is DeliveryStatus.SENT:
                stats.sent_ok += 1
                continue
            stats.sent_failed += 1
            if status is DeliveryStatus.WEBHOOK_GONE:
                await feed_db.remove_subscription(sub.guild_id, sub.channel_id)

        await feed_db.mark_sent(item.id)

    logger.info("Feed cycle finished: %s", stats)
    return stats


# --------------------------------------------------------------------------- #
# Task setup
# --------------------------------------------------------------------------- #


def setup_feed_task(
    bot: FeedBot,
    interval_seconds: int = 7200,
    feed_urls: Sequence[str] = DEFAULT_FEED_URLS,
) -> tasks.Loop[Callable[[], Coroutine[Any, Any, None]]]:
    """Create the periodic feed task (the caller is responsible for starting it).

    Args:
        bot: The bot instance (must expose ``webhook_session``).
        interval_seconds: Time between cycles.
        feed_urls: Feeds to monitor.

    Returns:
        The configured, not yet started, task loop.
    """
    fetcher = FeedFetcher(get_http_client)
    parser = CVEFeedParser()
    sources = [FeedSource(url=url) for url in feed_urls]

    @tasks.loop(seconds=interval_seconds)
    async def feed_task() -> None:
        try:
            await process_feeds_once(bot.webhook_session, fetcher, parser, sources)
        except Exception:
            logger.exception("Error while processing feed cycle")

    @feed_task.before_loop
    async def before_feed_task() -> None:
        await bot.wait_until_ready()

    @feed_task.error
    async def feed_task_error(error: BaseException) -> None:
        logger.critical(
            "Feed task crashed: %s",
            error,
            exc_info=(type(error), error, error.__traceback__),
        )

    return feed_task
