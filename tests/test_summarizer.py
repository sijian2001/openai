import json
import pathlib
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from src.summary.summarizer import (
    SummarizationError,
    _default_client,
    _extract_text,
    _files_create,
    _load_cached_response,
    _response_to_dict,
    _responses_create,
    summarize_pdf,
)


class FakeFiles:
    def __init__(self, summary_text: str) -> None:
        self._summary_text = summary_text

    def create(self, *, file, purpose: str):
        file.read()
        return SimpleNamespace(id="file-123", purpose=purpose)


class FakeResponses:
    def __init__(self, summary_text: str) -> None:
        self._summary_text = summary_text

    def create(self, **kwargs):
        return FakeResponse(self._summary_text)


class FakeResponse:
    def __init__(self, summary_text: str) -> None:
        self.output_text = summary_text

    def model_dump(self):  # pragma: no cover - trivial passthrough.
        return {"output_text": self.output_text}


class FakeClient:
    """Minimal stub emulating the OpenAI client methods we call."""

    def __init__(self, summary_text: str = "Bullet 1\nBullet 2") -> None:
        self.files = FakeFiles(summary_text)
        self.responses = FakeResponses(summary_text)


class SummarizerTests(TestCase):
    def test_summarize_pdf_writes_summary_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = pathlib.Path(tmpdir) / "mock.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 placeholder")

            output_dir = pathlib.Path(tmpdir) / "summaries"
            result = summarize_pdf(
                pdf_path,
                client=FakeClient(),
                output_dir=output_dir,
                model="test-model",
            )

            self.assertEqual(result.model, "test-model")
            self.assertTrue(result.output_path.exists())
            self.assertIn("Bullet 1", result.summary_text)
            response_file = output_dir / "mock_response.json"
            self.assertTrue(response_file.exists())
            cached = json.loads(response_file.read_text(encoding="utf-8"))
            self.assertEqual(cached["output_text"], "Bullet 1\nBullet 2")

    def test_summarize_pdf_raises_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = pathlib.Path(tmpdir) / "missing.pdf"
            with self.assertRaises(SummarizationError):
                summarize_pdf(pdf_path, client=FakeClient())

    def test_summarize_pdf_uses_cached_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = pathlib.Path(tmpdir) / "mock.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 placeholder")

            output_dir = pathlib.Path(tmpdir) / "summaries"
            output_dir.mkdir()

            cached_response = {"output_text": "Cached summary text"}
            response_path = output_dir / "mock_response.json"
            response_path.write_text(json.dumps(cached_response), encoding="utf-8")

            summary = summarize_pdf(
                pdf_path,
                client=ExplodingClient(),
                output_dir=output_dir,
                model="test-model",
            )

            self.assertEqual(summary.summary_text, "Cached summary text")
            self.assertTrue((output_dir / "mock_summary.txt").exists())


class ExplodingClient:
    def __getattr__(self, name):
        raise AssertionError("Client should not be used when cache exists.")


class SummarizerHelperTests(TestCase):
    def test_default_client_requires_openai(self) -> None:
        with patch("src.summary.summarizer.OpenAI", None):
            with self.assertRaises(SummarizationError):
                _default_client()

    def test_files_create_prefers_method_alias(self) -> None:
        class Client:
            def files_create(self, **kwargs):
                return kwargs

        result = _files_create(Client(), file="data")
        self.assertEqual(result["file"], "data")

    def test_files_create_raises_without_support(self) -> None:
        with self.assertRaises(AttributeError):
            _files_create(object(), file="data")

    def test_responses_create_prefers_alias(self) -> None:
        class Client:
            def responses_create(self, **kwargs):
                return kwargs

        result = _responses_create(Client(), model="m")
        self.assertEqual(result["model"], "m")

    def test_responses_create_raises_without_support(self) -> None:
        with self.assertRaises(AttributeError):
            _responses_create(object(), model="m")

    def test_response_to_dict_uses_model_dump_json(self) -> None:
        class Response:
            def model_dump_json(self):
                return json.dumps({"output_text": "json path"})

        parsed = _response_to_dict(Response())
        self.assertEqual(parsed["output_text"], "json path")

    def test_response_to_dict_raises_for_unknown_object(self) -> None:
        class Response:
            pass

        with self.assertRaises(SummarizationError):
            _response_to_dict(Response())

    def test_extract_text_from_dict_output_list(self) -> None:
        response = {
            "output": [
                {"content": [{"type": "output_text", "text": "line1"}]},
                {"content": [{"type": "input_text", "text": "line2"}]},
            ]
        }
        result = _extract_text(response)
        self.assertEqual(result, "line1\nline2")

    def test_extract_text_from_object_output_attribute(self) -> None:
        class Message:
            def __init__(self) -> None:
                self.content = [{"type": "text", "text": "hello"}]

        class Response:
            def __init__(self) -> None:
                self.output = [Message()]

        result = _extract_text(Response())
        self.assertEqual(result, "hello")

    def test_extract_text_fallback_to_string(self) -> None:
        result = _extract_text(12345)
        self.assertEqual(result, "12345")

    def test_load_cached_response_raises_on_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            response_path = pathlib.Path(tmpdir) / "bad_response.json"
            response_path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(SummarizationError):
                _load_cached_response(response_path)
