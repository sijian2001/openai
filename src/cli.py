"""Command-line interface for downloading and summarizing earnings reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from .fetcher import DownloadError, download_pdf
from .summarizer import SummarizationError, summarize_pdf


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download an earnings report PDF and summarize it using OpenAI."
    )
    parser.add_argument("url", help="URL pointing to an earnings report in PDF format.")
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model identifier to use for summarization.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("summaries"),
        help="Directory where summary text files will be written.",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path("pdf"),
        help="Directory where downloaded PDFs will be stored.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    try:
        download = download_pdf(args.url, directory=args.pdf_dir)
    except DownloadError as exc:
        print(f"Download error: {exc}", file=sys.stderr)
        return 1

    try:
        summary = summarize_pdf(download.path, model=args.model, output_dir=args.output_dir)
    except SummarizationError as exc:
        print(f"Summarization error: {exc}", file=sys.stderr)
        return 1

    print(summary.summary_text)
    print(f"\nSummary written to: {summary.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
