"""CVE feed parser.

Turns the raw :class:`~.feed_fetcher.FeedResponse` produced by the fetching
engine into typed domain objects. This module performs **no I/O**: no HTTP
requests and no database access. Deduplication against already-sent items is
the responsibility of the consumer (the task layer).

Data flow::

    FeedResponse --CVEFeedParser.parse()--> ParsedCVEFeed
                                              +-- VulnerabilityData (many)
                                                    +-- Severity
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

import feedparser

from feeds.engine import FeedResponse, FeedSource

logger = logging.getLogger(__name__)

__all__ = [
    "CVEFeedParser",
    "ParsedCVEFeed",
    "Severity",
    "SeverityLevel",
    "VulnerabilityData",
    "clean_html",
    "extract_severity_score",
]

MAX_SUMMARY_LENGTH: int = 3000
"""Maximum number of characters kept from an entry summary."""

_HTML_TAG_PATTERN: re.Pattern[str] = re.compile(r"<.*?>")

_SEVERITY_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:Severity|CVSS(?:\s+Score)?|Base\s+Score|Score)\s*[:\-]\s*(\d+[.,]\d+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:Severity|CVSS(?:\s+Score)?|Base\s+Score|Score)\s*[:\-]\s*(\d+)",
        re.IGNORECASE,
    ),
)


# --------------------------------------------------------------------------- #
# Domain objects
# --------------------------------------------------------------------------- #


class SeverityLevel(Enum):
    """Severity bucket, carrying its display label and color."""

    CRITICAL = ("[CRITICAL]", "#FF0000")
    HIGH = ("[HIGH]", "#FFA500")
    MEDIUM = ("[MEDIUM]", "#FFFF00")
    LOW = ("[LOW]", "#008000")
    UNKNOWN = ("[UNKNOWN]", "#5865F2")

    def __init__(self, label: str, color_hex: str) -> None:
        self.label: str = label
        self.color_hex: str = color_hex


@dataclass(frozen=True, slots=True)
class Severity:
    """Severity of a vulnerability.

    Attributes:
        level: Severity bucket.
        score: CVSS-like numeric score, or ``None`` when the feed did not
            provide one (in which case ``level`` is ``UNKNOWN``).
    """

    level: SeverityLevel
    score: float | None

    @property
    def label(self) -> str:
        """Display label, e.g. ``"[HIGH]"``."""
        return self.level.label

    @property
    def color_hex(self) -> str:
        """Display color as a ``#RRGGBB`` string."""
        return self.level.color_hex

    @property
    def is_unknown(self) -> bool:
        """``True`` when no numeric score was available."""
        return self.score is None

    @classmethod
    def from_score(cls, score: float | None) -> Severity | None:
        """Classify a numeric score.

        Args:
            score: Numeric score, or ``None`` if unavailable.

        Returns:
            A :class:`Severity`, or ``None`` when the score is not classifiable
            (zero or negative) and the item should be discarded.
        """
        if score is None:
            return cls(SeverityLevel.UNKNOWN, None)
        if score >= 9.0:
            return cls(SeverityLevel.CRITICAL, score)
        if score >= 7.0:
            return cls(SeverityLevel.HIGH, score)
        if score >= 4.0:
            return cls(SeverityLevel.MEDIUM, score)
        if score > 0.0:
            return cls(SeverityLevel.LOW, score)
        return None


@dataclass(frozen=True, slots=True)
class VulnerabilityData:
    """A single classified vulnerability entry.

    Attributes:
        id: Unique entry identifier (used for deduplication).
        title: Entry title.
        link: URL of the entry.
        summary: Plain-text summary (HTML stripped, truncated).
        severity: Classified severity.
        thumbnail: Thumbnail URL, if the entry provides one.
    """

    id: str
    title: str
    link: str
    summary: str
    severity: Severity
    thumbnail: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedCVEFeed:
    """Result of parsing one feed response.

    Attributes:
        source: The source the content came from.
        vulnerabilities: Classified entries, **oldest first**.
        total_entries: Number of entries present in the feed.
        discarded_unclassified: Entries dropped because their severity could
            not be classified (zero or negative score).
        discarded_invalid: Entries dropped because they were malformed
            (e.g. missing link).
    """

    source: FeedSource
    vulnerabilities: tuple[VulnerabilityData, ...]
    total_entries: int
    discarded_unclassified: int = 0
    discarded_invalid: int = 0


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def clean_html(text: str | None) -> str:
    """Strip HTML tags and surrounding whitespace.

    Args:
        text: Raw text, possibly containing HTML.

    Returns:
        Plain text, or an empty string for empty input.
    """
    if not text:
        return ""
    return _HTML_TAG_PATTERN.sub("", text).strip()


def extract_severity_score(text: str | None) -> float | None:
    """Extract a numeric severity score from free text.

    Recognizes labels such as ``Severity``, ``CVSS``, ``CVSS Score``,
    ``Base Score`` and ``Score`` followed by ``:`` or ``-`` and a number
    (decimal separator may be ``.`` or ``,``).

    Args:
        text: Text to search.

    Returns:
        The score, or ``None`` if none was found.
    """
    if not text:
        return None
    for pattern in _SEVERITY_PATTERNS:
        match = pattern.search(text)
        if match:
            return float(match.group(1).replace(",", "."))
    return None


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #


class CVEFeedParser:
    """Parses RSS/Atom CVE feeds into :class:`ParsedCVEFeed` objects."""

    def parse(self, response: FeedResponse) -> ParsedCVEFeed:
        """Parse a fetched feed.

        A ``304 Not Modified`` response yields an empty result.

        Args:
            response: Raw response from the fetching engine.

        Returns:
            The parsed feed. Entries are ordered oldest first.
        """
        if response.not_modified:
            return ParsedCVEFeed(
                source=response.source, vulnerabilities=(), total_entries=0
            )

        feed = feedparser.parse(response.content)
        entries: list[Any] = list(feed.entries)
        logger.debug("%s: %d entry(ies) in feed", response.source.label, len(entries))

        vulnerabilities: list[VulnerabilityData] = []
        discarded_unclassified = 0
        discarded_invalid = 0

        for entry in reversed(entries):
            link = getattr(entry, "link", None)
            title = getattr(entry, "title", None)
            if not link or not title:
                logger.warning(
                    "%s: skipping malformed entry (missing title or link)",
                    response.source.label,
                )
                discarded_invalid += 1
                continue

            summary = clean_html(getattr(entry, "summary", ""))[:MAX_SUMMARY_LENGTH]
            severity = Severity.from_score(extract_severity_score(summary))
            if severity is None:
                discarded_unclassified += 1
                continue

            vulnerabilities.append(
                VulnerabilityData(
                    id=getattr(entry, "id", link),
                    title=title,
                    link=link,
                    summary=summary,
                    severity=severity,
                    thumbnail=self._extract_thumbnail(entry),
                )
            )

        return ParsedCVEFeed(
            source=response.source,
            vulnerabilities=tuple(vulnerabilities),
            total_entries=len(entries),
            discarded_unclassified=discarded_unclassified,
            discarded_invalid=discarded_invalid,
        )

    @staticmethod
    def _extract_thumbnail(entry: Any) -> str | None:
        """Return the first ``media_thumbnail`` URL of an entry, if any."""
        thumbnails = entry.get("media_thumbnail")
        if thumbnails:
            return thumbnails[0].get("url")
        return None