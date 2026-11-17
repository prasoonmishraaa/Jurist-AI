import re
from typing import Tuple, Dict, Any, List

class HardenedTargetLeakageSanitizer:
    """
    Hardened Pre-Decision Text Sanitizer for Judicial Outcome Prediction.
    Strictly removes target outcome leakage while preserving factual narratives,
    statutory provisions, and judicial reasoning.
    """

    # Structural operative headings in the concluding portion of judgments
    OPERATIVE_HEADINGS = [
        # Explicit formal headings
        r"(?:^|\n)\s*(?:O\s*R\s*D\s*E\s*R|OPERATIVE\s+ORDER|FINAL\s+ORDER|ORDER\s+OF\s+THE\s+COURT)\s*(?::|-|\n)",
        r"(?:^|\n)\s*(?:CONCLUSION|D\s*I\s*S\s*P\s*O\s*S\s*I\s*T\s*I\s*O\s*N)\s*(?::|-|\n)",
        r"(?:^|\n)\s*(?:IN\s+THE\s+RESULT|RESULT\s+OF\s+THE\s+APPEAL|RESULT)\s*(?::|-|\n)",
        r"(?:^|\n)\s*(?:PER\s+CURIAM|BY\s+THE\s+COURT)\s*(?::|-|\n)",
        # Web scraper Kanoon section headers
        r"(?:^|\n)\s*\[SECTION\]\s*##\s*(?:Appeal|Petition|Order|Judgment|Holding|Conclusion|Disposition)",
    ]

    # Concluding operative holding introductory clauses (in final 35% of judgment text)
    # Marks where the bench begins its final operative decree in older/unheaded judgments
    CONCLUDING_OPERATIVE_TRANSITIONS = [
        r"(?:\n\s*(?:[0-9]{1,3}\.|\([0-9]{1,3}\))\s*)?(?:For\s+(?:the\s+)?(?:foregoing\s+|aforementioned\s+)?reasons|In\s+these\s+circumstances|In\s+(?:the\s+)?result|In\s+view\s+of\s+the\s+above(?:\s+discussion)?|As\s+a\s+result\s+of\s+the\s+foregoing|Consequently|Accordingly)[,\s]+(?:we\s+(?:find|are\s+of\s+the\s+opinion|hold|do\s+not\s+differ|dismiss|allow|set\s+aside|remit|quash|direct)|the\s+appeals?\s+(?:is|are|fails?|succeeds?|stands?)|the\s+impugned\s+(?:judgment|order)|this\s+appeal|these\s+appeals|the\s+writ\s+petition)\b",
    ]

    # Terminal verdict stamps and reporter sign-offs (typically in the final 2,000 chars)
    TERMINAL_VERDICT_STAMPS = [
        r"(?:^|\n)\s*(?:(?:Special\s+Leave\s+Petition|Writ\s+Petition|Petition|Appeals?|Civil\s+Appeals?|Criminal\s+Appeals?)\s+(?:is|are|stands?|hereby)?\s*(?:allowed|dismissed|disposed\s+of|partly\s+allowed|remitted|remanded)\s*[:.]?)\s*$",
        r"(?:^|\n)\s*(?:Order\s+accordingly|Ordered\s+accordingly)\s*[:.]?\s*$",
        r"(?:^|\n)\s*\[SECTION\]\s*##\s*[^\n]*$",
    ]

    # Redaction patterns applied across the body to scrub operative disposition phrases
    DISPOSITION_PATTERNS = [
        # 1. Bare / Standalone terminal dispositions on own lines or following punctuation
        r"(?:^|\n|\.\s+)(?:Special\s+Leave\s+Petition|Writ\s+Petition|Petition|Appeals?|Civil\s+Appeals?|Criminal\s+Appeals?)\s+(?:is|are|stands?|hereby)?\s*(?:allowed|dismissed|disposed\s+of|partly\s+allowed|remitted|remanded)\s*[:.]?",
        r"(?:^|\n|\.\s+)(?:Order\s+accordingly|Ordered\s+accordingly)\s*[:.]?",

        # 2. Intervening adverbs and compound clauses
        r"\b(?:the\s+|this\s+|these\s+)?appeals?\s+(?:therefore\s+|accordingly\s+|consequently\s+)?(?:fails?|succeeds?)\s*(?:and\s+is\s+(?:hereby\s+)?(?:dismissed|allowed))?\b",
        r"\b(?:the\s+|this\s+|these\s+)?appeals?\s+(?:is|are|stands?)\s+(?:hereby\s+|therefore\s+|accordingly\s+|consequently\s+)?(?:allowed|dismissed|partly\s+allowed|disposed\s+of)\b",
        r"\b(?:the\s+|this\s+|these\s+)?(?:writ\s+)?petition\s+(?:is|stands?)\s+(?:hereby\s+|therefore\s+|accordingly\s+|consequently\s+)?(?:allowed|dismissed|disposed\s+of|withdrawn)\b",
        r"\b(?:the\s+|this\s+|these\s+)?application\s+(?:is|stands?)\s+(?:hereby\s+|therefore\s+|accordingly\s+|consequently\s+)?(?:allowed|dismissed|rejected|disposed\s+of)\b",

        # 3. First-person active-voice judicial operative phrases
        r"\bwe\s+(?:hereby\s+|accordingly\s+|therefore\s+)?(?:allow|dismiss|partly\s+allow)\s+(?:the\s+|this\s+|these\s+)?(?:writ\s+|special\s+leave\s+|civil\s+|criminal\s+)?(?:appeals?|petitions?|applications?)\b.*?(?:\.|\n|$)",
        r"\bwe\s+(?:hereby\s+|accordingly\s+|therefore\s+)?set\s+aside\s+(?:the\s+)?(?:ihe\s+)?(?:impugned\s+)?(?:order|judgment|decree|conviction|sentence|order\s+of\s+detention)\b.*?(?:\.|\n|$)",
        r"\bwe\s+(?:hereby\s+|accordingly\s+|therefore\s+)?remit\s+the\s+matter\b.*?(?:\.|\n|$)",
        r"\bwe\s+(?:do\s+not\s+differ\s+from\s+the\s+view\s+taken\s+by\s+the\s+High\s+Court\s+in\s+maintaining\s+the\s+conviction)\b",

        # 4. Decree, judgment and order reversal phrases
        r"\b(?:the\s+)?(?:impugned\s+)?(?:orders?|judgments?|decrees?|convictions?)(?:\s+dated\s+[0-9\.\-/]+)?\s+(?:of\s+the\s+High\s+Court\s+)?(?:is|are|stands?)\s+(?:hereby\s+)?(?:set\s+aside|quashed|reversed|annulled)\b",
        r"\b(?:the\s+same\s+are\s+set\s+aside\s+and\s+the\s+appeal\s+is\s+allowed)\b",
        r"\b(?:the\s+matter\s+be\s+remitted\s+to\s+the\s+High\s+Court)\b",
        r"\bproceedings\s+(?:are|stand)\s+(?:hereby\s+)?quashed\b",

        # 5. Scraper suffixes and Kanoon markup
        r"\[SECTION\]\s*##\s*[^\n]*",

        # 6. Bail and specific relief
        r"\b(?:the\s+)?(?:applicant|accused|appellant|petitioner)\s+is\s+(?:directed\s+to\s+be\s+)?(?:released|enlarged)\s+on\s+bail\b",
        r"\b(?:the\s+)?(?:prayer|application)\s+for\s+bail\s+is\s+(?:rejected|dismissed|refused|declined)\b",
        r"\bbail\s+is\s+(?:granted|rejected|refused|cancelled)\b",
        r"\banticipatory\s+bail\s+is\s+(?:granted|rejected|refused)\b",
        r"\bpetitioner\s+be\s+set\s+at\s+liberty\s+forthwith\b",
    ]

    def __init__(self):
        self.compiled_headings = [re.compile(p, re.IGNORECASE) for p in self.OPERATIVE_HEADINGS]
        self.compiled_transitions = [re.compile(p, re.IGNORECASE) for p in self.CONCLUDING_OPERATIVE_TRANSITIONS]
        self.compiled_stamps = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in self.TERMINAL_VERDICT_STAMPS]
        self.compiled_dispositions = [re.compile(p, re.IGNORECASE) for p in self.DISPOSITION_PATTERNS]

    def sanitize_judgment_text(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Sanitizes raw judgment text by:
        1. Checking for formal operative headings in the second half of text.
        2. Checking for concluding operative transitions in the final 35% of text (for older/unheaded judgments).
        3. Stripping terminal verdict stamps and scraper suffixes.
        4. Redacting residual operative phrases throughout remaining text.
        """
        if not text:
            return "", {"original_length": 0, "sanitized_length": 0, "truncated_operative_section": False, "stripped_phrase_count": 0}

        orig_len = len(text)
        truncated_operative = False
        earliest_cut_idx = -1

        # Phase 1: Structural operative heading in the second half of the text
        half_point = len(text) // 2
        for rx in self.compiled_headings:
            for match in rx.finditer(text):
                if match.start() >= half_point:
                    if earliest_cut_idx == -1 or match.start() < earliest_cut_idx:
                        earliest_cut_idx = match.start()

        # Phase 2: If no formal heading, detect concluding operative transition in final 35%
        if earliest_cut_idx == -1:
            concluding_zone = int(len(text) * 0.65)
            for rx in self.compiled_transitions:
                for match in rx.finditer(text):
                    if match.start() >= concluding_zone:
                        if earliest_cut_idx == -1 or match.start() < earliest_cut_idx:
                            earliest_cut_idx = match.start()

        pre_decision_text = text
        if earliest_cut_idx != -1:
            pre_decision_text = text[:earliest_cut_idx].strip()
            truncated_operative = True

        # Phase 3: Strip terminal verdict stamps in concluding tail
        tail_start = max(0, len(pre_decision_text) - 2000)
        tail = pre_decision_text[tail_start:]
        for rx in self.compiled_stamps:
            tail = rx.sub("", tail)
        pre_decision_text = pre_decision_text[:tail_start] + tail
        pre_decision_text = pre_decision_text.strip()

        # Phase 4: Redact residual disposition holding phrases throughout text
        stripped_patterns = 0
        for rx in self.compiled_dispositions:
            if rx.search(pre_decision_text):
                pre_decision_text, n_sub = rx.subn("[DISPOSITION_REDACTED]", pre_decision_text)
                stripped_patterns += n_sub

        # Clean multiple redacted tokens
        pre_decision_text = re.sub(r"(\[DISPOSITION_REDACTED\]\s*)+", "[DISPOSITION_REDACTED] ", pre_decision_text).strip()

        return pre_decision_text, {
            "original_length": orig_len,
            "sanitized_length": len(pre_decision_text),
            "truncated_operative_section": truncated_operative,
            "stripped_phrase_count": stripped_patterns
        }

if __name__ == "__main__":
    import json
    source_path = "ml-service/app/datasets/open_india_law_sample_150.json"
    with open(source_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    sanitizer = HardenedTargetLeakageSanitizer()
    
    leakage_audit_patterns = [
        ("bare_appeal_dismissed", re.compile(r"(?:^|\n|\.\s+)(?:Appeals?|Petitions?)\s+(?:allowed|dismissed|disposed\s+of)\s*[\.:]?", re.IGNORECASE)),
        ("we_dismiss_allow", re.compile(r"\bwe\s+(?:hereby\s+|accordingly\s+|therefore\s+)?(?:allow|dismiss|partly\s+allow|set\s+aside|quash)\b", re.IGNORECASE)),
        ("therefore_fails_dismissed", re.compile(r"\bappeal\s+therefore\s+fails\s+and\s+is\s+hereby\s+dismissed\b", re.IGNORECASE)),
        ("set_aside_order_of_detention", re.compile(r"\bset\s+aside\s+(?:the\s+)?(?:ihe\s+)?order\s+of\s+detention\b", re.IGNORECASE)),
        ("scraper_header", re.compile(r"\[SECTION\]\s*##", re.IGNORECASE)),
        ("operative_order_heading", re.compile(r"(?:^|\n)\s*(?:O\s*R\s*D\s*E\s*R|CONCLUSION|IN\s+THE\s+RESULT)\s*:", re.IGNORECASE)),
    ]

    leakage_found = {name: 0 for name, _ in leakage_audit_patterns}
    affected_cases = set()

    for c in cases:
        cid = c["id"]
        text = c.get("judgmentText", "")
        sanitized, meta = sanitizer.sanitize_judgment_text(text)
        
        for name, rx in leakage_audit_patterns:
            m = rx.search(sanitized)
            if m:
                leakage_found[name] += 1
                affected_cases.add(cid)

    print("\n=== HARDENED SANITIZER LEAKAGE AUDIT (150 Cases) ===")
    for name, cnt in leakage_found.items():
        print(f"  {name:30s}: {cnt} occurrences")
    print(f"Total affected cases with residual leakage: {len(affected_cases)} / 150")
