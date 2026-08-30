import asyncio
import logging

import discord

from .cve_spider import CVEClassifier, VulnerabilityData
from database import FeedDatabase, FeedSubscription

logger = logging.getLogger(__name__)


def _build_embed(item: VulnerabilityData) -> discord.Embed:
    embed = discord.Embed(
        title=f"{item.severity_label} {item.title}"[:256],
        url=item.link,
        description=item.summary[:4000],
        color=discord.Color(int(item.color_hex.lstrip("#"), 16)),
    )
    if item.severity_score >= 0:
        embed.add_field(name="Severidade", value=f"{item.severity_score:.1f}")
    else:
        embed.add_field(name="Severidade", value="Desconhecida")
    if item.thumbnail:
        embed.set_thumbnail(url=item.thumbnail)
    return embed


def _matches_filter(item: VulnerabilityData, sub: FeedSubscription) -> bool:
    """Verifica se o item passa no filtro de severidade configurado para a inscrição."""
    if item.severity_score == -1.0:
        return sub.allow_unknown
    return item.severity_score >= sub.min_severity


async def _resolve_channel(bot: discord.Client, channel_id: int) -> discord.abc.Messageable | None:
    channel = bot.get_channel(channel_id)
    if channel is not None:
        return channel
    try:
        return await bot.fetch_channel(channel_id)
    except discord.HTTPException:
        return None


async def _send_to_subscription(bot: discord.Client, sub: FeedSubscription, item: VulnerabilityData) -> None:
    channel = await _resolve_channel(bot, sub.channel_id)
    if channel is None:
        logger.warning(
            "Não foi possível acessar o canal %s no servidor %s", sub.channel_id, sub.guild_id
        )
        return

    embed = _build_embed(item)
    try:
        if isinstance(channel, discord.TextChannel):
            thread = await channel.create_thread(
                name=item.thread_name[:100],
                type=discord.ChannelType.public_thread,
            )
            await thread.send(embed=embed)
        else:
            await channel.send(embed=embed)
    except discord.HTTPException as e:
        logger.error("Falha ao enviar item %s para canal %s: %s", item.id, sub.channel_id, e)
        return

    if item.should_crosspost and sub.crosspost_channel_id:
        crosspost_channel = await _resolve_channel(bot, sub.crosspost_channel_id)
        if crosspost_channel is not None:
            try:
                await crosspost_channel.send(embed=embed)
            except discord.HTTPException as e:
                logger.error("Falha ao crosspostar item %s: %s", item.id, e)


async def process_feeds_once(bot: discord.Client, database: FeedDatabase, classifier: CVEClassifier) -> None:
    items = await classifier.fetch_and_classify()
    if not items:
        return

    subscriptions = await database.list_subscriptions()

    for item in items:
        matching_subs = [s for s in subscriptions if _matches_filter(item, s)]

        if not matching_subs:
            # Nenhuma inscrição bate com esse item ainda — não marca como
            # enviado, para que ele seja reavaliado nos próximos ciclos
            # (ex: alguém pode registrar um canal compatível depois).
            continue

        for sub in matching_subs:
            await _send_to_subscription(bot, sub, item)
            if item.should_crosspost:
                classifier.register_crosspost()

        await database.mark_sent(item.id)


async def run_feed_task(
    bot: discord.Client,
    database: FeedDatabase,
    classifier: CVEClassifier,
    interval_seconds: int = 300,
) -> None:
    """
    Loop assíncrono principal: verifica os feeds periodicamente e envia
    as vulnerabilidades classificadas para os canais inscritos, respeitando
    o filtro de severidade configurado em cada assinatura (guild + canal).
    """
    await bot.wait_until_ready()

    while not bot.is_closed():
        try:
            await process_feeds_once(bot, database, classifier)
        except Exception:
            logger.exception("Erro ao processar o ciclo de feeds")

        await asyncio.sleep(interval_seconds)


def start_feed_task(
    bot: discord.Client,
    database: FeedDatabase,
    classifier: CVEClassifier,
    interval_seconds: int = 300,
) -> asyncio.Task:
    """
    Agenda a task de feeds no loop de eventos do bot (chamar em on_ready
    ou em um setup_hook, por exemplo).

    Exemplo de uso:
        database = FeedDatabase("feeds.db")
        await database.init()

        classifier = CVEClassifier(is_sent_checker=database.is_sent)

        start_feed_task(bot, database, classifier, interval_seconds=300)
    """
    return bot.loop.create_task(
        run_feed_task(bot, database, classifier, interval_seconds=interval_seconds)
    )