"""
Jurist AI — Multi-Format Document Intelligence & Page Classifier
Inspects PDFs per-page to differentiate digital text from raster scans,
rasterizes scanned pages for Tesseract OCR, and produces structured document dossiers.
"""

import io
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image

try:
    import pymupdf
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from .ocr_engine import OCREngine
from .legal_formatter import LegalFormatter


class DocumentExtractor:
    """
    Orchestrates extraction across digital PDFs, scanned PDFs, images, and text.
    """

    MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB
    MAX_PDF_PAGES = 50                # Page cap
    MAX_SCANNED_PAGES_TO_OCR = 20     # Max OCR pages
    OCR_RESOLUTION_DPI = 200          # 200 DPI balance

    # Magic byte signatures
    SIGNATURES = {
        "pdf": b"%PDF-",
        "png": b"\x89PNG\r\n\x1a\n",
        "jpeg": b"\xff\xd8\xff",
        "docx": b"PK\x03\x04"
    }

    def __init__(self, ocr_engine: Optional[OCREngine] = None):
        self.ocr_engine = ocr_engine or OCREngine()

    def validate_file(self, buffer: bytes, filename: str) -> Tuple[bool, str, str]:
        """
        Validates file size, extension, and magic bytes.
        """
        if not buffer or len(buffer) == 0:
            return False, "File is empty (0 bytes).", "unknown"

        if len(buffer) > self.MAX_FILE_SIZE:
            return False, f"File size ({len(buffer)/(1024*1024):.1f} MB) exceeds maximum allowed limit of 15 MB.", "unknown"

        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if not ext:
            return False, "File has no extension.", "unknown"

        if ext == "pdf":
            if not buffer.startswith(b"%PDF-"):
                return False, "Invalid PDF: File does not start with valid PDF magic bytes (%PDF-).", "pdf"
            return True, "", "pdf"

        if ext == "png":
            if not buffer.startswith(b"\x89PNG\r\n\x1a\n"):
                return False, "Invalid PNG: File header does not match PNG signature.", "png"
            return True, "", "png"

        if ext in ("jpg", "jpeg"):
            if not buffer.startswith(b"\xff\xd8\xff"):
                return False, "Invalid JPEG: File header does not match JPEG signature.", "jpeg"
            return True, "", "jpeg"

        if ext == "docx":
            if not buffer.startswith(b"PK\x03\x04"):
                return False, "Invalid DOCX: File is not a valid OpenXML ZIP archive.", "docx"
            return True, "", "docx"

        if ext == "txt":
            return True, "", "txt"

        return False, f"Unsupported document format '.{ext}'. Supported formats: .pdf, .docx, .txt, .png, .jpg, .jpeg.", ext

    def classify_pdf_page(self, page) -> str:
        """
        Refined per-page classifier that analyzes text volume, alphanumeric density,
        and image bounding box coverage.

        Does NOT classify solely on alphanumeric count >= 60.
        Returns: 'DIGITAL_NATIVE' or 'SCANNED_IMAGE'.
        """
        page_rect = page.rect
        page_area = max(1.0, page_rect.width * page_rect.height)

        raw_text = page.get_text("text").strip()
        # Count Latin alphanumeric and Devanagari Unicode characters (U+0900 to U+097F)
        alpha_count = len(re.findall(r"[a-zA-Z0-9\u0900-\u097F]", raw_text))

        image_list = page.get_images(full=True)
        has_images = len(image_list) > 0

        # Calculate total image bounding box area on page
        total_img_area = 0.0
        if has_images:
            for img_info in image_list:
                xref = img_info[0]
                try:
                    rects = page.get_image_rects(xref)
                    for r in rects:
                        total_img_area += (r.width * r.height)
                except Exception:
                    pass

        image_coverage_ratio = min(1.0, total_img_area / page_area)

        # 1. Zero alphanumeric characters -> definitely scanned image
        if alpha_count == 0:
            return "SCANNED_IMAGE"

        # 2. High image coverage (> 50%) with low/moderate text (< 300 alpha chars)
        #    Represents a full page scan containing watermarks, page numbers, or stamps
        if image_coverage_ratio > 0.50 and alpha_count < 300:
            return "SCANNED_IMAGE"

        # 3. Substantial legal text block (>= 300 alpha chars) -> digital page
        if alpha_count >= 300:
            return "DIGITAL_NATIVE"

        # 4. No images on page -> digital page (handles sparse title/endorsement pages)
        if not has_images:
            return "DIGITAL_NATIVE"

        # 5. Modest text (>= 60 chars) with small logo/seal (<= 25% area) -> digital page
        if alpha_count >= 60 and image_coverage_ratio <= 0.25:
            return "DIGITAL_NATIVE"

        # 6. Fallback (low text with image present) -> scanned image
        return "SCANNED_IMAGE"

    def extract_document(self, buffer: bytes, filename: str) -> Dict[str, Any]:
        """
        Primary entry point. Ingests raw bytes and extracts structured page-wise content.
        """
        is_valid, err_msg, doc_type = self.validate_file(buffer, filename)
        if not is_valid:
            return {
                "success": False,
                "filename": filename,
                "documentType": doc_type,
                "extractedText": "",
                "pageCount": 0,
                "pages": [],
                "extractionMethod": "none",
                "overallStatus": "FAILED",
                "warnings": [err_msg]
            }

        if doc_type == "pdf":
            return self._extract_pdf(buffer, filename)
        elif doc_type in ("png", "jpeg"):
            return self._extract_image(buffer, filename, doc_type)
        elif doc_type == "txt":
            return self._extract_txt(buffer, filename)
        elif doc_type == "docx":
            return self._extract_docx(buffer, filename)
        else:
            return {
                "success": False,
                "filename": filename,
                "documentType": doc_type,
                "extractedText": "",
                "pageCount": 0,
                "pages": [],
                "extractionMethod": "none",
                "overallStatus": "FAILED",
                "warnings": [f"Unsupported document type: {doc_type}"]
            }

    def _extract_pdf(self, buffer: bytes, filename: str) -> Dict[str, Any]:
        """Extracts text from PDF with per-page digital vs scanned inspection."""
        if not PYMUPDF_AVAILABLE:
            return {
                "success": False,
                "filename": filename,
                "documentType": "pdf",
                "extractedText": "",
                "pageCount": 0,
                "pages": [],
                "extractionMethod": "none",
                "overallStatus": "FAILED",
                "warnings": ["PyMuPDF library is not installed on the server."]
            }

        try:
            doc = pymupdf.open(stream=buffer, filetype="pdf")
        except Exception as e:
            return {
                "success": False,
                "filename": filename,
                "documentType": "pdf",
                "extractedText": "",
                "pageCount": 0,
                "pages": [],
                "extractionMethod": "none",
                "overallStatus": "FAILED",
                "warnings": [f"Corrupted or invalid PDF file: {str(e)}"]
            }

        # Check for encrypted or password protected PDFs
        if doc.is_encrypted or doc.needs_pass:
            doc.close()
            return {
                "success": False,
                "filename": filename,
                "documentType": "pdf",
                "extractedText": "",
                "pageCount": 0,
                "pages": [],
                "extractionMethod": "none",
                "overallStatus": "FAILED",
                "warnings": ["The uploaded PDF is password-protected. Please remove password encryption and re-upload."]
            }

        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            return {
                "success": False,
                "filename": filename,
                "documentType": "pdf",
                "extractedText": "",
                "pageCount": 0,
                "pages": [],
                "extractionMethod": "none",
                "overallStatus": "FAILED",
                "warnings": ["The uploaded PDF contains 0 pages."]
            }

        global_warnings: List[str] = []
        pages_to_process = total_pages
        if total_pages > self.MAX_PDF_PAGES:
            pages_to_process = self.MAX_PDF_PAGES
            global_warnings.append(
                f"Document contains {total_pages} pages, which exceeds the limit of {self.MAX_PDF_PAGES}. Processing capped at first {self.MAX_PDF_PAGES} pages."
            )

        extracted_pages: List[Dict[str, Any]] = []
        scanned_count = 0
        native_count = 0
        unprocessed_count = 0
        low_conf_count = 0

        for i in range(pages_to_process):
            page_num = i + 1
            page = doc[i]
            page_classification = self.classify_pdf_page(page)

            if page_classification == "DIGITAL_NATIVE":
                native_count += 1
                raw_text = page.get_text("text")
                clean_text = LegalFormatter.clean_page_text(raw_text, page_num, total_pages)
                extracted_pages.append({
                    "pageNumber": page_num,
                    "text": clean_text,
                    "extractionMethod": "native",
                    "scriptType": "digital",
                    "handwrittenDetected": False,
                    "uncertainTokens": [],
                    "status": "SUCCESS",
                    "confidence": 1.0,
                    "warnings": []
                })
            else:
                # SCANNED_IMAGE page
                scanned_count += 1
                if scanned_count > self.MAX_SCANNED_PAGES_TO_OCR:
                    extracted_pages.append({
                        "pageNumber": page_num,
                        "text": "",
                        "extractionMethod": "ocr",
                        "scriptType": "unknown",
                        "handwrittenDetected": False,
                        "uncertainTokens": [],
                        "status": "SCANNED_UNPROCESSED",
                        "confidence": None,
                        "warnings": [
                            f"Page exceeded maximum scanned OCR limit of {self.MAX_SCANNED_PAGES_TO_OCR} pages."
                        ]
                    })
                    unprocessed_count += 1
                    continue

                if not self.ocr_engine.is_available:
                    extracted_pages.append({
                        "pageNumber": page_num,
                        "text": "",
                        "extractionMethod": "ocr",
                        "scriptType": "unknown",
                        "handwrittenDetected": False,
                        "uncertainTokens": [],
                        "status": "SCANNED_UNPROCESSED",
                        "confidence": None,
                        "warnings": [
                            "Tesseract OCR system binary is not available. Scanned content was not extracted."
                        ]
                    })
                    unprocessed_count += 1
                    continue

                # Render page to 200 DPI pixmap
                try:
                    pix = page.get_pixmap(dpi=self.OCR_RESOLUTION_DPI)
                    pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    ocr_res = self.ocr_engine.process_image(pil_img)

                    clean_ocr_text = LegalFormatter.clean_page_text(ocr_res["text"], page_num, total_pages)
                    if ocr_res["status"] == "LOW_CONFIDENCE_OCR":
                        low_conf_count += 1
                    elif ocr_res["status"] == "SCANNED_UNPROCESSED":
                        unprocessed_count += 1

                    extracted_pages.append({
                        "pageNumber": page_num,
                        "text": clean_ocr_text,
                        "extractionMethod": "ocr",
                        "scriptType": ocr_res.get("scriptType", "printed"),
                        "handwrittenDetected": ocr_res.get("handwrittenDetected", False),
                        "uncertainTokens": ocr_res.get("uncertainTokens", []),
                        "status": ocr_res["status"],
                        "confidence": ocr_res["confidence"],
                        "warnings": ocr_res["warnings"]
                    })
                except Exception as e:
                    unprocessed_count += 1
                    extracted_pages.append({
                        "pageNumber": page_num,
                        "text": "",
                        "extractionMethod": "ocr",
                        "scriptType": "unknown",
                        "handwrittenDetected": False,
                        "uncertainTokens": [],
                        "status": "FAILED",
                        "confidence": None,
                        "warnings": [f"Page rasterization or OCR failed: {str(e)}"]
                    })

        doc.close()

        # Determine composite extraction method
        if native_count > 0 and scanned_count > 0:
            extraction_method = "hybrid"
        elif native_count > 0:
            extraction_method = "native"
        elif scanned_count > 0:
            extraction_method = "ocr"
        else:
            extraction_method = "none"

        # Determine composite script type and handwriting presence
        has_handwriting = any(p.get("handwrittenDetected", False) for p in extracted_pages)
        unique_scripts = {p.get("scriptType", "unknown") for p in extracted_pages}
        if "handwritten" in unique_scripts and len(unique_scripts - {"handwritten"}) == 0:
            composite_script = "handwritten"
        elif has_handwriting:
            composite_script = "mixed"
        elif "printed" in unique_scripts:
            composite_script = "printed"
        elif "digital" in unique_scripts:
            composite_script = "digital"
        else:
            composite_script = "unknown"

        # Determine overall status
        if unprocessed_count > 0 and native_count == 0:
            overall_status = "SCANNED_UNPROCESSED"
            global_warnings.append("Document consists of scanned pages and OCR engine is unavailable.")
        elif unprocessed_count > 0:
            overall_status = "SUCCESS_WITH_WARNINGS"
            global_warnings.append(f"{unprocessed_count} scanned pages could not be processed via OCR.")
        elif low_conf_count > 0:
            overall_status = "LOW_CONFIDENCE_OCR"
            global_warnings.append(f"{low_conf_count} pages had low OCR confidence.")
        elif has_handwriting:
            overall_status = "SUCCESS_WITH_WARNINGS"
        else:
            overall_status = "SUCCESS"

        if has_handwriting:
            global_warnings.append(
                "Handwritten content detected in document. Automated OCR cannot reliably transcribe unconstrained or cursive handwriting without error. Extracted text is for reference only and must be verified against original document before legal reliance."
            )

        composite_text = LegalFormatter.assemble_document(extracted_pages)

        return {
            "success": True,
            "filename": filename,
            "documentType": "pdf",
            "extractedText": composite_text,
            "pageCount": len(extracted_pages),
            "pages": extracted_pages,
            "extractionMethod": extraction_method,
            "scriptType": composite_script,
            "handwrittenDetected": has_handwriting,
            "overallStatus": overall_status,
            "warnings": global_warnings
        }

    def _extract_image(self, buffer: bytes, filename: str, doc_type: str) -> Dict[str, Any]:
        """Extracts text from standalone image file (PNG / JPEG)."""
        try:
            pil_img = Image.open(io.BytesIO(buffer))
            pil_img.load()
        except Exception as e:
            return {
                "success": False,
                "filename": filename,
                "documentType": doc_type,
                "extractedText": "",
                "pageCount": 0,
                "pages": [],
                "extractionMethod": "ocr",
                "overallStatus": "FAILED",
                "warnings": [f"Failed to open image file: {str(e)}"]
            }

        ocr_res = self.ocr_engine.process_image(pil_img)
        page_dict = {
            "pageNumber": 1,
            "text": ocr_res["text"],
            "extractionMethod": "ocr",
            "scriptType": ocr_res.get("scriptType", "printed"),
            "handwrittenDetected": ocr_res.get("handwrittenDetected", False),
            "uncertainTokens": ocr_res.get("uncertainTokens", []),
            "status": ocr_res["status"],
            "confidence": ocr_res["confidence"],
            "warnings": ocr_res["warnings"]
        }

        composite_text = LegalFormatter.assemble_document([page_dict])
        overall_status = ocr_res["status"]

        warnings = list(ocr_res["warnings"])
        if overall_status == "SCANNED_UNPROCESSED":
            warnings.append("OCR system binary is not available. Image text could not be extracted.")

        return {
            "success": True,
            "filename": filename,
            "documentType": doc_type,
            "extractedText": composite_text,
            "pageCount": 1,
            "pages": [page_dict],
            "extractionMethod": "ocr",
            "scriptType": ocr_res.get("scriptType", "printed"),
            "handwrittenDetected": ocr_res.get("handwrittenDetected", False),
            "overallStatus": overall_status,
            "warnings": warnings
        }

    def _extract_txt(self, buffer: bytes, filename: str) -> Dict[str, Any]:
        """Extracts text from plain text file."""
        try:
            text = buffer.decode("utf-8").strip()
        except UnicodeDecodeError:
            try:
                text = buffer.decode("latin-1").strip()
            except Exception as e:
                return {
                    "success": False,
                    "filename": filename,
                    "documentType": "txt",
                    "extractedText": "",
                    "pageCount": 0,
                    "pages": [],
                    "extractionMethod": "native",
                    "overallStatus": "FAILED",
                    "warnings": [f"Could not decode text file: {str(e)}"]
                }

        page_dict = {
            "pageNumber": 1,
            "text": text,
            "extractionMethod": "native",
            "scriptType": "digital",
            "handwrittenDetected": False,
            "uncertainTokens": [],
            "status": "SUCCESS",
            "confidence": 1.0,
            "warnings": []
        }

        return {
            "success": True,
            "filename": filename,
            "documentType": "txt",
            "extractedText": LegalFormatter.assemble_document([page_dict]),
            "pageCount": 1,
            "pages": [page_dict],
            "extractionMethod": "native",
            "scriptType": "digital",
            "handwrittenDetected": False,
            "overallStatus": "SUCCESS",
            "warnings": []
        }

    def _extract_docx(self, buffer: bytes, filename: str) -> Dict[str, Any]:
        """
        Extracts text from DOCX. If python-docx is not installed, signals caller
        to use Express Mammoth engine.
        """
        return {
            "success": True,
            "filename": filename,
            "documentType": "docx",
            "extractedText": "",
            "pageCount": 1,
            "pages": [],
            "extractionMethod": "native",
            "overallStatus": "DELEGATE_TO_BACKEND",
            "warnings": ["DOCX processing delegated to backend Mammoth extraction engine."]
        }

