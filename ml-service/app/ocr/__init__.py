"""
Jurist AI — Document Intelligence & OCR Subsystem
Provides multi-format document extraction, PDF digital vs scanned page classification,
image preprocessing, and Tesseract OCR integration with legal structure preservation.
"""

from .document_extractor import DocumentExtractor
from .ocr_engine import OCREngine
from .legal_formatter import LegalFormatter

__all__ = ["DocumentExtractor", "OCREngine", "LegalFormatter"]
