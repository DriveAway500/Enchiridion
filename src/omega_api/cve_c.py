from __future__ import annotations

from .httpx_client import request_json


async def get_cve(cve_id):
    return await request_json("GET", f"/cve/{cve_id}", not_found_ok=True)


async def search_cves_by_package(
    package_name, year, page=1, limit=5
):
    offset = (page - 1) * limit
    params = {
        "package_name": package_name,
        "year": str(year),
        "limit": limit,
        "offset": offset,
    }
    result = await request_json(
        "GET",
        "/cve/search/package",
        params=params,
        not_found_ok=True,
    )
    return result or []