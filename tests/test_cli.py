import io
import os
import pathlib
import tempfile
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from src.summary.cli import (
    ConfigurationError,
    _config_value,
    load_config,
    main,
    parse_args,
)
from src.summary.fetcher import DownloadError
from src.summary.summarizer import SummarizationError


class LoadConfigTests(TestCase):
    def test_uses_packaged_defaults_when_override_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = pathlib.Path(tmpdir) / "config.yaml"
            self.assertFalse(missing_path.exists())
            config = load_config(missing_path)
            self.assertEqual(config["summarizer"]["model"], "gpt-4o-mini")
            self.assertEqual(config["fetcher"]["pdf_dir"], "output/pdf")

    def test_raises_for_non_mapping_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / "config.yaml"
            config_path.write_text("- not-a-mapping", encoding="utf-8")

            with self.assertRaises(ConfigurationError):
                load_config(config_path)

    def test_override_merges_with_packaged_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = pathlib.Path(tmpdir) / "config.yaml"
            config_path.write_text(
                "summarizer:\n  model: custom-model\nfetcher:\n  pdf_dir: /tmp/pdf\n",
                encoding="utf-8",
            )

            config = load_config(config_path)
            self.assertEqual(config["summarizer"]["model"], "custom-model")
            self.assertEqual(config["fetcher"]["pdf_dir"], "/tmp/pdf")

    def test_load_config_returns_empty_when_bundled_missing(self) -> None:
        with patch("src.summary.cli.resources.files", side_effect=FileNotFoundError):
            config = load_config(pathlib.Path("missing.yaml"))
            self.assertEqual(config, {})

    def test_load_config_returns_empty_when_bundled_file_missing(self) -> None:
        class MissingResource:
            def joinpath(self, name):
                return self

            def open(self, *args, **kwargs):
                raise FileNotFoundError

        with patch("src.summary.cli.resources.files", return_value=MissingResource()):
            config = load_config(pathlib.Path("missing.yaml"))
            self.assertEqual(config, {})

    def test_load_config_raises_for_invalid_bundled_structure(self) -> None:
        class BadResource:
            def joinpath(self, name):
                return self

            def open(self, *args, **kwargs):
                return io.StringIO("- not-a-mapping")

        with patch("src.summary.cli.resources.files", return_value=BadResource()):
            with self.assertRaises(ConfigurationError):
                load_config(pathlib.Path("missing.yaml"))


class CliExecutionTests(TestCase):
    def test_parse_args_uses_config_defaults(self) -> None:
        config = {
            "summarizer": {"model": "custom-model", "output_dir": "nested/output"},
            "fetcher": {"pdf_dir": "nested/pdf"},
        }
        args = parse_args(
            ["https://example.com/report.pdf"],
            config=config,
        )
        self.assertEqual(args.model, "custom-model")
        self.assertEqual(args.output_dir, pathlib.Path("nested/output"))
        self.assertEqual(args.pdf_dir, pathlib.Path("nested/pdf"))

    def test_main_returns_error_when_api_key_missing(self) -> None:
        config = {
            "summarizer": {"model": "gpt-4o-mini", "output_dir": "output/summaries"},
            "fetcher": {"pdf_dir": "output/pdf"},
        }
        with patch("src.summary.cli.load_config", return_value=config), patch.dict(
            os.environ, {}, clear=True
        ), patch("src.summary.cli.download_pdf") as mock_download, patch(
            "src.summary.cli.summarize_pdf"
        ) as mock_summary:
            exit_code = main(["https://example.com/report.pdf"])

        self.assertEqual(exit_code, 1)
        mock_download.assert_not_called()
        mock_summary.assert_not_called()

    def test_main_runs_successfully(self) -> None:
        config = {
            "summarizer": {"model": "test-model", "output_dir": "output/summaries"},
            "fetcher": {"pdf_dir": "output/pdf"},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = pathlib.Path(tmpdir) / "downloaded.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 placeholder")

            summary_path = pathlib.Path(tmpdir) / "summary.txt"
            download_result = SimpleNamespace(
                path=pdf_path, bytes_written=len(b"%PDF-1.4 placeholder")
            )
            summary_result = SimpleNamespace(
                summary_text="まとめテキスト",
                model="test-model",
                output_path=summary_path,
            )

            with patch("src.summary.cli.load_config", return_value=config), patch.dict(
                os.environ, {"OPENAI_API_KEY": "token"}, clear=True
            ), patch(
                "src.summary.cli.download_pdf", return_value=download_result
            ) as mock_download, patch(
                "src.summary.cli.summarize_pdf", return_value=summary_result
            ) as mock_summarize:
                captured_output = io.StringIO()
                with patch("sys.stdout", captured_output):
                    exit_code = main(["https://example.com/report.pdf"])

        self.assertEqual(exit_code, 0)
        mock_download.assert_called_once_with(
            "https://example.com/report.pdf", directory=pathlib.Path("output/pdf")
        )
        mock_summarize.assert_called_once_with(
            pdf_path, model="test-model", output_dir=pathlib.Path("output/summaries")
        )
        output_text = captured_output.getvalue()
        self.assertIn("まとめテキスト", output_text)
        self.assertIn("Summary written to:", output_text)

    def test_main_returns_error_on_config_failure(self) -> None:
        with patch(
            "src.summary.cli.load_config", side_effect=ConfigurationError("boom")
        ), patch.dict(os.environ, {"OPENAI_API_KEY": "token"}, clear=True):
            captured_error = io.StringIO()
            with patch("sys.stderr", captured_error):
                exit_code = main(["https://example.com/report.pdf"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Configuration error: boom", captured_error.getvalue())

    def test_main_returns_error_on_download_failure(self) -> None:
        config = {
            "summarizer": {"model": "m", "output_dir": "output/summaries"},
            "fetcher": {"pdf_dir": "output/pdf"},
        }
        with patch("src.summary.cli.load_config", return_value=config), patch.dict(
            os.environ, {"OPENAI_API_KEY": "token"}, clear=True
        ), patch(
            "src.summary.cli.download_pdf", side_effect=DownloadError("network down")
        ) as mock_download, patch(
            "src.summary.cli.summarize_pdf"
        ) as mock_summarize:
            captured_error = io.StringIO()
            with patch("sys.stderr", captured_error):
                exit_code = main(["https://example.com/report.pdf"])

        self.assertEqual(exit_code, 1)
        mock_download.assert_called_once()
        mock_summarize.assert_not_called()
        self.assertIn("Download error: network down", captured_error.getvalue())

    def test_main_returns_error_on_summarization_failure(self) -> None:
        config = {
            "summarizer": {"model": "m", "output_dir": "output/summaries"},
            "fetcher": {"pdf_dir": "output/pdf"},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = pathlib.Path(tmpdir) / "downloaded.pdf"
            pdf_path.write_bytes(b"%PDF")
            download_result = SimpleNamespace(path=pdf_path, bytes_written=4)

            with patch("src.summary.cli.load_config", return_value=config), patch.dict(
                os.environ, {"OPENAI_API_KEY": "token"}, clear=True
            ), patch(
                "src.summary.cli.download_pdf", return_value=download_result
            ), patch(
                "src.summary.cli.summarize_pdf",
                side_effect=SummarizationError("api failure"),
            ) as mock_summarize:
                captured_error = io.StringIO()
                with patch("sys.stderr", captured_error):
                    exit_code = main(["https://example.com/report.pdf"])

        self.assertEqual(exit_code, 1)
        mock_summarize.assert_called_once()
        self.assertIn("Summarization error: api failure", captured_error.getvalue())


class ConfigValueTests(TestCase):
    def test_config_value_returns_default_when_intermediate_not_mapping(self) -> None:
        config = {"summarizer": "invalid"}
        self.assertEqual(
            _config_value(config, "summarizer", "model", default="fallback"), "fallback"
        )

    def test_config_value_returns_default_when_key_missing(self) -> None:
        self.assertEqual(
            _config_value({}, "summarizer", "model", default="fallback"), "fallback"
        )
