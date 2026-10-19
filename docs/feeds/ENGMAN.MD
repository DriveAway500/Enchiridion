# Hacking Manual: `src/feeds/engine.py`

A practical guide to modifying the feed fetching engine — including a dedicated section on using it correctly in your own code.

---

# Part I — Using the Engine

Before hacking on it, understand how to consume it. Most "modifications" people think they need are actually usage patterns.

## 1. Basic single fetch

```python
from src.feeds.engine import FeedFetcher, FeedSource, FeedFetchSuccess

fetcher = FeedFetcher(get_http_client)  # get_http_client is your factory
result = await fetcher.fetch(FeedSource(url="https://example.com/feed.atom"))

if isinstance(result, FeedFetchSuccess):
    body = result.response.content
else:
    log.error("%s: %s", result.source.label, result.error.message)
```

`fetch()` opens a **new client per call**. Use it for one-off fetches, CLI tools, or tests.

## 2. Batch fetch with ordering guarantees

```python
sources = [
    FeedSource(url="https://a.com/rss", name="A"),
    FeedSource(url="https://b.com/atom", name="B"),
]
results = await fetcher.fetch_many(sources)

for source, result in zip(sources, results):
    assert result.source is source  # order is preserved
```

`fetch_many()` shares **one client** across all requests. The returned list is index-aligned with the input. Empty input returns `[]` without opening a client — cheap to call unconditionally.

## 3. Conditional requests (the important pattern)

The engine is designed around a two-phase contract:

**Phase 1 — fetch and persist validators:**

```python
result = await fetcher.fetch(source)
if isinstance(result, FeedFetchSuccess) and not result.response.not_modified:
    store.save(
        url=source.url,
        etag=result.response.etag,                    # may be None
        last_modified=result.response.last_modified,  # may be None
        content=result.response.content,
    )
```

**Phase 2 — rehydrate validators and refetch:**

```python
cached = store.load(source.url)
source = FeedSource(
    url=source.url,
    etag=cached.etag,
    last_modified=cached.last_modified,
)
result = await fetcher.fetch(source)
if isinstance(result, FeedFetchSuccess) and result.response.not_modified:
    return cached.content  # server confirmed nothing changed
```

Two rules that will bite you if ignored:

- **Store validators verbatim.** Do not normalize or strip quotes from `ETag`. Servers do byte comparison on `If-None-Match`.
- **Both validators are independent.** A server may send only one. Populate whichever you have; leave the other `None`. The engine only sends headers for non-`None` values.

## 4. Custom `Accept` header (format-restricted sources)

By default the engine advertises a feed-friendly `Accept` header. To restrict a specific source (e.g. a JSON-only endpoint that misbehaves on generic `Accept`):

```python
source = FeedSource(
    url="https://example.com/feed.json",
    headers={"Accept": "application/feed+json"},
)
```

Per-source headers win over `default_headers`. They are also overridden by conditional headers, so you cannot break `If-None-Match` by accident.

## 5. Global header override (auth, user-agent, API keys)

```python
fetcher = FeedFetcher(
    get_http_client,
    default_headers={
        "Accept": "application/atom+xml",
        "User-Agent": "my-app/1.0 (+https://example.com)",
        "Authorization": f"Bearer {token}",
    },
)
```

The default `default_headers` is **replaced**, not merged. If you supply `default_headers={"User-Agent": ...}`, the `Accept` header is gone — set it explicitly.

## 6. Reading the body without a parser

```python
resp = result.response
resp.content          # bytes — preferred for XML parsers
resp.text             # str — decoded with resp.encoding or UTF-8, errors="replace"
resp.content_type     # 'application/atom+xml' or None
resp.not_modified     # True iff status_code == 304
resp.fetched_at       # tz-aware UTC datetime
```

`resp.text` never raises on undecodable bytes. If you need strict decoding, decode `resp.content` yourself.

## 7. Tuning concurrency

```python
fetcher = FeedFetcher(get_http_client, max_concurrency=20)
```

Raises `ValueError` if `< 1`. The semaphore is created **per `fetch_many` call**, not per fetcher — reusing a fetcher does not leak permits across calls.

## 8. What NOT to do

| Anti-pattern | Why it breaks |
|---|---|
| Catching `FeedFetchFailure` and re-raising as an exception | Defeats isolation; one bad feed aborts the batch |
| Assuming `response.content` is non-empty for `not_modified` | It's `b""` by design |
| Parsing inside `fetch_many` | The engine yields before parsing; parsers may block the event loop |
| Calling `fetch()` in a loop for batch work | Opens N clients; use `fetch_many()` |
| Relying on `result.error.exception` being set for `HTTP_STATUS` | It's only set for `TRANSPORT` |
| Treating cancellation as a failure | `CancelledError` propagates — do not wrap `fetch_many` in a bare `except Exception` if you need shutdown semantics |

---

# Part II — Modifying the Engine

The engine is deliberately small. Most extensions fall into one of five categories.

## A. Adding a new HTTP client

You don't touch the engine. Implement the protocol:

```python
class MyClient:
    def __init__(self, session): self._session = session

    async def get(self, url, *, headers=None):
        return await self._session.get(url, headers=headers)

class MyResponse:
    def __init__(self, r): self._r = r
    @property
    def status_code(self): return self._r.status
    @property
    def content(self): return self._r.body
    @property
    def headers(self): return self._r.headers
    @property
    def encoding(self): return self._r.charset
```

Rules the engine relies on:

- `headers` may be any `Mapping[str, str]`. The engine lower-cases keys itself, so mixed-case from the client is fine.
- `encoding` may be `None`. `FeedResponse.text` falls back to UTF-8.
- `status_code` is read exactly once — no need to cache.
- Exceptions from `get()` are caught by a broad `except Exception`. If your client raises `BaseException` subclasses (rare), they will escape — fix the client.

Register via a factory:

```python
def my_factory():
    return _AsyncCM(MyClient(...))  # anything with __aenter__/__aexit__
```

## B. Adding a new failure category

Example: distinguishing `TOO_MANY_REDIRECTS` from generic transport errors.

1. Add the enum member:

```python
class FeedFetchErrorKind(str, Enum):
    HTTP_STATUS = "http_status"
    TRANSPORT = "transport"
    REDIRECT_LOOP = "redirect_loop"   # new
```

2. Classify in `_fetch_one` **before** the generic `except`:

```python
try:
    response = await client.get(source.url, headers=self._build_headers(source))
except RedirectLoopError as exc:
    return FeedFetchFailure(
        source=source,
        error=FeedFetchError(
            kind=FeedFetchErrorKind.REDIRECT_LOOP,
            message=str(exc),
            exception=exc,
        ),
    )
except Exception as exc:
    ...
```

Ordering matters: specific handlers must come before `except Exception`. Preserve the `CancelledError` behavior — do not add `except BaseException`.

3. Update `__all__` only if you add new public names. Enum members don't need it.

## C. Adding a new successful outcome

Example: treat `410 Gone` as a distinct "feed is dead" signal that consumers should act on (unsubscribe), without making it a failure.

**Option 1 — new result type (preferred):**

```python
@dataclass(frozen=True, slots=True)
class FeedFetchGone:
    source: FeedSource

FeedFetchResult = FeedFetchSuccess | FeedFetchFailure | FeedFetchGone
```

Then in `_fetch_one`, branch before the status check:

```python
if status == 410:
    return FeedFetchGone(source=source)
```

Add to `__all__`. Every consumer's `isinstance` chain needs an `else` branch — this is a breaking change to the union, so bump accordingly.

**Option 2 — a flag on `FeedResponse` (non-breaking):**

Add a property:

```python
@property
def gone(self) -> bool:
    return self.status_code == 410
```

…but this requires `410` to be treated as success, which contradicts the current contract. Don't do this; use Option 1.

## D. Adding response metadata

Example: expose `Retry-After` for rate-limit handling.

```python
@property
def retry_after(self) -> str | None:
    return self.headers.get("retry-after")
```

Since headers are already lower-cased and stored, this is a pure addition. No constructor change.

For **request-side** metadata (things you want to know at fetch time), add fields to `FeedSource`:

```python
@dataclass(frozen=True, slots=True)
class FeedSource:
    url: str
    ...
    timeout_s: float | None = None   # new
```

Then plumb it through `_build_headers` … except headers can't carry timeouts. You'll need to extend `HttpClient.get`:

```python
async def get(
    self,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout_s: float | None = None,   # new
) -> HttpResponse: ...
```

This is a **breaking protocol change** — every client implementation must accept the new kwarg (or use `**kwargs`). Coordinate it. Existing `httpx.AsyncClient` does **not** accept `timeout_s`; you'll need an adapter or a keyword rename (`timeout=` collides with httpx semantics).

## E. Changing header precedence

Current order: `defaults < source.headers < source.conditional_headers()`. The engine's test suite likely asserts this. If you flip it (e.g. to allow per-source `If-None-Match` override), document why and update:

```python
def _build_headers(self, source: FeedSource) -> dict[str, str]:
    return {
        **self._default_headers,
        **source.conditional_headers(),   # moved up
        **source.headers,                 # moved down
    }
```

Risk: consumers with misconfigured caches can now *disable* conditional requests by setting an empty-string header. Decide whether that's acceptable.

## F. Changing concurrency semantics

The semaphore is created inside `fetch_many`. To enforce concurrency across **multiple** `fetch_many` calls on the same fetcher:

```python
def __init__(self, ...):
    ...
    self._semaphore = asyncio.Semaphore(max_concurrency)  # moved here

async def fetch_many(self, sources):
    ...
    async def guarded(client, source):
        async with self._semaphore:   # shared
            return await self._fetch_one(client, source)
```

Trade-off: a fetcher created outside an event loop binds the semaphore to that loop. If you reuse fetchers across loops (e.g. pytest with fresh loops per test), you'll get `RuntimeError: ... bound to a different event loop`. Either keep the per-call semaphore, or document the single-loop constraint loudly.

## G. Cancellation semantics — do not touch

The `except Exception` clause excludes `CancelledError` by design. If you're tempted to catch `BaseException`:

- You will swallow shutdown signals.
- `asyncio.timeout()` will no longer cancel in-flight fetches.
- Structured concurrency (`TaskGroup`) will hang.

If you need to log cancellations, use `try/finally`, not `except`:

```python
try:
    response = await client.get(...)
finally:
    logger.debug("fetch finished for %s", source.label)
```

The `finally` runs on both success and cancellation without swallowing the exception.

## H. Adding retries

Do not add retries inside `_fetch_one`. Retries are policy and belong to the caller:

```python
async def fetch_with_retry(fetcher, source, attempts=3):
    for i in range(attempts):
        result = await fetcher.fetch(source)
        if isinstance(result, FeedFetchSuccess):
            return result
        if result.error.kind is FeedFetchErrorKind.HTTP_STATUS and \
           result.error.status_code and 400 <= result.error.status_code < 500:
            return result  # 4xx: don't retry
        await asyncio.sleep(2 ** i)
    return result
```

If you insist on in-engine retries, respect these rules:

- Never retry `CancelledError`.
- Never retry `HTTP_STATUS` with `status_code` in `{400, 401, 403, 404, 410}`.
- Honor `Retry-After` when present.
- Do not retry inside the `fetch_many` semaphore without releasing it — you'll deadlock. Acquire/release per attempt:

```python
async def guarded(client, source):
    for attempt in range(max_retries):
        async with semaphore:
            result = await self._fetch_one(client, source)
        if should_retry(result) and attempt + 1 < max_retries:
            await asyncio.sleep(...)
            continue
        return result
```

## I. Testing your changes

The engine's contracts that your changes must preserve:

| Contract | Test with |
|---|---|
| Order preservation in `fetch_many` | Fake client returning out-of-order; assert `zip(sources, results)` |
| Semaphore bound | Fake client that records `max_in_flight`; assert ≤ `max_concurrency` |
| Failure isolation | One fake that raises, one that succeeds; assert one of each |
| Conditional headers | Assert `If-None-Match` / `If-Modified-Since` appear exactly when set |
| Header precedence | Source header overrides default; conditional overrides source |
| 304 handling | Assert `not_modified` is `True`, `content == b""` |
| Cancellation propagation | `asyncio.wait_for(fetch, 0.01)` with a slow fake; assert `TimeoutError` escapes |
| Empty input | `fetch_many([])` returns `[]` without calling factory |

Fake client template:

```python
class FakeClient:
    def __init__(self, responses): self._responses = responses
    async def get(self, url, *, headers=None):
        self.last_headers = headers
        return self._responses[url]
```

---

## Checklist before merging a change to `engine.py`

- [ ] The change does **not** add parsing logic. If it does, it belongs elsewhere.
- [ ] The change does **not** swallow `CancelledError`.
- [ ] The change does **not** raise for expected network or HTTP failures.
- [ ] `fetch_many` still returns one result per source, in input order.
- [ ] All result dataclasses are still `frozen=True, slots=True`.
- [ ] `__all__` is updated if you added public names.
- [ ] `FeedResponse.headers` keys are still lower-cased.
- [ ] `FeedResponse.text` still never raises.
- [ ] Header precedence is documented if changed.
- [ ] A new `FeedFetchErrorKind` member has a matching branch in `_fetch_one`.
- [ ] A new `FeedFetchResult` member forces every `isinstance` consumer to handle it (search the codebase).