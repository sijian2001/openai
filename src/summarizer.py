"""OpenAI-powered summarization pipelines for earnings report PDFs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - allows dependency injection in tests.
    OpenAI = None  # type: ignore

DEFAULT_MODEL = "gpt-4o-mini"


@dataclass
class SummaryResult:
    """Normalized summary data returned by :func:`summarize_pdf`."""

    summary_text: str
    model: str
    output_path: Path


class SummarizationError(RuntimeError):
    """Raised when the OpenAI API fails or configuration is missing."""


def _default_client():
    if OpenAI is None:  # pragma: no cover - executed when dependency missing.
        raise SummarizationError(
            "The 'openai' package is not installed. Install it via pip to use summarization."
        )
    return OpenAI()


def summarize_pdf(
    pdf_path: Path,
    *,
    client: Optional[object] = None,
    model: str = DEFAULT_MODEL,
    output_dir: Optional[Path] = None,
) -> SummaryResult:
    """Upload ``pdf_path`` to OpenAI and persist the generated summary."""

    if not pdf_path.exists():
        raise SummarizationError(f"PDF not found: {pdf_path}")

    api_client = client or _default_client()

    try:
        with pdf_path.open("rb") as file_obj:
            upload = _files_create(
                api_client,
                file=file_obj,
                purpose="assistants",
            )
        response = _responses_create(
            api_client,
            model=model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "You analyze corporate earnings reports and produce "
                                "clear bullet summaries highlighting revenue, profit, "
                                "guidance, and strategic updates."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Summarize the attached earnings report. Provide concise bullet points "
                                "and a closing paragraph on outlook if available."
                            ),
                        },
                        {
                            "type": "file",
                            "file_id": getattr(upload, "id", None),
                        },
                    ],
                },
            ],
        )
    except Exception as exc:  # pragma: no cover - hit when API fails.
        raise SummarizationError(f"OpenAI API call failed: {exc}") from exc

    summary_text = _extract_text(response)

    target_dir = output_dir or Path("summaries")
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / (pdf_path.stem + "_summary.txt")
    output_path.write_text(summary_text, encoding="utf-8")

    return SummaryResult(summary_text=summary_text, model=model, output_path=output_path)


def _extract_text(response) -> str:
    """Normalize the varied response schema for the Responses API."""
    if hasattr(response, "output_text"):
        return response.output_text  # type: ignore[return-value]

    if hasattr(response, "output") and response.output:
        fragments = []
        for message in response.output:
            if not hasattr(message, "content"):
                continue
            for item in message.content:
                if getattr(item, "type", None) == "output_text":
                    fragments.append(getattr(item, "text", ""))
                elif getattr(item, "type", None) == "text":
                    fragments.append(getattr(item, "text", ""))
        if fragments:
            return "\n".join(fragments)

    # Fallback best-effort string cast.
    return str(response)


def _files_create(client: object, **kwargs):
    if hasattr(client, "files") and hasattr(client.files, "create"):
        return client.files.create(**kwargs)
    if hasattr(client, "files_create"):
        return client.files_create(**kwargs)
    raise AttributeError("Provided client does not support file uploads")


def _responses_create(client: object, **kwargs):
    if hasattr(client, "responses") and hasattr(client.responses, "create"):
        return client.responses.create(**kwargs)
    if hasattr(client, "responses_create"):
        return client.responses_create(**kwargs)
    raise AttributeError("Provided client does not support responses API")
