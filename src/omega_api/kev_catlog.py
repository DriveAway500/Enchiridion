from __future__ import annotations

from typing import Any

from httpx_client import request_json


async def get_kev_diff() -> dict[str, Any] | None:
    """Full diff (added / removed / modified) between the current index
    and the one from the previous builder run.

    Returns None if there is no previous index yet (404).
    """
    return await request_json(
        "GET",
        "/kev/diff",
        not_found_ok=True,
    )


async def get_kev_new() -> dict[str, Any] | None:
    """CVEs present in the current index but not in the previous one.

    Returns {"count": int, "entries": list}, or None if there is no
    previous index yet (404).
    """
    return await request_json(
        "GET",
        "/kev/new",
        not_found_ok=True,
    )


async def get_kev_removed() -> dict[str, Any] | None:
    """CVEs present in the previous index but no longer in the current one.

    Returns {"count": int, "entries": list}, or None if there is no
    previous index yet (404).
    """
    return await request_json(
        "GET",
        "/kev/removed",
        not_found_ok=True,
    )


async def search_kev(
    q: str,
    fields=None,
    page: int = 1,
    limit: int = 5,
) -> dict[str, Any] | None:
    """Free-text search across the indexed KEV rows.

    Returns None if the index has not been built yet (404).
    """
    offset = (page - 1) * limit
    payload: dict[str, Any] = {
        "q": q,
        "limit": limit,
        "offset": offset,
    }

    if fields:
        payload["fields"] = getattr(fields, "value", fields)

    return await request_json(
        "POST",
        "/kev/search",
        json=payload,
        not_found_ok=True,
    )


async def get_kev_entry(cve_id: str) -> dict[str, Any] | None:
    """Direct lookup of a single CVE in the KEV index by id.

    Returns None if the CVE is not in the index (404).
    """
    return await request_json(
        "GET",
        f"/kev/get/{cve_id}",
        not_found_ok=True,
    )