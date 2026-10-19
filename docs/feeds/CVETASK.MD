# Periodic Feed Task Documentation

## Overview

The periodic feed task lives at `src/feeds/task.py` and orchestrates the entire feed pipeline, from HTTP download to Discord delivery. It is the glue layer that connects four independent components:

```
FeedFetcher (HTTP) -> CVEFeedParser (parsing) -> dedup (database)
    -> subscription filter -> Discord webhook delivery
```

Unlike `engine.py` (which is pure transport) and the parser (which is pure interpretation), this module owns **policy**: which feeds to poll, how often, which items to send to which subscribers, how many sends to run in parallel, and what to do when a webhook dies.

---

## Module Constants

| Constant | Value | Purpose |
|---|---|---|
| `MAX_CONCURRENT_SENDS` | `20` | Maximum simultaneous webhook deliveries in one cycle |
| `WEBHOOK_SEND_TIMEOUT_SECONDS` | `10.0` | Per-webhook timeout for a single send |
| `DEFAULT_FEED_URLS` | `("https://cvefeed.io/rssfeed/latest.atom",)` | Feeds polled when the caller does not supply any |

---

## Types

### `FeedSubscription` (Protocol)

Structural type describing a subscription row returned by `feed_db`. Any object exposing these properties works — no inheritance required.

| Member | Type | Meaning |
|---|---|---|
| `guild_id` | `int` | Discord guild (server) the subscription belongs to |
| `channel_id` | `int` | Discord channel the subscription targets |
| `webhook_url` | `str \| None` | Webhook used for delivery; `None` means misconfigured |
| `min_severity` | `float` | Minimum severity score required to deliver an item |
| `allow_unknown` | `bool` | Whether items with no classifiable severity pass the filter |

### `FeedBot` (Protocol)

The subset of the bot instance this task depends on:

| Member | Type | Meaning |
|---|---|---|
| `webhook_session` | `aiohttp.ClientSession` | Shared session used for Discord webhook delivery |
| `wait_until_ready()` | `async` | Coroutine the task awaits before its first run |

Keeping this narrow means the task is testable without a full bot.

### `DeliveryStatus` (Enum)

Outcome of sending **one item to one subscription**:

| Member | Meaning |
|---|---|
| `SENT` | Webhook accepted the message |
| `FAILED` | Send failed (timeout, transient Discord error, or no webhook URL) |
| `WEBHOOK_GONE` | Discord reports the webhook no longer exists; the subscription should be deleted |

### `CycleStats` (dataclass, `slots=True`)

Counters for one feed cycle. All default to `0`.

| Field | Meaning |
|---|---|
| `items_found` | New items discovered after deduplication |
| `subscriptions` | Subscriptions loaded from the database |
| `matched` | Total (item, subscription) pairs that passed the severity filter |
| `sent_ok` | Successful deliveries |
| `sent_failed` | Failed deliveries (including webhook-gone cases) |

`CycleStats` is logged at the end of every cycle, so its `repr` doubles as a summary line.

---

## Delivery Layer

### `_build_embed(item: VulnerabilityData) -> discord.Embed`

Converts a parsed vulnerability into a Discord embed:

| Field | Source | Truncation |
|---|---|---|
| `title` | `"{label} {title}"` | 256 chars (Discord limit) |
| `url` | `item.link` | — |
| `description` | `item.summary` | 4000 chars (safety margin under Discord's 4096) |
| `color` | `item.severity.color_hex` | Parsed as base-16 int |

The label prefix (e.g. `CRITICAL`, `HIGH`) makes the severity visible in the notification preview, before the title.

### `_matches_filter(item, sub) -> bool`

Decides whether an item should be delivered to a subscription:

- If `item.severity.score` is **`None`** (unknown severity), the item passes only when `sub.allow_unknown` is `True`.
- Otherwise, the item passes when `score >= sub.min_severity`.

The unknown-severity branch is the important one: it lets subscribers opt **in** to items the parser could not classify, rather than silently dropping them.

### `_send_to_subscription(session, sub, item) -> DeliveryStatus`

Sends one item to one subscription's webhook:

1. If `sub.webhook_url` is falsy, returns `FAILED` without touching the network.
2. Builds a `discord.Webhook` from the URL using the shared aiohttp session.
3. Sends the embed wrapped in `asyncio.wait_for(..., timeout=WEBHOOK_SEND_TIMEOUT_SECONDS)`.
4. Maps outcomes to `DeliveryStatus`:

| Exception / case | Status | Log level |
|---|---|---|
| Success | `SENT` | — |
| `asyncio.TimeoutError` | `FAILED` | WARNING |
| `discord.NotFound` | `WEBHOOK_GONE` | WARNING |
| `discord.DiscordException` | `FAILED` | WARNING (with traceback) |

The `discord.NotFound` → `WEBHOOK_GONE` distinction is what allows the pipeline to **self-heal**: subscriptions pointing at deleted webhooks are removed automatically. Every other failure is treated as transient and the subscription is preserved.

---

## Pipeline

The pipeline is split into two functions: one for **gathering new items**, one for **distributing** them. Keeping them separate means you can run collection alone (for debugging or dry runs) without touching Discord.

### `collect_new_items(fetcher, parser, sources) -> list[VulnerabilityData]`

Fetches, parses, and deduplicates items across all sources.

**Flow:**

1. Calls `fetcher.fetch_many(sources)` — all feeds in parallel, one result per source, in input order.
2. For each **successful** result:
   - Failures (`FeedFetchFailure`) are skipped silently — the engine already logged them. One broken feed never aborts the cycle.
   - The response is handed to `parser.parse(result.response)`.
3. For each parsed vulnerability:
   - If its `id` was already seen **in this cycle**, skip it (cross-feed dedup).
   - If `feed_db.is_sent(id)` returns `True`, count it as `already_sent` and skip (persistent dedup).
   - Otherwise, add it to `seen_ids` and the output list.
4. Per-source logging reports: total entries, already sent, discarded unclassified, discarded invalid, and new items ready to send.

**Deduplication has two layers** and both matter:

- **In-cycle (`seen_ids`)**: the same CVE appearing in multiple feeds is sent once.
- **Cross-cycle (`feed_db.is_sent`)**: a CVE delivered in a previous cycle is never re-sent.

Both are checked before the item is appended, so the ordering is deterministic.

**Returns** new items, oldest first within each feed, in the order feeds were processed.

### `process_feeds_once(session, fetcher, parser, sources) -> CycleStats`

Runs one complete cycle: collection, filtering, delivery, and bookkeeping.

**Flow:**

1. Call `collect_new_items(...)`. Set `stats.items_found`. Short-circuit with the stats object if no items were found — **no subscriptions are loaded and no Discord traffic happens**.
2. Load all subscriptions via `feed_db.list_subscriptions()`. Set `stats.subscriptions`.
3. Create a single `asyncio.Semaphore(MAX_CONCURRENT_SENDS)` for the cycle. The limit applies **across items**, so a single item with hundreds of matching subscribers cannot saturate the event loop.
4. For each item, in order:
   - Filter subscriptions with `_matches_filter`. Accumulate `stats.matched`.
   - If no subscription matches, `continue` — **the item is still marked as sent at the end of the loop**, ensuring it is never reconsidered.
   - Send to all matching subscriptions concurrently via `asyncio.gather`, each wrapped by `send_with_limit` (semaphore-guarded).
   - Inspect the gathered statuses in input order:
     - `SENT` → `stats.sent_ok += 1`
     - Anything else → `stats.sent_failed += 1`
     - `WEBHOOK_GONE` → also `await feed_db.remove_subscription(guild_id, channel_id)`
   - Call `await feed_db.mark_sent(item.id)` **unconditionally**, even if all sends failed.

**Design decisions worth noting:**

- **Items are marked sent even when delivery fails.** This prevents a permanently broken subscription from blocking a queue of items forever. The trade-off is that a transient Discord outage loses items for affected subscriptions. If you need at-least-once delivery, this is the line to change (see the hacking manual for details).
- **Semaphore is per-cycle**, not per-fetcher. A fresh cycle starts with a fresh budget.
- **Concurrency is bounded twice**: `FeedFetcher.fetch_many` caps *fetches*, and `MAX_CONCURRENT_SENDS` caps *webhook sends*. They are independent.
- **Ordering is preserved where it matters**: `gather` returns results in argument order, and `zip(matching_subs, statuses)` relies on that. Do not reorder the send coroutines.
- **Webhook removal happens inside the loop**, so a subscription with a dead webhook is removed at most once per item it matched — but the DB call is idempotent, so repeated removal is harmless.

**Returns** the populated `CycleStats`, which is also logged at INFO level.

---

## Task Setup

### `setup_feed_task(bot, interval_seconds=7200, feed_urls=DEFAULT_FEED_URLS) -> tasks.Loop`

Creates the periodic task. **The caller is responsible for starting it** (`feed_task.start()`), which allows the bot's startup sequence to control when polling begins.

**Construction:**

- Builds a single `FeedFetcher(get_http_client)` — reused across cycles, so the client factory is called once per `fetch_many`, not per fetcher.
- Builds a single `CVEFeedParser()` — reused, so any parser caches survive between cycles.
- Converts `feed_urls` into `FeedSource` objects **once**, at setup time. This means `etag` / `last_modified` are **not** persisted across restarts; conditional requests are effectively disabled unless the caller supplies validators (see the hacking manual for how to add persistence).

**The loop itself (`feed_task`):**

- Decorated with `@tasks.loop(seconds=interval_seconds)` — 2 hours by default.
- Wraps `process_feeds_once` in a broad `try/except Exception` and logs with `logger.exception`. This is deliberate: a raised exception would otherwise kill the loop. The `FeedFetcher` already swallows expected failures, so anything reaching this handler is a genuine bug — but the loop must survive it.
- `asyncio.CancelledError` propagates (it is not a subclass of `Exception` in Python 3.8+), so shutdown still works.

**`before_loop` hook (`before_feed_task`):**

- Awaits `bot.wait_until_ready()` before the first iteration. Without this, the first cycle would run before Discord state (sessions, caches) is initialized.

**`error` hook (`feed_task_error`):**

- Called by `discord.ext.tasks` when the loop body raises **outside** the inner try/except — for example, if `before_loop` fails, or if a future refactor removes the inner handler.
- Logs at `CRITICAL` with the full traceback, re-constructed from `error.__traceback__` since `exc_info` needs a tuple outside an `except` block.
- Does **not** restart the loop. `discord.ext.tasks` handles restart policy (backoff, retry count) based on loop configuration.

---

## Lifecycle Walkthrough

A single cycle, end to end:

1. `before_loop` completes (bot ready).
2. `feed_task` fires after `interval_seconds`.
3. `process_feeds_once` runs:
   - `fetch_many` downloads all feeds concurrently (bounded by the fetcher's `max_concurrency`, default 5).
   - Each successful response is parsed; failures are skipped.
   - Items are deduplicated against the current cycle and the database.
   - Subscriptions are loaded; items are filtered per subscription.
   - Matching (item, subscription) pairs are delivered concurrently (bounded by 20).
   - Dead webhooks trigger subscription removal.
   - Every processed item is marked sent.
4. `CycleStats` is logged.
5. The loop sleeps for `interval_seconds`.
6. Repeat until the bot shuts down.

---

## Failure Isolation Summary

The task layers failures so that no single problem cascades:

| Failure | Handled by | Effect |
|---|---|---|
| One feed down (DNS, TLS, timeout) | `FeedFetcher` returns `FeedFetchFailure` | Other feeds still processed |
| One feed returns garbage | `parser.parse` (out of scope here) | Logged; other feeds unaffected |
| One webhook times out | `asyncio.wait_for` → `FAILED` | Other subscriptions unaffected |
| One webhook deleted | `discord.NotFound` → `WEBHOOK_GONE` | Subscription removed |
| One webhook returns transient error | `discord.DiscordException` → `FAILED` | Subscription preserved |
| Database `is_sent` raises | **Not caught** — bubbles to `feed_task`'s handler | Cycle aborted, loop survives, retried next interval |
| Database `mark_sent` raises | **Not caught** — same | Same |
| Entire cycle raises | `feed_task`'s `except Exception` | Loop survives, next cycle retried |
| Bot shutting down | `CancelledError` propagates | Loop terminates cleanly |

The asymmetry is intentional: **network and Discord failures are expected and isolated; database failures are not**. A failed DB write means state is inconsistent, and silently continuing would risk re-sending or losing items. Better to abort the cycle and retry.

---

## Configuration Surface

| Knob | Where | Default | Effect |
|---|---|---|---|
| Poll interval | `setup_feed_task(interval_seconds=...)` | `7200` (2 h) | Time between cycles |
| Feeds | `setup_feed_task(feed_urls=...)` | `DEFAULT_FEED_URLS` | Which URLs are monitored |
| Fetch concurrency | `FeedFetcher(max_concurrency=...)` | `5` (engine default) | Simultaneous downloads |
| Delivery concurrency | `MAX_CONCURRENT_SENDS` (module constant) | `20` | Simultaneous webhook sends |
| Per-send timeout | `WEBHOOK_SEND_TIMEOUT_SECONDS` (module constant) | `10.0` | Max time per webhook call |

The last two are module-level constants, not parameters. To change them per deployment you must either edit the module or refactor them into `setup_feed_task` arguments — see the hacking manual for the recommended approach.

---

## Testing the Task

The protocols make the task fully testable without Discord or a real database:

- **Fake `FeedBot`**: any object with a `webhook_session` attribute and an `async def wait_until_ready`. For tests of `process_feeds_once`, you only need the session.
- **Fake `FeedSubscription`**: a frozen dataclass with the five properties. Use `webhook_url=None` to exercise the `FAILED` path without network.
- **Fake `FeedFetcher`**: a stub with an async `fetch_many` returning canned `FeedFetchSuccess` / `FeedFetchFailure` objects.
- **Fake parser**: an object with a `parse(response)` returning a `ParsedFeed` with controllable `vulnerabilities`, `total_entries`, `discarded_unclassified`, `discarded_invalid`, and `source`.
- **Mock `feed_db`**: a module-level monkeypatch of `is_sent`, `list_subscriptions`, `mark_sent`, and `remove_subscription`. Assert call counts and arguments.

Key behaviors to assert:

- A `FeedFetchFailure` in `fetch_many` does not prevent other feeds from being processed.
- Duplicate IDs **across feeds in one cycle** are sent once.
- IDs **already in `feed_db`** are not included in the output.
- `allow_unknown=False` drops items with `severity.score is None`.
- `WEBHOOK_GONE` triggers exactly one `remove_subscription` call with the correct `(guild_id, channel_id)`.
- `mark_sent` is called for **every** item that reached the delivery loop, including items with zero matching subscriptions.
- `mark_sent` is **not** called for items that failed the filter in `collect_new_items` (i.e. items never entered the delivery loop because they were deduplicated).
- `process_feeds_once` returns early with `items_found == 0` and does not call `list_subscriptions`.
- `setup_feed_task` returns a loop that is **not yet started**.

---

## Relationship to `engine.py`

`task.py` treats `engine.py` as a black box. The only interactions are:

- Constructing a `FeedFetcher(get_http_client)` once per task setup.
- Building `FeedSource` objects from URLs.
- Calling `fetch_many` and branching on `FeedFetchSuccess` vs `FeedFetchFailure`.

All transport concerns — retries, conditional headers, header precedence, cancellation propagation — remain inside the engine. If you need to change any of those, modify `engine.py` (see its hacking manual) and the task inherits the change automatically. Conversely, changes to how items are *routed*, *filtered*, *deduplicated*, or *delivered* belong here, not in the engine.

---

## Known Limitations and Extension Points

These are documented here because they are the most common sources of "why didn't my feed get delivered?" confusion:

1. **Conditional requests are not persisted.** `FeedSource` objects are built once in `setup_feed_task` without `etag` / `last_modified`, so every cycle re-downloads full bodies. Adding persistence requires storing validators per URL and rebuilding sources each cycle (see the hacking manual for `engine.py` for the pattern).

2. **Items are marked sent even when all deliveries fail.** Intentional trade-off for queue liveness; see "Failure Isolation Summary" above. Changing this requires a per-(item, subscription) delivery ledger rather than a single `is_sent` bit.

3. **Database failures abort the cycle.** Also intentional — silent continuation risks inconsistency. If you want best-effort behavior, catch `feed_db` exceptions at the call sites inside `process_feeds_once` and log instead of raising.

4. **Concurrency constants are not parameters.** `MAX_CONCURRENT_SENDS` and `WEBHOOK_SEND_TIMEOUT_SECONDS` are module-level. Promoting them to `setup_feed_task` arguments is a small, non-breaking change.

5. **The parser is constructed once and shared.** If `CVEFeedParser` holds mutable state that is not cycle-safe, this becomes a bug. Verify the parser is stateless (or that its state is intentionally reset per `parse` call) before relying on the shared instance.