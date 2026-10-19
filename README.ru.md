<div align="center">

# 📖 Enchiridion

**Discord-бот для OSINT и разведки уязвимостей — CVE, CISA KEV, Exploit-DB и 0day.today в одном месте.**

[🇺🇸 English](README.md) · [🇧🇷 Português](README.pt-BR.md) · 🇷🇺 **Русский** · [🇨🇳 中文](README.zh-CN.md)

[![Architecture diagram](https://gitdiagram.com/diagram-badge.svg)](https://gitdiagram.com/driveaway500/enchiridion?utm_source=readme&utm_medium=badge)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Rust](https://img.shields.io/badge/rust-chart--lib-orange)
![discord.py](https://img.shields.io/badge/discord.py-2.x-5865F2)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## 🎯 Для чего этот репозиторий и кому он поможет

**Enchiridion** (с греческого — *«справочник»*) приносит данные об уязвимостях туда, где многие команды и сообщества по безопасности уже общаются, — в **Discord**. Вместо того чтобы переключаться между NVD, CISA, Exploit-DB и другими сайтами, участники сервера вводят слэш-команду и получают отформатированный ответ с постраничной навигацией прямо в канале — или автоматически получают новые CVE, отфильтрованные по критичности.

### Какую проблему он решает

- Данные об уязвимостях разбросаны по множеству источников, у каждого свой интерфейс.
- Следить за новыми CVE вручную долго, и об этом легко забыть.
- Командам, говорящим на разных языках, нужна одна и та же информация на родном языке.

### Кому он поможет

| Аудитория | Чем помогает Enchiridion |
| --- | --- |
| **Аналитики SOC и Blue Team** | Автоматическая лента CVE для каждого канала с фильтром по минимальной критичности; быстрый просмотр оценки CVSS, вектора и ссылок во время триажа. |
| **Пентестеры, Red Team и багхантеры** | Поиск в Exploit-DB и 0day.today по названию или CVE и просмотр кода эксплойта прямо в Discord. |
| **Системные администраторы и DevOps** | Поиск CVE по пакету/продукту и году (например, `openssl`, `sudo`, `linux`), чтобы понять, затронут ли их стек. |
| **Специалисты по управлению уязвимостями** | Доступ к каталогу **CISA KEV** (активно эксплуатируемые уязвимости) со сроком устранения и признаком использования в атаках шифровальщиков. |
| **Сообщества по безопасности, CTF-команды и студенты** | Общая, бесплатная и многоязычная (PT-BR / EN / ES) база знаний на сервере с радарной диаграммой CVSS, которая помогает понять метрики. |
| **Разработчики** | Аккуратный пример модульного бота на `discord.py`: cogs, асинхронный SQLite, HTTP-движок лент и расширение на Rust через PyO3. |

> ⚠️ **Ответственное использование:** Enchiridion показывает публичную информацию и публичный код эксплойтов. Используйте его только для защиты, исследований, обучения и тестирования систем, на которые у вас есть разрешение.

---

## ✨ Возможности

- 🔎 **Поиск CVE** по ID (`CVE-2021-44228`) или по пакету + году + критичности, с постраничной навигацией.
- 📊 **Радарная диаграмма CVSS** (PNG) для каждой CVE, которую рисует нативная библиотека на **Rust** (`chart-lib`).
- 💥 **Поиск в Exploit-DB** и **0day.today** с кнопкой показа кода эксплойта (если код длиннее 2000 символов, он отправляется файлом).
- 🚨 **Поиск в CISA KEV** (`/active_cve`) — уязвимости, которые реально эксплуатируются.
- 📡 **Автоматическая лента CVE**: каждые 2 часа бот читает `cvefeed.io`, убирает дубликаты и публикует новые CVE в подписанные каналы через вебхуки с учётом минимальной критичности каждого канала.
- 🌐 **Язык для каждого сервера**: португальский (Бразилия), английский и испанский.
- 🧾 **Структурированные логи**: ежедневная ротация и отдельный файл ошибок для каждого модуля.

---

## 💬 Слэш-команды

| Команда | Параметры | Права | Что делает |
| --- | --- | --- | --- |
| `/cve` | `method`: *CVE ID* или *Package Name* | все | Открывает модальное окно. **CVE ID** → подробности с радарной диаграммой и ссылками. **Package** → выбор критичности, года (2002–2026) и пакета/термина; список со страницами. |
| `/exploitdb` | `search` (мин. 3 символа) | все | Поиск в Exploit-DB; у каждого результата есть кнопка для просмотра кода. |
| `/zerodaytoday` | `search` (мин. 3 символа) | все | Поиск в 0day.today (база с 2004 года); у каждого результата есть кнопка для просмотра кода. |
| `/active_cve` | `query` (например, *Windows*, *Chrome*) | все | Поиск в каталоге CISA KEV; красная подсветка, если уязвимость использовалась шифровальщиками. |
| `/help` | `opcao`: exploitdb, cve, zerodaytoday | все | Описывает каждый инструмент поиска на языке сервера. |
| `/language set` | `idioma`: PTBR, EN, ES | Управление сервером | Задаёт язык сервера. |
| `/language current` | — | Управление сервером | Показывает текущий язык. |
| `/feeds register` | `channel`, `severity`, `include_unknown` | Управление сервером + Управление вебхуками | Создаёт вебхук в канале и подписывает его на ленту CVE. |
| `/feeds severity` | `channel`, `severity`, `include_unknown` | Управление сервером + Управление вебхуками | Меняет фильтр критичности для подписанного канала. |
| `/feeds remove` | `channel` | Управление сервером + Управление вебхуками | Удаляет вебхук и подписку. |
| `/feeds list` | — | Управление сервером + Управление вебхуками | Показывает подписанные каналы и их фильтры. |

Варианты критичности для ленты: **Critical (9.0+)**, **High (7.0+)**, **Medium (4.0+)**, **All (0.0, включая неизвестную)**.
Все команды работают только на серверах (`guild_only`).

---

## 🏗️ Архитектура

```
                         ┌────────────────────────────┐
  Пользователи Discord ► │  Cogs (слэш-команды)       │
                         │  src/cogs/*                │
                         └──────┬──────────────┬──────┘
                                │              │
                     ┌──────────▼───┐   ┌──────▼──────────┐
                     │ UI (views,   │   │ Переводчик       │◄── lang_db (SQLite)
                     │ модальные)   │   │ PTBR / EN / ES   │
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
          │  Omega-Api   │  (отдельный проект: данные CVE / Exploit-DB / 0day / KEV)
          └──────────────┘

  Периодическая лента (каждые 2 ч):
  cvefeed.io ──► FeedFetcher (engine.py) ──► CVEFeedParser ──► дедупликация (feed_db)
            ──► фильтр критичности для каждой подписки ──► вебхуки Discord
```

Интерактивная схема находится в [docs/architecture.html](docs/architecture.html).

**Главная зависимость:** бот сам не собирает данные из источников. Поисковые запросы уходят в **[Omega-Api](https://github.com/DriveAway500/Omega-Api)** — отдельный API, который должен работать по адресу `http://127.0.0.1:3000`. Напрямую в интернет обращается только лента CVE (`cvefeed.io`).

---

## 📁 Структура проекта

```
Enchiridion/
├── README*.md                 # Эта документация (EN, PT-BR, RU, ZH-CN)
├── LICENSE                    # MIT
├── requirements.txt           # Зависимости Python
├── .env                       # Токены (не попадает в git)
├── chart-lib/                 # Библиотека на Rust (PyO3 + plotters + resvg) → модуль `chart_lib`
│   ├── src/lib.rs             # CVSSRadarChartGenerator: JSON CVSS → PNG-радар
│   ├── Cargo.toml / pyproject.toml
│   └── .github/workflows/CI.yml  # Сборка wheel через Maturin (Linux, musl, Windows, macOS)
├── docs/
│   ├── SETUP.MD               # Пошаговая установка (Arch Linux)
│   ├── architecture.html      # Интерактивная схема архитектуры
│   └── feeds/
│       ├── ENGINE.MD          # Справочник по движку лент
│       ├── ENGMAN.MD          # Руководство по доработке движка
│       └── CVETASK.MD         # Справочник по периодической задаче ленты
└── src/
    ├── main.py                # Точка входа: читает .env, настраивает логи, запускает бота
    ├── bot.py                 # EnchiridionBot: загружает cogs, синхронизирует команды, запускает ленту
    ├── httpx_client.py        # Общий клиент httpx для Omega-Api + APIError/NotFoundError
    ├── cogs/                  # Слэш-команды (cve, exploit, zeroday, kev, help, lang, feed)
    ├── ui/                    # Views, модальные окна, кнопки и пагинация Discord
    ├── omega_api/             # Тонкие асинхронные обёртки для каждого маршрута Omega-Api
    ├── feeds/                 # engine.py (HTTP), cve_task.py (периодический цикл), kev_task.py
    ├── parser/                # cve_parser.py (RSS/Atom → типизированные объекты), kev_parser.py
    ├── database/              # feed_db, lang_db (aiosqlite), json_handler (атомарный JSON)
    ├── graph/                 # cve_radar.py: асинхронная обёртка над chart_lib
    └── translator/            # Строки PTBR/EN/ES для каждого cog
```

---

## 🧩 Описание модулей

### Ядро

| Файл | Назначение |
| --- | --- |
| `src/main.py` | Загружает `.env` из корня репозитория, настраивает логирование и запускает бота. Флаг `DEV` выбирает `DEV_TOKEN` (`True`) или `DISCORD_TOKEN` (`False`) и уровень логов (DEBUG/INFO). Устанавливает обработчики необработанных исключений в главном и других потоках. |
| `src/bot.py` | `EnchiridionBot(commands.Bot)` с `Intents.all()`. В `setup_hook` открывает сессию `aiohttp` для вебхуков, загружает 7 cogs, синхронизирует глобальное дерево команд и запускает задачу ленты. Статус: *«Searching Exploits...»*. |
| `src/httpx_client.py` | Глобальный `httpx.AsyncClient` с `BASE_URL = http://127.0.0.1:3000` (таймауты 5/10/5/5 с, до 20 соединений). `request_json()` превращает 404 в `NotFoundError` (или `None` при `not_found_ok=True`), ≥400 — в `APIError`, 204/пустой ответ — в `None`. `get_http_client()` создаёт отдельный клиент для движка лент. |

### `omega_api/` — маршруты Omega-Api

| Функция | Метод и маршрут | Тело / примечания |
| --- | --- | --- |
| `get_cve(cve_id)` | `POST /cve/search` | `{"cve_id"}` |
| `search_cve_by_package(package_name, year, severity, page, limit)` | `POST /cve/search/package` | `{"package_name","year","limit","offset","severity"?}` |
| `search_exploits(query, page, limit)` | `POST /exploit/search` | `{"q","limit","offset"}` |
| `get_exploit(exploit_id)` | `POST /exploit/get` | `{"exploit_id"}` |
| `search_zeroday_exploits(query, page, limit)` | `POST /zeroday/search` | `{"q","limit","offset"}` |
| `get_zeroday_exploit(exploit_id)` | `POST /zeroday/get` | `{"exploit_id"}` |
| `get_kev_new()` / `get_kev_removed()` / `get_kev_diff()` | `GET /kev/new`, `/kev/removed`, `/kev/diff` | Изменения между сборками индекса KEV |
| `search_kev(q, fields, page, limit)` | `POST /kev/search` | Полнотекстовый поиск |
| `get_kev_entry(cve_id)` | `GET /kev/get/{cve_id}` | Одна запись KEV |

Пагинация всегда считается как `offset = (page - 1) * limit`, по 5 результатов на страницу.

### `feeds/` — автоматическая лента CVE

- **`engine.py`** — HTTP-движок, отвечающий только за транспорт. `FeedFetcher.fetch_many()` параллельно скачивает несколько лент (по умолчанию 5), используя один клиент, и возвращает по одному результату на источник в том же порядке. Не выбрасывает исключений при сетевых/HTTP-ошибках: возвращает `FeedFetchSuccess` или `FeedFetchFailure` (`TRANSPORT` или `HTTP_STATUS`). Поддерживает `ETag`/`Last-Modified`. Подробнее: [docs/feeds/ENGINE.MD](docs/feeds/ENGINE.MD) и [docs/feeds/ENGMAN.MD](docs/feeds/ENGMAN.MD).
- **`cve_task.py`** — слой правил. `setup_feed_task(bot, interval_seconds=7200)` создаёт цикл `discord.ext.tasks`, который ждёт готовности бота и выполняет `process_feeds_once()`: загрузка → разбор → дедупликация (внутри цикла и по `feed_db`) → фильтр по `min_severity`/`allow_unknown` → отправка embed через вебхук (до 20 параллельно, таймаут 10 с на каждую). Если Discord отвечает, что вебхука больше нет, подписка удаляется автоматически. Каждый обработанный элемент помечается как отправленный, даже если доставка не удалась. Подробнее: [docs/feeds/CVETASK.MD](docs/feeds/CVETASK.MD).
- **`kev_task.py`** — прототип публикации новых записей KEV через вебхук. Пока не подключён к боту.

### `parser/`

- **`cve_parser.py`** — `CVEFeedParser.parse(FeedResponse)` использует `feedparser`, удаляет HTML, обрезает описание до 3000 символов и извлекает оценку из текста вида `CVSS: 9.8` / `Severity - 7`. Классификация: **CRITICAL ≥ 9.0**, **HIGH ≥ 7.0**, **MEDIUM ≥ 4.0**, **LOW > 0**, **UNKNOWN** — без оценки; оценка ≤ 0 отбрасывается. Записи возвращаются от старых к новым.
- **`kev_parser.py`** — `KevParser` превращает ответы KEV от Omega-Api в dataclass `KevNew`/`KevRemoved`. Чтобы обнаруживать изменения, хранит SHA-256 последнего ответа в `src/database/kve_sha.json` (первый запуск только сохраняет исходное значение).

### `database/`

| Файл | Хранилище | Содержимое |
| --- | --- | --- |
| `feed_db.py` | `src/database/feeds.db` | Таблица `subscriptions` (guild_id, channel_id, min_severity, allow_unknown, webhook_url) и таблица `sent_items` (item_id, sent_at) для дедупликации. |
| `lang_db.py` | `src/database/language.db` | Таблица `guild_languages` (guild_id, language). По умолчанию: `EN`. |
| `json_handler.py` | любой `.json` | Проверенное (`list[dict]`) и **атомарное** чтение/запись JSON (временный файл + `os.replace`). |

Таблицы создаются автоматически при первом обращении. `*.db` и `kve_sha.json` указаны в `.gitignore`.

### `ui/`

Построен на **Components V2** из discord.py (`LayoutView`, `Container`, `TextDisplay`, `MediaGallery`, `Label`). Каждая панель показывает 5 результатов с кнопками *Назад / Страница N / Далее* и отключается через 180 с.

- `cve_modal.py` — модальные окна поиска по ID (проверка `^CVE-\d{4}-\d{4,7}$`) и по пакету.
- `cve_view.py` — `CVEDetailView` (статус, даты, оценка CVSS v4.0 или v3.1, вектор, описание, до 3 ссылок, радарная диаграмма) и `CVEPanel` (список со страницами).
- `exploit_ui.py` / `zeroday_ui.py` — панели результатов; кнопка показывает код в блоке кода или вложением, если он длиннее 2000 символов, переиспользуя одно и то же сообщение.
- `kev_ui.py` — `KevView` (CVE, вендор, продукт, CWE, описание, требуемое действие, даты, шифровальщики) и `KevPanel`.

### `graph/` и `chart-lib/`

`graph/cve_radar.py` (`CVSSRadar`) принимает `dict` или JSON-строку NVD и вызывает библиотеку на Rust. `chart-lib` переводит 7 метрик CVSS (AV, AC, PR, UI, C, I, A) в шкалу 0–10, рисует SVG-радар через `plotters`, конвертирует его в PNG через `resvg`/`tiny-skia` и выполняет работу в `tokio::spawn_blocking`, чтобы не блокировать event loop Python. Нужны системные шрифты (например, DejaVu); без них возвращается явная ошибка.

### `translator/`

По одному файлу на cog (`cvecog_t`, `exploitdbcog_t`, `zerodaycog_t`, `feedcog_t`, `helpcog_t`, `langcog_t`) со словарём `{"PTBR"|"EN"|"ES": {...}}`. Функции `*_translate(guild_id, *keys, **kwargs)` берут язык сервера из `lang_db` и форматируют строку.

---

## ⚙️ Настройка

### Файл `.env` (корень репозитория)

```env
DISCORD_TOKEN=ваш_боевой_токен
DEV_TOKEN=ваш_токен_для_разработки
```

В `src/main.py` стоит `DEV = True`; в этом режиме читается **`DEV_TOKEN`**. Установите `DEV = False`, чтобы использовать `DISCORD_TOKEN`.

### Значения в коде

| Параметр | Где | По умолчанию |
| --- | --- | --- |
| URL Omega-Api | `src/httpx_client.py` → `BASE_URL` | `http://127.0.0.1:3000` |
| Интервал ленты | `setup_feed_task(interval_seconds=...)` | `7200` с (2 ч) |
| Отслеживаемые ленты | `DEFAULT_FEED_URLS` в `cve_task.py` | `https://cvefeed.io/rssfeed/latest.atom` |
| Параллельные отправки в вебхуки | `MAX_CONCURRENT_SENDS` | `20` |
| Таймаут одной отправки | `WEBHOOK_SEND_TIMEOUT_SECONDS` | `10.0` с |
| Результатов на странице | `PAGE_SIZE` в `src/ui/*` | `5` |

### Discord Developer Portal

Бот использует `discord.Intents.all()`, поэтому включите на портале **привилегированные intents** (Presence, Server Members, Message Content). На сервере боту нужны права на отправку сообщений, embed и файлов, а также **Управление вебхуками** в каналах, которые будут получать ленту.

---

## 🚀 Установка (кратко)

Полное пошаговое руководство — в **[docs/SETUP.MD](docs/SETUP.MD)**. Вкратце:

```bash
# 1. Установите и запустите Omega-Api (отдельный проект)
git clone https://github.com/DriveAway500/Omega-Api.git

# 2. Виртуальное окружение и зависимости
cd Enchiridion
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Соберите библиотеку на Rust (нужны Rust и системные шрифты, например DejaVu)
cd chart-lib
maturin develop --release
cd ..

# 4. Создайте .env и запустите
python src/main.py
```

Требования: Python 3.10+ (код использует синтаксис `X | Y` и `slots=True`), Rust (edition 2024), discord.py с поддержкой Components V2 и запущенный Omega-Api.

---

## 📜 Логирование

| Куда | Что |
| --- | --- |
| `logs/bot.log` | Всё (DEBUG в режиме DEV), ротация в полночь, хранится 14 дней. |
| `logs/errors/<модуль>.log` | Только ERROR/CRITICAL, разделённые по модулю проекта, где возникла ошибка (5 МБ × 3 копии). |
| консоль | Тот же уровень, что и `bot.log`. |

Библиотеки `discord` и `discord.http` ограничены уровнями INFO/WARNING, чтобы уменьшить шум.

---

## 🚧 Известные ограничения / планы

- **Лента KEV пока не подключена:** `src/feeds/kev_task.py` — прототип (использует неопределённый `WEBHOOK_URL` и не запускается ботом). Сейчас автоматической является только лента CVE.
- **Интерфейс KEV только на английском:** `/active_cve` и `kev_ui.py` пока не используют переводчик.
- **`/help`** описывает только `exploitdb`, `cve` и `zerodaytoday`.
- **URL Omega-Api зашит** в код (`BASE_URL`) и не настраивается через `.env`.
- **`ETag`/`Last-Modified` ленты** не сохраняются между циклами, поэтому лента скачивается целиком каждые 2 часа.
- **Список годов** в поиске по пакету фиксирован (2002–2026).
- **В `requirements.txt` нет закреплённых версий**, и там одновременно указаны `dotenv` и `python-dotenv`; проекту нужен только `python-dotenv`.
- **Лицензия:** проект под MIT, но в `src/database/json_handler.py` указан заголовок `SPDX-License-Identifier: GPL-3.0-only`.

---

## 📚 Дополнительная документация

- [docs/SETUP.MD](docs/SETUP.MD) — руководство по установке
- [docs/architecture.html](docs/architecture.html) — схема архитектуры
- [docs/feeds/ENGINE.MD](docs/feeds/ENGINE.MD) — движок лент
- [docs/feeds/ENGMAN.MD](docs/feeds/ENGMAN.MD) — руководство по доработке движка
- [docs/feeds/CVETASK.MD](docs/feeds/CVETASK.MD) — периодическая задача ленты

---

## 📄 Лицензия

[MIT](LICENSE) © 2026 DriveAway500
