<div align="center">

# 📖 Enchiridion

**Um bot de Discord para OSINT e inteligência de vulnerabilidades — CVEs, CISA KEV, Exploit-DB e 0day.today, tudo em um só lugar.**

[🇺🇸 English](README.md) · 🇧🇷 **Português** · [🇷🇺 Русский](README.ru.md) · [🇨🇳 中文](README.zh-CN.md)

[![Architecture diagram](https://gitdiagram.com/diagram-badge.svg)](https://gitdiagram.com/driveaway500/enchiridion?utm_source=readme&utm_medium=badge)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Rust](https://img.shields.io/badge/rust-chart--lib-orange)
![discord.py](https://img.shields.io/badge/discord.py-2.x-5865F2)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## 🎯 Para que serve este repositório e para quem ele vai ajudar

O **Enchiridion** (do grego, *"manual"*) leva inteligência de vulnerabilidades para o lugar onde muitas equipes e comunidades de segurança já conversam: o **Discord**. Em vez de pular entre NVD, CISA, Exploit-DB e outros sites, os membros do servidor usam um comando de barra e recebem a resposta formatada e paginada no próprio canal — ou recebem novas CVEs automaticamente, filtradas por severidade.

### O problema que ele resolve

- Os dados de vulnerabilidades estão espalhados em várias fontes, cada uma com sua própria interface.
- Acompanhar CVEs novas manualmente é lento e fácil de esquecer.
- Equipes que falam idiomas diferentes precisam da mesma informação na sua língua.

### Para quem ele serve

| Público | Como o Enchiridion ajuda |
| --- | --- |
| **Analistas de SOC e Blue Teams** | Feed automático de CVEs por canal, filtrado por severidade mínima; consulta rápida de score CVSS, vetor e referências durante a triagem. |
| **Pentesters, Red Teams e caçadores de bug bounty** | Busca no Exploit-DB e no 0day.today por nome ou CVE e leitura do código do exploit dentro do Discord. |
| **Sysadmins e DevOps** | Busca de CVEs por pacote/produto e ano (ex.: `openssl`, `sudo`, `linux`) para saber se a sua stack é afetada. |
| **Gestores de vulnerabilidades** | Consulta ao catálogo **CISA KEV** (vulnerabilidades sendo exploradas ativamente), com prazo de correção e uso em ransomware. |
| **Comunidades de segurança, times de CTF e estudantes** | Uma base de conhecimento compartilhada, gratuita e multilíngue (PT-BR / EN / ES) dentro do servidor, com gráfico radar do CVSS que facilita entender as métricas. |
| **Desenvolvedores** | Um exemplo organizado de bot `discord.py` modular, com cogs, SQLite assíncrono, motor de feeds HTTP e extensão em Rust feita com PyO3. |

> ⚠️ **Uso responsável:** o Enchiridion mostra informações e códigos de exploit públicos. Use apenas para defesa, pesquisa, ensino e testes em sistemas que você tem autorização para testar.

---

## ✨ Funcionalidades

- 🔎 **Busca de CVE** por ID (`CVE-2021-44228`) ou por pacote + ano + severidade, com paginação.
- 📊 **Gráfico radar do CVSS** (PNG) para cada CVE, gerado por uma biblioteca nativa em **Rust** (`chart-lib`).
- 💥 **Busca no Exploit-DB** e no **0day.today**, com botão que mostra o código do exploit (enviado como arquivo quando passa de 2000 caracteres).
- 🚨 **Busca no CISA KEV** (`/active_cve`) — vulnerabilidades sabidamente exploradas no mundo real.
- 📡 **Feed automático de CVEs**: a cada 2 horas o bot lê o `cvefeed.io`, remove duplicadas e publica as CVEs novas nos canais cadastrados por webhook, respeitando a severidade mínima de cada canal.
- 🌐 **Idioma por servidor**: Português (Brasil), Inglês e Espanhol.
- 🧾 **Logs organizados**: log diário rotativo e um arquivo de erros por módulo.

---

## 💬 Comandos de barra

| Comando | Parâmetros | Permissão | O que faz |
| --- | --- | --- | --- |
| `/cve` | `method`: *CVE ID* ou *Package Name* | todos | Abre um modal. **CVE ID** → detalhes com gráfico radar e referências. **Pacote** → escolha severidade, ano (2002–2026) e pacote/termo; lista paginada. |
| `/exploitdb` | `search` (mín. 3 caracteres) | todos | Busca no Exploit-DB; cada resultado tem um botão para ver o código. |
| `/zerodaytoday` | `search` (mín. 3 caracteres) | todos | Busca no 0day.today (base desde 2004); cada resultado tem um botão para ver o código. |
| `/active_cve` | `query` (ex.: *Windows*, *Chrome*) | todos | Busca no catálogo CISA KEV; destaque vermelho quando usada em campanhas de ransomware. |
| `/help` | `opcao`: exploitdb, cve, zerodaytoday | todos | Explica cada ferramenta de busca no idioma do servidor. |
| `/language set` | `idioma`: PTBR, EN, ES | Gerenciar Servidor | Define o idioma do servidor. |
| `/language current` | — | Gerenciar Servidor | Mostra o idioma atual. |
| `/feeds register` | `channel`, `severity`, `include_unknown` | Gerenciar Servidor + Gerenciar Webhooks | Cria um webhook no canal e o inscreve no feed de CVEs. |
| `/feeds severity` | `channel`, `severity`, `include_unknown` | Gerenciar Servidor + Gerenciar Webhooks | Altera o filtro de severidade de um canal já cadastrado. |
| `/feeds remove` | `channel` | Gerenciar Servidor + Gerenciar Webhooks | Apaga o webhook e a inscrição. |
| `/feeds list` | — | Gerenciar Servidor + Gerenciar Webhooks | Lista os canais cadastrados e seus filtros. |

Opções de severidade do feed: **Critical (9.0+)**, **High (7.0+)**, **Medium (4.0+)**, **All (0.0, inclui desconhecidas)**.
Todos os comandos funcionam apenas em servidores (`guild_only`).

---

## 🏗️ Arquitetura

```
                         ┌────────────────────────────┐
  Usuários do Discord ─► │  Cogs (comandos de barra)  │
                         │  src/cogs/*                │
                         └──────┬──────────────┬──────┘
                                │              │
                     ┌──────────▼───┐   ┌──────▼──────────┐
                     │ UI (views,   │   │ Tradutor         │◄── lang_db (SQLite)
                     │ modais)      │   │ PTBR / EN / ES   │
                     │ src/ui/*     │   └──────────────────┘
                     └──┬───────┬───┘
                        │       │
          ┌─────────────▼─┐   ┌─▼──────────────────────┐
          │ omega_api/*   │   │ graph/cve_radar.py      │
          │ (httpx)       │   │  └─► chart_lib (Rust)   │
          └──────┬────────┘   └─────────────────────────┘
                 │ HTTP  http://127.0.0.1:3000
                 ▼
          ┌──────────────┐
          │  Omega-Api   │  (projeto separado: dados de CVE / Exploit-DB / 0day / KEV)
          └──────────────┘

  Feed periódico (a cada 2 h):
  cvefeed.io ──► FeedFetcher (engine.py) ──► CVEFeedParser ──► deduplicação (feed_db)
            ──► filtro de severidade por inscrição ──► webhooks do Discord
```

Há um diagrama interativo em [docs/architecture.html](docs/architecture.html).

**Dependência principal:** o bot não coleta os dados diretamente das fontes. As buscas vão para a **[Omega-Api](https://github.com/DriveAway500/Omega-Api)**, uma API separada que precisa estar rodando em `http://127.0.0.1:3000`. Só o feed de CVEs acessa a internet diretamente (`cvefeed.io`).

---

## 📁 Estrutura do projeto

```
Enchiridion/
├── README*.md                 # Esta documentação (EN, PT-BR, RU, ZH-CN)
├── LICENSE                    # MIT
├── requirements.txt           # Dependências Python
├── .env                       # Tokens (não vai para o git)
├── chart-lib/                 # Biblioteca Rust (PyO3 + plotters + resvg) → módulo `chart_lib`
│   ├── src/lib.rs             # CVSSRadarChartGenerator: JSON CVSS → PNG radar
│   ├── Cargo.toml / pyproject.toml
│   └── .github/workflows/CI.yml  # Build de wheels com Maturin (Linux, musl, Windows, macOS)
├── docs/
│   ├── SETUP.MD               # Guia de instalação passo a passo (Arch Linux)
│   ├── architecture.html      # Diagrama interativo da arquitetura
│   └── feeds/
│       ├── ENGINE.MD          # Referência do motor de feeds
│       ├── ENGMAN.MD          # Manual de modificação do motor
│       └── CVETASK.MD         # Referência da tarefa periódica de feed
└── src/
    ├── main.py                # Ponto de entrada: carrega .env, configura logs, inicia o bot
    ├── bot.py                 # EnchiridionBot: carrega cogs, sincroniza comandos, inicia o feed
    ├── httpx_client.py        # Cliente httpx compartilhado para a Omega-Api + APIError/NotFoundError
    ├── cogs/                  # Comandos de barra (cve, exploit, zeroday, kev, help, lang, feed)
    ├── ui/                    # Views, modais, botões e paginação do Discord
    ├── omega_api/             # Funções assíncronas simples para cada rota da Omega-Api
    ├── feeds/                 # engine.py (HTTP), cve_task.py (loop periódico), kev_task.py
    ├── parser/                # cve_parser.py (RSS/Atom → objetos tipados), kev_parser.py
    ├── database/              # feed_db, lang_db (aiosqlite), json_handler (JSON atômico)
    ├── graph/                 # cve_radar.py: camada assíncrona sobre o chart_lib
    └── translator/            # Textos PTBR/EN/ES de cada cog
```

---

## 🧩 Referência dos módulos

### Núcleo

| Arquivo | Responsabilidade |
| --- | --- |
| `src/main.py` | Carrega o `.env` da raiz do repositório, configura os logs e inicia o bot. A flag `DEV` escolhe `DEV_TOKEN` (`True`) ou `DISCORD_TOKEN` (`False`) e o nível de log (DEBUG/INFO). Registra handlers para exceções não tratadas na thread principal e nas demais threads. |
| `src/bot.py` | `EnchiridionBot(commands.Bot)` com `Intents.all()`. No `setup_hook` abre uma sessão `aiohttp` para webhooks, carrega os 7 cogs, sincroniza a árvore global de comandos e inicia a tarefa de feed. Status: *"Searching Exploits..."*. |
| `src/httpx_client.py` | `httpx.AsyncClient` global apontando para `BASE_URL = http://127.0.0.1:3000` (timeouts 5/10/5/5 s, máx. 20 conexões). `request_json()` transforma 404 em `NotFoundError` (ou `None` com `not_found_ok=True`), ≥400 em `APIError` e 204/vazio em `None`. `get_http_client()` cria um cliente separado para o motor de feeds. |

### `omega_api/` — rotas da Omega-Api

| Função | Método e rota | Corpo / observações |
| --- | --- | --- |
| `get_cve(cve_id)` | `POST /cve/search` | `{"cve_id"}` |
| `search_cve_by_package(package_name, year, severity, page, limit)` | `POST /cve/search/package` | `{"package_name","year","limit","offset","severity"?}` |
| `search_exploits(query, page, limit)` | `POST /exploit/search` | `{"q","limit","offset"}` |
| `get_exploit(exploit_id)` | `POST /exploit/get` | `{"exploit_id"}` |
| `search_zeroday_exploits(query, page, limit)` | `POST /zeroday/search` | `{"q","limit","offset"}` |
| `get_zeroday_exploit(exploit_id)` | `POST /zeroday/get` | `{"exploit_id"}` |
| `get_kev_new()` / `get_kev_removed()` / `get_kev_diff()` | `GET /kev/new`, `/kev/removed`, `/kev/diff` | Mudanças entre builds do índice KEV |
| `search_kev(q, fields, page, limit)` | `POST /kev/search` | Busca por texto livre |
| `get_kev_entry(cve_id)` | `GET /kev/get/{cve_id}` | Uma entrada do KEV |

A paginação sempre usa `offset = (page - 1) * limit`, com 5 resultados por página.

### `feeds/` — feed automático de CVEs

- **`engine.py`** — motor HTTP só de transporte. `FeedFetcher.fetch_many()` baixa vários feeds em paralelo (padrão 5), compartilhando um cliente, e devolve um resultado por fonte, na mesma ordem. Nunca lança exceção por erro de rede/HTTP: retorna `FeedFetchSuccess` ou `FeedFetchFailure` (`TRANSPORT` ou `HTTP_STATUS`). Suporta `ETag`/`Last-Modified`. Detalhes: [docs/feeds/ENGINE.MD](docs/feeds/ENGINE.MD) e [docs/feeds/ENGMAN.MD](docs/feeds/ENGMAN.MD).
- **`cve_task.py`** — a camada de regras. `setup_feed_task(bot, interval_seconds=7200)` cria um loop do `discord.ext.tasks` que espera o bot ficar pronto e executa `process_feeds_once()`: baixa → interpreta → deduplica (no ciclo e contra o `feed_db`) → filtra por `min_severity`/`allow_unknown` → envia embeds via webhook (máx. 20 em paralelo, timeout de 10 s cada). Se o Discord responder que o webhook não existe mais, a inscrição é removida automaticamente. Todo item processado é marcado como enviado, mesmo que alguma entrega falhe. Detalhes: [docs/feeds/CVETASK.MD](docs/feeds/CVETASK.MD).
- **`kev_task.py`** — protótipo para publicar novas entradas do KEV via webhook. Ainda não está ligado ao bot.

### `parser/`

- **`cve_parser.py`** — `CVEFeedParser.parse(FeedResponse)` usa o `feedparser`, remove HTML, corta o resumo em 3000 caracteres e extrai o score de textos como `CVSS: 9.8` / `Severity - 7`. Classificação: **CRITICAL ≥ 9.0**, **HIGH ≥ 7.0**, **MEDIUM ≥ 4.0**, **LOW > 0**, **UNKNOWN** sem score; score ≤ 0 é descartado. As entradas saem da mais antiga para a mais nova.
- **`kev_parser.py`** — `KevParser` converte as respostas KEV da Omega-Api em dataclasses `KevNew`/`KevRemoved`. Para detectar mudanças, guarda um SHA-256 da última resposta em `src/database/kve_sha.json` (a primeira execução só salva a referência).

### `database/`

| Arquivo | Armazenamento | Conteúdo |
| --- | --- | --- |
| `feed_db.py` | `src/database/feeds.db` | Tabela `subscriptions` (guild_id, channel_id, min_severity, allow_unknown, webhook_url) e tabela `sent_items` (item_id, sent_at) para deduplicação. |
| `lang_db.py` | `src/database/language.db` | Tabela `guild_languages` (guild_id, language). Padrão: `EN`. |
| `json_handler.py` | qualquer `.json` | Leitura e escrita de JSON validada (`list[dict]`) e **atômica** (arquivo temporário + `os.replace`). |

As tabelas são criadas automaticamente no primeiro uso. `*.db` e `kve_sha.json` estão no `.gitignore`.

### `ui/`

Feita com os **Components V2** do discord.py (`LayoutView`, `Container`, `TextDisplay`, `MediaGallery`, `Label`). Cada painel mostra 5 resultados com botões *Anterior / Página N / Próxima* e se desativa depois de 180 s.

- `cve_modal.py` — modais de busca por ID (validado com `^CVE-\d{4}-\d{4,7}$`) e por pacote.
- `cve_view.py` — `CVEDetailView` (status, datas, score CVSS v4.0 ou v3.1, vetor, descrição, até 3 links de referência, gráfico radar) e `CVEPanel` (lista paginada).
- `exploit_ui.py` / `zeroday_ui.py` — painéis de resultados; o botão mostra o código em bloco de código ou como anexo se passar de 2000 caracteres, reaproveitando a mesma mensagem.
- `kev_ui.py` — `KevView` (CVE, fornecedor, produto, CWE, descrição, ação exigida, datas, ransomware) e `KevPanel`.

### `graph/` e `chart-lib/`

`graph/cve_radar.py` (`CVSSRadar`) recebe um `dict` ou string JSON do NVD e chama a biblioteca Rust. O `chart-lib` converte 7 métricas CVSS (AV, AC, PR, UI, C, I, A) para uma escala de 0 a 10, desenha um radar SVG com `plotters`, converte para PNG com `resvg`/`tiny-skia` e roda o trabalho em `tokio::spawn_blocking` para não travar o event loop do Python. Precisa de fontes instaladas no sistema (ex.: DejaVu); sem elas, devolve um erro explícito.

### `translator/`

Um arquivo por cog (`cvecog_t`, `exploitdbcog_t`, `zerodaycog_t`, `feedcog_t`, `helpcog_t`, `langcog_t`) com um dicionário `{"PTBR"|"EN"|"ES": {...}}`. As funções `*_translate(guild_id, *keys, **kwargs)` leem o idioma do servidor no `lang_db` e formatam o texto.

---

## ⚙️ Configuração

### Arquivo `.env` (raiz do repositório)

```env
DISCORD_TOKEN=seu_token_de_producao
DEV_TOKEN=seu_token_de_desenvolvimento
```

O `src/main.py` está com `DEV = True`; nesse modo ele lê **`DEV_TOKEN`**. Mude para `DEV = False` para usar `DISCORD_TOKEN`.

### Valores no código

| Configuração | Onde | Padrão |
| --- | --- | --- |
| URL da Omega-Api | `src/httpx_client.py` → `BASE_URL` | `http://127.0.0.1:3000` |
| Intervalo do feed | `setup_feed_task(interval_seconds=...)` | `7200` s (2 h) |
| Feeds monitorados | `DEFAULT_FEED_URLS` em `cve_task.py` | `https://cvefeed.io/rssfeed/latest.atom` |
| Envios paralelos por webhook | `MAX_CONCURRENT_SENDS` | `20` |
| Timeout por envio | `WEBHOOK_SEND_TIMEOUT_SECONDS` | `10.0` s |
| Resultados por página | `PAGE_SIZE` em `src/ui/*` | `5` |

### Discord Developer Portal

O bot usa `discord.Intents.all()`, então ative os **intents privilegiados** (Presence, Server Members, Message Content) no portal. No servidor ele precisa enviar mensagens, embeds e arquivos, e ter **Gerenciar Webhooks** nos canais que vão receber o feed.

---

## 🚀 Instalação (resumo)

O guia completo passo a passo está em **[docs/SETUP.MD](docs/SETUP.MD)**. Resumindo:

```bash
# 1. Instale e inicie a Omega-Api (projeto separado)
git clone https://github.com/DriveAway500/Omega-Api.git

# 2. Ambiente virtual e dependências
cd Enchiridion
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Compile a biblioteca Rust (precisa de Rust + fontes do sistema, como DejaVu)
cd chart-lib
maturin develop --release
cd ..

# 4. Crie o .env e inicie
python src/main.py
```

Requisitos: Python 3.10+ (o código usa a sintaxe `X | Y` e `slots=True`), Rust (edition 2024), discord.py com suporte a Components V2 e a Omega-Api rodando.

---

## 📜 Logs

| Destino | Conteúdo |
| --- | --- |
| `logs/bot.log` | Tudo (DEBUG no modo DEV), rotacionado à meia-noite, guarda 14 dias. |
| `logs/errors/<módulo>.log` | Só ERROR/CRITICAL, separados pelo módulo do projeto onde o erro começou (5 MB × 3 backups). |
| console | Mesmo nível do `bot.log`. |

As bibliotecas `discord` e `discord.http` ficam em INFO/WARNING para reduzir ruído.

---

## 🚧 Limitações conhecidas / próximos passos

- **Feed do KEV ainda não está ligado:** `src/feeds/kev_task.py` é um protótipo (usa um `WEBHOOK_URL` não definido e não é iniciado pelo bot). Hoje só o feed de CVEs é automático.
- **Interface do KEV só em inglês:** `/active_cve` e `kev_ui.py` ainda não usam o tradutor.
- **`/help`** cobre apenas `exploitdb`, `cve` e `zerodaytoday`.
- **URL da Omega-Api fixa** no código (`BASE_URL`), não configurável pelo `.env`.
- **`ETag`/`Last-Modified` do feed** não são guardados entre ciclos, então o feed inteiro é baixado a cada 2 horas.
- **Lista de anos** da busca por pacote é fixa (2002–2026).
- **`requirements.txt` sem versões fixas** e com `dotenv` e `python-dotenv` ao mesmo tempo; o projeto só precisa do `python-dotenv`.
- **Licença:** o projeto é MIT, mas `src/database/json_handler.py` tem o cabeçalho `SPDX-License-Identifier: GPL-3.0-only`.

---

## 📚 Mais documentação

- [docs/SETUP.MD](docs/SETUP.MD) — guia de instalação
- [docs/architecture.html](docs/architecture.html) — diagrama da arquitetura
- [docs/feeds/ENGINE.MD](docs/feeds/ENGINE.MD) — motor de feeds
- [docs/feeds/ENGMAN.MD](docs/feeds/ENGMAN.MD) — manual de modificação do motor
- [docs/feeds/CVETASK.MD](docs/feeds/CVETASK.MD) — tarefa periódica de feed

---

## 📄 Licença

[MIT](LICENSE) © 2026 DriveAway500
