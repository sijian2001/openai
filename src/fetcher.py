"""Network layer for retrieving earnings report HTML content."""

from __future__ import annotations

import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

DEFAULT_TIMEOUT = 15


@dataclass
class FetchResult:
    """Container for fetched payloads."""

    url: str
    content: str
    encoding: str


class FetchError(RuntimeError):
    """Raised when an earnings report cannot be retrieved."""


def fetch_content(url: str, *, timeout: Optional[int] = None) -> FetchResult:
    """Download the report at ``url`` and return the decoded payload.

    The function relies on :mod:`urllib` to avoid external dependencies.
    """

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "earnings-summarizer/1.0 (+https://github.com/sijian2001/openai)"
            )
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout or DEFAULT_TIMEOUT) as resp:
            raw_bytes = resp.read()
            encoding = resp.headers.get_content_charset() or "utf-8"
            try:
                text = raw_bytes.decode(encoding, errors="replace")
            except LookupError as exc:  # Unknown encoding
                logging.getLogger(__name__).warning(
                    "Unknown encoding %s, falling back to utf-8: %s", encoding, exc
                )
                text = raw_bytes.decode("utf-8", errors="replace")
                encoding = "utf-8"
    except urllib.error.URLError as exc:
        raise FetchError(f"Failed to download {url}: {exc}") from exc

    return FetchResult(url=url, content=text, encoding=encoding)
