"""
Jurist AI — Feature 2 Document Intelligence & OCR Unit Test Suite
Verifies:
1. Digital PDF extraction.
2. Scanned PDF with Tesseract available (mocked & live).
3. Mixed digital/scanned PDF.
4. PNG/JPG upload.
5. Password-protected PDF detection.
6. Tesseract unavailable graceful handling (SCANNED_UNPROCESSED).
7. Low-confidence OCR detection.
8. Corrupted PDF/image handling.
9. Max PDF page limit enforcement (50 pages).
10. Max OCR page limit enforcement (20 pages).
11. Page-number and boundary preservation.
12. Legal section and citation preservation.
"""

import io
import sys
import os
import pytest
from PIL import Image, ImageDraw

# Add ml-service to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymupdf
from app.ocr.document_extractor import DocumentExtractor
from app.ocr.ocr_engine import OCREngine
from app.ocr.legal_formatter import LegalFormatter


class MockOCREngineAvailable:
    """Mock OCR engine simulating active Tesseract with high confidence."""
    is_available = True
    tesseract_version = "5.3.4"
    availability_status = "available (Mock Tesseract)"

    def process_image(self, img):
        return {
            "text": "First Information Report under Section 154 CrPC. Cognizable offence registered on 15.08.2024.",
            "confidence": 0.92,
            "status": "SUCCESS",
            "extractionMethod": "ocr",
            "warnings": []
        }


class MockOCREngineLowConfidence:
    """Mock OCR engine simulating low confidence extraction."""
    is_available = True
    tesseract_version = "5.3.4"
    availability_status = "available (Mock Tesseract)"

    def process_image(self, img):
        return {
            "text": "[?F1rst?] [?1nformat1on?] [?Rep0rt?]",
            "confidence": 0.32,
            "status": "LOW_CONFIDENCE_OCR",
            "extractionMethod": "ocr",
            "warnings": ["Low confidence OCR extraction (32% average confidence). Text may contain errors."]
        }


class MockOCREngineUnavailable:
    """Mock OCR engine simulating host missing Tesseract binary."""
    is_available = False
    tesseract_version = None
    availability_status = "unavailable (Tesseract system binary not found)"

    def process_image(self, img):
        return {
            "text": "",
            "confidence": None,
            "status": "SCANNED_UNPROCESSED",
            "extractionMethod": "ocr",
            "warnings": ["Tesseract OCR system binary is not available. Scanned content was not extracted."]
        }


def make_digital_pdf(text_content: str, num_pages: int = 1) -> bytes:
    """Creates an in-memory PDF containing native digital text with word-wrapping."""
    doc = pymupdf.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)
        rect = pymupdf.Rect(50, 50, 545, 800)
        page.insert_textbox(rect, f"Page {i + 1} Content:\n{text_content}", fontsize=11)
    buf = doc.tobytes()
    doc.close()
    return buf


def make_scanned_pdf(num_pages: int = 1) -> bytes:
    """Creates an in-memory PDF where each page consists solely of a raster image scan."""
    # Create a synthetic scan image
    img = Image.new("RGB", (800, 1100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((60, 60), "Police Station Crime Register Memo", fill=(0, 0, 0))
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_bytes = img_buf.getvalue()

    doc = pymupdf.open()
    for _ in range(num_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_image(page.rect, stream=img_bytes)
    buf = doc.tobytes()
    doc.close()
    return buf


def make_mixed_pdf() -> bytes:
    """Creates a 2-page PDF: Page 1 is digital text, Page 2 is a scanned image."""
    img = Image.new("RGB", (800, 1100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((60, 60), "Annexure P-1 Scanned Receipt", fill=(0, 0, 0))
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")

    doc = pymupdf.open()
    # Page 1: Native digital text
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text(
        (50, 72),
        "IN THE HIGH COURT OF DELHI\nCRIMINAL MISC. APPLICATION NO. 450 OF 2024\n\n"
        "1. That the Petitioner seeks anticipatory bail under Section 438 of the Code of Criminal Procedure, 1973.\n"
        "2. That the Petitioner has complied with notice under Section 41A CrPC.",
        fontsize=11
    )
    # Page 2: Scanned image
    p2 = doc.new_page(width=595, height=842)
    p2.insert_image(p2.rect, stream=img_buf.getvalue())

    buf = doc.tobytes()
    doc.close()
    return buf


def test_01_digital_pdf_extraction():
    """Test 1: Digital PDF extracts native text without invoking OCR."""
    extractor = DocumentExtractor(ocr_engine=MockOCREngineUnavailable())
    legal_text = (
        "IN THE SUPREME COURT OF INDIA\n"
        "CIVIL APPELLATE JURISDICTION\n"
        "Section 138 of Negotiable Instruments Act, 1881.\n"
        "1. The presumption under Section 139 is rebuttable by preponderance of probabilities.\n"
        "2. Reliance placed on Rangappa v. Sri Mohan (2010) 11 SCC 441."
    )
    pdf_bytes = make_digital_pdf(legal_text, num_pages=2)

    result = extractor.extract_document(pdf_bytes, "petition.pdf")

    assert result["success"] is True
    assert result["documentType"] == "pdf"
    assert result["pageCount"] == 2
    assert result["extractionMethod"] == "native"
    assert result["overallStatus"] == "SUCCESS"
    assert "Section 138" in result["extractedText"]
    assert "Rangappa v. Sri Mohan" in result["extractedText"]
    assert "(2010) 11 SCC 441" in result["extractedText"]
    # Check page markers
    assert "[--- PAGE 1 (Native Digital - 100% Conf.) ---]" in result["extractedText"]
    assert "[--- PAGE 2 (Native Digital - 100% Conf.) ---]" in result["extractedText"]


def test_02_scanned_pdf_with_tesseract_available():
    """Test 2: Scanned PDF uses OCR when Tesseract is available."""
    extractor = DocumentExtractor(ocr_engine=MockOCREngineAvailable())
    scanned_bytes = make_scanned_pdf(num_pages=1)

    result = extractor.extract_document(scanned_bytes, "fir_scan.pdf")

    assert result["success"] is True
    assert result["documentType"] == "pdf"
    assert result["pageCount"] == 1
    assert result["extractionMethod"] == "ocr"
    assert result["overallStatus"] == "SUCCESS"
    assert "Section 154 CrPC" in result["extractedText"]
    assert result["pages"][0]["confidence"] == 0.92


def test_03_mixed_digital_scanned_pdf():
    """Test 3: Mixed PDF extracts digital page via native and scanned page via OCR."""
    extractor = DocumentExtractor(ocr_engine=MockOCREngineAvailable())
    mixed_bytes = make_mixed_pdf()

    result = extractor.extract_document(mixed_bytes, "mixed_case.pdf")

    assert result["success"] is True
    assert result["documentType"] == "pdf"
    assert result["pageCount"] == 2
    assert result["extractionMethod"] == "hybrid"
    assert result["overallStatus"] == "SUCCESS"
    # Page 1 should be native
    assert result["pages"][0]["extractionMethod"] == "native"
    assert "Section 438" in result["pages"][0]["text"]
    # Page 2 should be OCR
    assert result["pages"][1]["extractionMethod"] == "ocr"
    assert result["pages"][1]["confidence"] == 0.92


def test_04_png_jpg_upload():
    """Test 4: Standalone image upload (PNG/JPG) routes through OCR."""
    extractor = DocumentExtractor(ocr_engine=MockOCREngineAvailable())

    img = Image.new("RGB", (400, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "Bail Order Copy", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    result = extractor.extract_document(buf.getvalue(), "order.png")

    assert result["success"] is True
    assert result["documentType"] == "png"
    assert result["pageCount"] == 1
    assert result["extractionMethod"] == "ocr"
    assert result["overallStatus"] == "SUCCESS"


def test_05_password_protected_pdf():
    """Test 5: Password-protected PDF is detected and returns safe error."""
    extractor = DocumentExtractor()
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 50), "Confidential")
    enc_bytes = doc.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="juristowner",
        user_pw="juristpass"
    )
    doc.close()

    result = extractor.extract_document(enc_bytes, "secret.pdf")

    assert result["success"] is False
    assert result["overallStatus"] == "FAILED"
    assert any("password-protected" in w.lower() for w in result["warnings"])


def test_06_tesseract_unavailable():
    """Test 6: Scanned PDF when Tesseract is unavailable returns SCANNED_UNPROCESSED."""
    extractor = DocumentExtractor(ocr_engine=MockOCREngineUnavailable())
    scanned_bytes = make_scanned_pdf(num_pages=1)

    result = extractor.extract_document(scanned_bytes, "scanned_order.pdf")

    assert result["success"] is True
    assert result["overallStatus"] == "SCANNED_UNPROCESSED"
    assert result["pages"][0]["status"] == "SCANNED_UNPROCESSED"
    assert result["pages"][0]["confidence"] is None
    assert any("unavailable" in w.lower() for w in result["warnings"])
    assert any("not available" in w.lower() for w in result["pages"][0]["warnings"])


def test_07_low_confidence_ocr():
    """Test 7: Low confidence OCR marks LOW_CONFIDENCE_OCR and annotates uncertain words."""
    extractor = DocumentExtractor(ocr_engine=MockOCREngineLowConfidence())
    scanned_bytes = make_scanned_pdf(num_pages=1)

    result = extractor.extract_document(scanned_bytes, "faint_xerox.pdf")

    assert result["success"] is True
    assert result["overallStatus"] == "LOW_CONFIDENCE_OCR"
    assert result["pages"][0]["confidence"] == 0.32
    assert "[?F1rst?]" in result["extractedText"]


def test_08_corrupted_pdf_and_image():
    """Test 8: Corrupted file bytes return safe FAILED status without crashing."""
    extractor = DocumentExtractor()

    # Corrupted PDF with valid magic byte prefix but malformed tail
    corrupted_pdf = b"%PDF-1.4\nGarbageCorruptedBytesNotValidPDFStreamTrailer"
    res_pdf = extractor.extract_document(corrupted_pdf, "broken.pdf")
    assert res_pdf["success"] is False
    assert res_pdf["overallStatus"] == "FAILED"

    # Corrupted PNG
    corrupted_png = b"\x89PNG\r\n\x1a\nGarbageImageBytes"
    res_png = extractor.extract_document(corrupted_png, "broken.png")
    assert res_png["success"] is False
    assert res_png["overallStatus"] == "FAILED"


def test_09_max_pdf_page_limit_enforcement():
    """Test 9: PDFs exceeding 50 pages are safely capped at 50 pages."""
    extractor = DocumentExtractor(ocr_engine=MockOCREngineUnavailable())
    long_pdf = make_digital_pdf("Standard trial court page text.", num_pages=53)

    result = extractor.extract_document(long_pdf, "paperbook_53_pages.pdf")

    assert result["success"] is True
    assert result["pageCount"] == 50
    assert len(result["pages"]) == 50
    assert any("exceeds the limit of 50" in w for w in result["warnings"])


def test_10_max_ocr_page_limit_enforcement():
    """Test 10: Scanned PDFs exceeding 20 scanned pages cap OCR at 20 pages."""
    extractor = DocumentExtractor(ocr_engine=MockOCREngineAvailable())
    scanned_22 = make_scanned_pdf(num_pages=22)

    result = extractor.extract_document(scanned_22, "huge_scan.pdf")

    assert result["success"] is True
    assert result["pageCount"] == 22
    # First 20 pages should have OCR success
    assert result["pages"][0]["status"] == "SUCCESS"
    assert result["pages"][19]["status"] == "SUCCESS"
    # Page 21 and 22 should be flagged for exceeding OCR limit
    assert result["pages"][20]["status"] == "SCANNED_UNPROCESSED"
    assert "exceeded maximum scanned OCR limit" in result["pages"][20]["warnings"][0]


def test_11_page_number_and_boundary_preservation():
    """Test 11: Multi-page document preserves explicit page boundary delimiters."""
    extractor = DocumentExtractor(ocr_engine=MockOCREngineUnavailable())
    pdf_bytes = make_digital_pdf("Distinct text on this page.", num_pages=3)

    result = extractor.extract_document(pdf_bytes, "multi_page.pdf")

    assert result["pageCount"] == 3
    assert "[--- PAGE 1 (Native Digital - 100% Conf.) ---]" in result["extractedText"]
    assert "[--- PAGE 2 (Native Digital - 100% Conf.) ---]" in result["extractedText"]
    assert "[--- PAGE 3 (Native Digital - 100% Conf.) ---]" in result["extractedText"]


def test_12_legal_section_and_citation_preservation():
    """Test 12: Complex legal citations, paragraph numbering, and section symbols are preserved."""
    legal_brief = (
        "IN THE HIGH COURT OF JUDICATURE AT BOMBAY\n\n"
        "1. The Petitioner has been charged under Section 420, Section 406 read with Section 34 of the Indian Penal Code.\n"
        "2. The statutory period under Section 167(2) CrPC expired on 10 August 2024.\n"
        "3. Right to default bail is an indefeasible fundamental right under Article 21, as held in Bikramjit Singh v. State of Punjab (2020) 10 SCC 616.\n"
        "4. The learned Special Judge failed to consider paragraph 27 of Satender Kumar Antil v. CBI (2022) 10 SCC 51."
    )
    extractor = DocumentExtractor(ocr_engine=MockOCREngineUnavailable())
    pdf_bytes = make_digital_pdf(legal_brief, num_pages=1)

    result = extractor.extract_document(pdf_bytes, "bail_petition.pdf")

    text = result["extractedText"]
    assert "Section 420" in text
    assert "Section 167(2) CrPC" in text
    assert "Article 21" in text
    assert "Bikramjit Singh" in text
    assert "State of Punjab" in text
    assert "(2020) 10 SCC 616" in text
    assert "Satender Kumar Antil v. CBI" in text
    assert "(2022)" in text
    assert "10 SCC 51" in text
    # Paragraph numbers preserved
    assert "1. The Petitioner" in text
    assert "2. The statutory" in text
    assert "3. Right to default" in text
    assert "4. The learned" in text
