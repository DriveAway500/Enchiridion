import re
import time
import traceback
from collections import deque
from dataclasses import dataclass
from typing import Callable, Awaitable
import feedparser

from .httpx_client import get_http_client


@dataclass
class VulnerabilityData:
    id: str
    title: str
    link: str
    summary: str
    severity_score: float
    severity_label: str
    color_hex: str
    thumbnail: str | None = None
    should_crosspost: bool = False
    thread_name: str = ""


class CVEClassifier:
    def __init__(
        self,
        is_sent_checker: Callable[[str], Awaitable[bool]],
        feeds: list[str] | None = None,
        crosspost_min_severity: float = 9.0,
        crosspost_limit_per_hour: int = 10,
    ):
        """
        :param is_sent_checker: Função assíncrona que recebe o ID do item (str)
                                e retorna True se ele já existir na database.
        """
        self.is_sent_checker = is_sent_checker
        self.feeds = feeds or ["https://cvefeed.io/rssfeed/latest.atom"]
        self.crosspost_min_severity = crosspost_min_severity
        self.crosspost_limit_per_hour = crosspost_limit_per_hour
        self._crosspost_timestamps = deque()

    @staticmethod
    def clean_html(text: str) -> str:
        if not text:
            return ""
        return re.sub(r"<.*?>", "", text).strip()

    @staticmethod
    def extract_severity(data: str) -> float:
        if not data:
            return -1.0
        patterns = [
            r"(?:Severity|CVSS(?:\s+Score)?|Base\s+Score|Score)\s*[:\-]\s*([\d]+[.,][\d]+)",
            r"(?:Severity|CVSS(?:\s+Score)?|Base\s+Score|Score)\s*[:\-]\s*([\d]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, data, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", "."))
        return -1.0

    @staticmethod
    def classify_severity(severity: float) -> tuple[str, str] | tuple[None, None]:
        if severity >= 9.0:
            return "[CRITICAL]", "#FF0000"
        elif severity >= 7.0:
            return "[HIGH]", "#FFA500"
        elif severity >= 4.0:
            return "[MEDIUM]", "#FFFF00"
        elif severity >= 0.1:
            return "[LOW]", "#008000"
        elif severity == -1.0:
            return "[UNKNOWN]", "#5865F2"
        else:
            return None, None

    def _check_crosspost_eligibility(self, severity: float) -> bool:
        if severity < self.crosspost_min_severity:
            return False

        now = time.monotonic()
        one_hour = 3600.0

        while self._crosspost_timestamps and now - self._crosspost_timestamps[0] > one_hour:
            self._crosspost_timestamps.popleft()

        if len(self._crosspost_timestamps) >= self.crosspost_limit_per_hour:
            return False

        return True

    def register_crosspost(self):
        self._crosspost_timestamps.append(time.monotonic())

    async def fetch_and_classify(self) -> list[VulnerabilityData]:
        classified_items = []

        async with get_http_client() as client:
            for url in self.feeds:
                try:
                    response = await client.get(url)
                    if response.status_code != 200:
                        print(f"Erro ao acessar {url}: Status {response.status_code}")
                        continue

                    body = response.text
                    feed = feedparser.parse(body)

                    for entry in reversed(feed.entries):
                        item_id = getattr(entry, "id", entry.link)

                        if await self.is_sent_checker(item_id):
                            continue

                        title = entry.title
                        link = entry.link
                        raw_summary = getattr(entry, "summary", "")
                        summary = self.clean_html(raw_summary)[:3000]

                        severity_score = self.extract_severity(summary)
                        label, color = self.classify_severity(severity_score)

                        if label is None:
                            continue

                        cve_match = re.search(r"CVE-\d{4}-\d+", title, re.IGNORECASE)
                        thread_name = f"{label} {cve_match.group(0)}" if cve_match else title[:100]

                        thumbnail = None
                        if "media_thumbnail" in entry:
                            thumbnail = entry.media_thumbnail[0]["url"]

                        should_crosspost = self._check_crosspost_eligibility(severity_score)

                        item_data = VulnerabilityData(
                            id=item_id,
                            title=title,
                            link=link,
                            summary=summary,
                            severity_score=severity_score,
                            severity_label=label,
                            color_hex=color,
                            thumbnail=thumbnail,
                            should_crosspost=should_crosspost,
                            thread_name=thread_name,
                        )

                        classified_items.append(item_data)

                except Exception as e:
                    print(f"Erro ao processar feed {url}: {e}")
                    traceback.print_exc()

        return classified_items