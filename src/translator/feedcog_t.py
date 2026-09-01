from database import lang_db

MESSAGES = {
    "PTBR": {
        "errors": {
            "no_webhook_permission": "⚠️ Não tenho permissão de **Gerenciar Webhooks** em {canal}. Dê essa permissão ao bot nesse canal e tente novamente.",
            "webhook_creation_failed": "⚠️ Não consegui criar o webhook em {canal}: {error}",
            "channel_not_registered": "⚠️ {canal} não está registrado. Use `/feeds registrar` primeiro.",
            "no_channels_registered": "Nenhum canal registrado neste servidor ainda.",
            "channel_not_found": "`{channel_id}` (canal não encontrado)",
        },
        "success": {
            "registered": "✅ Feeds registrados em {canal} com severidade mínima **{severidade}**.",
            "severity_updated": "🔧 Filtro de {canal} atualizado para **{severidade}**.",
            "removed": "🗑️ {canal} removido dos feeds de vulnerabilidades.",
        },
        "ui": {
            "list_line": "{canal} — severidade mínima **{min_severity}** (inclui desconhecidas: {desconhecidas})",
            "yes": "sim",
            "no": "não",
        },
    },
    "ES": {
        "errors": {
            "no_webhook_permission": "⚠️ No tengo permiso de **Gestionar Webhooks** en {canal}. Concede este permiso al bot en este canal e inténtalo de nuevo.",
            "webhook_creation_failed": "⚠️ No pude crear el webhook en {canal}: {error}",
            "channel_not_registered": "⚠️ {canal} no está registrado. Usa `/feeds registrar` primero.",
            "no_channels_registered": "Aún no hay canales registrados en este servidor.",
            "channel_not_found": "`{channel_id}` (canal no encontrado)",
        },
        "success": {
            "registered": "✅ Feeds registrados en {canal} con severidad mínima **{severidade}**.",
            "severity_updated": "🔧 Filtro de {canal} actualizado a **{severidade}**.",
            "removed": "🗑️ {canal} eliminado de los feeds de vulnerabilidades.",
        },
        "ui": {
            "list_line": "{canal} — severidad mínima **{min_severity}** (incluye desconocidas: {desconhecidas})",
            "yes": "sí",
            "no": "no",
        },
    },
    "EN": {
        "errors": {
            "no_webhook_permission": "⚠️ I don't have **Manage Webhooks** permission in {canal}. Grant this permission to the bot in this channel and try again.",
            "webhook_creation_failed": "⚠️ Couldn't create webhook in {canal}: {error}",
            "channel_not_registered": "⚠️ {canal} is not registered. Use `/feeds registrar` first.",
            "no_channels_registered": "No channels registered in this server yet.",
            "channel_not_found": "`{channel_id}` (channel not found)",
        },
        "success": {
            "registered": "✅ Feeds registered in {canal} with minimum severity **{severidade}**.",
            "severity_updated": "🔧 Filter for {canal} updated to **{severidade}**.",
            "removed": "🗑️ {canal} removed from vulnerability feeds.",
        },
        "ui": {
            "list_line": "{canal} — minimum severity **{min_severity}** (includes unknown: {desconhecidas})",
            "yes": "yes",
            "no": "no",
        },
    },
}

async def feedcog_translate(guild_id, *keys, **kwargs):
    result = MESSAGES[await lang_db.get_language(guild_id, default="EN")]
    for key in keys:
        result = result[key]
    return result.format(**kwargs)