<div align="center">

# 📖 Enchiridion

**A Discord bot for OSINT and vulnerability intelligence — CVEs, CISA KEV, Exploit-DB and 0day.today, all in one place.**

🇺🇸 **English** · [🇧🇷 Português](README.pt-BR.md) · [🇷🇺 Русский](README.ru.md) · [🇨🇳 中文](README.zh-CN.md)

[![Architecture diagram](https://gitdiagram.com/diagram-badge.svg)](https://gitdiagram.com/driveaway500/enchiridion?utm_source=readme&utm_medium=badge)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Rust](https://img.shields.io/badge/rust-chart--lib-orange)
![discord.py](https://img.shields.io/badge/discord.py-2.x-5865F2)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## 🎯 What this repository is for and who it helps

**Enchiridion** (Greek for *"handbook"*) brings vulnerability intelligence into the place where many security teams and communities already talk: **Discord**. Instead of jumping between NVD, CISA, Exploit-DB and other sites, members of a server run a slash command and get a formatted, paginated answer right in the channel — or receive new CVEs automatically, filtered by severity.

### The problem it solves

- Vulnerability data is scattered across many sources, each with its own interface.
- Following new CVEs by hand is slow and easy to forget.
- Teams that speak different languages need the same information in their own language.

### Who it helps

| Audience | How Enchiridion helps |
| --- | --- |
| **SOC analysts and Blue Teams** | Automatic CVE feed per channel, filtered by minimum severity; quick lookups of CVSS score, vector and references while triaging. |
| **Pentesters, Red Teams and bug-bounty hunters** | Search Exploit-DB and 0day.today by name or CVE and read the exploit code inside Discord. |
| **Sysadmins and DevOps** | Search CVEs by package/product and year (e.g. `openssl`, `sudo`, `linux`) to see if their stack is affected. |
| **Vulnerability managers** | Check the **CISA KEV** catalog (vulnerabilities being actively exploited), including the remediation deadline and ransomware usage. |
| **Security communities, CTF teams and students** | A shared, free and multilingual (PT-BR / EN / ES) knowledge base inside the server, with a CVSS radar chart that makes metrics easier to understand. |
| **Developers** | A clean example of a modular `discord.py` bot with cogs, async SQLite, an HTTP feed engine and a Rust extension built with PyO3. |

> ⚠️ **Responsible use:** Enchiridion shows public information and public exploit code. Use it only for defense, research, education and testing on systems you are authorized to test.

---

## ✨ Features

- 🔎 **CVE search** by ID (`CVE-2021-44228`) or by package + year + severity, with pagination.
- 📊 **CVSS radar chart** (PNG) for each CVE, rendered by a native **Rust** library (`chart-lib`).
- 💥 **Exploit-DB** and **0day.today** search, with a button that shows the exploit code (sent as a file when it exceeds 2000 characters).
- 🚨 **CISA KEV** search (`/active_cve`) — vulnerabilities known to be exploited in the wild.
- 📡 **Automatic CVE feed**: every 2 hours the bot reads `cvefeed.io`, removes duplicates and posts new CVEs to registered channels through webhooks, respecting each channel's minimum severity.
- 🌐 **Per-server language**: Portuguese (Brazil), English and Spanish.
- 🧾 **Structured logging**: daily rotating log plus one error file per module.

---

## 💬 Slash commands

| Command | Parameters | Permission | What it does |
| --- | --- | --- | --- |
| `/cve` | `method`: *CVE ID* or *Package Name* | everyone | Opens a modal. **CVE ID** → detail view with radar chart and references. **Package** → choose severity, year (2002–2026) and package/term; paginated list. |
| `/exploitdb` | `search` (min. 3 chars) | everyone | Searches Exploit-DB; each result has a button to view the code. |
| `/zerodaytoday` | `search` (min. 3 chars) | everyone | Searches 0day.today (database since 2004); each result has a button to view the code. |
| `/active_cve` | `query` (e.g. *Windows*, *Chrome*) | everyone | Searches the CISA KEV catalog; red highlight when used in ransomware campaigns. |
| `/help` | `opcao`: exploitdb, cve, zerodaytoday | everyone | Explains each search tool in the server's language. |
| `/language set` | `idioma`: PTBR, EN, ES | Manage Server | Sets the server language. |
| `/language current` | — | Manage Server | Shows the current language. |
| `/feeds register` | `channel`, `severity`, `include_unknown` | Manage Server + Manage Webhooks | Creates a webhook in the channel and subscribes it to the CVE feed. |
| `/feeds severity` | `channel`, `severity`, `include_unknown` | Manage Server + Manage Webhooks | Changes the severity filter of a registered channel. |
| `/feeds remove` | `channel` | Manage Server + Manage Webhooks | Deletes the webhook and the subscription. |
| `/feeds list` | — | Manage Server + Manage Webhooks | Lists registered channels and their filters. |

Severity options for feeds: **Critical (9.0+)**, **High (7.0+)**, **Medium (4.0+)**, **All (0.0, includes unknown)**.
All commands are server-only (`guild_only`).

---

## 🏗️ Architecture

```
                         ┌────────────────────────────┐
  Discord users ───────► │  Cogs (slash commands)     │
                         │  src/cogs/*                │
                         └──────┬──────────────┬──────┘
                                │              │
                     ┌──────────▼───┐   ┌──────▼──────────┐
                     │ UI (views,   │   │ Translator       │◄── lang_db (SQLite)
                     │ modals)      │   │ PTBR / EN / ES   │
                     │ src/ui/*     │   └──────────────────┘
                     └──┬───────┬───┘
                        │       │
          ┌─────────────▼─┐   ┌─▼──────────────────────┐
          │ omega_api/*   │   │ graph/cve_radar.py      │
          │ (httpx client)│   │  └─► chart_lib (Rust)   │
          └──────┬────────┘   └─────────────────────────┘
                 │ HTTP  http://127.0.0.1:3000
                 ▼
          ┌──────────────┐
          │  Omega-Api   │  (separate project: CVE / Exploit-DB / 0day / KEV data)
          └──────────────┘

  Periodic feed (every 2 h):
  cvefeed.io ──► FeedFetcher (engine.py) ──► CVEFeedParser ──► dedup (feed_db)
            ──► severity filter per subscription ──► Discord webhooks
```

An interactive diagram is available in [docs/architecture.html](docs/architecture.html).

**Main dependency:** the bot does not scrape the data sources itself. Searches go to **[Omega-Api](https://github.com/DriveAway500/Omega-Api)**, a separate API that must be running at `http://127.0.0.1:3000`. Only the CVE feed talks directly to the internet (`cvefeed.io`).

---

## 📁 Project structure

```
Enchiridion/
├── README*.md                 # This documentation (EN, PT-BR, RU, ZH-CN)
├── LICENSE                    # MIT
├── requirements.txt           # Python dependencies
├── .env                       # Tokens (not committed)
├── chart-lib/                 # Rust library (PyO3 + plotters + resvg) → module `chart_lib`
│   ├── src/lib.rs             # CVSSRadarChartGenerator: CVSS JSON → radar PNG
│   ├── Cargo.toml / pyproject.toml
│   └── .github/workflows/CI.yml  # Maturin wheel builds (Linux, musl, Windows, macOS)
├── docs/
│   ├── SETUP.MD               # Step-by-step installation guide (Arch Linux)
│   ├── architecture.html      # Interactive architecture diagram
│   └── feeds/
│       ├── ENGINE.MD          # Feed fetching engine reference
│       ├── ENGMAN.MD          # Engine hacking manual
│       └── CVETASK.MD         # Periodic feed task reference
└── src/
    ├── main.py                # Entry point: loads .env, sets up logging, starts the bot
    ├── bot.py                 # EnchiridionBot: loads cogs, syncs commands, starts feed task
    ├── httpx_client.py        # Shared httpx client for Omega-Api + APIError/NotFoundError
    ├── cogs/                  # Slash commands (cve, exploit, zeroday, kev, help, lang, feed)
    ├── ui/                    # Discord views, modals, buttons and pagination
    ├── omega_api/             # Thin async wrappers for each Omega-Api route
    ├── feeds/                 # engine.py (HTTP), cve_task.py (periodic loop), kev_task.py
    ├── parser/                # cve_parser.py (RSS/Atom → typed objects), kev_parser.py
    ├── database/              # feed_db, lang_db (aiosqlite), json_handler (atomic JSON)
    ├── graph/                 # cve_radar.py: async wrapper for chart_lib
    └── translator/            # PTBR/EN/ES strings for each cog
```

---

## 🧩 Module reference

### Core

| File | Responsibility |
| --- | --- |
| `src/main.py` | Loads `.env` from the repository root, configures logging and starts the bot. The `DEV` flag selects `DEV_TOKEN` (`True`) or `DISCORD_TOKEN` (`False`) and the log level (DEBUG/INFO). Installs hooks for unhandled exceptions in the main thread and in other threads. |
| `src/bot.py` | `EnchiridionBot(commands.Bot)` with `Intents.all()`. In `setup_hook` it opens an `aiohttp` session for webhooks, loads the 7 cogs, syncs the global slash command tree and starts the feed task. Status: *"Searching Exploits..."*. |
| `src/httpx_client.py` | Global `httpx.AsyncClient` pointed at `BASE_URL = http://127.0.0.1:3000` (timeouts 5/10/5/5 s, max 20 connections). `request_json()` converts 404 into `NotFoundError` (or `None` with `not_found_ok=True`), ≥400 into `APIError`, and 204/empty into `None`. `get_http_client()` creates a separate client for the feed engine. |

### `omega_api/` — Omega-Api routes

| Function | Method and route | Body / notes |
| --- | --- | --- |
| `get_cve(cve_id)` | `POST /cve/search` | `{"cve_id"}` |
| `search_cve_by_package(package_name, year, severity, page, limit)` | `POST /cve/search/package` | `{"package_name","year","limit","offset","severity"?}` |
| `search_exploits(query, page, limit)` | `POST /exploit/search` | `{"q","limit","offset"}` |
| `get_exploit(exploit_id)` | `POST /exploit/get` | `{"exploit_id"}` |
| `search_zeroday_exploits(query, page, limit)` | `POST /zeroday/search` | `{"q","limit","offset"}` |
| `get_zeroday_exploit(exploit_id)` | `POST /zeroday/get` | `{"exploit_id"}` |
| `get_kev_new()` / `get_kev_removed()` / `get_kev_diff()` | `GET /kev/new`, `/kev/removed`, `/kev/diff` | Changes between KEV index builds |
| `search_kev(q, fields, page, limit)` | `POST /kev/search` | Free-text search |
| `get_kev_entry(cve_id)` | `GET /kev/get/{cve_id}` | Single KEV entry |

Pagination always uses `offset = (page - 1) * limit`, with 5 results per page.

### `feeds/` — automatic CVE feed

- **`engine.py`** — transport-only HTTP engine. `FeedFetcher.fetch_many()` downloads several feeds concurrently (default 5), sharing one client, and returns one result per source in the same order. It never raises for network/HTTP errors: it returns `FeedFetchSuccess` or `FeedFetchFailure` (`TRANSPORT` or `HTTP_STATUS`). Supports `ETag`/`Last-Modified`. Details: [docs/feeds/ENGINE.MD](docs/feeds/ENGINE.MD) and [docs/feeds/ENGMAN.MD](docs/feeds/ENGMAN.MD).
- **`cve_task.py`** — the policy layer. `setup_feed_task(bot, interval_seconds=7200)` creates a `discord.ext.tasks` loop that waits for the bot to be ready and runs `process_feeds_once()`: fetch → parse → deduplicate (in the cycle and against `feed_db`) → filter by `min_severity`/`allow_unknown` → send embeds via webhook (max. 20 in parallel, 10 s timeout each). If Discord answers that a webhook no longer exists, the subscription is removed automatically. Every processed item is marked as sent, even if a delivery failed. Details: [docs/feeds/CVETASK.MD](docs/feeds/CVETASK.MD).
- **`kev_task.py`** — prototype for posting new KEV entries through a webhook. Not connected to the bot yet.

### `parser/`

- **`cve_parser.py`** — `CVEFeedParser.parse(FeedResponse)` uses `feedparser`, strips HTML, truncates the summary to 3000 characters and extracts the score from text like `CVSS: 9.8` / `Severity - 7`. Classification: **CRITICAL ≥ 9.0**, **HIGH ≥ 7.0**, **MEDIUM ≥ 4.0**, **LOW > 0**, **UNKNOWN** without a score; score ≤ 0 is discarded. Entries are returned oldest first.
- **`kev_parser.py`** — `KevParser` turns Omega-Api KEV responses into `KevNew`/`KevRemoved` dataclasses. To detect changes, it stores a SHA-256 of the last response in `src/database/kve_sha.json` (the first run only saves the baseline).

### `database/`

| File | Storage | Content |
| --- | --- | --- |
| `feed_db.py` | `src/database/feeds.db` | Table `subscriptions` (guild_id, channel_id, min_severity, allow_unknown, webhook_url) and table `sent_items` (item_id, sent_at) for deduplication. |
| `lang_db.py` | `src/database/language.db` | Table `guild_languages` (guild_id, language). Default: `EN`. |
| `json_handler.py` | any `.json` | Validated (`list[dict]`) and **atomic** JSON reading/writing (temporary file + `os.replace`). |

The tables are created automatically on first use. `*.db` and `kve_sha.json` are in `.gitignore`.

### `ui/`

Built with discord.py **Components V2** (`LayoutView`, `Container`, `TextDisplay`, `MediaGallery`, `Label`). Each panel shows 5 results with *Previous / Page N / Next* buttons and disables itself after 180 s.

- `cve_modal.py` — modals for search by ID (validated with `^CVE-\d{4}-\d{4,7}$`) and by package.
- `cve_view.py` — `CVEDetailView` (status, dates, CVSS v4.0 or v3.1 score, vector, description, up to 3 reference links, radar chart) and `CVEPanel` (paginated list).
- `exploit_ui.py` / `zeroday_ui.py` — result panels; the button shows the code in a code block or as an attachment if it is longer than 2000 characters, reusing the same message.
- `kev_ui.py` — `KevView` (CVE, vendor, product, CWE, description, required action, dates, ransomware) and `KevPanel`.

### `graph/` and `chart-lib/`

`graph/cve_radar.py` (`CVSSRadar`) accepts a `dict` or JSON string from NVD and calls the Rust library. `chart-lib` maps 7 CVSS metrics (AV, AC, PR, UI, C, I, A) to a 0–10 scale, draws an SVG radar with `plotters`, converts it to PNG with `resvg`/`tiny-skia` and runs the work in `tokio::spawn_blocking` so it does not block Python's event loop. It needs system fonts (e.g. DejaVu); without them it returns an explicit error.

### `translator/`

One file per cog (`cvecog_t`, `exploitdbcog_t`, `zerodaycog_t`, `feedcog_t`, `helpcog_t`, `langcog_t`) with a dictionary `{"PTBR"|"EN"|"ES": {...}}`. The `*_translate(guild_id, *keys, **kwargs)` functions read the server language from `lang_db` and format the string.

---

## ⚙️ Configuration

### `.env` file (repository root)

```env
DISCORD_TOKEN=your_production_token
DEV_TOKEN=your_development_token
```

`src/main.py` has `DEV = True`; in this mode it reads **`DEV_TOKEN`**. Set `DEV = False` to use `DISCORD_TOKEN`.

### Values in the code

| Setting | Location | Default |
| --- | --- | --- |
| Omega-Api URL | `src/httpx_client.py` → `BASE_URL` | `http://127.0.0.1:3000` |
| Feed interval | `setup_feed_task(interval_seconds=...)` | `7200` s (2 h) |
| Monitored feeds | `DEFAULT_FEED_URLS` in `cve_task.py` | `https://cvefeed.io/rssfeed/latest.atom` |
| Parallel webhook sends | `MAX_CONCURRENT_SENDS` | `20` |
| Timeout per send | `WEBHOOK_SEND_TIMEOUT_SECONDS` | `10.0` s |
| Results per page | `PAGE_SIZE` in `src/ui/*` | `5` |

### Discord Developer Portal

The bot uses `discord.Intents.all()`, so enable the **privileged intents** (Presence, Server Members, Message Content) in the portal. In the server it needs to send messages, embeds and files, and **Manage Webhooks** in the channels that will receive the feed.

---

## 🚀 Installation (summary)

The full step-by-step guide is in **[docs/SETUP.MD](docs/SETUP.MD)**. In short:

```bash
# 1. Install and start Omega-Api (separate project)
git clone https://github.com/DriveAway500/Omega-Api.git

# 2. Virtual environment and dependencies
cd Enchiridion
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Build the Rust library (requires Rust + system fonts such as DejaVu)
cd chart-lib
maturin develop --release
cd ..

# 4. Create .env and start
python src/main.py
```

Requirements: Python 3.10+ (the code uses `X | Y` syntax and `slots=True`), Rust (edition 2024), discord.py with Components V2 support, and Omega-Api running.

---

## 📜 Logging

| Destination | Content |
| --- | --- |
| `logs/bot.log` | Everything (DEBUG in DEV mode), rotated at midnight, 14 days kept. |
| `logs/errors/<module>.log` | ERROR/CRITICAL only, split by the project module where the error started (5 MB × 3 backups). |
| console | Same level as `bot.log`. |

The `discord` and `discord.http` libraries are kept at INFO/WARNING to reduce noise.

---

## 🚧 Known limitations / roadmap

- **KEV feed is not connected yet:** `src/feeds/kev_task.py` is a prototype (it uses an undefined `WEBHOOK_URL` and is not started by the bot). Today only the CVE feed is automatic.
- **KEV UI is English only:** `/active_cve` and `kev_ui.py` do not use the translator yet.
- **`/help`** only covers `exploitdb`, `cve` and `zerodaytoday`.
- **Fixed Omega-Api URL** in the code (`BASE_URL`), not configurable via `.env`.
- **Feed `ETag`/`Last-Modified`** are not persisted between cycles, so the whole feed is downloaded every 2 hours.
- **Year list** in the package search is fixed (2002–2026).
- **`requirements.txt` has no pinned versions** and lists both `dotenv` and `python-dotenv`; the project only needs `python-dotenv`.
- **Licensing:** the project is MIT, but `src/database/json_handler.py` has the header `SPDX-License-Identifier: GPL-3.0-only`.

---

## 📚 More documentation

- [docs/SETUP.MD](docs/SETUP.MD) — installation guide
- [docs/architecture.html](docs/architecture.html) — architecture diagram
- [docs/feeds/ENGINE.MD](docs/feeds/ENGINE.MD) — feed engine
- [docs/feeds/ENGMAN.MD](docs/feeds/ENGMAN.MD) — engine hacking manual
- [docs/feeds/CVETASK.MD](docs/feeds/CVETASK.MD) — periodic feed task

---

## 📄 License

[MIT](LICENSE) © 2026 DriveAway500
