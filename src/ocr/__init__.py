"""OCR package providing image-to-text utilities."""

from .cli import main
from .recognizer import OCRProcessingError, recognize_image

__all__ = ["main", "OCRProcessingError", "recognize_image"]
