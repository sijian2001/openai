"""Command-line interface for performing OCR on image files."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable, Optional

from .recognizer import DEFAULT_MODEL, OCRProcessingError, recognize_image

DEFAULT_INPUT_DIR = Path("input/images")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Perform OCR on PNG images and export the results as CSV files."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help="Directory containing PNG images to process (default: input/images).",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="OpenAI model identifier to use for OCR (default: gpt-4o-mini).",
    )
    return parser.parse_args(argv)


def process_images(
    images: Iterable[Path],
    *,
    model: str = DEFAULT_MODEL,
) -> list[Path]:
    """Process ``images`` and return the generated CSV paths."""

    csv_paths: list[Path] = []
    for image_path in images:
        text = recognize_image(image_path, model=model)
        csv_path = image_path.with_suffix(".csv")
        _write_csv(csv_path, text)
        csv_paths.append(csv_path)
    return csv_paths


def _write_csv(csv_path: Path, text: str) -> None:
    lines = text.splitlines()
    if not lines:
        lines = [""]

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["line"])
        for line in lines:
            writer.writerow([line])


def _discover_images(directory: Path) -> list[Path]:
    return sorted(path for path in directory.glob("*.png") if path.is_file())


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    input_dir = args.input_dir

    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        return 1

    images = _discover_images(input_dir)
    if not images:
        print(f"No PNG images found in {input_dir}")
        return 0

    try:
        csv_paths = process_images(images, model=args.model)
    except OCRProcessingError as exc:
        print(f"OCR error: {exc}", file=sys.stderr)
        return 1

    print("Generated CSV files:")
    for path in csv_paths:
        print(f"- {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
