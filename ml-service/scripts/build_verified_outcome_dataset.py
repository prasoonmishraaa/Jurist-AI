"""
Verified Outcome Dataset Builder & Target Leakage Prevention Engine
JURIST AI — Feature 4.4: Supervised Legal Outcome Prediction Pipeline

Builds a reproducible, leakage-safe training dataset from human-approved judicial outcome annotations.
Enforces strict ML safety principles:
1. Approved-Only Gatekeeper: Only records with review_status == 'approved' can enter training datasets.
2. Target Leakage Prevention: Strips operative orders, concluding holdings, outcome fields, and disposition phrases.
3. Case-Level Lineage & Grouping: Preserves case IDs and maps related proceedings to prevent split leakage.
4. Data Integrity: Never fabricates missing labels or auto-approves provisional candidates.
"""

import os
import sys
import re
import json
import csv
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import Counter

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VerifiedOutcomeDatasetBuilder")

# Feature 4.14: Dual-Model Training Gatekeeper Eligibility Sets
MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS = {
    "appeal_allowed",
    "appeal_dismissed",
    "petition_allowed",
    "petition_dismissed",
}

MODEL_A_EXCLUDED_PROCEDURAL_DISPOSITIONS = {
    "remanded",
    "dismissed_as_infructuous",
    "uncertain",
    "withdrawn",
    "partly_allowed",
    "disposed_procedural",
    "disposed_with_substantive_directions",
    "other",
    "unknown",
}

MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES = {
    "respondent",
    "petitioner",
    "state_prosecution",
    "accused",
}

MODEL_B_EXCLUDED_NON_SUBSTANTIVE_PARTIES = {
    "none_procedural",
    "unresolved",
    "unknown",
}


class InsufficientApprovedLabelsError(ValueError):
    """Raised when there are insufficient human-approved labels to train a statistical model."""
    pass


class TargetLeakageSanitizer:
    """
    Identifies and removes outcome-bearing, post-decision, and operative disposition text
    from judicial opinion records to prevent feature leakage.
    Feature 4.18: Enforces a conservative, trigger-aware tail-truncation safety envelope.
    """

    SANITIZER_VERSION = "v4.18.0-safety-envelope"

    # Headings indicating the start of the court's final operative order
    OPERATIVE_HEADINGS = [
        # Explicit formal headings
        r"(?:^|\n)\s*(?:O\s*R\s*D\s*E\s*R|OPERATIVE\s+ORDER|FINAL\s+ORDER|ORDER\s+OF\s+THE\s+COURT)\s*(?::|-|\n)",
        r"(?:^|\n)\s*(?:CONCLUSION|D\s*I\s*S\s*P\s*O\s*S\s*I\s*T\s*I\s*O\s*N)\s*(?::|-|\n)",
        r"(?:^|\n)\s*(?:IN\s+THE\s+RESULT|RESULT\s+OF\s+THE\s+APPEAL|RESULT)\s*(?::|-|\n)",
        r"(?:^|\n)\s*(?:PER\s+CURIAM|BY\s+THE\s+COURT)\s*(?::|-|\n)",
        r"(?:^|\n)\s*(?:DECISION|FINDINGS?\s+AND\s+ORDER|FINAL\s+DIRECTIONS?)\s*(?::|-|\n)",
        # Web scraper Kanoon section headers
        r"(?:^|\n)\s*\[SECTION\]\s*##\s*(?:Appeal|Petition|Order|Judgment|Holding|Conclusion|Disposition)",
    ]

    # Concluding operative holding introductory clauses (in final 40% of judgment text)
    # Marks where the bench begins its final operative decree in older/unheaded judgments
    CONCLUDING_OPERATIVE_TRANSITIONS = [
        # 1. Main judicial operative decretal transitions (handling plural forms, OCR concatenations, Resultantly/Thus/Hence, above/foregoing/aforementioned reasons)
        r"(?:\n\s*(?:[0-9]{1,3}\.|\([0-9]{1,3}\))\s*)?(?:For\s+(?:the\s+)?(?:foregoing|aforementioned|above|aforesaid|stated\s+above)?\s*reasons|For\s+(?:the\s+)?reasons\s+(?:stated\s+|mentioned\s+)?above|In\s+these\s+circumstances|In\s+(?:the\s+)?result|Resultantly|Thus|Hence|Looked\s+at\s+from\s+any\s+angle|In\s+view\s+of\s+the\s+above(?:\s+reasoning|\s+discussion)?|As\s+a\s+result\s+of\s+the\s+foregoing|On\s+the\s+basis\s+of\s+(?:the\s+)?(?:foregoing|above)\s+(?:discussions?|reasons?)|Since\s+the\s+application\s+for\s+leave\s+to\s*(?:appeal|toappeal)|Consequently|Accordingly)[,\s]+(?:we\s+(?:find|are\s+of\s+the\s+opinion|hold|do\s+not\s+differ|dismiss|allow|set\s+aside|remit|quash|direct)|(?:the\s+|this\s+|these\s+)?appeals?(?:\s+filed\s+by\s+[^\n,]+)?\s+(?:is|are|fails?|succeeds?|stands?|allowed|sans\s+merit)|the\s+impugned\s+(?:[A-Za-z]+\s+)?(?:judgment|order)|this\s+appeal|these\s+appeals|(?:the\s+|this\s+|these\s+)?(?:writ\s+)?petitions?\s+(?:is|are|fails?|fail\s+and\s+are|succeeds?|stands?|deserves?\s+to\s+be\s+allowed|is\s+dismissed|are\s+dismissed)|(?:the\s+|this\s+)?application\s+for\s+leave\s+to\s*(?:appeal|toappeal)\s+lacks\s+merit|FIR\s+(?:No\.?)?[0-9/]+|(?:the\s+)?order\s+of\s+CEGAT)\b",

        # 2. Decretal outcome anticipation transitions (e.g. Atul Shukla, Inder Jeet Singh)
        r"(?:\n\s*(?:[0-9]{1,3}\.|\([0-9]{1,3}\))\s*|\.\s+)?(?:On\s+this\s+ground\s+alone[,\s]*|Accordingly[,\s]*|Consequently[,\s]*|In\s+view\s+of\s+the\s+above[,\s]*)(?:keeping\s+in\s+view\s+the\s+proposition\s+of\s+law[^\n]*?)?(?:the\s+|this\s+|these\s+)?(?:writ\s+)?petitions?\s+(?:also\s+)?(?:deserves?|(?:is|are)\s+liable)\s+to\s+be\s+(?:allowed|dismissed)\b",

        # 3. Leave to appeal rejection + consequential appeal dismissal (e.g. Santosh Kumar)
        r"(?:\n\s*(?:[0-9]{1,3}\.|\([0-9]{1,3}\))\s*)?(?:Since\s+the\s+application\s+for\s+leave\s+to\s*(?:appeal|toappeal)\s+has\s+been\s+rejected|application\s+for\s+leave\s+to\s*(?:appeal|toappeal)\s+lacks\s+merit)[^\n]*?(?:appeal(?:also)?\s+does\s+not\s+survive|appeal\s+stands\s+dismissed)\b",

        # 4. Direct numbered or unnumbered final operative holding (e.g. Pegasus Assets, Atul Shukla, Santosh Kumar)
        r"(?:\n\s*(?:[0-9]{1,3}\.|\([0-9]{1,3}\))\s*|\n\n|\n\s*)(?:The\s+|This\s+|These\s+)?(?:writ\s+)?petitions?\s+(?:is|are|lacks\s+merit\s+and\s+is|fails\s+and\s+is|consequently\s+fails\s+and\s+is|stands?)[,\s]*(?:hereby|therefore|accordingly|consequently)?[,\s]*(?:allowed|dismissed|disposed\s+of)\b",

        # 5. Direct paragraph final operative holding (e.g. Orix Auto: The appeal is allowed to the aforesaid extent)
        r"(?:\n\s*(?:[0-9]{1,3}\.|\([0-9]{1,3}\))\s*|\n\n|\n\s*|\.\s+)(?:The\s+|This\s+|These\s+)?appeals?\s+(?:is|are|stands?)[,\s]*(?:hereby|therefore|accordingly|consequently|unmerited\s+and\s+(?:consequently\s+)?|sans\s+merit\s+and\s+(?:consequently\s+)?)?[,\s]*(?:allowed|dismissed|disposed\s+of)\b",

        # 6. Direct paragraph or numbered final administrative order quashing transition (e.g. Brijesh Kumar Shukla)
        r"(?:\n\s*(?:[0-9]{1,3}\.|\([0-9]{1,3}\))\s*|\n\n|\n\s*)?(?:In\s+view\s+of\s+the\s+above[,\s]*|Accordingly[,\s]*|Consequently[,\s]*)?(?:the\s+)?impugned\s+(?:[A-Za-z]+\s+)?(?:orders?|notices?|letters?|notifications?|decisions?)[^\n.]*?\s+(?:is|are|stands?)\s+(?:hereby\s+)?(?:quashed|set\s+aside)\b",

        # 7. Eviction decrees and vacate directions (e.g. Ramkarandas, OIL-SC-2000_INSC_110)
        r"(?:\n\n|\n\s*|\.\s+)(?:Hence\s+|Thus\s+)?(?:the\s+)?(?:appellant|tenant|judgment\s+debtor)\s+is\s+liable\s+for\s+eviction\b",
        r"(?:\n\n|\n\s*|\.\s+)(?:Tenant\s+may\s+vacate|premises\s+shall\s+be\s+vacated|vacate\s+the\s+premises)\b",

        # 8. Incarceration, surrender, and arrest directions (e.g. OIL-SC-2010_INSC_109)
        r"(?:\n\n|\n\s*|\.\s+)(?:the\s+)?(?:respondent-State|State|police|trial\s+court)\s+would\s+take\s+(?:all\s+)?necessary\s+steps\s+to\s+arrest\s+the\s+appellant\b",
        r"(?:\n\n|\n\s*|\.\s+)(?:the\s+)?(?:appellant|accused|convict)\s+(?:shall|is\s+directed\s+to)\s+(?:surrender|be\s+arrested|lodge\s+him\s+in\s+jail|serve\s+out\s+(?:the\s+remaining\s+period\s+of\s+)?sentence)\b",

        # 9. Mandatory injunction / compliance / cost deposit directions (e.g. OIL-SC-2007_INSC_1082, OIL-AHC-UPHC020380352022)
        r"(?:\n\n|\n\s*|\.\s+)(?:We,\s+however,\s+before\s+taking\s+any\s+punitive\s+action[^\n.]*?direction\s+upon\s+them\s+to\s+fully\s+implement\s+the\s+orders\s+of\s+this\s+Court)\b",
        r"(?:\n\n|\n\s*|\.\s*|\b)(?:However[,\s]*)?(?:the\s+)?(?:petitioner|appellant)\s+is\s+put\s+to\s+costs?\s+of\s+Rs\.?[0-9/,\s\-]+",

        # 10. OCR typos in operative disposition phrases (e.g. OIL-SC-1973_INSC_247, OIL-SC-1984_INSC_90, OIL-DHC-DLHC011594232016)
        r"(?:\n\n|\n\s*|\.\s+)(?:The\s+|This\s+)?(?:petition|appeal)\s+dismis[sj]ed\b",
        r"(?:\n\n|\n\s*|\.\s+)(?:are|is|stands?)\s+disppsed\s+of\s+accordingly\b",
        r"(?:\n\n|\n\s*|\.\s+)(?:Consequently[,\s]*|Accordingly[,\s]*)?(?:the\s+)?Court\s+set\s+asides\s+(?:the\s+)?impugned\s+order\b",
    ]

    # Terminal verdict stamps and reporter sign-offs (typically in the final 2,000 chars)
    TERMINAL_VERDICT_STAMPS = [
        r"(?:^|\n)\s*(?:(?:Special\s+Leave\s+Petitions?|Writ\s+Petitions?|Petitions?|Appeals?|Civil\s+Appeals?|Criminal\s+Appeals?)\s+(?:is|are|stands?|hereby)?\s*(?:allowed|dismissed|disposed\s+of|partly\s+allowed|remitted|remanded)\s*[:.]?)\s*(?:[A-Z\.]+\s*)*$",
        r"(?:^|\n)\s*(?:Order\s+accordingly|Ordered\s+accordingly)\s*[:.]?\s*$",
        r"(?:^|\n)\s*\[SECTION\]\s*##\s*[^\n]*$",
        r"(?:^|\n)\s*(?:Dismissed\s+as\s+infructuous|Dismissed\s+as\s+withdrawn)\s*[:.]?\s*$",
    ]

    # Explicit disposition holding phrases to strip wherever they occur
    DISPOSITION_PATTERNS = [
        # 1. Bare / Standalone terminal dispositions on own lines or following punctuation
        r"(?:^|\n|\.\s+)(?:Special\s+Leave\s+Petitions?|Writ\s+Petitions?|Petitions?|Appeals?|Civil\s+Appeals?|Criminal\s+Appeals?)\s+(?:is|are|stands?|hereby)?\s*(?:allowed|dismissed|disposed\s+of|partly\s+allowed|remitted|remanded)\s*[:.]?",
        r"(?:^|\n|\.\s+)(?:Order\s+accordingly|Ordered\s+accordingly)\s*[:.]?",

        # 2. Intervening adverbs, compound clauses, plural forms, and OCR concatenations
        r"\b(?:the\s+|this\s+|these\s+)?appeals?(?:\s+filed\s+by\s+[^\n,]+)?\s+(?:therefore\s+|accordingly\s+|consequently\s+)?(?:fails?|succeeds?)\s*(?:and\s+(?:is|are|the\s+same\s+is)\s+(?:hereby\s+)?(?:dismissed|allowed))?\b",
        r"\b(?:the\s+|this\s+|these\s+)?appeals?(?:\s+filed\s+by\s+[^\n,]+)?\s+(?:is|are|stands?)\s+(?:hereby\s+|therefore\s+|accordingly\s+|consequently\s+|unmerited\s+and\s+(?:consequently\s+)?|sans\s+merit\s+and\s+(?:consequently\s+)?)?(?:allowed|dismissed|partly\s+allowed|disposed\s+of)\b",
        r"\b(?:the\s+|this\s+|these\s+)?appeals?\s+isallowed\b",
        r"\b(?:the\s+|this\s+|these\s+)?(?:writ\s+)?petitions?\s+(?:is|are|stands?)\s+(?:hereby\s+|therefore\s+|accordingly\s+|consequently\s+)?(?:allowed|dismissed|dismissedbeing|disposed\s+of|withdrawn)\b",
        r"\b(?:the\s+|this\s+|these\s+)?(?:writ\s+)?petitions?\s+(?:fail\s+and\s+are|fails\s+and\s+is)\s+(?:hereby\s+|accordingly\s+)?dismissed\b",
        r"\b(?:the\s+|this\s+|these\s+)?(?:writ\s+)?petitions?\s+(?:lacks\s+merit\s+and\s+is|fails\s+and\s+is|consequently\s+fails\s+and\s+is)[,\s]*(?:hereby|therefore|accordingly|consequently)?[,\s]*(?:allowed|dismissed)\b",
        r"\b(?:the\s+|this\s+|these\s+)?application\s+(?:is|stands?)\s+(?:hereby\s+|therefore\s+|accordingly\s+|consequently\s+)?(?:allowed|dismissed|rejected|disposed\s+of)\b",
        r"\b(?:the\s+)?appeal(?:also)?\s+does\s+not\s+survive\s+(?:and\s+(?:the\s+same\s+)?stands?\s+dismissed)?\b",
        r"\bapplication\s+for\s+leave\s+to\s*(?:appeal|toappeal)\s+lacks\s+merit\s+and\s+is(?:,\s+accordingly,)?\s+rejected\b",
        r"\b(?:the\s+|this\s+|these\s+|instant\s+)?(?:writ\s+)?(?:petitions?|appeals?|applications?)\s+(?:also\s+)?(?:deserves?|(?:is|are)\s+liable)\s+to\s+be\s+(?:allowed|dismissed)\b",
        r"\b(?:the\s+|this\s+|these\s+)?appeals?\s+(?:are|is)\s+sans\s+merit\s+and\s+deserve\s+dismissal(?:\s+which\s+we\s+direct)?\b",
        r"\b(?:the\s+|this\s+)?(?:petitions?|appeals?)\s+dismis[sj]ed\b",
        r"\b(?:are|is|stands?)\s+disppsed\s+of(?:\s+accordingly)?\b",

        # 3. First-person active-voice judicial operative phrases
        r"\bwe\s+(?:hereby\s+|accordingly\s+|therefore\s+)?(?:allow|dismiss|partly\s+allow)\s+(?:the\s+|this\s+|these\s+)?(?:writ\s+|special\s+leave\s+|civil\s+|criminal\s+)?(?:appeals?|petitions?|applications?)\b.*?(?:\.|\n|$)",
        r"\bwe\s+(?:hereby\s+|accordingly\s+|therefore\s+)?set\s+aside\s+(?:the\s+)?(?:ihe\s+)?(?:impugned\s+)?(?:order|judgment|decree|conviction|sentence|order\s+of\s+detention)\b.*?(?:\.|\n|$)",
        r"\bwe\s+(?:hereby\s+|accordingly\s+|therefore\s+)?remit\s+the\s+matter\b.*?(?:\.|\n|$)",
        r"\bwe\s+(?:do\s+not\s+differ\s+from\s+the\s+view\s+taken\s+by\s+the\s+High\s+Court\s+in\s+maintaining\s+the\s+conviction)\b",

        # 4. Decree, judgment and order reversal phrases and tribunal findings
        r"\b(?:the\s+)?(?:impugned\s+)?(?:orders?|judgments?|decrees?|convictions?)(?:\s+dated\s+[0-9\.\-/]+)?\s*(?:of\s+the\s+High\s+Court\s+)?(?:\s*is)?\s*(?:hereby\s+)?(?:set\s+aside|set\s+asides|quashed|reversed|annulled)\b",
        r"\b(?:the\s+same\s+(?:is|are)\s+(?:hereby\s+)?set\s+aside)\b",
        r"\b(?:the\s+matter\s+be\s+remitted\s+to\s+the\s+High\s+Court)\b",
        r"\bproceedings\s+(?:arising\s+therefrom\s+)?(?:are|stand)\s+(?:hereby\s+)?quashed\b",
        r"\bproceedings\s+(?:arising\s+therefrom\s+)?are\s+(?:hereby\s+)?set\s+aside\b",
        r"\b(?:the\s+)?negative\s+finding\s+recorded\s+by\s+the\s+Tribunal[^\n.]*?\s+is\s+set\s+aside\b",

        # 5. Bail and specific relief
        r"\b(?:the\s+)?(?:applicant|accused|appellant|petitioner)\s+is\s+(?:directed\s+to\s+be\s+)?(?:released|enlarged)\s+on\s+bail\b",
        r"\b(?:the\s+)?(?:prayer|application)\s+for\s+bail\s+is\s+(?:rejected|dismissed|refused|declined)\b",
        r"\bbail\s+is\s+(?:granted|rejected|refused|cancelled)\b",
        r"\banticipatory\s+bail\s+is\s+(?:granted|rejected|refused)\b",
        r"\bpetitioner\s+be\s+set\s+at\s+liberty\s+forthwith\b",
        r"\b(?:CM\s+No\.?[0-9/]+\s*)?Dismissed\s+as\s+infructuous\.?\b",

        # 7. Consequential cost orders, refunds, and decretal reliefs
        r"\b(?:the\s+)?(?:appellant|respondent|petitioner)\s+shall\s+pay\s+costs\b.*?(?:\.|\n|$)",
        r"\bcosts?\s+quantified\s+@\s+Rs\.?[0-9/,\s]+(?:\([A-Za-z\s]+\))?\s+to\s+the\s+(?:respondent|petitioner|appellant)\b.*?(?:\.|\n|$)",
        r"\b(?:the\s+)?amount\s+shall\s+(?:also\s+)?be\s+refunded\b.*?(?:\.|\n|$)",
        r"\b(?:the\s+)?(?:appellant|tenant|judgment\s+debtor)\s+is\s+liable\s+for\s+eviction\b.*?(?:\.|\n|$)",
        r"\btenant\s+may\s+vacate\s+the\s+premises\b.*?(?:\.|\n|$)",
        r"\barrest\s+the\s+appellant\s+and\s+lodge\s+him\s+in\s+jail\b.*?(?:\.|\n|$)",
        r"\bserve\s+out\s+(?:the\s+remaining\s+period\s+of\s+)?sentence\b.*?(?:\.|\n|$)",
        r"\bpetitioner\s+is\s+put\s+to\s+costs?\s+of\s+Rs\.?[0-9/,\s\-]+.*?(?:\.|\n|$)",

        # 8. Administrative / movement order quashing and consequential fresh order directions
        r"\b(?:the\s+)?impugned\s+(?:[A-Za-z]+\s+)?(?:orders?|notices?|letters?)\s*(?:dated\s+[^\n,]+)?\s+(?:is|are|stands?)\s+(?:hereby\s+)?(?:quashed|set\s+aside)\b",
        r"\b(?:the\s+)?respondents?\s+shall\s+issue\s+(?:a\s+)?fresh\s*(?:[A-Za-z]+\s+)?(?:orders?|movement\s+orders?)\b.*?(?:\.|\n|$)",
        r"\b(?:the\s+)?(?:writ\s+)?petitions?\s+and\s+(?:the\s+)?applications?\s+(?:is|are|stands?)\s+(?:hereby\s+)?disposed\s+of\b",
    ]

    # Forbidden fields that must NEVER be passed as model inputs
    FORBIDDEN_FIELDS = {
        "outcome",
        "outcomeRationale",
        "summary",  # Often contains post-judgment summaries (e.g. "The SC held that...")
        "article141Status",
        "obiterAndScopeNote",
        "subsequentTreatment",
        "human_approved_label",
        "human_successful_party",
        "candidate_disposition",
        "original_disposition_phrase",
        "matched_text",
        "evidence",
        "evidence_offset_start",
        "evidence_offset_end",
        "human_notes",
        "notes",
    }

    def __init__(self):
        self.compiled_headings = [re.compile(p, re.IGNORECASE) for p in self.OPERATIVE_HEADINGS]
        self.compiled_transitions = [re.compile(p, re.IGNORECASE) for p in self.CONCLUDING_OPERATIVE_TRANSITIONS]
        self.compiled_stamps = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.TERMINAL_VERDICT_STAMPS]
        self.compiled_dispositions = [re.compile(p, re.IGNORECASE) for p in self.DISPOSITION_PATTERNS]

    def sanitize_judgment_text(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Strips final operative holdings and disposition sentences from judgment text.
        Applies a conservative, trigger-aware safety envelope:
        - Structural operative headings in concluding 50%.
        - Concluding operative decretal transitions in concluding 40%.
        - Dispositive holding patterns in concluding 25% boundary-aware cutoff.
        - Terminal verdict stamps stripping in tail.
        - Comprehensive pattern scrubbing across remaining text.
        Returns the sanitized pre-decision text and diagnostic metrics.
        """
        if not text:
            return "", {
                "sanitizer_version": self.SANITIZER_VERSION,
                "original_length": 0,
                "sanitized_length": 0,
                "truncation_boundary_position": -1,
                "truncated_operative_section": False,
                "stripped_phrase_count": 0,
                "original_text_hash": "",
                "sanitized_text_hash": "",
                "triggered_patterns": []
            }

        orig_len = len(text)
        orig_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        truncated_operative = False
        earliest_match_idx = -1
        triggered_patterns: List[str] = []

        # 1. Check for structural operative heading in the concluding half of the text
        half_point = len(text) // 2
        for idx, rx in enumerate(self.compiled_headings):
            for match in rx.finditer(text):
                if match.start() >= half_point:
                    if earliest_match_idx == -1 or match.start() < earliest_match_idx:
                        earliest_match_idx = match.start()
                        triggered_patterns.append(f"heading_{idx}")

        # 2. Check for concluding operative transitions in final 40% of text
        concluding_zone = int(len(text) * 0.60)
        for idx, rx in enumerate(self.compiled_transitions):
            for match in rx.finditer(text):
                if match.start() >= concluding_zone:
                    if earliest_match_idx == -1 or match.start() < earliest_match_idx:
                        earliest_match_idx = match.start()
                        triggered_patterns.append(f"transition_{idx}")

        # 3. Trigger-Aware Safety Envelope: Dispositive holdings in final 25% of substantive judgments
        # When an explicit disposition pattern matches in the final 25% of a full judgment (len >= 1000),
        # it structurally marks the decretal conclusion. Truncate from the boundary of that sentence/paragraph.
        if len(text) >= 1000:
            concluding_zone_25 = int(len(text) * 0.75)
            for idx, rx in enumerate(self.compiled_dispositions):
                for match in rx.finditer(text):
                    if match.start() >= concluding_zone_25:
                        p_start = max(text.rfind("\n\n", 0, match.start()), text.rfind(". ", 0, match.start()))
                        b_start = p_start + 2 if p_start != -1 else match.start()
                        if earliest_match_idx == -1 or b_start < earliest_match_idx:
                            earliest_match_idx = b_start
                            triggered_patterns.append(f"disposition_envelope_{idx}")

        pre_decision_text = text
        if earliest_match_idx != -1:
            pre_decision_text = text[:earliest_match_idx].strip()
            truncated_operative = True

        # 4. Strip terminal verdict stamps in concluding tail of whatever remains
        tail_start = max(0, len(pre_decision_text) - 2000)
        tail = pre_decision_text[tail_start:]
        for rx in self.compiled_stamps:
            tail = rx.sub("", tail)
        pre_decision_text = pre_decision_text[:tail_start] + tail
        pre_decision_text = pre_decision_text.strip()

        # 5. Check for disposition holding phrases anywhere in the remaining text and scrub them
        stripped_patterns = 0
        for rx in self.compiled_dispositions:
            if rx.search(pre_decision_text):
                pre_decision_text, n_sub = rx.subn("[DISPOSITION_REDACTED]", pre_decision_text)
                stripped_patterns += n_sub

        # Normalize consecutive redacted placeholders and strip Kanoon scraper markup
        pre_decision_text = re.sub(r"\[SECTION\]\s*##[^\n]*", "", pre_decision_text)
        pre_decision_text = re.sub(r"(\[DISPOSITION_REDACTED\]\s*)+", "[DISPOSITION_REDACTED] ", pre_decision_text).strip()
        san_hash = hashlib.sha256(pre_decision_text.encode("utf-8")).hexdigest()

        return pre_decision_text, {
            "sanitizer_version": self.SANITIZER_VERSION,
            "original_length": orig_len,
            "sanitized_length": len(pre_decision_text),
            "truncation_boundary_position": earliest_match_idx,
            "truncated_operative_section": truncated_operative,
            "stripped_phrase_count": stripped_patterns,
            "original_text_hash": orig_hash,
            "sanitized_text_hash": san_hash,
            "triggered_patterns": triggered_patterns
        }

    def extract_pre_decision_features(self, raw_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts pre-decision facts, procedural posture, legal provisions, and issues.
        Strictly excludes any forbidden outcome-bearing fields.
        """
        sanitized_text, meta = self.sanitize_judgment_text(raw_case.get("judgmentText", ""))

        provisions = raw_case.get("legalProvisions", [])
        if isinstance(provisions, list):
            provisions_str = ", ".join(str(p) for p in provisions)
        else:
            provisions_str = str(provisions)

        # Composite pre-decision factual document
        factual_composite = (
            f"Case Title: {raw_case.get('caseTitle', '')}\n"
            f"Court: {raw_case.get('court', '')}\n"
            f"Category: {raw_case.get('category', '')}\n"
            f"Legal Provisions: {provisions_str}\n\n"
            f"Factual Narrative and Contentions:\n{sanitized_text}"
        )

        return {
            "case_id": raw_case.get("id"),
            "case_title": raw_case.get("caseTitle"),
            "court": raw_case.get("court"),
            "decision_date": raw_case.get("judgmentDate"),
            "category": raw_case.get("category"),
            "legal_provisions": provisions,
            "sanitized_pre_decision_text": sanitized_text,
            "factual_composite": factual_composite,
            "sanitization_diagnostics": meta
        }


class OutcomeDataAuditor:
    """
    Performs comprehensive audit of outcome annotation datasets, candidate files,
    and review logs.
    """

    def __init__(self, datasets_dir: Optional[str] = None):
        if datasets_dir is None:
            self.datasets_dir = Path(__file__).resolve().parent.parent / "app" / "datasets"
        else:
            self.datasets_dir = Path(datasets_dir)

    def audit_all(self) -> Dict[str, Any]:
        """Runs the complete audit across review artifacts and source judgments."""
        oil_path = self.datasets_dir / "open_india_law_sample_150.json"
        review_csv_path = self.datasets_dir / "outcome_label_review_v2.csv"
        review_cand_path = self.datasets_dir / "outcome_label_candidates_v2.json"
        landmark_path = self.datasets_dir / "indian_judgments.json"

        results: Dict[str, Any] = {
            "candidate_records_count": 0,
            "human_approved_count": 0,
            "pending_review_count": 0,
            "uncertain_count": 0,
            "rejected_count": 0,
            "verified_class_distribution": {},
            "candidate_class_distribution": {},
            "cases_with_sufficient_pre_decision_text": 0,
            "duplicate_or_related_cases": [],
            "source_files": {}
        }

        # 1. Audit Source OIL 150
        oil_records = []
        if oil_path.exists():
            with open(oil_path, "r", encoding="utf-8") as f:
                oil_records = json.load(f)
            results["source_files"]["open_india_law_sample_150"] = {
                "exists": True,
                "count": len(oil_records),
                "path": str(oil_path)
            }
        else:
            results["source_files"]["open_india_law_sample_150"] = {"exists": False}

        # Check pre-decision text lengths
        sufficient_text_cases = 0
        text_lengths = []
        for c in oil_records:
            t = c.get("judgmentText", "")
            t_len = len(t)
            text_lengths.append(t_len)
            if t_len >= 500:
                sufficient_text_cases += 1
        results["cases_with_sufficient_pre_decision_text"] = sufficient_text_cases
        results["text_length_stats"] = {
            "min": min(text_lengths) if text_lengths else 0,
            "max": max(text_lengths) if text_lengths else 0,
            "mean": round(sum(text_lengths) / len(text_lengths), 1) if text_lengths else 0,
            "near_cap_cases": sum(1 for l in text_lengths if l >= 39900)
        }

        # Check for related / duplicate cases
        seen_identifiers: Dict[str, List[str]] = {}
        for c in oil_records:
            cid = c.get("caseIdentifier", "").strip()
            if cid and cid != "neutral citation pending":
                seen_identifiers.setdefault(cid, []).append(c.get("id"))
        related = [ids for cid, ids in seen_identifiers.items() if len(ids) > 1]
        results["duplicate_or_related_cases"] = related

        # 2. Audit Review CSV (v2)
        if review_csv_path.exists():
            with open(review_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            results["candidate_records_count"] = len(rows)
            for r in rows:
                status = (r.get("review_status") or "pending_review").strip().lower()
                approved_label = (r.get("human_approved_label") or "").strip()
                cand_disp = (r.get("normalized_disposition") or r.get("original_disposition") or "").strip()

                if cand_disp:
                    results["candidate_class_distribution"][cand_disp] = (
                        results["candidate_class_distribution"].get(cand_disp, 0) + 1
                    )

                if status in ["approved", "corrected", "adjudicated_approved"]:
                    results["human_approved_count"] += 1
                    if approved_label:
                        results["verified_class_distribution"][approved_label] = (
                            results["verified_class_distribution"].get(approved_label, 0) + 1
                        )
                elif status == "pending_review":
                    results["pending_review_count"] += 1
                elif status in ["uncertain", "ambiguous", "deferred_needs_full_text", "unknown"]:
                    results["uncertain_count"] += 1
                elif status == "rejected":
                    results["rejected_count"] += 1
                else:
                    results["pending_review_count"] += 1

            results["source_files"]["outcome_label_review_v2"] = {
                "exists": True,
                "count": len(rows),
                "path": str(review_csv_path)
            }
        else:
            results["source_files"]["outcome_label_review_v2"] = {"exists": False}

        # 3. Audit Landmark dataset (for reference on existing model)
        if landmark_path.exists():
            with open(landmark_path, "r", encoding="utf-8") as f:
                ij_records = json.load(f)
            ij_outcomes = Counter(c.get("outcome") for c in ij_records)
            results["landmark_corpus_audit"] = {
                "exists": True,
                "count": len(ij_records),
                "outcomes": dict(ij_outcomes),
                "note": "Curated landmark corpus; 26 Allowed vs 1 Dismissed (extreme class imbalance and target leakage)."
            }

        return results


class VerifiedOutcomeDatasetBuilder:
    """
    Constructs a verified outcome dataset only from human-approved annotations.
    """

    MIN_APPROVED_THRESHOLD = 30  # Minimum verified samples required before statistical model training

    def __init__(self, datasets_dir: Optional[str] = None):
        if datasets_dir is None:
            self.datasets_dir = Path(__file__).resolve().parent.parent / "app" / "datasets"
        else:
            self.datasets_dir = Path(datasets_dir)
        self.auditor = OutcomeDataAuditor(str(self.datasets_dir))
        self.sanitizer = TargetLeakageSanitizer()

    def build_dataset(
        self,
        output_path: Optional[str] = None,
        min_approved_required: Optional[int] = None,
        allow_empty_manifest: bool = True,
        target: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Builds the verified outcome dataset.
        If approved labels are insufficient, creates an unfinalized audit manifest and refuses
        to generate a pseudo-training set.
        Feature 4.14: Supports target-specific dataset creation ("disposition" / "model_a" vs "successful_party" / "model_b").
        """
        if min_approved_required is None:
            min_approved_required = self.MIN_APPROVED_THRESHOLD

        audit = self.auditor.audit_all()
        target_norm = target.strip().lower() if target else None

        # Determine approved count based on target
        if target_norm in ["disposition", "model_a", "judicial_disposition"]:
            approved_count = sum(
                count for lbl, count in audit["verified_class_distribution"].items()
                if lbl in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS
            )
        elif target_norm in ["successful_party", "model_b", "party"]:
            # Count substantive party approvals from review csv
            review_csv_path = self.datasets_dir / "outcome_label_review_v2.csv"
            approved_count = 0
            if review_csv_path.exists():
                with open(review_csv_path, "r", encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        if (r.get("review_status") or "").strip().lower() in ["approved", "corrected", "adjudicated_approved"]:
                            if (r.get("human_successful_party") or "").strip() in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES:
                                approved_count += 1
        else:
            # Dual-model gatekeeper: both Model A (merits) and Model B (substantive) must satisfy threshold
            model_a_count = sum(
                count for lbl, count in audit["verified_class_distribution"].items()
                if lbl in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS
            )
            review_csv_path = self.datasets_dir / "outcome_label_review_v2.csv"
            model_b_count = 0
            if review_csv_path.exists():
                with open(review_csv_path, "r", encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        if (r.get("review_status") or "").strip().lower() in ["approved", "corrected", "adjudicated_approved"]:
                            if (r.get("human_successful_party") or "").strip() in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES:
                                model_b_count += 1
            approved_count = min(model_a_count, model_b_count)

        manifest: Dict[str, Any] = {
            "builder_version": "v4.4.0-verified-outcome-builder",
            "target": target_norm or "all",
            "audit_summary": audit,
            "minimum_approved_required": min_approved_required,
            "human_approved_found": approved_count,
            "dataset_status": "unfinalized_pending_human_review",
            "is_training_eligible": False,
            "records": []
        }

        if approved_count < min_approved_required:
            logger.warning(
                f"Insufficient human-approved outcome labels found: {approved_count} (minimum required: {min_approved_required}). "
                "Adhering to strict safety rule: zero automated approvals or pseudo-label generation."
            )
            manifest["dataset_status"] = "unfinalized_pending_human_review"
            manifest["missing_requirements"] = [
                f"Requires at least {min_approved_required} human-approved outcome records with signed-off review_status in ['approved', 'corrected', 'adjudicated_approved'].",
                f"Currently {approved_count} of 150 candidate records are verified ({150 - approved_count} pending review).",
                "Qualified legal annotator must complete batch review in outcome_label_review_v2.csv.",
                "Qualitative research fallback mode must be preserved in prediction APIs."
            ]

            if output_path:
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2)

            if not allow_empty_manifest:
                raise InsufficientApprovedLabelsError(
                    f"Found {approved_count} approved labels; requires at least {min_approved_required}."
                )

            return manifest

        # If approved records exist: build verified dataset
        # Load source judgments
        oil_path = self.datasets_dir / "open_india_law_sample_150.json"
        with open(oil_path, "r", encoding="utf-8") as f:
            oil_records = {c["id"]: c for c in json.load(f)}

        # Load review records
        review_csv_path = self.datasets_dir / "outcome_label_review_v2.csv"
        approved_records = []
        with open(review_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if (r.get("review_status") or "").strip().lower() in ["approved", "corrected", "adjudicated_approved"]:
                    case_id = r.get("case_id")
                    disp_label = (r.get("human_approved_label") or "").strip()
                    party_label = (r.get("human_successful_party") or "").strip()

                    # Apply target eligibility filter if target specified
                    if target_norm in ["disposition", "model_a", "judicial_disposition"]:
                        if disp_label not in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS:
                            continue
                    elif target_norm in ["successful_party", "model_b", "party"]:
                        if party_label not in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES:
                            continue

                    if case_id in oil_records:
                        raw_case = oil_records[case_id]
                        clean_features = self.sanitizer.extract_pre_decision_features(raw_case)
                        clean_features["verified_label"] = disp_label
                        clean_features["verified_successful_party"] = party_label
                        clean_features["reviewer_reference"] = r.get("reviewer_reference")
                        clean_features["review_notes"] = r.get("human_notes")
                        clean_features["case_group_id"] = raw_case.get("caseIdentifier") or case_id
                        approved_records.append(clean_features)

        manifest["dataset_status"] = "verified_production_ready"
        manifest["is_training_eligible"] = True
        manifest["records"] = approved_records
        manifest["record_count"] = len(approved_records)

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

        return manifest

    def get_eligible_records(self, target: str = "model_a") -> List[Dict[str, Any]]:
        """
        Returns pre-decision sanitized feature dictionaries for records eligible for the specified model target.
        """
        oil_path = self.datasets_dir / "open_india_law_sample_150.json"
        with open(oil_path, "r", encoding="utf-8") as f:
            oil_records = {c["id"]: c for c in json.load(f)}

        target_norm = target.strip().lower()
        review_csv_path = self.datasets_dir / "outcome_label_review_v2.csv"
        results = []
        if review_csv_path.exists():
            with open(review_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    if (r.get("review_status") or "").strip().lower() in ["approved", "corrected", "adjudicated_approved"]:
                        case_id = r.get("case_id")
                        disp_label = (r.get("human_approved_label") or "").strip()
                        party_label = (r.get("human_successful_party") or "").strip()

                        if target_norm in ["disposition", "model_a", "judicial_disposition"]:
                            if disp_label not in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS:
                                continue
                        elif target_norm in ["successful_party", "model_b", "party"]:
                            if party_label not in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES:
                                continue

                        if case_id in oil_records:
                            raw_case = oil_records[case_id]
                            clean_features = self.sanitizer.extract_pre_decision_features(raw_case)
                            clean_features["verified_label"] = disp_label
                            clean_features["verified_successful_party"] = party_label
                            clean_features["reviewer_reference"] = r.get("reviewer_reference")
                            clean_features["review_notes"] = r.get("human_notes")
                            clean_features["case_group_id"] = raw_case.get("caseIdentifier") or case_id
                            results.append(clean_features)
        return results


def main():
    datasets_dir = Path(__file__).resolve().parent.parent / "app" / "datasets"
    builder = VerifiedOutcomeDatasetBuilder(str(datasets_dir))
    manifest_out = datasets_dir / "verified_outcome_dataset_manifest.json"
    result = builder.build_dataset(output_path=str(manifest_out))
    print(f"Dataset Build Result: {result['dataset_status']}")
    print(f"Approved: {result['human_approved_found']} / {result['minimum_approved_required']}")
    print(f"Manifest written to: {manifest_out}")


if __name__ == "__main__":
    main()
