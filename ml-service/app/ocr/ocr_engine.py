"""
Jurist AI — OCR Engine & Image Preprocessing Subsystem
Integrates Pillow for image conditioning and pytesseract for OCR extraction,
calculating word-level confidence and tagging uncertain legal tokens.
Includes script-nature classification (printed vs. handwritten) and epistemic
safeguards to prevent inaccurate handwriting recognition from posing as verified legal evidence.
"""

import os
import re
import shutil
import sys
from typing import Dict, Any, Optional, List, Tuple
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np

try:
    import pytesseract
    PYTESSERACT_INSTALLED = True
except ImportError:
    PYTESSERACT_INSTALLED = False


# Comprehensive legal and standard English lexicon for epistemic validation
BASE_VOCABULARY = {
    "the", "of", "and", "in", "to", "a", "is", "that", "for", "it", "as", "was", "with",
    "be", "by", "on", "not", "he", "at", "this", "from", "had", "his", "which", "or",
    "an", "they", "were", "their", "are", "have", "has", "been", "one", "all", "would",
    "there", "her", "him", "my", "no", "if", "out", "so", "said", "what", "up", "its",
    "about", "into", "than", "them", "can", "only", "other", "new", "some", "could",
    "time", "these", "two", "may", "then", "do", "first", "any", "like", "now", "such",
    "our", "over", "even", "most", "me", "after", "also", "made", "before", "must",
    "well", "back", "where", "much", "your", "way", "down", "should", "because", "each",
    "just", "state", "those", "people", "mr", "mrs", "ms", "how", "too", "little", "good",
    "very", "make", "world", "still", "own", "see", "men", "work", "long", "get", "here",
    "between", "both", "life", "being", "under", "never", "day", "days", "same", "another",
    "know", "while", "last", "might", "great", "off", "come", "since", "against", "go",
    "came", "right", "used", "take", "three", "himself", "few", "more", "without", "again",
    "case", "part", "number", "place", "found", "order", "shall", "may", "upon", "such",
    "date", "year", "month", "signed", "copy", "true", "name", "address", "age", "years"
}

INDIAN_LEGAL_VOCABULARY = {
    "court", "high", "supreme", "district", "sessions", "magistrate", "tribunal", "bench",
    "jurisdiction", "appellate", "original", "writ", "petition", "petitioner", "respondent",
    "appellant", "applicant", "accused", "complainant", "prosecution", "state", "police",
    "station", "fir", "first", "information", "report", "crime", "cognizable", "non-cognizable",
    "offence", "offences", "investigation", "investigating", "officer", "arrest", "arrested",
    "remand", "remanded", "custody", "judicial", "bail", "anticipatory", "regular", "interim",
    "grounds", "notice", "statutory", "compliance", "section", "article", "order", "rule",
    "crpc", "ipc", "bnss", "bns", "bsa", "act", "code", "procedure", "penal", "evidence",
    "constitution", "fundamental", "rights", "liberty", "personal", "judgment", "decree",
    "quash", "quashing", "charge", "chargesheet", "witness", "testimony", "affidavit",
    "record", "proceedings", "judicature", "bombay", "delhi", "madras", "calcutta", "allahabad",
    "memo", "diary", "panchnama", "seizure", "medical", "injury", "certificate", "hospital",
    "reasons", "recorded", "writing", "satisfaction", "necessity", "safeguard", "guidelines",
    "directions", "application", "pursuant", "herein", "therein", "thereof", "aforesaid",
    "allegations", "prima", "facie", "substantive", "procedural", "limitation", "appeal",
    "dismissed", "allowed", "disposed", "pending", "matter", "cause", "title", "versus", "vs",
    "crl", "misc", "special", "leave", "slp", "civil", "criminal", "advocate", "counsel",
    "learned", "hon'ble", "honourable", "justice", "coram", "sub-inspector", "constable"
}

LEGAL_AND_ENGLISH_LEXICON = {w.lower() for w in BASE_VOCABULARY | INDIAN_LEGAL_VOCABULARY}


class OCREngine:
    """
    Tesseract OCR engine wrapper with image preprocessing, script nature classification,
    and confidence scoring with epistemic uncertainty tagging.
    """

    MAX_DIMENSION = 2500
    Image.MAX_IMAGE_PIXELS = 40_000_000  # Decompression bomb guard

    # Epistemic thresholds
    PRINTED_UNCERTAINTY_THRESHOLD = 40.0       # < 40% confidence in print -> [?word?]
    HANDWRITTEN_UNCERTAINTY_THRESHOLD = 60.0   # < 60% confidence in handwriting -> [?word?]
    HANDWRITTEN_LEXICON_THRESHOLD = 85.0       # < 85% confidence for non-lexical words in handwriting -> [?word?]

    KNOWN_WINDOWS_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]

    def __init__(self):
        self._tesseract_path: Optional[str] = None
        self._version: Optional[str] = None
        self._available = False
        self._available_langs: List[str] = []
        self._detect_tesseract()

    def _detect_tesseract(self):
        """Detects whether Tesseract binary is accessible on the host."""
        if not PYTESSERACT_INSTALLED:
            self._available = False
            return

        # 1. Check custom environment variable
        env_cmd = os.environ.get("TESSERACT_CMD")
        if env_cmd and os.path.exists(env_cmd):
            self._tesseract_path = env_cmd

        # 2. Check standard system PATH
        if not self._tesseract_path:
            which_path = shutil.which("tesseract")
            if which_path:
                self._tesseract_path = which_path

        # 3. Check known Windows installations
        if not self._tesseract_path and sys.platform == "win32":
            for path in self.KNOWN_WINDOWS_PATHS:
                if os.path.exists(path):
                    self._tesseract_path = path
                    break

        if self._tesseract_path:
            try:
                pytesseract.pytesseract.tesseract_cmd = self._tesseract_path
                self._version = str(pytesseract.get_tesseract_version())
                self._available = True
                try:
                    self._available_langs = pytesseract.get_languages()
                except Exception:
                    self._available_langs = ["eng"]
            except Exception:
                self._available = False
        else:
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    @property
    def tesseract_version(self) -> Optional[str]:
        return self._version

    @property
    def tesseract_path(self) -> Optional[str]:
        return self._tesseract_path

    @property
    def availability_status(self) -> str:
        if self._available:
            return f"available (Tesseract v{self._version} at {self._tesseract_path})"
        if not PYTESSERACT_INSTALLED:
            return "unavailable (pytesseract package not installed)"
        return "unavailable (Tesseract system binary not found in PATH or standard directories)"

    @classmethod
    def is_known_token(cls, token: str) -> bool:
        """Checks if a token is in the legal/standard lexicon, is numeric, is Devanagari, or is a statutory section."""
        clean = re.sub(r"[^\w\u0900-\u097F]", "", token).lower()
        if not clean:
            return True
        if clean.isdigit():
            return True
        # Devanagari script token (Hindi legal vocabulary)
        if re.search(r"[\u0900-\u097F]", clean):
            return True
        # Statutory notation like "35(1)", "41a", "498a", "138", "154"
        if re.match(r"^\d+[a-z]*$", clean):
            return True
        return clean in LEGAL_AND_ENGLISH_LEXICON

    def analyze_script_type(
        self, img: Image.Image, tokens_with_conf: List[Tuple[str, float]]
    ) -> Tuple[str, bool, Dict[str, Any]]:
        """
        Classifies script nature as 'printed', 'handwritten', or 'mixed'.
        Combines edge orientation distribution with OCR confidence variance and lexicon hit rate.
        """
        # 1. Edge gradient orientation
        try:
            gray = np.array(img.convert("L"), dtype=np.float32)
            gx = np.diff(gray, axis=1)[:-1, :]
            gy = np.diff(gray, axis=0)[:, :-1]
            mag = np.sqrt(gx**2 + gy**2)
            edge_mask = mag > 30.0

            if np.sum(edge_mask) > 100:
                angles_deg = np.rad2deg(np.arctan2(gy[edge_mask], gx[edge_mask])) % 180
                hist, _ = np.histogram(angles_deg, bins=18, range=(0, 180), density=True)
                # Rectilinear fraction (+- 15 deg of vertical 0/180 and horizontal 90)
                rectilinear_fraction = float(np.sum(hist[[0, 1, 8, 9, 10, 17]]) * 10)
            else:
                rectilinear_fraction = 1.0
        except Exception:
            rectilinear_fraction = 0.65

        # 2. OCR token metrics
        confs = [c for _, c in tokens_with_conf if c >= 0]
        avg_conf = (sum(confs) / len(confs)) if confs else 0.0
        std_conf = float(np.std(confs)) if confs else 0.0

        known_count = sum(1 for w, _ in tokens_with_conf if self.is_known_token(w))
        total_tokens = len(tokens_with_conf)
        lexicon_ratio = (known_count / total_tokens) if total_tokens > 0 else 1.0

        # Classify script nature
        # High-confidence printed typography exhibits rock-solid uniform confidence (std <= 6%),
        # high average confidence (>= 88%), and high dictionary coherence.
        is_strong_print = (
            std_conf <= 6.0 and
            avg_conf >= 88.0 and
            lexicon_ratio >= 0.85
        )

        hw_signals = 0
        if rectilinear_fraction < 0.62:
            hw_signals += 1
        if std_conf > 12.0:
            hw_signals += 1
        if lexicon_ratio < 0.85:
            hw_signals += 1

        if is_strong_print:
            script_type = "printed"
            is_handwritten = False
        elif hw_signals >= 2:
            script_type = "handwritten"
            is_handwritten = True
        elif hw_signals == 1 and rectilinear_fraction < 0.58:
            script_type = "handwritten"
            is_handwritten = True
        elif hw_signals == 1 and std_conf > 10.0:
            script_type = "mixed"
            is_handwritten = True
        else:
            script_type = "printed"
            is_handwritten = False

        stats = {
            "rectilinearFraction": round(rectilinear_fraction, 3),
            "confidenceMean": round(avg_conf, 2),
            "confidenceStd": round(std_conf, 2),
            "lexiconRatio": round(lexicon_ratio, 3),
            "totalTokens": total_tokens
        }

        return script_type, is_handwritten, stats

    def preprocess_image(self, img: Image.Image, script_type: str = "printed") -> Image.Image:
        """
        Conditions image for optimal OCR extraction:
        - Downscales if exceeding MAX_DIMENSION
        - Converts to Grayscale
        - Printed: contrast enhancement (1.8x) + mild sharpening
        - Handwritten/Mixed: median speckle suppression + higher contrast enhancement (2.0x)
        """
        # Guard against oversized bitmaps
        w, h = img.size
        if max(w, h) > self.MAX_DIMENSION:
            scale = self.MAX_DIMENSION / max(w, h)
            new_w, new_h = int(w * scale), int(h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Convert to Grayscale
        if img.mode != "L":
            img = img.convert("L")

        if script_type in ("handwritten", "mixed"):
            # Median filter to clean paper grain and carbon bleed without breaking continuous strokes
            img = img.filter(ImageFilter.MedianFilter(size=3))
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2.0)
            img = img.filter(ImageFilter.SHARPEN)
        else:
            # Standard contrast enhancement for printed typography
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.8)
            img = img.filter(ImageFilter.SHARPEN)

        return img

    def _run_tesseract(self, img: Image.Image, psm: int = 3) -> List[Tuple[str, float]]:
        """Helper to run Tesseract data extraction with given PSM mode and bilingual Hindi-English support."""
        lang = "eng+hin" if "hin" in getattr(self, "_available_langs", []) else "eng"
        data = pytesseract.image_to_data(
            img,
            output_type=pytesseract.Output.DICT,
            lang=lang,
            config=f"--oem 3 --psm {psm}"
        )
        texts = data.get("text", [])
        confs = data.get("conf", [])

        tokens_with_conf: List[Tuple[str, float]] = []
        for word, conf in zip(texts, confs):
            clean_word = word.strip()
            if not clean_word:
                continue
            try:
                conf_float = float(conf)
            except (ValueError, TypeError):
                conf_float = -1.0

            if conf_float >= 0:
                tokens_with_conf.append((clean_word, conf_float))
            else:
                tokens_with_conf.append((clean_word, 50.0))

        return tokens_with_conf

    def process_image(self, img: Image.Image) -> Dict[str, Any]:
        """
        Executes OCR on an image with script detection and epistemic uncertainty tagging.
        """
        if not self.is_available:
            return {
                "text": "",
                "confidence": None,
                "status": "SCANNED_UNPROCESSED",
                "extractionMethod": "ocr",
                "scriptType": "unknown",
                "handwrittenDetected": False,
                "uncertainTokens": [],
                "warnings": [
                    "Tesseract OCR system binary is not installed on the server. Scanned content was not extracted."
                ]
            }

        try:
            # 1. Initial pass with standard conditioning
            initial_img = self.preprocess_image(img, script_type="printed")
            tokens_with_conf = self._run_tesseract(initial_img, psm=3)

            if not tokens_with_conf:
                # Try PSM 6 for sparse single-block pages
                tokens_with_conf = self._run_tesseract(initial_img, psm=6)

            if not tokens_with_conf:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "status": "LOW_CONFIDENCE_OCR",
                    "extractionMethod": "ocr",
                    "scriptType": "unknown",
                    "handwrittenDetected": False,
                    "uncertainTokens": [],
                    "warnings": ["OCR engine detected no readable text on page."]
                }

            # 2. Analyze script nature (printed vs handwritten vs mixed)
            script_type, is_handwritten, stats = self.analyze_script_type(img, tokens_with_conf)

            # 3. If handwriting detected, perform specialized reconditioning and dual-mode PSM comparison
            if is_handwritten:
                hw_img = self.preprocess_image(img, script_type=script_type)
                hw_tokens_psm6 = self._run_tesseract(hw_img, psm=6)
                hw_tokens_psm3 = self._run_tesseract(hw_img, psm=3)

                # Pick candidate with higher valid token count & coherent confidence
                def score_candidate(cand_tokens):
                    if not cand_tokens:
                        return -1.0
                    known = sum(1 for w, _ in cand_tokens if self.is_known_token(w))
                    c_sum = sum(c for _, c in cand_tokens if c >= 0)
                    return known * 1000.0 + c_sum

                if score_candidate(hw_tokens_psm6) >= score_candidate(hw_tokens_psm3):
                    tokens_with_conf = hw_tokens_psm6 or tokens_with_conf
                else:
                    tokens_with_conf = hw_tokens_psm3 or tokens_with_conf

            # 4. Calculate average confidence
            valid_confs = [c for _, c in tokens_with_conf if c >= 0]
            avg_conf = (sum(valid_confs) / len(valid_confs) / 100.0) if valid_confs else 0.0

            # 5. Epistemic uncertainty flagging
            # Never silently treat inaccurate OCR output as verified legal evidence!
            annotated_words: List[str] = []
            uncertain_tokens: List[str] = []

            for word, c in tokens_with_conf:
                is_uncertain = False

                if is_handwritten:
                    # In handwriting, Tesseract over-confidently assigns 50-75% to garbled syllables
                    known = self.is_known_token(word)
                    if c < self.HANDWRITTEN_UNCERTAINTY_THRESHOLD:
                        is_uncertain = True
                    elif not known and c < self.HANDWRITTEN_LEXICON_THRESHOLD:
                        is_uncertain = True
                else:
                    # Printed text uncertainty threshold
                    if c < self.PRINTED_UNCERTAINTY_THRESHOLD:
                        is_uncertain = True

                if is_uncertain:
                    annotated_words.append(f"[?{word}?]")
                    uncertain_tokens.append(word)
                else:
                    annotated_words.append(word)

            page_text = " ".join(annotated_words)

            warnings: List[str] = []

            # 6. Status assignment and evidentiary warnings
            if is_handwritten:
                warnings.append(
                    f"Handwritten content detected on page ({script_type} script). "
                    "Automated handwriting recognition is inherently imperfect and legally unverified. "
                    "Do not rely on transcribed dates, names, or penal sections without inspecting the original manuscript."
                )
                if uncertain_tokens:
                    warnings.append(
                        f"Page contains {len(uncertain_tokens)} uncertain or unreadable token(s) flagged with [?...?]."
                    )
                if avg_conf < 0.65 or len(uncertain_tokens) > (len(tokens_with_conf) * 0.25):
                    status = "LOW_CONFIDENCE_OCR"
                else:
                    status = "SUCCESS_WITH_WARNINGS"
            else:
                if avg_conf < 0.45:
                    status = "LOW_CONFIDENCE_OCR"
                    warnings.append(
                        f"Low confidence OCR extraction ({int(avg_conf * 100)}% average confidence). Text may contain errors."
                    )
                elif uncertain_tokens:
                    status = "SUCCESS_WITH_WARNINGS"
                    warnings.append(
                        f"Page contains {len(uncertain_tokens)} uncertain token(s) flagged with [?...?]."
                    )
                else:
                    status = "SUCCESS"

            return {
                "text": page_text,
                "confidence": round(avg_conf, 4),
                "status": status,
                "extractionMethod": "ocr",
                "scriptType": script_type,
                "handwrittenDetected": is_handwritten,
                "uncertainTokens": uncertain_tokens,
                "warnings": warnings
            }

        except Exception as e:
            return {
                "text": "",
                "confidence": None,
                "status": "FAILED",
                "extractionMethod": "ocr",
                "scriptType": "unknown",
                "handwrittenDetected": False,
                "uncertainTokens": [],
                "warnings": [f"OCR execution failed on page: {str(e)}"]
            }
