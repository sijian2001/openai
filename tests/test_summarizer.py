import pathlib
import tempfile
from types import SimpleNamespace
from unittest import TestCase

from src.summarizer import SummarizationError, summarize_pdf


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
        return SimpleNamespace(output_text=self._summary_text)


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

    def test_summarize_pdf_raises_for_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = pathlib.Path(tmpdir) / "missing.pdf"
            with self.assertRaises(SummarizationError):
                summarize_pdf(pdf_path, client=FakeClient())
