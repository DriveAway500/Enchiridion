<div align="center">

# 📖 Enchiridion

**一个用于 OSINT 与漏洞情报的 Discord 机器人 —— CVE、CISA KEV、Exploit-DB 和 0day.today，一站式查询。**

[🇺🇸 English](README.md) · [🇧🇷 Português](README.pt-BR.md) · [🇷🇺 Русский](README.ru.md) · 🇨🇳 **中文**

[![Architecture diagram](https://gitdiagram.com/diagram-badge.svg)](https://gitdiagram.com/driveaway500/enchiridion?utm_source=readme&utm_medium=badge)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Rust](https://img.shields.io/badge/rust-chart--lib-orange)
![discord.py](https://img.shields.io/badge/discord.py-2.x-5865F2)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

## 🎯 这个仓库是做什么的，能帮助谁

**Enchiridion**（希腊语，意为 *“手册”*）把漏洞情报带到许多安全团队和社区日常交流的地方 —— **Discord**。服务器成员无需在 NVD、CISA、Exploit-DB 等网站之间来回切换，只需输入一个斜杠命令，就能在频道里直接看到格式化、可分页的结果；也可以自动接收按严重程度过滤的最新 CVE。

### 它解决的问题

- 漏洞数据分散在许多来源中，每个来源的界面都不一样。
- 手动跟踪新 CVE 既费时又容易遗漏。
- 使用不同语言的团队需要用自己的语言获取同样的信息。

### 它能帮助谁

| 受众 | Enchiridion 如何提供帮助 |
| --- | --- |
| **SOC 分析师与蓝队** | 按频道自动推送 CVE，并按最低严重程度过滤；在研判时快速查看 CVSS 分数、向量和参考链接。 |
| **渗透测试人员、红队与漏洞赏金猎人** | 按名称或 CVE 搜索 Exploit-DB 和 0day.today，并直接在 Discord 中阅读漏洞利用代码。 |
| **系统管理员与 DevOps** | 按软件包/产品和年份（如 `openssl`、`sudo`、`linux`）搜索 CVE，判断自己的技术栈是否受影响。 |
| **漏洞管理人员** | 查询 **CISA KEV** 目录（正在被实际利用的漏洞），包括修复截止日期以及是否被勒索软件利用。 |
| **安全社区、CTF 战队与学生** | 在服务器内拥有一个共享、免费、多语言（PT-BR / EN / ES）的知识库，CVSS 雷达图让指标更容易理解。 |
| **开发者** | 一个结构清晰的模块化 `discord.py` 机器人示例：cogs、异步 SQLite、HTTP 订阅源引擎，以及用 PyO3 编写的 Rust 扩展。 |

> ⚠️ **负责任地使用：** Enchiridion 展示的是公开信息和公开的漏洞利用代码。请仅将其用于防御、研究、教学，以及在你已获授权的系统上进行测试。

---

## ✨ 功能

- 🔎 **CVE 搜索**：按 ID（`CVE-2021-44228`）或按软件包 + 年份 + 严重程度搜索，支持分页。
- 📊 **CVSS 雷达图**（PNG）：由原生 **Rust** 库（`chart-lib`）为每个 CVE 生成。
- 💥 **Exploit-DB** 与 **0day.today** 搜索：通过按钮查看漏洞利用代码（超过 2000 个字符时以文件形式发送）。
- 🚨 **CISA KEV** 搜索（`/active_cve`）：已知在真实环境中被利用的漏洞。
- 📡 **自动 CVE 推送**：每 2 小时读取一次 `cvefeed.io`，去重后通过 webhook 把新 CVE 发布到已登记的频道，并遵守每个频道设置的最低严重程度。
- 🌐 **按服务器设置语言**：葡萄牙语（巴西）、英语和西班牙语。
- 🧾 **结构化日志**：按天轮转的日志文件，以及按模块划分的错误日志。

---

## 💬 斜杠命令

| 命令 | 参数 | 权限 | 作用 |
| --- | --- | --- | --- |
| `/cve` | `method`：*CVE ID* 或 *Package Name* | 所有人 | 打开一个弹窗。**CVE ID** → 显示带雷达图和参考链接的详情。**Package** → 选择严重程度、年份（2002–2026）和软件包/关键词，返回分页列表。 |
| `/exploitdb` | `search`（至少 3 个字符） | 所有人 | 搜索 Exploit-DB；每条结果都有查看代码的按钮。 |
| `/zerodaytoday` | `search`（至少 3 个字符） | 所有人 | 搜索 0day.today（数据始于 2004 年）；每条结果都有查看代码的按钮。 |
| `/active_cve` | `query`（如 *Windows*、*Chrome*） | 所有人 | 搜索 CISA KEV 目录；若被用于勒索软件活动则以红色标出。 |
| `/help` | `opcao`：exploitdb、cve、zerodaytoday | 所有人 | 用服务器语言说明每个搜索工具。 |
| `/language set` | `idioma`：PTBR、EN、ES | 管理服务器 | 设置服务器语言。 |
| `/language current` | — | 管理服务器 | 显示当前语言。 |
| `/feeds register` | `channel`、`severity`、`include_unknown` | 管理服务器 + 管理 Webhook | 在频道中创建 webhook 并订阅 CVE 推送。 |
| `/feeds severity` | `channel`、`severity`、`include_unknown` | 管理服务器 + 管理 Webhook | 修改已登记频道的严重程度过滤条件。 |
| `/feeds remove` | `channel` | 管理服务器 + 管理 Webhook | 删除 webhook 和订阅。 |
| `/feeds list` | — | 管理服务器 + 管理 Webhook | 列出已登记的频道及其过滤条件。 |

推送的严重程度选项：**Critical (9.0+)**、**High (7.0+)**、**Medium (4.0+)**、**All (0.0，包括未知)**。
所有命令都只能在服务器中使用（`guild_only`）。

---

## 🏗️ 架构

```
                         ┌────────────────────────────┐
  Discord 用户 ────────► │  Cogs（斜杠命令）          │
                         │  src/cogs/*                │
                         └──────┬──────────────┬──────┘
                                │              │
                     ┌──────────▼───┐   ┌──────▼──────────┐
                     │ UI（视图、   │   │ 翻译器           │◄── lang_db (SQLite)
                     │ 弹窗）       │   │ PTBR / EN / ES   │
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
          │  Omega-Api   │  （独立项目：CVE / Exploit-DB / 0day / KEV 数据）
          └──────────────┘

  定时推送（每 2 小时）：
  cvefeed.io ──► FeedFetcher (engine.py) ──► CVEFeedParser ──► 去重 (feed_db)
            ──► 按订阅过滤严重程度 ──► Discord webhooks
```

交互式架构图见 [docs/architecture.html](docs/architecture.html)。

**主要依赖：** 机器人本身不直接抓取数据源。所有搜索都会发送到 **[Omega-Api](https://github.com/DriveAway500/Omega-Api)** —— 一个必须运行在 `http://127.0.0.1:3000` 的独立 API。只有 CVE 推送会直接访问互联网（`cvefeed.io`）。

---

## 📁 项目结构

```
Enchiridion/
├── README*.md                 # 本文档（EN、PT-BR、RU、ZH-CN）
├── LICENSE                    # MIT
├── requirements.txt           # Python 依赖
├── .env                       # 令牌（不提交到 git）
├── chart-lib/                 # Rust 库（PyO3 + plotters + resvg）→ 模块 `chart_lib`
│   ├── src/lib.rs             # CVSSRadarChartGenerator：CVSS JSON → 雷达图 PNG
│   ├── Cargo.toml / pyproject.toml
│   └── .github/workflows/CI.yml  # 使用 Maturin 构建 wheel（Linux、musl、Windows、macOS）
├── docs/
│   ├── SETUP.MD               # 分步安装指南（Arch Linux）
│   ├── architecture.html      # 交互式架构图
│   └── feeds/
│       ├── ENGINE.MD          # 订阅源引擎参考
│       ├── ENGMAN.MD          # 引擎修改手册
│       └── CVETASK.MD         # 定时推送任务参考
└── src/
    ├── main.py                # 入口：读取 .env、配置日志、启动机器人
    ├── bot.py                 # EnchiridionBot：加载 cogs、同步命令、启动推送任务
    ├── httpx_client.py        # 访问 Omega-Api 的共享 httpx 客户端 + APIError/NotFoundError
    ├── cogs/                  # 斜杠命令（cve、exploit、zeroday、kev、help、lang、feed）
    ├── ui/                    # Discord 视图、弹窗、按钮与分页
    ├── omega_api/             # 每个 Omega-Api 路由的轻量异步封装
    ├── feeds/                 # engine.py（HTTP）、cve_task.py（定时循环）、kev_task.py
    ├── parser/                # cve_parser.py（RSS/Atom → 类型化对象）、kev_parser.py
    ├── database/              # feed_db、lang_db（aiosqlite）、json_handler（原子写入 JSON）
    ├── graph/                 # cve_radar.py：chart_lib 的异步封装
    └── translator/            # 各 cog 的 PTBR/EN/ES 文本
```

---

## 🧩 模块说明

### 核心

| 文件 | 职责 |
| --- | --- |
| `src/main.py` | 从仓库根目录加载 `.env`，配置日志并启动机器人。`DEV` 标志决定使用 `DEV_TOKEN`（`True`）还是 `DISCORD_TOKEN`（`False`），以及日志级别（DEBUG/INFO）。为主线程和其他线程中未处理的异常安装钩子。 |
| `src/bot.py` | `EnchiridionBot(commands.Bot)`，使用 `Intents.all()`。在 `setup_hook` 中为 webhook 打开一个 `aiohttp` 会话，加载 7 个 cog，同步全局斜杠命令树，并启动推送任务。状态显示：*“Searching Exploits...”*。 |
| `src/httpx_client.py` | 指向 `BASE_URL = http://127.0.0.1:3000` 的全局 `httpx.AsyncClient`（超时 5/10/5/5 秒，最多 20 个连接）。`request_json()` 把 404 转为 `NotFoundError`（若 `not_found_ok=True` 则返回 `None`），≥400 转为 `APIError`，204/空响应返回 `None`。`get_http_client()` 为推送引擎创建独立客户端。 |

### `omega_api/` —— Omega-Api 路由

| 函数 | 方法与路由 | 请求体 / 说明 |
| --- | --- | --- |
| `get_cve(cve_id)` | `POST /cve/search` | `{"cve_id"}` |
| `search_cve_by_package(package_name, year, severity, page, limit)` | `POST /cve/search/package` | `{"package_name","year","limit","offset","severity"?}` |
| `search_exploits(query, page, limit)` | `POST /exploit/search` | `{"q","limit","offset"}` |
| `get_exploit(exploit_id)` | `POST /exploit/get` | `{"exploit_id"}` |
| `search_zeroday_exploits(query, page, limit)` | `POST /zeroday/search` | `{"q","limit","offset"}` |
| `get_zeroday_exploit(exploit_id)` | `POST /zeroday/get` | `{"exploit_id"}` |
| `get_kev_new()` / `get_kev_removed()` / `get_kev_diff()` | `GET /kev/new`、`/kev/removed`、`/kev/diff` | KEV 索引两次构建之间的变化 |
| `search_kev(q, fields, page, limit)` | `POST /kev/search` | 全文搜索 |
| `get_kev_entry(cve_id)` | `GET /kev/get/{cve_id}` | 单条 KEV 记录 |

分页统一使用 `offset = (page - 1) * limit`，每页 5 条结果。

### `feeds/` —— 自动 CVE 推送

- **`engine.py`** —— 只负责传输的 HTTP 引擎。`FeedFetcher.fetch_many()` 共享同一个客户端并发下载多个订阅源（默认 5 个），并按输入顺序为每个来源返回一个结果。遇到网络/HTTP 错误不会抛出异常，而是返回 `FeedFetchSuccess` 或 `FeedFetchFailure`（`TRANSPORT` 或 `HTTP_STATUS`）。支持 `ETag`/`Last-Modified`。详见 [docs/feeds/ENGINE.MD](docs/feeds/ENGINE.MD) 和 [docs/feeds/ENGMAN.MD](docs/feeds/ENGMAN.MD)。
- **`cve_task.py`** —— 策略层。`setup_feed_task(bot, interval_seconds=7200)` 创建一个 `discord.ext.tasks` 循环，等待机器人就绪后执行 `process_feeds_once()`：下载 → 解析 → 去重（本轮内以及对照 `feed_db`）→ 按 `min_severity`/`allow_unknown` 过滤 → 通过 webhook 发送 embed（最多 20 个并行，每次超时 10 秒）。如果 Discord 返回 webhook 已不存在，会自动删除该订阅。每个处理过的条目都会被标记为已发送，即使某次投递失败。详见 [docs/feeds/CVETASK.MD](docs/feeds/CVETASK.MD)。
- **`kev_task.py`** —— 通过 webhook 发布新 KEV 条目的原型，尚未接入机器人。

### `parser/`

- **`cve_parser.py`** —— `CVEFeedParser.parse(FeedResponse)` 使用 `feedparser`，去除 HTML，把摘要截断到 3000 个字符，并从 `CVSS: 9.8` / `Severity - 7` 这类文本中提取分数。分级：**CRITICAL ≥ 9.0**、**HIGH ≥ 7.0**、**MEDIUM ≥ 4.0**、**LOW > 0**，没有分数为 **UNKNOWN**；分数 ≤ 0 的条目会被丢弃。条目按从旧到新的顺序返回。
- **`kev_parser.py`** —— `KevParser` 把 Omega-Api 的 KEV 响应转换为 `KevNew`/`KevRemoved` 数据类。为检测变化，它会把上一次响应的 SHA-256 保存在 `src/database/kve_sha.json` 中（首次运行只保存基准值）。

### `database/`

| 文件 | 存储位置 | 内容 |
| --- | --- | --- |
| `feed_db.py` | `src/database/feeds.db` | `subscriptions` 表（guild_id、channel_id、min_severity、allow_unknown、webhook_url）以及用于去重的 `sent_items` 表（item_id、sent_at）。 |
| `lang_db.py` | `src/database/language.db` | `guild_languages` 表（guild_id、language）。默认：`EN`。 |
| `json_handler.py` | 任意 `.json` | 带校验（`list[dict]`）且**原子化**的 JSON 读写（临时文件 + `os.replace`）。 |

数据表会在首次使用时自动创建。`*.db` 和 `kve_sha.json` 已加入 `.gitignore`。

### `ui/`

基于 discord.py 的 **Components V2**（`LayoutView`、`Container`、`TextDisplay`、`MediaGallery`、`Label`）构建。每个面板显示 5 条结果，带有 *上一页 / 第 N 页 / 下一页* 按钮，180 秒后自动禁用。

- `cve_modal.py` —— 按 ID 搜索（用 `^CVE-\d{4}-\d{4,7}$` 校验）和按软件包搜索的弹窗。
- `cve_view.py` —— `CVEDetailView`（状态、日期、CVSS v4.0 或 v3.1 分数、向量、描述、最多 3 个参考链接、雷达图）和 `CVEPanel`（分页列表）。
- `exploit_ui.py` / `zeroday_ui.py` —— 结果面板；按钮以代码块形式显示代码，超过 2000 个字符时改为附件，并复用同一条消息。
- `kev_ui.py` —— `KevView`（CVE、厂商、产品、CWE、描述、所需措施、日期、勒索软件）和 `KevPanel`。

### `graph/` 与 `chart-lib/`

`graph/cve_radar.py`（`CVSSRadar`）接收 NVD 的 `dict` 或 JSON 字符串并调用 Rust 库。`chart-lib` 把 7 项 CVSS 指标（AV、AC、PR、UI、C、I、A）映射到 0–10 分，用 `plotters` 绘制 SVG 雷达图，再用 `resvg`/`tiny-skia` 转为 PNG，并在 `tokio::spawn_blocking` 中执行，避免阻塞 Python 的事件循环。需要系统中安装字体（如 DejaVu），否则会返回明确的错误。

### `translator/`

每个 cog 一个文件（`cvecog_t`、`exploitdbcog_t`、`zerodaycog_t`、`feedcog_t`、`helpcog_t`、`langcog_t`），内含字典 `{"PTBR"|"EN"|"ES": {...}}`。`*_translate(guild_id, *keys, **kwargs)` 函数从 `lang_db` 读取服务器语言并格式化文本。

---

## ⚙️ 配置

### `.env` 文件（仓库根目录）

```env
DISCORD_TOKEN=你的生产环境令牌
DEV_TOKEN=你的开发环境令牌
```

`src/main.py` 中设置为 `DEV = True`，此模式下读取 **`DEV_TOKEN`**。改为 `DEV = False` 即可使用 `DISCORD_TOKEN`。

### 代码中的配置项

| 配置 | 位置 | 默认值 |
| --- | --- | --- |
| Omega-Api 地址 | `src/httpx_client.py` → `BASE_URL` | `http://127.0.0.1:3000` |
| 推送间隔 | `setup_feed_task(interval_seconds=...)` | `7200` 秒（2 小时） |
| 监控的订阅源 | `cve_task.py` 中的 `DEFAULT_FEED_URLS` | `https://cvefeed.io/rssfeed/latest.atom` |
| webhook 并行发送数 | `MAX_CONCURRENT_SENDS` | `20` |
| 单次发送超时 | `WEBHOOK_SEND_TIMEOUT_SECONDS` | `10.0` 秒 |
| 每页结果数 | `src/ui/*` 中的 `PAGE_SIZE` | `5` |

### Discord 开发者门户

机器人使用 `discord.Intents.all()`，因此需要在门户中开启**特权 intents**（Presence、Server Members、Message Content）。在服务器中，它需要发送消息、embed 和文件的权限，并在接收推送的频道中拥有**管理 Webhook** 权限。

---

## 🚀 安装（简要）

完整的分步指南见 **[docs/SETUP.MD](docs/SETUP.MD)**。简要步骤：

```bash
# 1. 安装并启动 Omega-Api（独立项目）
git clone https://github.com/DriveAway500/Omega-Api.git

# 2. 虚拟环境与依赖
cd Enchiridion
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. 编译 Rust 库（需要 Rust 以及系统字体，如 DejaVu）
cd chart-lib
maturin develop --release
cd ..

# 4. 创建 .env 并启动
python src/main.py
```

环境要求：Python 3.10+（代码使用了 `X | Y` 语法和 `slots=True`）、Rust（edition 2024）、支持 Components V2 的 discord.py，以及正在运行的 Omega-Api。

---

## 📜 日志

| 位置 | 内容 |
| --- | --- |
| `logs/bot.log` | 所有日志（DEV 模式下为 DEBUG），每天午夜轮转，保留 14 天。 |
| `logs/errors/<模块>.log` | 仅 ERROR/CRITICAL，按错误发生的项目模块分别记录（5 MB × 3 份备份）。 |
| 控制台 | 与 `bot.log` 级别相同。 |

`discord` 和 `discord.http` 库被限制在 INFO/WARNING 级别，以减少噪音。

---

## 🚧 已知限制 / 路线图

- **KEV 推送尚未接入：** `src/feeds/kev_task.py` 只是原型（使用了未定义的 `WEBHOOK_URL`，且不会由机器人启动）。目前只有 CVE 推送是自动的。
- **KEV 界面仅有英文：** `/active_cve` 和 `kev_ui.py` 尚未使用翻译器。
- **`/help`** 只覆盖 `exploitdb`、`cve` 和 `zerodaytoday`。
- **Omega-Api 地址写死**在代码中（`BASE_URL`），无法通过 `.env` 配置。
- **订阅源的 `ETag`/`Last-Modified`** 不会在轮次之间保存，因此每 2 小时都会完整下载一次。
- 软件包搜索中的**年份列表**是固定的（2002–2026）。
- **`requirements.txt` 未锁定版本**，并且同时列出了 `dotenv` 和 `python-dotenv`；项目只需要 `python-dotenv`。
- **许可证：** 项目采用 MIT，但 `src/database/json_handler.py` 的文件头是 `SPDX-License-Identifier: GPL-3.0-only`。

---

## 📚 更多文档

- [docs/SETUP.MD](docs/SETUP.MD) —— 安装指南
- [docs/architecture.html](docs/architecture.html) —— 架构图
- [docs/feeds/ENGINE.MD](docs/feeds/ENGINE.MD) —— 订阅源引擎
- [docs/feeds/ENGMAN.MD](docs/feeds/ENGMAN.MD) —— 引擎修改手册
- [docs/feeds/CVETASK.MD](docs/feeds/CVETASK.MD) —— 定时推送任务

---

## 📄 许可证

[MIT](LICENSE) © 2026 DriveAway500
