"""Functions for downloading earnings report PDFs."""

from __future__ import annotations

import pathlib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

DEFAULT_TIMEOUT = 30
DEFAULT_DIR = pathlib.Path("pdf")


@dataclass
class DownloadResult:
    """Metadata about a downloaded PDF file."""

    url: str
    path: pathlib.Path
    bytes_written: int


class DownloadError(RuntimeError):
    """Raised when the earnings report download fails."""


def download_pdf(
    url: str,
    *,
    directory: Optional[pathlib.Path] = None,
    timeout: Optional[int] = None,
) -> DownloadResult:
    """Download the PDF at ``url`` and persist it under ``directory``."""

    target_dir = directory or DEFAULT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = _suggest_filename(url)
    destination = target_dir / filename

    if destination.exists():
        size = destination.stat().st_size
        return DownloadResult(url=url, path=destination, bytes_written=size)

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "earnings-summarizer/1.0"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request, timeout=timeout or DEFAULT_TIMEOUT
        ) as resp:
            data = resp.read()
    except urllib.error.URLError as exc:
        raise DownloadError(f"Failed to download {url}: {exc}") from exc

    destination.write_bytes(data)
    return DownloadResult(url=url, path=destination, bytes_written=len(data))


def _suggest_filename(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    name = pathlib.Path(parsed.path).name or "report.pdf"
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    return name
