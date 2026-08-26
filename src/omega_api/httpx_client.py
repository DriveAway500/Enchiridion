from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import httpx

from .exceptions import APIError, NotFoundError

BASE_URL = "http://127.0.0.1:3000"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) "
        "Gecko/20100101 Firefox/119.0"
    ),
    "Accept": "application/json",
}

_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)

_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)

client = httpx.AsyncClient(
    base_url=BASE_URL,
    timeout=_TIMEOUT,
    limits=_LIMITS,
    headers=HEADERS,
    follow_redirects=True,
)


async def close() -> None:
    if not client.is_closed:
        await client.aclose()


@asynccontextmanager
async def lifespan() -> AsyncGenerator[None]:
    try:
        yield
    finally:
        await close()


def _extract_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])
    except ValueError:
        pass
    return response.text or response.reason_phrase or "UNKNOWN ERROR"


async def request_json(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    not_found_ok: bool = False,
    **kwargs: Any,
) -> Any:

    response = await client.request(method, url, params=params, **kwargs)

    if response.status_code == 404:
        if not_found_ok:
            return None
        raise NotFoundError(response.status_code, _extract_detail(response))

    if response.status_code >= 400:
        raise APIError(response.status_code, _extract_detail(response))

    if response.status_code == 204 or not response.content:
        return None

    return response.json()