import io
import pathlib
import tempfile
import urllib.error
from unittest import TestCase
from unittest.mock import patch

from src.fetcher import DownloadError, download_pdf


class FetcherTests(TestCase):
    @patch("urllib.request.urlopen")
    def test_download_pdf_writes_file(self, mock_urlopen) -> None:
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"%PDF-1.4"

        with tempfile.TemporaryDirectory() as tmpdir:
            result = download_pdf(
                "https://example.com/report.pdf", directory=pathlib.Path(tmpdir)
            )
            self.assertTrue(result.path.exists())
            self.assertEqual(result.bytes_written, 8)

    @patch("urllib.request.urlopen")
    def test_download_pdf_raises_on_error(self, mock_urlopen) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("network down")

        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(DownloadError):
                download_pdf(
                    "https://example.com/report.pdf", directory=pathlib.Path(tmpdir)
                )
