import io
import pathlib
import tempfile
from unittest import TestCase
from unittest.mock import patch
import csv

from src.ocr import cli
from src.ocr.recognizer import OCRProcessingError


class CliTests(TestCase):
    def test_process_images_writes_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_dir = pathlib.Path(tmpdir)
            image_paths = []
            for idx in range(2):
                path = image_dir / f"image_{idx}.png"
                path.write_bytes(b"fake-png")
                image_paths.append(path)

            with patch(
                "src.ocr.cli.recognize_image", side_effect=["one\nalpha", "two\nbeta"]
            ):
                csv_paths = cli.process_images(image_paths, model="test-model")

            self.assertEqual(len(csv_paths), 2)
            for csv_path, expected_first_line in zip(
                csv_paths, ["one", "two"], strict=True
            ):
                self.assertTrue(csv_path.exists())
                with csv_path.open("r", encoding="utf-8", newline="") as handle:
                    reader = csv.reader(handle)
                    header = next(reader)
                    rows = list(reader)
                self.assertEqual(header, ["line"])
                self.assertIn(expected_first_line, rows[0][0])

    def test_process_images_handles_empty_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = pathlib.Path(tmpdir) / "image.png"
            image_path.write_bytes(b"fake")

            with patch("src.ocr.cli.recognize_image", return_value=""):
                csv_paths = cli.process_images([image_path])

            self.assertEqual(len(csv_paths), 1)
            with csv_paths[0].open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader)
                rows = list(reader)
            self.assertEqual(header, ["line"])
            self.assertEqual(rows, [[""]])

    def test_main_returns_error_when_input_dir_missing(self) -> None:
        with patch("sys.stderr", new_callable=io.StringIO) as stderr:
            exit_code = cli.main(["--input-dir", "missing/dir"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Input directory not found", stderr.getvalue())

    def test_main_prints_message_when_no_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "sys.stdout", new_callable=io.StringIO
        ) as stdout:
            exit_code = cli.main(["--input-dir", tmpdir])

        self.assertEqual(exit_code, 0)
        self.assertIn("No PNG images found", stdout.getvalue())

    def test_main_handles_ocr_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_dir = pathlib.Path(tmpdir)
            image_path = image_dir / "image.png"
            image_path.write_bytes(b"fake")

            with patch(
                "src.ocr.cli._discover_images", return_value=[image_path]
            ), patch(
                "src.ocr.cli.process_images", side_effect=OCRProcessingError("boom")
            ), patch(
                "sys.stderr", new_callable=io.StringIO
            ) as stderr:
                exit_code = cli.main(["--input-dir", tmpdir])

        self.assertEqual(exit_code, 1)
        self.assertIn("OCR error: boom", stderr.getvalue())

    def test_main_reports_created_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_dir = pathlib.Path(tmpdir)
            image_path = image_dir / "image.png"
            image_path.write_bytes(b"fake")

            csv_path = image_path.with_suffix(".csv")

            with patch(
                "src.ocr.cli._discover_images", return_value=[image_path]
            ), patch("src.ocr.cli.process_images", return_value=[csv_path]), patch(
                "sys.stdout", new_callable=io.StringIO
            ) as stdout:
                exit_code = cli.main(["--input-dir", tmpdir])

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Generated CSV files", output)
        self.assertIn(str(csv_path), output)
