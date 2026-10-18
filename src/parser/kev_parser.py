from __future__ import annotations

import hashlib
import asyncio
from pathlib import Path
from typing import ClassVar
from dataclasses import dataclass
import json
import re

from database import JSONHandler, JSONLoadError
from omega_api import get_kev_removed, get_kev_new, get_kev_diff, search_kev, get_kev_entry

_SHA256_RE = re.compile(r"[0-9a-f]{64}")

@dataclass(slots=True)
class KevNew:
    cve_id:             str
    vendor_project:     str
    product:            str
    vulnerability_name: str
    date_added:         str
    short_description:  str
    required_action:    str
    due_date:           str
    known_ransomware:   str
    forensic_triage:    str
    notes:              str
    cwes:               str

@dataclass
class KevRemoved:
    cve_id:             str
    vendor_project:     str
    product:            str
    vulnerability_name: str
    date_added:         str
    short_description:  str
    required_action:    str
    due_date:           str
    known_ransomware:   str
    forensic_triage:    str
    notes:              str
    cwes:               list[str] | str


@dataclass
class JsonLoad:
    kev_new256:  str = ""
    kev_diff256: str = ""

    path: ClassVar[Path] = Path(__file__).resolve().parent.parent / "database" / "kve_sha.json"

    @classmethod
    def load_sha256(cls) -> JsonLoad:
        try:
            data = JSONHandler.load(cls.path)[0]
            return cls(
                kev_new256  = data["kev_new_sha256"],
                kev_diff256 = data["kev_diff_sha256"],
            )
        except (JSONLoadError, IndexError, KeyError):
            instance = cls()
            instance.save()
            return instance

    def save(self) -> None:
        JSONHandler.save(
            self.path,
            [{
                "kev_new_sha256":  self.kev_new256,
                "kev_diff_sha256": self.kev_diff256,
            }],
        )


class KevParser:
    def __init__(self) -> None:
        self.loaded_hash = JsonLoad.load_sha256()

    @staticmethod
    def _json_to_sha256(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_sha256(value: str) -> str:
        """Normalize and validate an SHA-256 hash (64 hexadecimal characters)."""
        if not isinstance(value, str):
            raise TypeError(f"Hash must be str, got: {type(value).__name__}")

        normalized = value.strip().lower()

        if not _SHA256_RE.fullmatch(normalized):
            raise ValueError(f"Invalid SHA-256 hash: {value!r}")

        return normalized

    def _check_sha256(self, current_hash: str, new_hash: str) -> bool:
        """Compare two SHA-256 hashes. Returns True if they are different."""
        return self._normalize_sha256(current_hash) != self._normalize_sha256(new_hash)

    async def parse_kev_new(self) -> list[KevNew] | None:
        data = await get_kev_new()
        if not isinstance(data, dict):
            return None

        old_sha256 = self.loaded_hash.kev_new256
        new_sha256 = self._json_to_sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":"))
        )

        # First run: store the baseline hash and report nothing
        if not old_sha256:
            self.loaded_hash.kev_new256 = new_sha256
            self.loaded_hash.save()
            return None

        # _check_sha256 returns True when hashes differ, so no change means exit
        if not self._check_sha256(old_sha256, new_sha256):
            return None

        self.loaded_hash.kev_new256 = new_sha256
        self.loaded_hash.save()

        entries = data.get("entries", [])
        if not entries:
            return None

        return [
            KevNew(
                cve_id              =   entry.get("cveID", "N/A"),
                vendor_project      =   entry.get("vendorProject", "N/A"),
                product             =   entry.get("product", "N/A"),
                vulnerability_name  =   entry.get("vulnerabilityName", "N/A"),
                date_added          =   entry.get("dateAdded", "N/A"),
                short_description   =   entry.get("shortDescription", "N/A"),
                required_action     =   entry.get("requiredAction", "N/A"),
                due_date            =   entry.get("dueDate", "N/A"),
                known_ransomware    =   entry.get("knownRansomwareCampaignUse", "N/A"),
                forensic_triage     =   entry.get("forensicTriage", "N/A"),
                notes               =   entry.get("notes", "N/A"),
                cwes                =   entry.get("cwes", "N/A"),
            )
            for entry in entries
        ]

    async def parse_removed(self) -> list[KevRemoved] | None:
        data = await get_kev_removed()
        if not isinstance(data, dict):
            return None

        old_sha256 = self.loaded_hash.kev_diff256
        new_sha256 = self._json_to_sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":"))
        )

        # First run: store the baseline hash and report nothing
        if not old_sha256:
            self.loaded_hash.kev_diff256 = new_sha256
            self.loaded_hash.save()
            return None

        if not self._check_sha256(old_sha256, new_sha256):
            return None

        self.loaded_hash.kev_diff256 = new_sha256
        self.loaded_hash.save()

        entries = data.get("entries", [])
        if not entries:
            return None

        return [
            KevRemoved(
                cve_id              =   entry.get("cveID", "N/A"),
                vendor_project      =   entry.get("vendorProject", "N/A"),
                product             =   entry.get("product", "N/A"),
                vulnerability_name  =   entry.get("vulnerabilityName", "N/A"),
                date_added          =   entry.get("dateAdded", "N/A"),
                short_description   =   entry.get("shortDescription", "N/A"),
                required_action     =   entry.get("requiredAction", "N/A"),
                due_date            =   entry.get("dueDate", "N/A"),
                known_ransomware    =   entry.get("knownRansomwareCampaignUse", "N/A"),
                forensic_triage     =   entry.get("forensicTriage", "N/A"),
                notes               =   entry.get("notes", "N/A"),
                cwes                =   entry.get("cwes", "N/A"),
            )
            for entry in entries
        ]

    @staticmethod
    async def parse_search(item: str, page: int = 1) -> list[KevNew] | None:
        data = await search_kev(item, page=page)
        if not isinstance(data, dict):
            return None

        entries = data.get("results", [])
        if not entries:
            return None

        return [
            KevNew(
                cve_id              =   entry.get("cveID", "N/A"),
                vendor_project      =   entry.get("vendorProject", "N/A"),
                product             =   entry.get("product", "N/A"),
                vulnerability_name  =   entry.get("vulnerabilityName", "N/A"),
                date_added          =   entry.get("dateAdded", "N/A"),
                short_description   =   entry.get("shortDescription", "N/A"),
                required_action     =   entry.get("requiredAction", "N/A"),
                due_date            =   entry.get("dueDate", "N/A"),
                known_ransomware    =   entry.get("knownRansomwareCampaignUse", "N/A"),
                forensic_triage     =   entry.get("forensicTriage", "N/A"),
                notes               =   entry.get("notes", "N/A"),
                cwes                =   entry.get("cwes", "N/A"),
            )
            for entry in entries
        ]

    @staticmethod
    async def parse_entry(cve_id: str) -> KevNew | None:
        data = await get_kev_entry(cve_id)
        if not isinstance(data, dict):
            return None

        return KevNew(
            cve_id=data.get("cveID", "N/A"),
            vendor_project=data.get("vendorProject", "N/A"),
            product=data.get("product", "N/A"),
            vulnerability_name=data.get("vulnerabilityName", "N/A"),
            date_added=data.get("dateAdded", "N/A"),
            short_description=data.get("shortDescription", "N/A"),
            required_action=data.get("requiredAction", "N/A"),
            due_date=data.get("dueDate", "N/A"),
            known_ransomware=data.get("knownRansomwareCampaignUse", "N/A"),
            forensic_triage=data.get("forensicTriage", "N/A"),
            notes=data.get("notes", "N/A"),
            cwes=data.get("cwes", "N/A"),
        )

    async def test(self):
        data = await self.parse_kev_new()
        if not data:
            return

        for d in data:
            print(
                d.cve_id,
                d.vendor_project,
                d.product,
                d.vulnerability_name,
                d.date_added,
                d.short_description,
                d.required_action,
                d.due_date,
                d.known_ransomware,
                d.forensic_triage,
                d.notes,
                d.cwes,
            )

def main()-> None:
    kev_parser = KevParser()
    asyncio.run(kev_parser.test())

if __name__ == "__main__":
    main()