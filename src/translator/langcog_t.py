from database import lang_db

LANG_MESSAGES = {
    "PTBR": {
        "success": {
            "changed": "🌐 Idioma do servidor alterado para: **{nome}** (`{codigo}`).",
            "current": "🌐 O idioma atual do servidor é: **{nome}** (`{codigo}`).",
        }
    },
    "ES": {
        "success": {
            "changed": "🌐 Idioma del servidor cambiado a: **{nome}** (`{codigo}`).",
            "current": "🌐 El idioma actual del servidor es: **{nome}** (`{codigo}`).",
        }
    },
    "EN": {
        "success": {
            "changed": "🌐 Server language changed to: **{nome}** (`{codigo}`).",
            "current": "🌐 Current server language is: **{nome}** (`{codigo}`).",
        }
    },
}

async def langcog_translate(guild_id, *keys, **kwargs):
    result = LANG_MESSAGES[await lang_db.get_language(guild_id, default="EN")]
    for key in keys:
        result = result[key]
    return result.format(**kwargs)