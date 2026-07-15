from collections.abc import Mapping

from sts.constants import HEADER_AUTHORIZATION


class TokenExtractor:
    """Extracts a bearer token from an incoming HTTP request.

    Resolution order:
        1. ``Authorization: Bearer <token>`` header (preferred)
        2. ``<cookie_name>`` cookie (fallback for browser-driven flows)
    """

    def __init__(self, cookie_name: str) -> None:
        if not cookie_name:
            raise ValueError("cookie_name is required")
        self._cookie_name = cookie_name

    def extract(self, headers: Mapping[str, str], cookies: Mapping[str, str]) -> str | None:
        if auth := headers.get(HEADER_AUTHORIZATION) or headers.get("authorization"):
            parts = auth.strip().split(None, 1)
            if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
                return parts[1].strip()

        # fallback from cookies
        return cookies.get(self._cookie_name)
