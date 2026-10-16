from __future__ import annotations

from httpx_client import request_json


async def search_zeroday_exploits(query: str, page: int = 1, limit: int = 5):
    offset = (page - 1) * limit
    return await request_json(
        "POST",
        "/zeroday/search",
        json={"q": query, "limit": limit, "offset": offset},
    )


async def get_zeroday_exploit(exploit_id: str):
    return await request_json(
        "POST",
        "/zeroday/get",
        json={"exploit_id": exploit_id},
        not_found_ok=True,
    )