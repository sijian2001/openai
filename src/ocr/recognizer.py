"""Utilities for performing OCR on images using the OpenAI API."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - allows dependency injection in tests
    OpenAI = None  # type: ignore

DEFAULT_MODEL = "gpt-4o-mini"


class OCRProcessingError(RuntimeError):
    """Raised when OCR processing fails."""


@dataclass
class OCRResult:
    """Normalized OCR result returned by :func:`recognize_image`."""

    text: str
    model: str


def recognize_image(
    image_path: Path,
    *,
    client: Optional[object] = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Perform OCR on ``image_path`` and return the extracted text."""

    if not image_path.exists():
        raise OCRProcessingError(f"Image not found: {image_path}")

    if not image_path.is_file():
        raise OCRProcessingError(f"Path is not a file: {image_path}")

    api_client = client or _default_client()
    b64_image = _encode_image(image_path)

    try:
        response = _responses_create(
            api_client,
            model=model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You are an OCR engine. Extract all text from the "
                                "following image and return it as plain text. "
                                "Preserve line breaks where possible."
                            ),
                        },
                        {
                            "type": "input_image",
                            "image": {"b64_json": b64_image},
                        },
                    ],
                }
            ],
        )
    except Exception as exc:  # pragma: no cover - exercised when API fails.
        raise OCRProcessingError(f"OpenAI API call failed: {exc}") from exc

    text = _extract_text(response)
    return text


def _encode_image(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _default_client():
    if OpenAI is None:  # pragma: no cover - executed when dependency missing.
        raise OCRProcessingError(
            "The 'openai' package is not installed. Install it via pip to use OCR."
        )
    return OpenAI()


def _responses_create(client: object, **kwargs):
    if hasattr(client, "responses") and hasattr(client.responses, "create"):
        return client.responses.create(**kwargs)
    if hasattr(client, "responses_create"):
        return client.responses_create(**kwargs)
    raise AttributeError("Provided client does not support the Responses API")


def _extract_text(response) -> str:
    """Extract text output from an OpenAI Responses API response."""

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

    if hasattr(response, "model_dump"):
        data = response.model_dump()  # type: ignore[call-arg]
        if isinstance(data, dict):
            return _extract_text(data)

    if hasattr(response, "model_dump_json"):
        try:
            return _extract_text(json.loads(response.model_dump_json()))  # type: ignore[call-arg]
        except Exception as exc:  # pragma: no cover - unexpected JSON failure.
            raise OCRProcessingError(
                f"Failed to parse response payload: {exc}"
            ) from exc

    return str(response)


def _extract_from_content(content) -> list[str]:
    fragments = []
    for item in content:
        item_type = getattr(item, "type", None)
        if item_type is None and isinstance(item, dict):
            item_type = item.get("type")
        text = getattr(item, "text", None)
        if text is None and isinstance(item, dict):
            text = item.get("text", "")
        if item_type in {"output_text", "text", "input_text"}:
            fragments.append(text or "")
    return fragments
