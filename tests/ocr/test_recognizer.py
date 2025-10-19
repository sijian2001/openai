import base64
import pathlib
import tempfile
from types import SimpleNamespace
from unittest import TestCase

from src.ocr.recognizer import OCRProcessingError, recognize_image


class FakeResponses:
    def __init__(self, expected_b64: str, text: str) -> None:
        self._expected_b64 = expected_b64
        self._text = text

    def create(self, **kwargs):
        payload = kwargs["input"][0]["content"][1]
        assert payload["type"] == "input_image"
        assert payload["image"]["b64_json"] == self._expected_b64
        return SimpleNamespace(output_text=self._text)


class FakeClient:
    def __init__(self, expected_b64: str, text: str = "line1\nline2") -> None:
        self.responses = FakeResponses(expected_b64, text)


class RecognizerTests(TestCase):
    def test_recognize_image_reads_and_encodes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = pathlib.Path(tmpdir) / "sample.png"
            image_path.write_bytes(b"\x89PNG\r\nmock payload")
            expected_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")

            client = FakeClient(expected_b64, text="hello\nworld")
            text = recognize_image(image_path, client=client, model="test-model")

            self.assertEqual(text, "hello\nworld")

    def test_recognize_image_raises_for_missing_file(self) -> None:
        missing = pathlib.Path("does-not-exist.png")
        with self.assertRaises(OCRProcessingError):
            recognize_image(missing)

    def test_recognize_image_raises_for_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            directory = pathlib.Path(tmpdir)
            with self.assertRaises(OCRProcessingError):
                recognize_image(directory)
