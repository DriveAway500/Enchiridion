import httpx


def get_http_client(timeout: float = 15.0) -> httpx.AsyncClient:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0"
    }
    return httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout)