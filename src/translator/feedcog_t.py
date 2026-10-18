import logging

from database import lang_db

logger = logging.getLogger(__name__)

MESSAGES = {
    "PTBR": {
        "errors": {
            "no_webhook_permission": "⚠️ Não tenho permissão de **Gerenciar Webhooks** em {channel}. Dê essa permissão ao bot nesse canal e tente novamente.",
            "webhook_creation_failed": "⚠️ Não consegui criar o webhook em {channel}: {error}",
            "channel_not_registered": "⚠️ {channel} não está registrado. Use `/feeds register` primeiro.",
            "no_channels_registered": "Nenhum canal registrado neste servidor ainda.",
            "channel_not_found": "`{channel_id}` (canal não encontrado)",
        },
        "success": {
            "registered": "✅ Feeds registrados em {channel} com severidade mínima **{severity}**.",
            "severity_updated": "🔧 Filtro de {channel} atualizado para **{severity}**.",
            "removed": "🗑️ {channel} removido dos feeds de vulnerabilidades.",
        },
        "ui": {
            "list_line": "{channel} — severidade mínima **{min_severity}** (inclui desconhecidas: {unknown})",
            "yes": "sim",
            "no": "não",
        },
    },
    "ES": {
        "errors": {
            "no_webhook_permission": "⚠️ No tengo permiso de **Gestionar Webhooks** en {channel}. Concede este permiso al bot en este canal e inténtalo de nuevo.",
            "webhook_creation_failed": "⚠️ No pude crear el webhook en {channel}: {error}",
            "channel_not_registered": "⚠️ {channel} no está registrado. Usa `/feeds register` primero.",
            "no_channels_registered": "Aún no hay canales registrados en este servidor.",
            "channel_not_found": "`{channel_id}` (canal no encontrado)",
        },
        "success": {
            "registered": "✅ Feeds registrados en {channel} con severidad mínima **{severity}**.",
            "severity_updated": "🔧 Filtro de {channel} actualizado a **{severity}**.",
            "removed": "🗑️ {channel} eliminado de los feeds de vulnerabilidades.",
        },
        "ui": {
            "list_line": "{channel} — severidad mínima **{min_severity}** (incluye desconocidas: {unknown})",
            "yes": "sí",
            "no": "no",
        },
    },
    "EN": {
        "errors": {
            "no_webhook_permission": "⚠️ I don't have **Manage Webhooks** permission in {channel}. Grant this permission to the bot in this channel and try again.",
            "webhook_creation_failed": "⚠️ Couldn't create webhook in {channel}: {error}",
            "channel_not_registered": "⚠️ {channel} is not registered. Use `/feeds register` first.",
            "no_channels_registered": "No channels registered in this server yet.",
            "channel_not_found": "`{channel_id}` (channel not found)",
        },
        "success": {
            "registered": "✅ Feeds registered in {channel} with minimum severity **{severity}**.",
            "severity_updated": "🔧 Filter for {channel} updated to **{severity}**.",
            "removed": "🗑️ {channel} removed from vulnerability feeds.",
        },
        "ui": {
            "list_line": "{channel} — minimum severity **{min_severity}** (includes unknown: {unknown})",
            "yes": "yes",
            "no": "no",
        },
    },
}


async def feedcog_translate(guild_id, *keys, **kwargs):
    lang = await lang_db.get_language(guild_id, default="EN")
    result = MESSAGES.get(lang, MESSAGES["EN"])
    for key in keys:
        result = result[key]

    try:
        return result.format(**kwargs)
    except (KeyError, IndexError) as error:
        logger.error("Placeholder inválido em %s (%s): %r", keys, lang, error)
        return result