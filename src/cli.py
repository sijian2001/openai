"""Command-line interface for downloading and summarizing earnings reports."""

from __future__ import annotations

import argparse
import os
import sys
from importlib import resources
from pathlib import Path
from typing import Optional

import yaml

from .fetcher import DownloadError, download_pdf
from .summarizer import SummarizationError, summarize_pdf

DEFAULT_CONFIG_OVERRIDE_PATH = Path("config.yaml")
PACKAGE_CONFIG_NAME = "config.yaml"


class ConfigurationError(RuntimeError):
    """Raised when the application configuration is missing or invalid."""


def load_config(path: Optional[Path] = DEFAULT_CONFIG_OVERRIDE_PATH) -> dict:
    """Load summarizer configuration.

    Defaults are sourced from ``src/config.yaml`` bundled with the package. When
    ``path`` is provided and exists (defaulting to ``config.yaml`` in the working
    directory), those values overlay the packaged defaults.
    """
    config = _load_package_defaults()

    override_path = path
    if override_path and override_path.exists():
        overrides = _load_yaml_mapping(override_path)
        config = _deep_merge(config, overrides)

    return config


def _load_package_defaults() -> dict:
    try:
        package_resource = resources.files(__package__).joinpath(PACKAGE_CONFIG_NAME)
    except (FileNotFoundError, AttributeError):
        return {}

    try:
        with package_resource.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
    except FileNotFoundError:
        return {}
    except (
        yaml.YAMLError
    ) as exc:  # pragma: no cover - indicates bundled config corruption.
        raise ConfigurationError(
            f"Failed to parse bundled configuration: {exc}"
        ) from exc

    if not isinstance(loaded, dict):
        raise ConfigurationError("Bundled configuration root must be a mapping.")

    return loaded


def _load_yaml_mapping(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - YAML parse errors are rare.
        raise ConfigurationError(f"Failed to parse configuration: {exc}") from exc

    if not isinstance(loaded, dict):
        raise ConfigurationError("Configuration root must be a mapping.")

    return loaded


def _deep_merge(base: dict, overrides: dict) -> dict:
    merged = dict(base)
    for key, value in overrides.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _config_value(
    config: dict, *keys: str, default: Optional[str] = None
) -> Optional[str]:
    """Retrieve a nested configuration value, returning ``default`` if missing."""
    current = config
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current if isinstance(current, (str, Path)) else default


def parse_args(argv: Optional[list[str]] = None, *, config: dict) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download an earnings report PDF and summarize it using OpenAI."
    )
    parser.add_argument("url", help="URL pointing to an earnings report in PDF format.")
    parser.add_argument(
        "--model",
        default=_config_value(config, "summarizer", "model", default="gpt-4o-mini"),
        help="OpenAI model identifier to use for summarization.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            _config_value(
                config, "summarizer", "output_dir", default="output/summaries"
            )
        ),
        help="Directory where summary text files will be written.",
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path(_config_value(config, "fetcher", "pdf_dir", default="output/pdf")),
        help="Directory where downloaded PDFs will be stored.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    try:
        config = load_config()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    args = parse_args(argv, config=config)

    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "Configuration error: environment variable OPENAI_API_KEY is not set.",
            file=sys.stderr,
        )
        return 1

    try:
        download = download_pdf(args.url, directory=args.pdf_dir)
    except DownloadError as exc:
        print(f"Download error: {exc}", file=sys.stderr)
        return 1

    try:
        summary = summarize_pdf(
            download.path, model=args.model, output_dir=args.output_dir
        )
    except SummarizationError as exc:
        print(f"Summarization error: {exc}", file=sys.stderr)
        return 1

    print(summary.summary_text)
    print(f"\nSummary written to: {summary.output_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
