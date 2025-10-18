"""Command-line interface for the earnings report summarizer."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from .fetcher import FetchError, fetch_content
from .parser.html_text import chunk_sections, extract_text
from .summarizer import summarize_text


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize a public company earnings report."
    )
    parser.add_argument(
        "url", help="URL to the earnings report (HTML or PDF converted to HTML)."
    )
    parser.add_argument(
        "--max-sentences",
        type=int,
        default=5,
        help="Maximum number of summary bullet points (default: 5).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    try:
        fetched = fetch_content(args.url)
    except FetchError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    text = extract_text(fetched.content)
    sections = list(chunk_sections(text))
    if not sections:
        print("No readable content found in the provided report.", file=sys.stderr)
        return 1

    summary = summarize_text(" ".join(sections), sentence_limit=args.max_sentences)
    print(summary.format_console())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
