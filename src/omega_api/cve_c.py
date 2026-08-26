from __future__ import annotations

from .httpx_client import request_json


async def get_cve(cve_id: str):
    return await request_json("GET", f"/cve/{cve_id}", not_found_ok=True)


async def search_cves_by_package(package_name: str, limit: int = 100):
    result = await request_json(
        "GET",
        "/cve/search/package",
        params={"package_name": package_name, "limit": limit},
        not_found_ok=True,
    )
    return result or []