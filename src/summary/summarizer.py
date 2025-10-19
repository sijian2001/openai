"""OpenAI-powered summarization pipelines for earnings report PDFs."""

from __future__ import annotations

import json
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

    target_dir = output_dir or Path("summaries")
    target_dir.mkdir(parents=True, exist_ok=True)
    response_path = target_dir / (pdf_path.stem + "_response.json")
    output_path = target_dir / (pdf_path.stem + "_summary.txt")

    if response_path.exists():
        response_payload = _load_cached_response(response_path)
        summary_text = _extract_text(response_payload)
        output_path.write_text(summary_text, encoding="utf-8")
        return SummaryResult(
            summary_text=summary_text, model=model, output_path=output_path
        )

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
                            "type": "input_text",
                            "text": (
                                "You analyze corporate earnings reports and produce "
                                "clear bullet summaries highlighting revenue, profit, "
                                "guidance, and strategic updates. Always respond in Japanese."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Summarize the attached earnings report. Provide concise bullet points "
                                "and a closing paragraph on outlook if available. "
                                "Output must be written entirely in Japanese. "
                                "Ensure the very first lines clearly identify the company: "
                                "output a header in the format '銘柄コード: XXXX 会社名: YYYY 決算期: yyyy年mm月期' "
                                "using information from the report. If the code or name cannot be "
                                "found, state '不明'. "
                                # "Include separate bullet sections that analyze the report from the perspectives "
                                # "of 収益性, 安全性, 生産性, 成長性, 株主還元, and 今後の見通し, providing at least one insight for each."
                            ),
                        },
                        {
                            "type": "input_file",
                            "file_id": getattr(upload, "id", None),
                        },
                    ],
                },
            ],
        )
    except Exception as exc:  # pragma: no cover - hit when API fails.
        raise SummarizationError(f"OpenAI API call failed: {exc}") from exc

    response_payload = _response_to_dict(response)
    response_path.write_text(
        json.dumps(response_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    summary_text = _extract_text(response)

    output_path.write_text(summary_text, encoding="utf-8")

    return SummaryResult(
        summary_text=summary_text, model=model, output_path=output_path
    )


def _extract_text(response) -> str:
    """Normalize the varied response schema for the Responses API."""

    if isinstance(response, dict):
        if isinstance(response.get("output_text"), str):
            return response["output_text"]

        output = response.get("output")
        if isinstance(output, list):
            fragments = []
            for message in output:
                content = None
                if isinstance(message, dict):
                    content = message.get("content")
                else:
                    content = getattr(message, "content", None)
                if not content:
                    continue
                fragments.extend(_extract_from_content(content))
            if fragments:
                return "\n".join(fragments)

    if hasattr(response, "output_text"):
        return response.output_text  # type: ignore[return-value]

    if hasattr(response, "output") and response.output:
        fragments = []
        for message in response.output:
            content = getattr(message, "content", None)
            if content is None and isinstance(message, dict):
                content = message.get("content")
            if not content:
                continue
            fragments.extend(_extract_from_content(content))
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


def _response_to_dict(response: object) -> dict:
    if isinstance(response, dict):
        return response
    if hasattr(response, "model_dump"):
        data = response.model_dump()  # type: ignore[call-arg]
        if isinstance(data, dict):
            return data
    if hasattr(response, "model_dump_json"):
        try:
            return json.loads(response.model_dump_json())  # type: ignore[call-arg]
        except (
            Exception
        ) as exc:  # pragma: no cover - unexpected JSON serialization failure.
            raise SummarizationError(
                f"Failed to serialize response to JSON: {exc}"
            ) from exc
    raise SummarizationError("OpenAI response object cannot be serialized to JSON.")


def _load_cached_response(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SummarizationError(f"Cached response is not valid JSON: {path}") from exc


def _extract_from_content(content) -> list[str]:
    fragments = []
    for item in content:
        item_type = getattr(item, "type", None)
        if item_type is None and isinstance(item, dict):
            item_type = item.get("type")
        text = getattr(item, "text", None)
        if text is None and isinstance(item, dict):
            text = item.get("text", "")
        if item_type in {"output_text", "summary_text"}:
            fragments.append(text or "")
        elif item_type in {"text", "input_text"}:
            fragments.append(text or "")
    return fragments
