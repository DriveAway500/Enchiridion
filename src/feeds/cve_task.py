"""Tarefa periódica que publica novas CVEs nos canais do Discord inscritos.

A cada ciclo, o módulo busca novas CVEs (via ``CVEClassifier``), filtra quais
inscrições devem recebê-las de acordo com a severidade mínima configurada e
envia um embed para cada canal através do webhook da inscrição. Inscrições cujo
webhook não existe mais são removidas automaticamente do banco.
"""

import asyncio
import logging
import json
import hashlib

import discord
from discord.ext import tasks

from .cve_spider import CVEClassifier
from database import feed_db

logger = logging.getLogger(__name__)

# criação das variaveis 
MAX_CONCURRENT_SENDS = 20
SEND_TIMEOUT = 10 # tempo por envio 
UNKNOWN_SEVERITY = -1.0
EMBED_TITLE_LIMIT = 256
EMBED_DESC_LIMIT = 4096
DEFAULT_COLOR = discord.Color.light_grey()
KIND_NEW = "new" #responsavel por dizer se a CVE e nova ou um update
KIND_UPDATE = "update"
# fim


def _fingerprint(item):
    
    relevant = {
        "score": item.severity_score,
        "label": item.severity_label,
        "title": item.title,
        "summary": " ".join((item.summary or "").split()),
    }
    raw = json.dumps(relevant, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

# DOCUMETATION
# Generation a SHA-256 hash of the CVE score, label, title and summary. If any of these fields change,
# the hash changes and the CVE is resent as an update.
# good luck

def _build_embed(item):
    """Monta o embed do Discord para uma CVE.

    Os textos são truncados para respeitar os limites do Discord
    (256 caracteres no título, 4096 na descrição).

    Args:
        item: CVE já classificada, com ``title``, ``link``, ``summary``,
            ``severity_label`` e ``color_hex``.

    Returns:
        discord.Embed: embed pronto para envio.
    """
    return discord.Embed(
        title=f"{item.severity_label} {item.title}"[:256],
        url=item.link,
        description=item.summary[:4000],
        color=discord.Color(int(item.color_hex.lstrip("#"), 16)),
    )


def _matches_filter(item, sub):
    """Verifica se uma CVE deve ser enviada para uma inscrição.

    Args:
        item: CVE classificada. ``severity_score == -1.0`` indica severidade
            desconhecida.
        sub: inscrição com ``min_severity`` e ``allow_unknown``.

    Returns:
        bool: ``True`` se a CVE atinge a severidade mínima da inscrição, ou se a
        severidade é desconhecida e a inscrição aceita esse caso.
    """
    if item.severity_score == -1.0:
        return sub.allow_unknown
    return item.severity_score >= sub.min_severity


async def _send_to_subscription(session, sub, item):
    """Envia uma CVE para o canal da inscrição via webhook.

    Nunca lança exceção: falhas são registradas no log e refletidas no retorno.

    Args:
        session: sessão HTTP (aiohttp) usada pelo webhook.
        sub: inscrição de destino, com ``webhook_url``, ``channel_id`` e ``guild_id``.
        item: CVE a ser enviada.

    Returns:
        tuple[bool, bool]: ``(enviado_com_sucesso, webhook_removido)``. O segundo
        valor é ``True`` quando o Discord responde que o webhook não existe mais,
        sinalizando que a inscrição deve ser apagada.
    """
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
        # Webhook apagado no Discord: a inscrição ficou órfã.
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
    """Executa um ciclo completo do feed de CVEs.

    Passos:
        1. Busca e classifica as CVEs novas (ainda não enviadas).
        2. Carrega todas as inscrições de todos os servidores.
        3. Para cada CVE, envia em paralelo (limitado por
           ``MAX_CONCURRENT_SENDS``) às inscrições que passam no filtro.
        4. Remove inscrições cujo webhook sumiu e marca a CVE como enviada.

    Args:
        bot: instância do bot; precisa expor ``webhook_session``.
        classifier: ``CVEClassifier`` responsável por buscar as CVEs.

    Returns:
        dict: estatísticas do ciclo (``items_found``, ``subscriptions``,
        ``matched``, ``sent_ok``, ``sent_failed``).
    """
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
        """Envia respeitando o limite de concorrência do semáforo."""
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

        # Marca como enviada mesmo com falhas parciais, para não reenviar no próximo ciclo.
        await feed_db.mark_sent(item.id)

    logger.info("Feed cycle finished: %s", stats)
    return stats


def setup_feed_task(bot, interval_seconds=7200):
    """Cria a tarefa em loop que roda ``process_feeds_once`` periodicamente.

    Também anexa o classificador ao bot (``bot.feed_classifier``) para que
    outras partes do código possam reutilizá-lo. A tarefa só começa depois que
    o bot estiver pronto, e erros de um ciclo são logados sem derrubar o loop.

    Args:
        bot: instância do bot do Discord.
        interval_seconds: intervalo entre ciclos, em segundos (padrão: 2 horas).

    Returns:
        discord.ext.tasks.Loop: a tarefa criada; é preciso chamar ``.start()``.
    """
    classifier = CVEClassifier(is_sent_checker=feed_db.is_sent)
    bot.feed_classifier = classifier

    @tasks.loop(seconds=interval_seconds)
    async def feed_task():
        try:
            await process_feeds_once(bot, classifier)
        except Exception:
            # Captura tudo para que um ciclo com erro não interrompa o loop.
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
