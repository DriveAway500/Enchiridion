import asyncio
import traceback

import discord
from discord.ext import tasks

from .cve_spider import CVEClassifier
from database import feed_db

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
    """Envia via webhook. Retorna (enviado_com_sucesso, webhook_sumiu)."""
    if not sub.webhook_url:
        return False, False

    webhook = discord.Webhook.from_url(sub.webhook_url, session=session)
    embed = _build_embed(item)
    try:
        await asyncio.wait_for(webhook.send(embed=embed), timeout=10)
        return True, False
    except asyncio.TimeoutError:
        print(f"Timeout ao enviar item {item.id} para canal {sub.channel_id}")
        return False, False
    except discord.NotFound:
        print(f"Webhook do canal {sub.channel_id} (servidor {sub.guild_id}) não existe mais - removendo inscrição.")
        return False, True
    except discord.DiscordException as e:
        print(f"Falha ao enviar item {item.id} para canal {sub.channel_id}: {e}")
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
    print(f"[feeds] ciclo: {len(items)} item(ns) novo(s) encontrado(s) no total")
    if not items:
        return stats

    subscriptions = await feed_db.list_subscriptions()
    stats["subscriptions"] = len(subscriptions)
    print(f"[feeds] ciclo: {len(subscriptions)} inscrição(ões) registrada(s) (em todos os servidores)")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SENDS)

    async def _send_with_limit(sub, item):
        async with semaphore:
            return await _send_to_subscription(bot.webhook_session, sub, item)

    for item in items:
        matching_subs = [s for s in subscriptions if _matches_filter(item, s)]
        stats["matched"] += len(matching_subs)
        print(
            f"[feeds] item {item.id} ({item.severity_label}, score={item.severity_score}) "
            f"-> {len(matching_subs)} canal(is) correspondente(s)"
        )

        if not matching_subs:
            continue

        resultados = await asyncio.gather(*(_send_with_limit(sub, item) for sub in matching_subs))

        for sub, (ok, webhook_sumiu) in zip(matching_subs, resultados):
            if ok:
                stats["sent_ok"] += 1
            else:
                stats["sent_failed"] += 1
                if webhook_sumiu:
                    await feed_db.remove_subscription(sub.guild_id, sub.channel_id)

        await feed_db.mark_sent(item.id)

    return stats


def setup_feed_task(bot, interval_seconds=7200):
    classifier = CVEClassifier(is_sent_checker=feed_db.is_sent)
    bot.feed_classifier = classifier

    @tasks.loop(seconds=interval_seconds)
    async def feed_task():
        try:
            await process_feeds_once(bot, classifier)
        except Exception as e:
            print(f"Erro ao processar o ciclo de feeds: {e}")
            traceback.print_exc()

    @feed_task.before_loop
    async def before_feed_task():
        await bot.wait_until_ready()

    @feed_task.error
    async def feed_task_error(error):
        print(f"FEED TASK CRASHOU: {error}")
        traceback.print_exception(type(error), error, error.__traceback__)

    return feed_task