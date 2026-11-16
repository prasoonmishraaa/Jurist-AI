"""
Jurist AI — Handwritten OCR & Multimodal Document Intelligence Test Suite
Tests:
1. Printed digital PDF (multi-page native digital text).
2. Scanned printed PDF (typeset typography raster scan).
3. Handwritten scanned PDF (cursive and neat manuscript raster scans).
4. Handwritten standalone image (PNG / JPG).
5. Epistemic safety: uncertain tokens flagged with [?token?], warnings attached,
   and unverified handwriting never silently elevated to verified legal evidence.
6. 15 MB upload limit preservation.
7. Page number and structural boundary preservation across all modalities.
"""

import io
import os
import sys
import pytest
from PIL import Image, ImageDraw, ImageFont

# Add ml-service to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymupdf
from app.ocr.document_extractor import DocumentExtractor
from app.ocr.ocr_engine import OCREngine
from app.ocr.legal_formatter import LegalFormatter


# Helper to obtain system fonts on Windows
FONT_ARIAL = r"C:\Windows\Fonts\arial.ttf"
FONT_SEGOE_PRINT = r"C:\Windows\Fonts\segoepr.ttf"
FONT_SEGOE_SCRIPT = r"C:\Windows\Fonts\segoesc.ttf"
FONT_INK_FREE = r"C:\Windows\Fonts\inkfree.ttf"


def create_rendered_image(lines: list, font_path: str, font_size: int = 22, width: int = 900, height: int = 400) -> Image.Image:
    """Renders text lines onto an image using specified font."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    if os.path.exists(font_path):
        font = ImageFont.truetype(font_path, font_size)
    else:
        font = ImageFont.load_default()

    y = 35
    for line in lines:
        draw.text((40, y), line, fill=(0, 0, 0), font=font)
        y += 45
    return img


def make_rendered_pdf(pages_lines: list, font_path: str, font_size: int = 22) -> bytes:
    """Creates a multi-page raster PDF from rendered lines."""
    doc = pymupdf.open()
    for lines in pages_lines:
        img = create_rendered_image(lines, font_path, font_size)
        img_buf = io.BytesIO()
        img.save(img_buf, format="PNG")
        img_bytes = img_buf.getvalue()

        page = doc.new_page(width=595, height=842)
        # Center image on page
        page.insert_image(pymupdf.Rect(20, 50, 575, 450), stream=img_bytes)

    buf = doc.tobytes()
    doc.close()
    return buf


def make_native_digital_pdf(pages_text: list) -> bytes:
    """Creates a multi-page digital PDF with native text layer."""
    doc = pymupdf.open()
    for text in pages_text:
        page = doc.new_page(width=595, height=842)
        page.insert_textbox(pymupdf.Rect(50, 50, 545, 800), text, fontsize=11)
    buf = doc.tobytes()
    doc.close()
    return buf


class TestMultimodalOCRVerification:
    """Comprehensive test suite for printed, scanned, and handwritten documents."""

    @classmethod
    def setup_class(cls):
        cls.ocr_engine = OCREngine()
        cls.extractor = DocumentExtractor(ocr_engine=cls.ocr_engine)

    def test_01_printed_digital_pdf(self):
        """Category 1: Printed digital multi-page PDF extracts natively with 100% confidence."""
        p1 = (
            "IN THE HIGH COURT OF JUDICATURE AT BOMBAY\n"
            "CRIMINAL APPELLATE JURISDICTION\n"
            "Criminal Appeal No. 782 of 2024\n\n"
            "1. The Appellant challenges order dated 15.08.2024.\n"
            "2. Section 35(1) BNSS requires mandatory recorded reasons prior to arrest."
        )
        p2 = (
            "3. Supreme Court in Arnesh Kumar v. State of Bihar (2014) 8 SCC 273 mandated notice compliance.\n"
            "4. Notice under Section 35(3) BNSS was never served upon the Appellant."
        )
        pdf_bytes = make_native_digital_pdf([p1, p2])

        res = self.extractor.extract_document(pdf_bytes, "digital_appeal.pdf")

        assert res["success"] is True
        assert res["documentType"] == "pdf"
        assert res["pageCount"] == 2
        assert res["extractionMethod"] == "native"
        assert res["overallStatus"] == "SUCCESS"
        assert res["handwrittenDetected"] is False
        assert res["scriptType"] == "digital"

        # Verify page boundary preservation
        assert "[--- PAGE 1 (Native Digital - 100% Conf.) ---]" in res["extractedText"]
        assert "[--- PAGE 2 (Native Digital - 100% Conf.) ---]" in res["extractedText"]
        assert "Section 35(1) BNSS" in res["extractedText"]
        assert "Arnesh Kumar" in res["extractedText"]

        # Ensure no evidentiary OCR warnings injected into clean digital text
        assert not any("handwritten" in w.lower() for w in res["warnings"])

    def test_02_scanned_printed_pdf(self):
        """Category 2: Scanned printed PDF (rasterized) extracts via OCR as printed script."""
        p1_lines = [
            "IN THE HIGH COURT OF JUDICATURE AT BOMBAY",
            "Bail Application No. 1240 of 2024",
            "The applicant was arrested on 15 August 2024 without statutory notice.",
            "Section 35(1) BNSS requires recorded reasons prior to arrest."
        ]
        pdf_bytes = make_rendered_pdf([p1_lines], font_path=FONT_ARIAL, font_size=20)

        res = self.extractor.extract_document(pdf_bytes, "scanned_printed_order.pdf")

        assert res["success"] is True
        assert res["documentType"] == "pdf"
        assert res["pageCount"] == 1
        assert res["extractionMethod"] == "ocr"
        # Script must be classified as printed
        assert res["pages"][0]["scriptType"] == "printed"
        assert res["pages"][0]["handwrittenDetected"] is False
        assert res["pages"][0]["confidence"] > 0.85
        assert "Section 35(1) BNSS" in res["extractedText"]
        assert "[--- PAGE 1 (OCR - Printed" in res["extractedText"]

    def test_03_handwritten_pdf_multipage(self):
        """Category 3: Multi-page handwritten PDF detects handwriting and flags epistemic warnings."""
        p1_lines = [
            "Police Station Crime Diary Entry",
            "Accused remanded to judicial custody for 14 days",
            "Bail application moved under Section 437 CrPC"
        ]
        p2_lines = [
            "Medico-legal injury certificate dated 16.08.2024",
            "Applicant sustained blunt trauma during police custody",
            "Referred to civil hospital for medical examination"
        ]
        # Use cursive script font for realistic handwriting simulation
        pdf_bytes = make_rendered_pdf([p1_lines, p2_lines], font_path=FONT_SEGOE_SCRIPT, font_size=20)

        res = self.extractor.extract_document(pdf_bytes, "handwritten_diary.pdf")

        assert res["success"] is True
        assert res["documentType"] == "pdf"
        assert res["pageCount"] == 2
        assert res["extractionMethod"] == "ocr"
        # Must detect handwriting!
        assert res["handwrittenDetected"] is True
        assert res["scriptType"] in ("handwritten", "mixed")

        # Crucial Requirement: Never silently treat inaccurate OCR output as verified legal evidence!
        assert res["overallStatus"] in ("SUCCESS_WITH_WARNINGS", "LOW_CONFIDENCE_OCR")
        assert any("handwritten" in w.lower() for w in res["warnings"])
        assert any("verified against original" in w.lower() for w in res["warnings"])

        # Page boundary and page numbering preserved
        assert res["pages"][0]["pageNumber"] == 1
        assert res["pages"][1]["pageNumber"] == 2
        assert "[--- PAGE 1 (OCR - Handwritten" in res["extractedText"]
        assert "[--- PAGE 2 (OCR - Handwritten" in res["extractedText"]
        assert "EVIDENTIARY NOTICE" in res["extractedText"]

    def test_04_handwritten_image_upload(self):
        """Category 4: Standalone handwritten image (.png / .jpg) detects script and flags uncertain tokens."""
        lines = [
            "Remand Order: Accused produced before Special Magistrate",
            "Investigation pending under Section 420 IPC",
            "Statutory notice not served upon applicant"
        ]
        img = create_rendered_image(lines, font_path=FONT_SEGOE_PRINT, font_size=22)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        res = self.extractor.extract_document(img_bytes, "handwritten_remand_order.png")

        assert res["success"] is True
        assert res["documentType"] == "png"
        assert res["pageCount"] == 1
        assert res["extractionMethod"] == "ocr"
        assert res["handwrittenDetected"] is True
        assert res["scriptType"] in ("handwritten", "mixed")
        assert res["overallStatus"] in ("SUCCESS_WITH_WARNINGS", "LOW_CONFIDENCE_OCR")
        assert any("handwritten" in w.lower() for w in res["warnings"])
        assert len(res["extractedText"]) > 0

    def test_05_uncertain_token_epistemic_tagging(self):
        """Verifies that mangled cursive words are caught and delimited with [?token?]."""
        # Render difficult cursive line
        lines = ["Accused remanded to judicial custody for 14 days"]
        img = create_rendered_image(lines, font_path=FONT_SEGOE_SCRIPT, font_size=22)

        ocr_res = self.ocr_engine.process_image(img)

        assert ocr_res["handwrittenDetected"] is True
        # If words were misrecognized, they must be marked with [?word?]
        text = ocr_res["text"]
        # If uncertain tokens exist, they must be recorded in uncertainTokens list
        if ocr_res["uncertainTokens"]:
            for token in ocr_res["uncertainTokens"]:
                assert f"[?{token}?]" in text

    def test_06_upload_limit_enforcement_15mb(self):
        """Requirement 9: Preserves 15 MB upload limit enforcement."""
        # 16 MB buffer exceeding limit
        oversized_buffer = b"%PDF-" + b"0" * (16 * 1024 * 1024)
        res = self.extractor.extract_document(oversized_buffer, "oversized.pdf")

        assert res["success"] is False
        assert res["overallStatus"] == "FAILED"
        assert any("exceeds maximum allowed limit of 15 MB" in w for w in res["warnings"])
