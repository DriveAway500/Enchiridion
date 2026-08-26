from __future__ import annotations

from httpx_client import request_json


async def search_zeroday_exploits(query: str, limit: int = 50):
    return await request_json(
        "GET", "/zeroday/search", params={"q": query, "limit": limit}
    )


async def get_zeroday_exploit(exploit_id: str):
    return await request_json("GET", f"/zeroday/{exploit_id}", not_found_ok=True)