# Feed Fetching Engine Documentation

## Overview

The feed fetching engine lives at `src/feeds/engine.py` and is responsible for **one thing only**: performing HTTP requests against feed sources (RSS, Atom, JSON Feed, or anything served over HTTP) and handing the raw payload to downstream consumers.

It deliberately contains **no parsing logic**. Parsers such as `feedparser` or custom JSON parsers receive a `FeedResponse` object and decide what to do with its `content` (bytes) or `text` (decoded string).

The design follows four core principles:

1. **Transport agnostic** — any HTTP client satisfying the `HttpClient` protocol works. `httpx.AsyncClient` satisfies it out of the box.
2. **Never raises for expected failures** — every fetch returns a `FeedFetchResult`, which is either a `FeedFetchSuccess` or a `FeedFetchFailure`. One broken feed never aborts the others.
3. **Conditional requests** — optional `ETag` / `Last-Modified` support so consumers can avoid re-downloading unchanged feeds.
4. **Immutable, strongly typed data objects** — all data classes are frozen and slotted.

---

## Transport Abstraction

The engine defines two protocols to decouple it from any specific HTTP library.

### `HttpResponse`

A minimal response interface requiring only four members:

| Member | Type | Description |
|---|---|---|
| `status_code` | `int` | HTTP status code |
| `content` | `bytes` | Raw response body |
| `headers` | `Mapping[str, str]` | Response headers |
| `encoding` | `str \| None` | Character encoding declared or inferred |

### `HttpClient`

A minimal async client interface requiring a single method:

```python
async def get(url: str, *, headers: Mapping[str, str] | None = None) -> HttpResponse
```

### `HttpClientFactory`

A `TypeAlias` for a zero-argument callable returning an async context manager that yields an `HttpClient`. Example: `get_http_client`.

---

## Request Description

### `FeedSource` (frozen dataclass)

Describes a feed to be fetched.

| Field | Type | Description |
|---|---|---|
| `url` | `str` | Absolute URL of the feed |
| `name` | `str \| None` | Optional human-friendly name for logs |
| `headers` | `Mapping[str, str]` | Extra request headers; override fetcher defaults |
| `etag` | `str \| None` | From a previous fetch; sent as `If-None-Match` |
| `last_modified` | `str \| None` | From a previous fetch; sent as `If-Modified-Since` |

Helper members:

- **`label`** — returns `name` when available, otherwise `url`. Used in log messages.
- **`conditional_headers()`** — builds a dict containing `If-None-Match` and/or `If-Modified-Since` from the stored cache validators.

---

## Results

All result types are frozen dataclasses, making them safe to pass around and store.

### `FeedResponse`

Raw payload retrieved from a feed source.

| Field | Type | Description |
|---|---|---|
| `source` | `FeedSource` | The source this response was fetched from |
| `status_code` | `int` | HTTP status code (2xx or 304) |
| `content` | `bytes` | Raw body; empty when `not_modified` is true |
| `headers` | `Mapping[str, str]` | Response headers with **lower-cased** keys |
| `encoding` | `str \| None` | Encoding reported by the HTTP client |
| `fetched_at` | `datetime` | UTC timestamp of receipt |

Convenience properties:

- **`not_modified`** — `True` when the server answered `304 Not Modified`.
- **`text`** — body decoded with `encoding` (UTF-8 fallback), using `errors="replace"` so it never raises.
- **`content_type`** — value of the `Content-Type` header.
- **`etag`** — value of the `ETag` header (store for future conditional requests).
- **`last_modified`** — value of the `Last-Modified` header (same purpose).

> **Parser tip:** prefer `content` (bytes) for XML-based parsers, since they can detect the encoding from the document itself. Use `text` for text-based parsers.

### `FeedFetchError` and `FeedFetchErrorKind`

`FeedFetchErrorKind` is an `Enum` with two members:

- **`HTTP_STATUS`** — the server answered with an unexpected HTTP status code.
- **`TRANSPORT`** — the request failed before a response was received (DNS, timeout, TLS, etc.).

`FeedFetchError` carries:

| Field | Type | Description |
|---|---|---|
| `kind` | `FeedFetchErrorKind` | Failure category |
| `message` | `str` | Human-readable description |
| `status_code` | `int \| None` | Set when `kind` is `HTTP_STATUS` |
| `exception` | `BaseException \| None` | Set when `kind` is `TRANSPORT` |

### `FeedFetchSuccess` / `FeedFetchFailure`

- **`FeedFetchSuccess`** holds `source` and `response` (a `FeedResponse`). It covers `304 Not Modified` as a success.
- **`FeedFetchFailure`** holds `source` and `error` (a `FeedFetchError`).

### `FeedFetchResult`

A `TypeAlias` for `FeedFetchSuccess | FeedFetchFailure`. Narrow it with `isinstance`.

---

## The Engine: `FeedFetcher`

### Constructor

```python
FeedFetcher(
    client_factory: HttpClientFactory,
    *,
    max_concurrency: int = 5,
    default_headers: Mapping[str, str] | None = None,
)
```

| Parameter | Description |
|---|---|
| `client_factory` | Callable producing an async context manager yielding an `HttpClient` |
| `max_concurrency` | Maximum simultaneous requests in `fetch_many` (must be ≥ 1) |
| `default_headers` | Headers sent with every request. Defaults to `{"Accept": DEFAULT_ACCEPT_HEADER}` |

Raises `ValueError` if `max_concurrency < 1`.

### `DEFAULT_ACCEPT_HEADER`

Unless overridden, every request sends:

```
application/atom+xml, application/rss+xml, application/feed+json,
application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5
```

This negotiates for known feed formats first, then generic XML, then anything.

### `async fetch(source: FeedSource) -> FeedFetchResult`

Fetches a single feed using a **fresh client** from the factory. Opens the client's async context manager, delegates to the internal fetch routine, and returns a `FeedFetchSuccess` or `FeedFetchFailure`.

### `async fetch_many(sources: Sequence[FeedSource]) -> list[FeedFetchResult]`

Fetches several feeds concurrently while **sharing one client**.

- Returns `[]` immediately when `sources` is empty.
- Uses an `asyncio.Semaphore` bound to `max_concurrency` to cap simultaneous requests.
- Uses `asyncio.gather` so requests run concurrently.
- Results are returned in the **same order** as the input `sources` list.

### Header Precedence

`_build_headers` merges three layers, later layers winning:

1. **Defaults** (`self._default_headers`)
2. **Source-specific** headers (`source.headers`)
3. **Conditional** headers (`If-None-Match`, `If-Modified-Since`)

This means a source can override the `Accept` header, and conditional validators always take precedence.

### Internal Fetch Routine (`_fetch_one`)

The flow for a single request:

1. Log the URL at `DEBUG`.
2. Call `client.get(url, headers=...)`.
3. **On any exception** (except `CancelledError`, see below): return a `FeedFetchFailure` with kind `TRANSPORT`, storing the exception. Log at `ERROR`.
4. **On a non-2xx, non-304 status**: return a `FeedFetchFailure` with kind `HTTP_STATUS`, storing the status code. Log at `ERROR`.
5. **On success (2xx or 304)**: build a `FeedResponse`:
   - `headers` keys are **lower-cased** so lookups are case-insensitive.
   - `fetched_at` is `datetime.now(timezone.utc)`.
   - Return `FeedFetchSuccess`.

Note the ordering: the `except Exception` clause is intentionally broad (`# noqa: BLE001`) because transport errors vary by client. `asyncio.CancelledError` is **not** a subclass of `Exception` in Python 3.8+, so cancellation still propagates — the engine never swallows it.

---

## Usage Example

```python
fetcher = FeedFetcher(get_http_client)
sources = [FeedSource(url="https://cvefeed.io/rssfeed/latest.atom")]

for result in await fetcher.fetch_many(sources):
    if isinstance(result, FeedFetchSuccess):
        if result.response.not_modified:
            continue
        parsed = feedparser.parse(result.response.content)
        ...
    else:
        logger.warning("Skipping %s: %s", result.source.label, result.error.message)
```

---

## Error-Handling Contract

| Scenario | Outcome |
|---|---|
| Successful 2xx response | `FeedFetchSuccess` with populated `FeedResponse` |
| `304 Not Modified` | `FeedFetchSuccess` with `response.not_modified == True` and empty `content` |
| Non-2xx / non-304 status | `FeedFetchFailure` (kind `HTTP_STATUS`) |
| DNS / timeout / TLS / connection error | `FeedFetchFailure` (kind `TRANSPORT`) |
| Task cancellation | `asyncio.CancelledError` propagates — **not** caught |
| Empty source list in `fetch_many` | Returns `[]` |

The engine guarantees that a batch fetch always returns one result per source, in input order, regardless of individual failures.

---

## Conditional Request Workflow

To avoid re-downloading unchanged feeds, consumers should:

1. Fetch a feed and, on success, store `response.etag` and `response.last_modified`.
2. On the next run, construct a `FeedSource` with `etag=` and `last_modified=` populated.
3. The engine automatically sends `If-None-Match` and `If-Modified-Since`.
4. If the server answers `304`, `response.not_modified` is `True` and `content` is empty — skip parsing.

---

## Extension Points

- **Custom HTTP clients**: implement the `HttpClient` protocol (any object with an async `get` method returning an `HttpResponse`-compatible object).
- **Custom headers**: pass `default_headers` to the constructor, or per-source `headers` on `FeedSource`.
- **Concurrency tuning**: adjust `max_concurrency` to balance throughput against server politeness.
- **Parsers**: consume `FeedResponse.content` / `.text` — the engine never interprets payloads.

---

## Summary

`src/feeds/engine.py` is a small, focused transport layer. It guarantees immutable typed results, per-feed failure isolation, ordered concurrent fetching, and optional conditional requests, while staying entirely agnostic to HTTP libraries and feed formats. Everything downstream — parsing, validation, persistence — belongs to other modules that consume `FeedFetchResult` values.