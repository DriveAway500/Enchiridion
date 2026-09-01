from database import lang_db

ZERODAY_MESSAGES = {
    "PTBR": {
        "commands": {
            "cmd_desc": "Pesquisar exploits no 0daytoday",
            "arg_search_desc": "Termo de pesquisa (texto livre ou CVE)",
        },
        "errors": {
            "too_short": "❌ O termo de pesquisa é muito curto (mínimo de 3 caracteres).",
            "not_found": "🔍 Nenhum zero-day encontrado para `{search}`.",
            "load_failed": "❌ Não foi possível carregar o código para este exploit.",
        },
        "ui": {
            "btn_view": "Ver Exploit",
            "btn_prev": "◀ Anterior",
            "btn_next": "Próximo ▶",
            "page_indicator": "Página {page}",
            "lbl_category": "Categoria",
            "lbl_platform": "Plataforma",
            "lbl_date": "Data",
            "lbl_author": "Autor",
        },
    },
    "ES": {
        "commands": {
            "cmd_desc": "Buscar exploits en 0daytoday",
            "arg_search_desc": "Término de búsqueda (texto libre o CVE)",
        },
        "errors": {
            "too_short": "❌ El término de búsqueda es demasiado corto (mínimo 3 caracteres).",
            "not_found": "🔍 No se encontró ningún zero-day para `{search}`.",
            "load_failed": "❌ No se pudo cargar el código de este exploit.",
        },
        "ui": {
            "btn_view": "Ver Exploit",
            "btn_prev": "◀ Anterior",
            "btn_next": "Siguiente ▶",
            "page_indicator": "Página {page}",
            "lbl_category": "Categoría",
            "lbl_platform": "Plataforma",
            "lbl_date": "Fecha",
            "lbl_author": "Autor",
        },
    },
    "EN": {
        "commands": {
            "cmd_desc": "Search exploits on 0daytoday",
            "arg_search_desc": "Search query (free text or CVE)",
        },
        "errors": {
            "too_short": "❌ Search query too short (minimum 3 characters).",
            "not_found": "🔍 No zero-day found for `{search}`.",
            "load_failed": "❌ Could not load code for this exploit.",
        },
        "ui": {
            "btn_view": "View Exploit",
            "btn_prev": "◀ Previous",
            "btn_next": "Next ▶",
            "page_indicator": "Page {page}",
            "lbl_category": "Category",
            "lbl_platform": "Platform",
            "lbl_date": "Date",
            "lbl_author": "Author",
        },
    },
}

async def zerodaycog_translate(guild_id, *keys, **kwargs):
    result = ZERODAY_MESSAGES[await lang_db.get_language(guild_id, default="EN")]
    for key in keys:
        result = result[key]
    return result.format(**kwargs)