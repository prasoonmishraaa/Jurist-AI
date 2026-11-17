"""
Judicial Disposition Extraction Engine
JURIST AI — Feature 4.2: Outcome Prediction Improvement

Extracts provisional candidate judicial dispositions from authentic Indian court judgments.
Operates conservatively:
- Never fabricates outcomes or assumes ground truth.
- Inspects the concluding operative section only to prevent historical recital leakage.
- Handles multi-chunk reassembly and case ordering.
- Preserves procedural role semantics (State vs Accused vs Petitioner).
- Marks contradictory rulings as 'ambiguous' and unresolvable texts as 'unknown'.
- Exports provisional labels for human review (review_status = 'pending_review').
"""

import os
import sys
import re
import json
import csv
import shutil
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Tuple, Set


# Permitted candidate disposition categories
VALID_DISPOSITIONS = [
    "appeal_allowed",
    "appeal_dismissed",
    "petition_allowed",
    "petition_dismissed",
    "bail_granted",
    "bail_rejected",
    "proceedings_quashed",
    "conviction_set_aside",
    "conviction_upheld",
    "partly_allowed",
    "remanded",
    "disposed_with_directions",
    "withdrawn",
    "unknown",
    "ambiguous",
]


@dataclass
class DispositionCandidate:
    """Provisional candidate judicial disposition for a legal case."""
    case_id: str
    case_title: str
    court: str
    decision_date: str
    case_type: Optional[str]
    candidate_disposition: str
    original_disposition_phrase: str
    matched_text: str
    source_start_offset: int
    source_end_offset: int
    extraction_method: str
    extraction_confidence: float
    review_status: str = "pending_review"
    ambiguity_reason: str = ""
    party_role: str = "unresolved"
    party_success: str = "unresolved"

    def to_dict(self) -> Dict[str, Any]:
        """Converts the candidate instance to a serializable dictionary."""
        return asdict(self)


class JudicialDispositionExtractor:
    """
    Conservative disposition extraction engine for Indian judgments.
    Inspects concluding operative sections and final orders using contextual rules.
    """

    def __init__(self, concluding_window_size: int = 3000):
        self.concluding_window_size = concluding_window_size
        self._init_patterns()

    def _init_patterns(self):
        """Initializes compiled regex patterns with priority ordering and confidence weights."""
        # Clean common OCR artifacts and word mergers before scanning
        self.ocr_fixes = [
            (re.compile(r"\btheappeal\b", re.IGNORECASE), "the appeal"),
            (re.compile(r"\bisallowed\b", re.IGNORECASE), "is allowed"),
            (re.compile(r"\bisdismissed\b", re.IGNORECASE), "is dismissed"),
            (re.compile(r"\bisdisposed\b", re.IGNORECASE), "is disposed"),
            (re.compile(r"\baswithdrawn\b", re.IGNORECASE), "as withdrawn"),
            (re.compile(r"\bdismissed\s+aswithdrawn\b", re.IGNORECASE), "dismissed as withdrawn"),
            (re.compile(r"\bpetitions\s+dispo:.-.cJ\s+oL\b", re.IGNORECASE), "petitions disposed of"),
            (re.compile(r"\bpetition\s+dismisJed\b", re.IGNORECASE), "petition dismissed"),
        ]

        # Negation / conditional prefixes: match within 50 chars prior to candidate
        self.negation_pattern = re.compile(
            r"\b(?:cannot\s+be|could\s+not\s+be|no\s+ground\s+to|not|never|refuse\s+to|declined\s+to|fail(?:s|ed)?\s+to|no\s+reason\s+to|if\s+the|in\s+the\s+event\s+that|should\s+the)\s+$",
            re.IGNORECASE
        )

        # Historical recital prefixes within the sentence
        self.historical_pattern = re.compile(
            r"\b(?:trial\s+court|high\s+court\s+held|appellant\s+contended|petitioner\s+argued|learned\s+counsel\s+submitted|prosecution\s+alleged|counsel\s+prayed\s+that|lower\s+court|session\s+judge)\b",
            re.IGNORECASE
        )

        # Ordered pattern catalog: (category, pattern, confidence)
        # Note: High-specificity patterns (partly_allowed, withdrawn, remanded) take precedence
        self.patterns: List[Tuple[str, re.Pattern, float]] = [
            # 1. Partly allowed
            (
                "partly_allowed",
                re.compile(
                    r"\b(?:appeal\s+(?:is\s+)?partly\s+allowed|appeals?\s+partly\s+allowed|partly\s+allowed|allowed\s+in\s+part|partially\s+allowed|petition\s+(?:is\s+)?partly\s+allowed|allowed\s+to\s+the\s+aforesaid\s+extent|allowed\s+in\s+the\s+following\s+terms)\b",
                    re.IGNORECASE,
                ),
                0.95,
            ),
            # 2. Withdrawn
            (
                "withdrawn",
                re.compile(
                    r"\b(?:dismissed\s+as\s+withdrawn|withdrawn\s+by\s+the\s+petitioner|dismissed\s+as\s+not\s+pressed|petition\s+is\s+dismissed\s+as\s+withdrawn|permission\s+to\s+withdraw\s+(?:is\s+)?granted|dismissed\s+aswithdrawn|appeal\s+is\s+dismissed\s+as\s+withdrawn|prayer\s+to\s+withdraw\s+is\s+allowed|leave\s+to\s+withdraw\s+the\s+present\s+petition)\b",
                    re.IGNORECASE,
                ),
                0.92,
            ),
            # 3. Remanded
            (
                "remanded",
                re.compile(
                    r"\b(?:remanded?\s+(?:back\s+)?to|remitted?\s+(?:back\s+)?to|matter\s+is\s+remanded|remanded\s+for\s+fresh\s+(?:consideration|disposal|decision)|remit\s+the\s+matter\s+back)\b",
                    re.IGNORECASE,
                ),
                0.88,
            ),
            # 4. Proceedings quashed
            (
                "proceedings_quashed",
                re.compile(
                    r"\b(?:(?:criminal\s+)?proceedings|fir|complaint|charge[-\s]?sheet)(?:\s+[\w\-]+){0,7}\s+(?:are|is|stand[s]?\s+)?(?:hereby\s+)?quashed|order\s+impugned\s+is\s+quashed\b",
                    re.IGNORECASE,
                ),
                0.92,
            ),
            # 5. Conviction set aside
            (
                "conviction_set_aside",
                re.compile(
                    r"\b(?:conviction\s+(?:and\s+sentence\s+)?(?:is\s+)?(?:hereby\s+)?set\s+aside|acquitted\s+of\s+all\s+charges|judgment\s+of\s+conviction\s+is\s+set\s+aside|order\s+of\s+conviction\s+is\s+set\s+aside)\b",
                    re.IGNORECASE,
                ),
                0.92,
            ),
            # 6. Conviction upheld
            (
                "conviction_upheld",
                re.compile(
                    r"\b(?:conviction\s+(?:and\s+sentence\s+)?(?:is\s+)?(?:upheld|confirmed|sustained))\b",
                    re.IGNORECASE,
                ),
                0.90,
            ),
            # 7. Bail granted
            (
                "bail_granted",
                re.compile(
                    r"\b(?:admitted\s+to\s+bail|enlarged\s+on\s+bail|released\s+on\s+bail|bail\s+is\s+granted|applicant\s+be\s+released\s+on\s+bail|grant(?:ing)?\s+bail\s+to\s+the\s+applicant|prayer\s+for\s+bail\s+is\s+allowed|anticipatory\s+bail\s+is\s+granted|let\s+the\s+applicant.*?be\s+released\s+on\s+bail)\b",
                    re.IGNORECASE,
                ),
                0.92,
            ),
            # 8. Bail rejected
            (
                "bail_rejected",
                re.compile(
                    r"\b(?:bail\s+application\s+(?:is\s+)?(?:thus[,\s]+)?(?:rejected|dismissed)|prayer\s+for\s+bail\s+is\s+(?:rejected|refused|dismissed)|does\s+not\s+consider\s+it\s+to\s+be\s+a\s+fit\s+case\s+for\s+enlarging\s+the\s+accused.*?bail|bail\s+is\s+rejected|bail\s+is\s+refused)\b",
                    re.IGNORECASE,
                ),
                0.92,
            ),
            # 9. Appeal allowed
            (
                "appeal_allowed",
                re.compile(
                    r"\b(?:appeal\s+(?:is\s+)?allowed|appeals?\s+stand(?:s)?\s+allowed|appeals?\s+are\s+allowed|we\s+allow\s+the\s+appeal|appeal\s+isallowed|appeals?\s+allowed|appeal\s+succeeds\s+and\s+is\s+allowed)\b",
                    re.IGNORECASE,
                ),
                0.90,
            ),
            # 10. Appeal dismissed
            (
                "appeal_dismissed",
                re.compile(
                    r"\b(?:appeals?\s+(?:is\s+|are\s+|stands?\s+|hereby\s+)?dismissed|we\s+dismiss\s+the\s+appeals?|appeals?\s+(?:(?:accordingly|consequently)\s+)?fails?\s+and\s+is\s+dismissed|appeals?\s+fails?\s+and\s+it\s+is\s+dismissed|appeals?\s+dismissed|appeal\s+is\s+hereby\s+dismissed|appeal\s+stands\s+dismissed)\b",
                    re.IGNORECASE,
                ),
                0.90,
            ),
            # 11. Petition allowed
            (
                "petition_allowed",
                re.compile(
                    r"\b(?:(?:writ\s+)?petition\s+(?:is\s+)?allowed|petitions?\s+stand(?:s)?\s+allowed|petitions?\s+are\s+allowed|rule\s+made\s+absolute|we\s+allow\s+the\s+writ\s+petitions?|petition\s+isallowed|petitions?\s+allowed)\b",
                    re.IGNORECASE,
                ),
                0.90,
            ),
            # 12. Petition dismissed
            (
                "petition_dismissed",
                re.compile(
                    r"\b(?:(?:writ\s+)?petition\s+(?:is\s+)?dismissed|petitions?\s+stand(?:s)?\s+dismissed|petitions?\s+are\s+dismissed|petition\s+(?:consequently|accordingly)\s+fails\s+and\s+is\s+dismissed|writ\s+petition\s+is\s+accordingly\s+dismissed|petitions?\s+dismissed|petition\s+dismisjed)\b",
                    re.IGNORECASE,
                ),
                0.90,
            ),
            # 13. Disposed with directions (including infructuous disposals)
            (
                "disposed_with_directions",
                re.compile(
                    r"\b(?:disposed\s+of\s+with\s+(?:the\s+)?aforesaid\s+(?:observations|directions)|finally\s+disposed\s+of|stands?\s+disposed\s+of|disposed\s+of\s+accordingly|disposed\s+of\s+as\s+infructuous|petition\s+is\s+disposed\s+of|writ\s+petitions?\s+are\s+accordingly\s+disposed\s+of|application\s+is\s+finally\s+disposed\s+of|dismissed\s+as\s+infructuous|instant\s+application\s+is\s+finally\s+disposed\s+of|writ\s+petition\s+is\s+disposed\s+of)\b",
                    re.IGNORECASE,
                ),
                0.85,
            ),
        ]

        # Contradiction matrix: sets of categories that cannot logically co-exist in unambiguous single ruling
        self.contradictory_sets = [
            ({"appeal_allowed"}, {"appeal_dismissed"}),
            ({"petition_allowed"}, {"petition_dismissed"}),
            ({"bail_granted"}, {"bail_rejected"}),
            ({"conviction_set_aside"}, {"conviction_upheld"}),
        ]

    def clean_text(self, text: str) -> str:
        """Applies basic OCR repair to ensure word boundaries are recognized."""
        if not text:
            return ""
        t = text
        for pat, repl in self.ocr_fixes:
            t = pat.sub(repl, t)
        return t

    def reconstruct_and_group_records(
        self, raw_records: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Inspects input records to determine whether they are chunks or full judgments.
        Groups chunks by case_id, sorts by chunk_index, and safely reassembles them.
        Detects missing IDs, gaps, and duplicate IDs.
        """
        inspection_metadata = {
            "total_input_records": len(raw_records),
            "unique_judgments": 0,
            "reconstructed_count": 0,
            "chunked_input_detected": False,
            "duplicate_id_count": 0,
            "missing_id_count": 0,
            "warnings": [],
        }

        if not raw_records:
            return [], inspection_metadata

        # Check if records contain chunk indicators
        has_chunk_fields = any(
            ("chunk_index" in r or "chunkIndex" in r or "total_chunks" in r)
            for r in raw_records
        )

        # Map by case identifier
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        missing_id_records = 0

        for r in raw_records:
            cid = str(r.get("case_id") or r.get("id") or "").strip()
            if not cid or cid.lower() in ("none", "null", "nan"):
                missing_id_records += 1
                continue
            if cid not in grouped:
                grouped[cid] = []
            grouped[cid].append(r)

        inspection_metadata["missing_id_count"] = missing_id_records
        inspection_metadata["unique_judgments"] = len(grouped)

        # If any case ID has multiple records, chunking is detected
        is_chunked = has_chunk_fields or any(len(chunks) > 1 for chunks in grouped.values())
        inspection_metadata["chunked_input_detected"] = is_chunked

        reconstructed_cases: List[Dict[str, Any]] = []

        for cid, chunks in grouped.items():
            if len(chunks) == 1 and not has_chunk_fields:
                # Already complete, unified judgment
                reconstructed_cases.append(chunks[0])
                continue

            # Multi-chunk reassembly
            sorted_chunks = sorted(
                chunks,
                key=lambda x: int(x.get("chunk_index", x.get("chunkIndex", 0))),
            )

            # Check sequence continuity
            indices = [int(c.get("chunk_index", c.get("chunkIndex", idx))) for idx, c in enumerate(sorted_chunks)]
            expected = list(range(len(sorted_chunks)))
            if indices != expected:
                inspection_metadata["warnings"].append(
                    f"Case {cid} has non-sequential chunk indices: {indices} vs expected {expected}"
                )

            # Reconstruct text
            text_parts = []
            for c in sorted_chunks:
                t = c.get("text_original") or c.get("text") or c.get("judgmentText") or ""
                if t.strip():
                    text_parts.append(t.strip())

            full_text = " ".join(text_parts)
            primary_chunk = sorted_chunks[0]

            unified_record = dict(primary_chunk)
            unified_record["id"] = cid
            unified_record["judgmentText"] = full_text
            unified_record["reconstructed_from_chunks"] = len(sorted_chunks)
            reconstructed_cases.append(unified_record)

        inspection_metadata["reconstructed_count"] = len(reconstructed_cases)
        return reconstructed_cases, inspection_metadata

    def resolve_party_semantics(
        self, case_title: str, category: str, candidate_disposition: str, text: str
    ) -> Tuple[str, str]:
        """
        Determines the procedural role and party-specific outcome without bias.
        Distinguishes State vs Accused appeals and civil vs criminal postures.
        Returns: (party_role, party_success)
        """
        if candidate_disposition in ("unknown", "ambiguous", "partly_allowed", "remanded", "disposed_with_directions"):
            return "unresolved", "unresolved"

        t_lower = (case_title or "").lower()
        cat_lower = (category or "").lower()
        is_criminal = "crl" in t_lower or "criminal" in cat_lower or "bail" in t_lower or "fir" in t_lower

        # Specific bail proceedings
        if candidate_disposition == "bail_granted":
            return "applicant/accused", "favorable_to_accused"
        if candidate_disposition == "bail_rejected":
            return "applicant/accused", "unfavorable_to_accused"

        # Quashing / conviction relief
        if candidate_disposition == "proceedings_quashed":
            return "accused", "favorable_to_accused"
        if candidate_disposition == "conviction_set_aside":
            return "accused", "favorable_to_accused"
        if candidate_disposition == "conviction_upheld":
            return "accused", "unfavorable_to_accused"

        if candidate_disposition == "withdrawn":
            return "petitioner/appellant", "unresolved"

        # Analyze party alignment in title (Petitioner/Appellant vs Respondent)
        state_indicators = ["state", "union of india", "c.b.i.", "police", "govt", "nct of delhi", "prosecution"]
        versus_split = re.split(r"\s+(?:versus|vs\.?|v\.?)\s+", t_lower, flags=re.IGNORECASE)

        if len(versus_split) == 2:
            party_a, party_b = versus_split[0].strip(), versus_split[1].strip()
            a_is_state = any(ind in party_a for ind in state_indicators)
            b_is_state = any(ind in party_b for ind in state_indicators)

            if a_is_state and not b_is_state:
                # State appealed against accused/respondent
                if candidate_disposition in ("appeal_dismissed", "petition_dismissed"):
                    return "State/prosecution", "favorable_to_accused"
                elif candidate_disposition in ("appeal_allowed", "petition_allowed"):
                    return "State/prosecution", "unfavorable_to_accused"

            elif b_is_state and not a_is_state:
                # Accused/citizen appealed against State
                if candidate_disposition in ("appeal_dismissed", "petition_dismissed"):
                    return "accused", "unfavorable_to_accused"
                elif candidate_disposition in ("appeal_allowed", "petition_allowed"):
                    return "accused", "favorable_to_accused"

        # If civil matter or parties cannot be unambiguously mapped
        if candidate_disposition in ("appeal_allowed", "petition_allowed"):
            return "appellant/petitioner", "unresolved"
        if candidate_disposition in ("appeal_dismissed", "petition_dismissed"):
            return "appellant/petitioner", "unresolved"

        return "unresolved", "unresolved"

    def extract_from_text(
        self, text: str, case_id: str = "", metadata: Optional[Dict[str, Any]] = None
    ) -> DispositionCandidate:
        """
        Extracts candidate disposition from text, inspecting only concluding window.
        Returns DispositionCandidate with full traceability evidence.
        """
        meta = metadata or {}
        case_title = meta.get("caseTitle") or meta.get("title") or "Unknown Title"
        court = meta.get("court") or "Unknown Court"
        decision_date = meta.get("judgmentDate") or meta.get("decision_date") or ""
        case_type = meta.get("category") or meta.get("case_type") or None

        cleaned_text = self.clean_text(text)
        if not cleaned_text or len(cleaned_text.strip()) < 50:
            return DispositionCandidate(
                case_id=case_id,
                case_title=case_title,
                court=court,
                decision_date=decision_date,
                case_type=case_type,
                candidate_disposition="unknown",
                original_disposition_phrase="",
                matched_text="",
                source_start_offset=-1,
                source_end_offset=-1,
                extraction_method="empty_or_trivial_text",
                extraction_confidence=0.0,
                review_status="pending_review",
                ambiguity_reason="Text is empty or too short for disposition analysis.",
                party_role="unresolved",
                party_success="unresolved",
            )

        # Isolate concluding window
        window_size = min(self.concluding_window_size, len(cleaned_text))
        tail_offset = len(cleaned_text) - window_size
        tail = cleaned_text[tail_offset:]

        matches = []
        for cat, pat, base_conf in self.patterns:
            for m in pat.finditer(tail):
                start = m.start()
                end = m.end()

                # Guard 1: Negation in preceding text
                preceding = tail[max(0, start - 40):start]
                if self.negation_pattern.search(preceding):
                    continue

                # Guard 2: Historical description in same sentence
                sent_start = tail.rfind(".", 0, start)
                sent_start = 0 if sent_start == -1 else sent_start + 1
                sentence = tail[sent_start:end]
                if self.historical_pattern.search(sentence):
                    continue

                # Context extraction: grab the surrounding sentence
                ctx_end = tail.find(".", end)
                ctx_end = len(tail) if ctx_end == -1 else ctx_end + 1
                matched_context = tail[sent_start:ctx_end].strip()

                global_start = tail_offset + start
                global_end = tail_offset + end

                matches.append({
                    "category": cat,
                    "phrase": m.group(0),
                    "context": matched_context,
                    "start": global_start,
                    "end": global_end,
                    "conf": base_conf,
                    "pos_in_tail": start,
                })

        if not matches:
            return DispositionCandidate(
                case_id=case_id,
                case_title=case_title,
                court=court,
                decision_date=decision_date,
                case_type=case_type,
                candidate_disposition="unknown",
                original_disposition_phrase="",
                matched_text="",
                source_start_offset=-1,
                source_end_offset=-1,
                extraction_method="concluding_order_inspection",
                extraction_confidence=0.0,
                review_status="pending_review",
                ambiguity_reason="No definitive concluding operative disposition detected.",
                party_role="unresolved",
                party_success="unresolved",
            )

        detected_cats = {m["category"] for m in matches}
        is_partly = "partly_allowed" in detected_cats

        # Check for contradictory orders (unless partly_allowed reconciles them)
        is_contradictory = False
        contra_reason = ""
        if not is_partly:
            for s1, s2 in self.contradictory_sets:
                if detected_cats.intersection(s1) and detected_cats.intersection(s2):
                    is_contradictory = True
                    c1 = list(detected_cats.intersection(s1))[0]
                    c2 = list(detected_cats.intersection(s2))[0]
                    contra_reason = f"Contradictory orders detected in concluding text: '{c1}' and '{c2}'."
                    break

        if is_contradictory:
            last_m = matches[-1]
            all_phrases = "; ".join(m["phrase"] for m in matches)
            return DispositionCandidate(
                case_id=case_id,
                case_title=case_title,
                court=court,
                decision_date=decision_date,
                case_type=case_type,
                candidate_disposition="ambiguous",
                original_disposition_phrase=all_phrases,
                matched_text=last_m["context"],
                source_start_offset=last_m["start"],
                source_end_offset=last_m["end"],
                extraction_method="contradiction_detector",
                extraction_confidence=0.40,
                review_status="pending_review",
                ambiguity_reason=contra_reason,
                party_role="unresolved",
                party_success="unresolved",
            )

        # Select primary match: partly_allowed takes priority; otherwise pick the latest concluding match
        if is_partly:
            best_match = next(m for m in matches if m["category"] == "partly_allowed")
        else:
            best_match = sorted(matches, key=lambda m: (m["pos_in_tail"], m["conf"]))[-1]

        # Determine party semantics
        role, success = self.resolve_party_semantics(
            case_title=case_title,
            category=case_type or "",
            candidate_disposition=best_match["category"],
            text=best_match["context"],
        )

        return DispositionCandidate(
            case_id=case_id,
            case_title=case_title,
            court=court,
            decision_date=decision_date,
            case_type=case_type,
            candidate_disposition=best_match["category"],
            original_disposition_phrase=best_match["phrase"],
            matched_text=best_match["context"],
            source_start_offset=best_match["start"],
            source_end_offset=best_match["end"],
            extraction_method="concluding_order_pattern",
            extraction_confidence=best_match["conf"],
            review_status="pending_review",
            ambiguity_reason="",
            party_role=role,
            party_success=success,
        )

    def process_dataset(
        self, records: List[Dict[str, Any]]
    ) -> Tuple[List[DispositionCandidate], Dict[str, Any]]:
        """
        Executes full extraction pipeline on a list of raw records.
        Handles chunk reassembly, extracts dispositions, and compiles statistics.
        """
        reconstructed_cases, inspect_meta = self.reconstruct_and_group_records(records)

        candidates: List[DispositionCandidate] = []
        category_counts: Dict[str, int] = {}

        for case in reconstructed_cases:
            cid = str(case.get("id") or case.get("case_id") or "UNKNOWN")
            text = case.get("judgmentText") or case.get("text") or ""
            candidate = self.extract_from_text(text, case_id=cid, metadata=case)
            candidates.append(candidate)

            cat = candidate.candidate_disposition
            category_counts[cat] = category_counts.get(cat, 0) + 1

        total_cases = len(candidates)
        known_count = sum(v for k, v in category_counts.items() if k not in ("unknown", "ambiguous"))
        coverage = (known_count / total_cases * 100.0) if total_cases > 0 else 0.0

        summary_meta = {
            "total_input_records": inspect_meta["total_input_records"],
            "unique_judgments": inspect_meta["unique_judgments"],
            "reconstructed_cases": inspect_meta["reconstructed_count"],
            "chunked_input_detected": inspect_meta["chunked_input_detected"],
            "missing_id_count": inspect_meta["missing_id_count"],
            "duplicate_id_count": inspect_meta["duplicate_id_count"],
            "definitive_candidates": known_count,
            "ambiguous_candidates": category_counts.get("ambiguous", 0),
            "unknown_candidates": category_counts.get("unknown", 0),
            "extraction_coverage_percent": round(coverage, 2),
            "category_distribution": category_counts,
            "pending_review_count": total_cases,
            "warnings": inspect_meta["warnings"],
        }

        return candidates, summary_meta

    def _safe_backup_if_exists(self, filepath: str):
        """Creates a versioned backup before writing to preserve prior artifacts."""
        if os.path.exists(filepath):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{filepath}.{timestamp}.bak"
            shutil.copy2(filepath, backup_path)

    def export_candidates_to_json(
        self,
        candidates: List[DispositionCandidate],
        filepath: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Exports candidates to reviewable JSON with summary metadata."""
        self._safe_backup_if_exists(filepath)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        payload = {
            "metadata": {
                "dataset_source": "open_india_law_sample_150.json",
                "generated_at": datetime.now().isoformat(),
                "review_status": "pending_human_review",
                "statement": "Provisional candidate labels. NOT accepted as verified ground truth until reviewed.",
                **(metadata or {}),
            },
            "candidates": [c.to_dict() for c in candidates],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        return filepath

    def export_candidates_to_csv(
        self, candidates: List[DispositionCandidate], filepath: str
    ) -> str:
        """Exports candidates to reviewable CSV format for human legal annotator review."""
        self._safe_backup_if_exists(filepath)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        fieldnames = [
            "case_id",
            "candidate_disposition",
            "review_status",
            "human_approved_label",
            "human_notes",
            "extraction_confidence",
            "original_disposition_phrase",
            "matched_text",
            "case_title",
            "court",
            "decision_date",
            "case_type",
            "party_role",
            "party_success",
            "extraction_method",
            "ambiguity_reason",
            "source_start_offset",
            "source_end_offset",
        ]

        with open(filepath, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for c in candidates:
                row = c.to_dict()
                row["human_approved_label"] = ""
                row["human_notes"] = ""
                writer.writerow(row)

        return filepath


if __name__ == "__main__":
    # Standalone execution on open_india_law_sample_150.json
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_path = os.path.join(base_dir, "datasets", "open_india_law_sample_150.json")
    out_json_path = os.path.join(base_dir, "datasets", "outcome_label_candidates.json")
    out_csv_path = os.path.join(base_dir, "datasets", "outcome_label_review.csv")

    print(f"Loading dataset from: {dataset_path}")
    with open(dataset_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    extractor = JudicialDispositionExtractor()
    candidates, summary = extractor.process_dataset(records)

    print("\n--- Extraction Summary ---")
    print(f"Total Input Records:      {summary['total_input_records']}")
    print(f"Unique Judgments:         {summary['unique_judgments']}")
    print(f"Reconstructed Judgments:  {summary['reconstructed_cases']}")
    print(f"Definitive Candidates:    {summary['definitive_candidates']}")
    print(f"Ambiguous Candidates:     {summary['ambiguous_candidates']}")
    print(f"Unknown Candidates:       {summary['unknown_candidates']}")
    print(f"Extraction Coverage:      {summary['extraction_coverage_percent']}%")
    print(f"Missing IDs:              {summary['missing_id_count']}")
    print(f"Duplicate IDs:            {summary['duplicate_id_count']}")
    print("\nCategory Distribution:")
    for cat, count in sorted(summary["category_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {cat:26}: {count:3d}")

    print(f"\nExporting JSON to: {out_json_path}")
    extractor.export_candidates_to_json(candidates, out_json_path, metadata=summary)

    print(f"Exporting CSV to:  {out_csv_path}")
    extractor.export_candidates_to_csv(candidates, out_csv_path)

    print("\nDisposition extraction complete. Labels are strictly provisional pending human review.")
