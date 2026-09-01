from database import lang_db

HELP_MESSAGES = {
    "PTBR": {
        "errors": {
            "not_found": "⚠️ Nenhuma informação encontrada para a opção selecionada.",
        },
        "docs": {
            "exploitdb": "Pesquisa exploits no Exploit Database. Use este comando para encontrar exploits públicos relacionados a uma vulnerabilidade, produto, versão ou identificador CVE.",
            "cve": "Pesquisa informações sobre vulnerabilidades identificadas por CVE ou pacote. Voce pode utilizar descricoes complexas ao pesquisar por pacote, incluindo versoes, vulnerabilidades etc. Retorna detalhes como descrição, severidade, pontuação CVSS, produtos afetados e outras informações disponíveis.",
            "zerodaytoday": "Pesquisa vulnerabilidades e exploits associados ao 0daytoday. Use este comando para consultar vulnerabilidades antigas, vindas de uma database com vulnerabilidades desde 2004",
        },
    },
    "ES": {
        "errors": {
            "not_found": "⚠️ No se encontró información para la opción seleccionada.",
        },
        "docs": {
            "exploitdb": "Busca exploits en Exploit Database. Utiliza este comando para encontrar exploits públicos relacionados con una vulnerabilidad, producto, versión o identificador CVE.",
            "cve": "Busca información sobre vulnerabilidades identificadas por CVE o paquete. Puedes utilizar descripciones complejas al buscar por paquete, incluyendo versiones, vulnerabilidades, etc. Devuelve detalles como descripción, severidad, puntuación CVSS, productos afectados y otra información disponible.",
            "zerodaytoday": "Busca vulnerabilidades y exploits asociados a 0daytoday. Utiliza este comando para consultar vulnerabilidades antiguas provenientes de una base de datos con vulnerabilidades desde 2004.",
        },
    },
    "EN": {
        "errors": {
            "not_found": "⚠️ No information found for the selected option.",
        },
        "docs": {
            "exploitdb": "Searches exploits in the Exploit Database. Use this command to find public exploits related to a vulnerability, product, version, or CVE identifier.",
            "cve": "Searches information about vulnerabilities identified by CVE or package. You can use complex descriptions when searching by package, including versions, vulnerabilities, etc. Returns details such as description, severity, CVSS score, affected products, and other available information.",
            "zerodaytoday": "Searches vulnerabilities and exploits associated with 0daytoday. Use this command to consult old vulnerabilities coming from a database with vulnerabilities since 2004.",
        },
    },
}

async def helpcog_translate(guild_id, *keys, **kwargs):
    result = HELP_MESSAGES[await lang_db.get_language(guild_id, default="EN")]
    for key in keys:
        result = result[key]
    return result.format(**kwargs)