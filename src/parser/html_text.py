"""Lightweight HTML to text conversion tailored for earnings reports."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Iterable, List


class _ReportHTMLParser(HTMLParser):
    """Streaming parser that collects readable text while skipping boilerplate."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: List[str] = []
        self._skip_stack: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_stack.append(tag)
        elif tag in {"p", "br", "div", "section", "li", "tr"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._skip_stack and self._skip_stack[-1] == tag:
            self._skip_stack.pop()
        elif tag in {"p", "div", "section"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_stack:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def get_text(self) -> str:
        """Return the collected text with normalized newlines."""
        joined = " ".join(part for part in self._chunks if part)
        # Collapse multiple whitespace sequences and trim leading/trailing space.
        normalized = " ".join(joined.split())
        return normalized


def extract_text(html: str) -> str:
    """Convert HTML into a whitespace-normalized text blob."""
    parser = _ReportHTMLParser()
    parser.feed(html)
    parser.close()
    return parser.get_text()


def chunk_sections(text: str, *, max_length: int = 600) -> Iterable[str]:
    """Yield text segments to aid downstream summarization."""
    if not text:
        return []

    sentences = text.split(". ")
    chunk: List[str] = []
    total = 0

    for sentence in sentences:
        normalized = sentence.strip()
        if not normalized:
            continue

        if total + len(normalized) > max_length and chunk:
            yield ". ".join(chunk).strip()
            chunk = []
            total = 0

        chunk.append(normalized)
        total += len(normalized)

    if chunk:
        yield ". ".join(chunk).strip()
