"""
Jurist AI — Legal Document Formatter & Structural Preserver
Preserves page boundaries, numbered paragraphs, statutory citations,
and court case references while filtering repetitive header/footer noise.
"""

import re
from typing import List, Dict, Any, Optional


class LegalFormatter:
    """
    Formats extracted document text with legal structure preservation.
    """

    # Common Indian court running header patterns
    RUNNING_HEADER_PATTERNS = [
        re.compile(r"^\s*IN\s+THE\s+SUPREME\s+COURT\s+OF\s+INDIA\s*$", re.IGNORECASE),
        re.compile(r"^\s*RECORD\s+OF\s+PROCEEDINGS\s*$", re.IGNORECASE),
        re.compile(r"^\s*COURT\s+NO\.\s*\d+\s*$", re.IGNORECASE),
        re.compile(r"^\s*SECTION\s+[IVXLCDM]+[-A-Z0-9]*\s*$", re.IGNORECASE),
        re.compile(r"^\s*Page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE),
        re.compile(r"^\s*WWW\.LIVELAW\.IN\s*$", re.IGNORECASE),
        re.compile(r"^\s*INDIAN\s+KANOON\s+-\s+HTTP://INDIANKANOON\.ORG/DOC/\d+/?\s*$", re.IGNORECASE),
    ]

    # Paragraph and section numbering regexes
    NUMBERED_PARAGRAPH_PATTERN = re.compile(
        r"^(?:\d{1,3}\.|\(\d{1,3}\)|\([a-zA-Z]\)|\([ivxIVX]+\)|\[\d{1,3}\]|(?:Para|Paragraph|Point)\s+\d{1,3}[:.]?)\s+",
        re.MULTILINE
    )

    # Statutory citation protection
    STATUTORY_CITATION_PATTERN = re.compile(
        r"\b(?:Section|Sec\.|Article|Art\.|Order|Rule|Clause)\s+\d+[A-Z]*(?:\([a-zA-Z0-9]+\))*",
        re.IGNORECASE
    )

    @classmethod
    def clean_page_text(cls, text: str, page_number: int, total_pages: int) -> str:
        """
        Cleans page text by normalizing linebreaks, stripping standalone page numbers,
        and preserving paragraph structure.
        """
        if not text:
            return ""

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Split into lines
        lines = [line.strip() for line in text.split("\n")]
        cleaned_lines: List[str] = []

        for idx, line in enumerate(lines):
            if not line:
                # Retain empty lines as paragraph dividers
                if cleaned_lines and cleaned_lines[-1] != "":
                    cleaned_lines.append("")
                continue

            # Strip isolated running page numbers like "12", "Page 12", "- 12 -"
            if re.match(r"^(?:Page\s+)?[-–—]?\s*\d+\s*[-–—]?$", line, re.IGNORECASE):
                continue

            # Suppress obvious repeating running headers on subsequent pages (page > 1)
            if page_number > 1 and idx < 3:
                is_header = any(pat.match(line) for pat in cls.RUNNING_HEADER_PATTERNS)
                if is_header:
                    continue

            cleaned_lines.append(line)

        # Recombine and clean excessive whitespace
        result = "\n".join(cleaned_lines)
        result = re.sub(r"\n{3,}", "\n\n", result).strip()
        return result

    @classmethod
    def assemble_document(cls, pages: List[Dict[str, Any]]) -> str:
        """
        Assembles page blocks into a single structured text document with explicit
        page boundary delimiters, script nature labels, and evidentiary notices.
        """
        if not pages:
            return ""

        formatted_blocks: List[str] = []
        for page in pages:
            page_num = page.get("pageNumber", 1)
            method = page.get("extractionMethod", "native")
            status = page.get("status", "SUCCESS")
            conf = page.get("confidence")
            script_type = page.get("scriptType", "printed" if method == "ocr" else "digital")
            is_handwritten = page.get("handwrittenDetected", False) or script_type in ("handwritten", "mixed")
            text = page.get("text", "").strip()

            if method == "native":
                method_tag = "Native Digital"
            else:
                script_label = "Handwritten" if is_handwritten else "Printed"
                method_tag = f"OCR - {script_label}"

            if conf is not None:
                method_tag += f" - {int(conf * 100)}% Conf."

            evidentiary_prefix = ""
            if is_handwritten:
                evidentiary_prefix = (
                    f"[EVIDENTIARY NOTICE: Handwritten manuscript detected on Page {page_num}. "
                    "Automated OCR cannot reliably transcribe unconstrained or cursive handwriting without error. "
                    "Flagged tokens [?token?] and unverified text must be checked against the original document before legal reliance.]\n\n"
                )

            if status == "SCANNED_UNPROCESSED":
                block_header = f"[--- PAGE {page_num} ({method_tag} - UNPROCESSED) ---]"
                content = "[SCANNED PAGE: OCR unavailable on server. Text not extracted.]"
            elif status == "LOW_CONFIDENCE_OCR":
                block_header = f"[--- PAGE {page_num} ({method_tag} - LOW CONFIDENCE) ---]"
                content = evidentiary_prefix + (text if text else "[Low confidence extraction yielded no usable words]")
            else:
                block_header = f"[--- PAGE {page_num} ({method_tag}) ---]"
                content = evidentiary_prefix + text

            formatted_blocks.append(f"{block_header}\n\n{content}")

        return "\n\n".join(formatted_blocks).strip()

    @classmethod
    def annotate_uncertain_tokens(cls, tokens_with_conf: List[tuple]) -> str:
        """
        Joins tokens, annotating tokens whose OCR confidence is below threshold.
        tokens_with_conf: list of (token_text, confidence_float_0_to_100)
        """
        words: List[str] = []
        for text, conf in tokens_with_conf:
            clean_word = text.strip()
            if not clean_word:
                continue
            if 0 < conf < 40:
                words.append(f"[?{clean_word}?]")
            else:
                words.append(clean_word)
        return " ".join(words)
