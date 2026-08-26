from __future__ import annotations


class APIError(Exception):

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


class NotFoundError(APIError):
    """NOT FOUND RECURSE (HTTP 404)."""