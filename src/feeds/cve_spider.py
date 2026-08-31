import re
import traceback
from dataclasses import dataclass

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


class CVEClassifier:
    def __init__(self, is_sent_checker, feeds=None):
        """
        :param is_sent_checker: Função assíncrona que recebe o ID do item (str)
                                 e retorna True se ele já existir na database.
        """
        self.is_sent_checker = is_sent_checker
        self.feeds = feeds or ["https://cvefeed.io/rssfeed/latest.atom"]

    @staticmethod
    def clean_html(text):
        if not text:
            return ""
        return re.sub(r"<.*?>", "", text).strip()

    @staticmethod
    def extract_severity(data):
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
    def classify_severity(severity):
        if severity >= 9.0:
            return "[CRITICAL]", "#FF0000"
        elif severity >= 7.0:
            return "[HIGH]", "#FFA500"
        elif severity >= 4.0:
            return "[MEDIUM]", "#FFFF00"
        elif severity >= 0.0:
            return "[LOW]", "#008000"
        elif severity == -1.0:
            return "[UNKNOWN]", "#5865F2"
        else:
            return None, None

    async def fetch_and_classify(self):
        classified_items = []

        async with get_http_client() as client:
            for url in self.feeds:
                try:
                    print(f"[feeds] buscando {url}")
                    response = await client.get(url)
                    if response.status_code != 200:
                        print(f"[feeds] erro ao acessar {url}: status {response.status_code}")
                        continue

                    body = response.text
                    feed = feedparser.parse(body)
                    print(f"[feeds] {url}: {len(feed.entries)} entrada(s) no feed")

                    ja_enviados = 0
                    descartados_sem_label = 0

                    for entry in reversed(feed.entries):
                        item_id = getattr(entry, "id", entry.link)

                        if await self.is_sent_checker(item_id):
                            ja_enviados += 1
                            continue

                        title = entry.title
                        link = entry.link
                        raw_summary = getattr(entry, "summary", "")
                        summary = self.clean_html(raw_summary)[:3000]

                        severity_score = self.extract_severity(summary)
                        label, color = self.classify_severity(severity_score)

                        if label is None:
                            descartados_sem_label += 1
                            continue

                        thumbnail = None
                        if "media_thumbnail" in entry:
                            thumbnail = entry.media_thumbnail[0]["url"]

                        item_data = VulnerabilityData(
                            id=item_id,
                            title=title,
                            link=link,
                            summary=summary,
                            severity_score=severity_score,
                            severity_label=label,
                            color_hex=color,
                            thumbnail=thumbnail,
                        )

                        classified_items.append(item_data)

                    print(
                        f"[feeds] {url}: {ja_enviados} já enviado(s) antes, "
                        f"{descartados_sem_label} sem severidade classificável, "
                        f"{len(classified_items)} novo(s) pronto(s) para envio"
                    )

                except Exception as e:
                    print(f"[feeds] erro ao processar feed {url}: {e}")
                    traceback.print_exc()

        return classified_items