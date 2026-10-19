"""Generic feed fetching engine.

This module is responsible for **one thing only**: performing HTTP requests
against feed sources (RSS, Atom, JSON Feed, or anything served over HTTP) and
handing the raw payload to downstream consumers.

It deliberately contains **no parsing logic**. Parsers (``feedparser``, custom
JSON parsers, etc.) receive a :class:`FeedResponse` and decide what to do with
its ``content`` / ``text``.

Design goals:

* **Transport agnostic**: any HTTP client that satisfies the :class:`HttpClient`
  protocol works (``httpx.AsyncClient`` does out of the box).
* **Never raises for expected failures**: every fetch returns a
  :data:`FeedFetchResult`, which is either a :class:`FeedFetchSuccess` or a
  :class:`FeedFetchFailure`. One broken feed never aborts the others.
* **Conditional requests**: optional ``ETag`` / ``Last-Modified`` support so
  consumers can avoid re-downloading unchanged feeds.
* **Immutable, strongly typed data objects**.

Example::

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
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Protocol, TypeAlias

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_ACCEPT_HEADER",
    "FeedFetchError",
    "FeedFetchErrorKind",
    "FeedFetchFailure",
    "FeedFetchResult",
    "FeedFetchSuccess",
    "FeedFetcher",
    "FeedResponse",
    "FeedSource",
    "HttpClient",
    "HttpClientFactory",
    "HttpResponse",
]

DEFAULT_ACCEPT_HEADER: str = (
    "application/atom+xml, application/rss+xml, application/feed+json, "
    "application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5"
)
"""Default ``Accept`` header sent with every request unless overridden."""


# --------------------------------------------------------------------------- #
# Transport abstraction
# --------------------------------------------------------------------------- #


class HttpResponse(Protocol):
    """Minimal response interface required by the fetcher.

    ``httpx.Response`` satisfies this protocol without any adaptation.
    """

    @property
    def status_code(self) -> int:
        """HTTP status code of the response."""
        ...

    @property
    def content(self) -> bytes:
        """Raw response body."""
        ...

    @property
    def headers(self) -> Mapping[str, str]:
        """Response headers."""
        ...

    @property
    def encoding(self) -> str | None:
        """Character encoding declared or inferred for the body, if any."""
        ...


class HttpClient(Protocol):
    """Minimal async HTTP client interface required by the fetcher.

    ``httpx.AsyncClient`` satisfies this protocol without any adaptation.
    """

    async def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        """Perform a ``GET`` request and return the response."""
        ...


HttpClientFactory: TypeAlias = Callable[[], AbstractAsyncContextManager[HttpClient]]
"""Zero-argument callable returning an async context manager that yields an
:class:`HttpClient`. Example: ``get_http_client``."""


# --------------------------------------------------------------------------- #
# Request description
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class FeedSource:
    """Describes a feed to be fetched.

    Attributes:
        url: Absolute URL of the feed.
        name: Optional human-friendly name, used for logs and identification.
        headers: Extra request headers. They override the fetcher defaults.
        etag: ``ETag`` from a previous fetch. When set, sent as ``If-None-Match``.
        last_modified: ``Last-Modified`` from a previous fetch. When set, sent
            as ``If-Modified-Since``.
    """

    url: str
    name: str | None = None
    headers: Mapping[str, str] = field(default_factory=dict)
    etag: str | None = None
    last_modified: str | None = None

    @property
    def label(self) -> str:
        """Display label: ``name`` when available, otherwise ``url``."""
        return self.name or self.url

    def conditional_headers(self) -> dict[str, str]:
        """Build the conditional-request headers derived from cache validators."""
        result: dict[str, str] = {}
        if self.etag:
            result["If-None-Match"] = self.etag
        if self.last_modified:
            result["If-Modified-Since"] = self.last_modified
        return result


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class FeedResponse:
    """Raw payload retrieved from a feed source.

    Parsers should consume :attr:`content` (bytes) whenever possible, since
    XML-based parsers can detect the encoding from the document itself.
    :attr:`text` is provided as a convenience for text-based parsers.

    Attributes:
        source: The source this response was fetched from.
        status_code: HTTP status code (2xx or 304).
        content: Raw response body. Empty when :attr:`not_modified` is true.
        headers: Response headers with **lower-cased** keys.
        encoding: Character encoding reported by the HTTP client, if any.
        fetched_at: UTC timestamp of when the response was received.
    """

    source: FeedSource
    status_code: int
    content: bytes
    headers: Mapping[str, str]
    encoding: str | None
    fetched_at: datetime

    @property
    def not_modified(self) -> bool:
        """``True`` if the server answered ``304 Not Modified``."""
        return self.status_code == 304

    @property
    def text(self) -> str:
        """Body decoded to ``str`` using :attr:`encoding` (UTF-8 fallback).

        Undecodable bytes are replaced rather than raising.
        """
        return self.content.decode(self.encoding or "utf-8", errors="replace")

    @property
    def content_type(self) -> str | None:
        """Value of the ``Content-Type`` header, if present."""
        return self.headers.get("content-type")

    @property
    def etag(self) -> str | None:
        """Value of the ``ETag`` header, to be stored for conditional requests."""
        return self.headers.get("etag")

    @property
    def last_modified(self) -> str | None:
        """Value of the ``Last-Modified`` header, to be stored for conditional requests."""
        return self.headers.get("last-modified")


class FeedFetchErrorKind(str, Enum):
    """Category of a fetch failure."""

    HTTP_STATUS = "http_status"
    """The server answered with an unexpected HTTP status code."""

    TRANSPORT = "transport"
    """The request failed before a response was received (DNS, timeout, TLS...)."""


@dataclass(frozen=True, slots=True)
class FeedFetchError:
    """Describes why a fetch failed.

    Attributes:
        kind: Failure category.
        message: Human-readable description.
        status_code: HTTP status code, when :attr:`kind` is ``HTTP_STATUS``.
        exception: Original exception, when :attr:`kind` is ``TRANSPORT``.
    """

    kind: FeedFetchErrorKind
    message: str
    status_code: int | None = None
    exception: BaseException | None = None


@dataclass(frozen=True, slots=True)
class FeedFetchSuccess:
    """A feed was fetched successfully (including ``304 Not Modified``)."""

    source: FeedSource
    response: FeedResponse


@dataclass(frozen=True, slots=True)
class FeedFetchFailure:
    """A feed could not be fetched."""

    source: FeedSource
    error: FeedFetchError


FeedFetchResult: TypeAlias = FeedFetchSuccess | FeedFetchFailure
"""Outcome of a single fetch. Narrow with ``isinstance``."""


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #


class FeedFetcher:
    """Fetches feeds over HTTP and returns their raw content.

    The fetcher never parses anything and never raises for expected network
    or HTTP errors: failures are reported as :class:`FeedFetchFailure`.
    ``asyncio.CancelledError`` is intentionally **not** swallowed.

    Args:
        client_factory: Callable producing an async context manager that yields
            an :class:`HttpClient`.
        max_concurrency: Maximum number of simultaneous requests in
            :meth:`fetch_many`.
        default_headers: Headers sent with every request. Defaults to an
            ``Accept`` header suited for feeds. Per-source headers override them.

    Raises:
        ValueError: If ``max_concurrency`` is lower than 1.
    """

    def __init__(
        self,
        client_factory: HttpClientFactory,
        *,
        max_concurrency: int = 5,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self._client_factory = client_factory
        self._max_concurrency = max_concurrency
        self._default_headers: dict[str, str] = (
            dict(default_headers)
            if default_headers is not None
            else {"Accept": DEFAULT_ACCEPT_HEADER}
        )

    async def fetch(self, source: FeedSource) -> FeedFetchResult:
        """Fetch a single feed using a fresh client.

        Args:
            source: The feed to fetch.

        Returns:
            :class:`FeedFetchSuccess` or :class:`FeedFetchFailure`.
        """
        async with self._client_factory() as client:
            return await self._fetch_one(client, source)

    async def fetch_many(self, sources: Sequence[FeedSource]) -> list[FeedFetchResult]:
        """Fetch several feeds concurrently, sharing one client.

        Args:
            sources: The feeds to fetch.

        Returns:
            One result per source, in the **same order** as ``sources``.
        """
        if not sources:
            return []

        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def guarded(client: HttpClient, source: FeedSource) -> FeedFetchResult:
            async with semaphore:
                return await self._fetch_one(client, source)

        async with self._client_factory() as client:
            return list(
                await asyncio.gather(*(guarded(client, source) for source in sources))
            )

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _build_headers(self, source: FeedSource) -> dict[str, str]:
        """Merge headers by precedence: defaults < source < conditional."""
        return {
            **self._default_headers,
            **source.headers,
            **source.conditional_headers(),
        }

    async def _fetch_one(self, client: HttpClient, source: FeedSource) -> FeedFetchResult:
        """Perform one request and convert the outcome into a result object."""
        logger.debug("Fetching %s", source.url)

        try:
            response = await client.get(source.url, headers=self._build_headers(source))
        except Exception as exc:  # noqa: BLE001 - transport errors vary by client
            logger.error("Failed to fetch %s: %s", source.label, exc)
            return FeedFetchFailure(
                source=source,
                error=FeedFetchError(
                    kind=FeedFetchErrorKind.TRANSPORT,
                    message=f"{type(exc).__name__}: {exc}",
                    exception=exc,
                ),
            )

        status = response.status_code
        if not (200 <= status < 300 or status == 304):
            logger.error("Failed to fetch %s: status %s", source.label, status)
            return FeedFetchFailure(
                source=source,
                error=FeedFetchError(
                    kind=FeedFetchErrorKind.HTTP_STATUS,
                    message=f"Unexpected HTTP status {status}",
                    status_code=status,
                ),
            )

        feed_response = FeedResponse(
            source=source,
            status_code=status,
            content=response.content,
            headers={key.lower(): value for key, value in response.headers.items()},
            encoding=response.encoding,
            fetched_at=datetime.now(timezone.utc),
        )
        logger.debug(
            "%s: status %s, %d byte(s)", source.label, status, len(feed_response.content)
        )
        return FeedFetchSuccess(source=source, response=feed_response)