"""
Interactive Human-Reviewed Judicial Outcome Annotation Session Manager
JURIST AI — Feature 4.5: Interactive Human-Reviewed Judicial Outcome Annotation

Manages human-in-the-loop annotation and verification for judicial outcomes:
1. Strict Data Integrity: Zero synthetic label generation or automated approvals.
2. Case-at-a-time review with resume functionality (prioritizing Batch 1 definitive candidates).
3. Complete provenance and audit trail (primary reviewer, second reviewer, lead adjudicator).
4. Full legal disposition taxonomy and procedural party success validation.
5. Synchronization between JSON queue and CSV review records with SHA-256 source integrity check.
6. Progress dashboard and training readiness validation integration.
"""

import os
import sys
import json
import csv
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import Counter

try:
    from app.prediction.risk_prioritized_queue import RiskPrioritizer, RiskTier
except ImportError:
    try:
        from risk_prioritized_queue import RiskPrioritizer, RiskTier
    except ImportError:
        from .risk_prioritized_queue import RiskPrioritizer, RiskTier

logger = logging.getLogger("OutcomeAnnotationSession")

# Canonical legal disposition classes
VALID_DISPOSITIONS = [
    "appeal_allowed",
    "appeal_dismissed",
    "petition_allowed",
    "petition_dismissed",
    "partly_allowed",
    "bail_granted",
    "bail_rejected",
    "disposed_procedural",
    "disposed_with_substantive_directions",
    "dismissed_as_infructuous",
    "withdrawn",
    "remanded",
    "other",
    "uncertain",
]

# Canonical successful party roles
VALID_SUCCESSFUL_PARTIES = [
    "accused",
    "state_prosecution",
    "petitioner",
    "respondent",
    "none_procedural",
    "unresolved",
]

# Feature 4.14: Dual-Model Training Gatekeeper Eligibility Sets

# Model A — Judicial Disposition (Merits-only supervised prediction)
MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS = [
    "appeal_allowed",
    "appeal_dismissed",
    "petition_allowed",
    "petition_dismissed",
]

MODEL_A_EXCLUDED_PROCEDURAL_DISPOSITIONS = [
    "remanded",
    "dismissed_as_infructuous",
    "uncertain",
    "withdrawn",
    "partly_allowed",
    "disposed_procedural",
    "disposed_with_substantive_directions",
    "other",
    "unknown",
    "unknown_truncated_text",
    "interlocutory_reference",
    "ambiguous",
]

# Model B — Successful Party (Substantive-party supervised prediction)
MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES = [
    "respondent",
    "petitioner",
    "state_prosecution",
    "accused",
]

MODEL_B_EXCLUDED_NON_SUBSTANTIVE_PARTIES = [
    "none_procedural",
    "unresolved",
    "unknown",
]

# Review statuses
VALID_REVIEW_STATUSES = [
    "pending_review",
    "approved",
    "corrected",
    "rejected",
    "uncertain",
    "deferred_needs_full_text",
    "disputed",
    "adjudicated_approved",
]

# Expected cryptographic hashes for original benchmark datasets
KNOWN_SOURCE_HASHES = {
    "open_india_law_sample_150.json": "006ea5b5bff63dc5e6423bf44273ae0a0dd23b557d22b7595212c8b8d19bf42b",
    "indian_judgments.json": "4c12413790bda140433695ce83fbb6a8c66542db86dc1fbc33646fe11409f849"
}


class AnnotationValidationError(ValueError):
    """Raised when an annotation payload fails validation rules."""
    pass


class ConfirmationRequiredError(ValueError):
    """Raised when an action is executed without explicit user confirmation."""
    pass


class OutcomeAnnotationSessionManager:
    """
    Session manager orchestrating human review of judicial outcome candidates.
    """

    def __init__(
        self,
        datasets_dir: Optional[str] = None,
        candidates_json_path: Optional[str] = None,
        review_csv_path: Optional[str] = None,
        source_json_path: Optional[str] = None,
    ):
        if datasets_dir is None:
            self.datasets_dir = Path(__file__).resolve().parent.parent / "datasets"
        else:
            self.datasets_dir = Path(datasets_dir)

        self.candidates_json_path = (
            Path(candidates_json_path)
            if candidates_json_path
            else self.datasets_dir / "outcome_label_candidates_v2.json"
        )
        self.review_csv_path = (
            Path(review_csv_path)
            if review_csv_path
            else self.datasets_dir / "outcome_label_review_v2.csv"
        )
        self.source_json_path = (
            Path(source_json_path)
            if source_json_path
            else self.datasets_dir / "open_india_law_sample_150.json"
        )

        self.records: List[Dict[str, Any]] = []
        self.records_by_id: Dict[str, Dict[str, Any]] = {}
        self.source_cases: Dict[str, Dict[str, Any]] = {}
        self.batch_1_ids: Set[str] = set()
        self.risk_prioritizer = RiskPrioritizer()

        self._load_data()

    def _load_data(self):
        """Loads candidates, review records, source judgments, and batch inventories."""
        # 1. Load source judgments if present
        if self.source_json_path.exists():
            with open(self.source_json_path, "r", encoding="utf-8") as f:
                raw_cases = json.load(f)
                self.source_cases = {c["id"]: c for c in raw_cases if "id" in c}

        # 2. Load Batch 1 IDs
        batch_1_path = self.datasets_dir / "review_batches" / "batch_1_definitive_candidates.json"
        if batch_1_path.exists():
            try:
                with open(batch_1_path, "r", encoding="utf-8") as f:
                    b1_data = json.load(f)
                    b1_recs = b1_data.get("records", b1_data.get("candidates", []))
                    self.batch_1_ids = set(r.get("case_id") for r in b1_recs if r.get("case_id"))
            except Exception as e:
                logger.warning(f"Could not load batch_1 metadata: {e}")

        # 3. Load candidate JSON queue
        if self.candidates_json_path.exists():
            with open(self.candidates_json_path, "r", encoding="utf-8") as f:
                cand_data = json.load(f)
                self.records = cand_data.get("records", [])
        elif self.review_csv_path.exists():
            # Fallback to CSV if JSON doesn't exist
            with open(self.review_csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.records = list(reader)
        else:
            raise FileNotFoundError(f"Neither {self.candidates_json_path} nor {self.review_csv_path} found.")

        # Ensure all records have an audit_history field
        for r in self.records:
            if "audit_history" not in r:
                r["audit_history"] = []
            self.records_by_id[r["case_id"]] = r

    def verify_source_integrity(self) -> Dict[str, bool]:
        """Verifies that source datasets have not been altered (cryptographic SHA-256 match)."""
        results: Dict[str, bool] = {}
        for filename, expected_hash in KNOWN_SOURCE_HASHES.items():
            fpath = self.datasets_dir / filename
            if fpath.exists():
                with open(fpath, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                results[filename] = file_hash == expected_hash
            else:
                results[filename] = False
        return results

    def get_progress_dashboard(self) -> Dict[str, Any]:
        """Calculates real-time progress across all 150 candidates and Batch 1."""
        total = len(self.records)
        b1_total = len(self.batch_1_ids)

        approved = 0
        corrected = 0
        rejected = 0
        uncertain = 0
        deferred = 0
        disputed = 0
        pending = 0
        adjudicated = 0

        b1_approved = 0
        b1_pending = 0

        verified_dispositions: Dict[str, int] = {}
        successful_party_distribution: Dict[str, int] = {}
        reviewer_wise_progress: Dict[str, Dict[str, int]] = {}

        for r in self.records:
            status = (r.get("review_status") or "pending_review").strip().lower()
            cid = r.get("case_id")
            label = (r.get("human_approved_label") or "").strip()
            party = (r.get("human_successful_party") or "").strip()
            reviewer = (r.get("reviewer_reference") or r.get("adjudicator_id") or "").strip()

            if status in ["approved", "corrected", "adjudicated_approved"]:
                if party:
                    successful_party_distribution[party] = successful_party_distribution.get(party, 0) + 1
                if reviewer:
                    rev_stats = reviewer_wise_progress.setdefault(reviewer, {"approved": 0, "corrected": 0, "adjudicated": 0, "total": 0})
                    rev_stats["total"] += 1
                    if status == "approved":
                        rev_stats["approved"] += 1
                    elif status == "corrected":
                        rev_stats["corrected"] += 1
                    elif status == "adjudicated_approved":
                        rev_stats["adjudicated"] += 1

            if status == "approved":
                approved += 1
                if cid in self.batch_1_ids:
                    b1_approved += 1
                if label:
                    verified_dispositions[label] = verified_dispositions.get(label, 0) + 1
            elif status == "corrected":
                corrected += 1
                if cid in self.batch_1_ids:
                    b1_approved += 1
                if label:
                    verified_dispositions[label] = verified_dispositions.get(label, 0) + 1
            elif status == "adjudicated_approved":
                adjudicated += 1
                if cid in self.batch_1_ids:
                    b1_approved += 1
                if label:
                    verified_dispositions[label] = verified_dispositions.get(label, 0) + 1
            elif status == "rejected":
                rejected += 1
            elif status == "uncertain":
                uncertain += 1
            elif status in ["deferred_needs_full_text", "unknown"]:
                deferred += 1
            elif status == "disputed":
                disputed += 1
            else:
                pending += 1
                if cid in self.batch_1_ids:
                    b1_pending += 1

        total_verified = approved + corrected + adjudicated
        remaining = pending + disputed

        # Calculate risk-tier stratification progress
        stratified = self.risk_prioritizer.stratify_queue(self.records, self.source_cases, only_pending=False)
        risk_tier_progress = {}
        for t_key in [
            RiskTier.TIER_1_DEFINITIVE_MERITS,
            RiskTier.TIER_2_MODERATE_RISK_BAIL_DIRECTIVES,
            RiskTier.TIER_3_HIGH_RISK_PROCEDURAL,
            RiskTier.TIER_4_CRITICAL_DEFERRED,
        ]:
            t_records = stratified.get(t_key, [])
            t_total = len(t_records)
            t_verified = sum(
                1 for r in t_records
                if (r.get("review_status") or "").strip().lower() in ["approved", "corrected", "adjudicated_approved"]
            )
            t_pending = sum(
                1 for r in t_records
                if (r.get("review_status") or "pending_review").strip().lower() == "pending_review"
            )
            t_other = t_total - t_verified - t_pending
            risk_tier_progress[t_key] = {
                "label": RiskTier.LABELS[t_key],
                "total": t_total,
                "verified": t_verified,
                "pending": t_pending,
                "other": t_other,
                "percent_complete": round((t_verified / t_total * 100) if t_total else 0.0, 1),
            }

        return {
            "total_candidates": total,
            "batch_1_definitive_candidates": b1_total if b1_total else 99,
            "approved": approved,
            "corrected": corrected,
            "adjudicated_approved": adjudicated,
            "total_verified": total_verified,
            "pending": pending,
            "rejected": rejected,
            "uncertain": uncertain,
            "deferred": deferred,
            "disputed": disputed,
            "remaining_candidates": remaining,
            "verified_disposition_distribution": verified_dispositions,
            "successful_party_distribution": successful_party_distribution,
            "reviewer_wise_progress": reviewer_wise_progress,
            "batch_1_progress": {
                "total": b1_total if b1_total else 99,
                "verified": b1_approved,
                "pending": b1_pending,
                "percent_complete": round((b1_approved / b1_total * 100) if b1_total else 0.0, 1)
            },
            "risk_tier_progress": risk_tier_progress,
            "source_integrity": self.verify_source_integrity()
        }

    def get_next_pending(self, batch_filter: Optional[str] = "batch_1") -> Optional[Dict[str, Any]]:
        """
        Returns the next case with review_status == 'pending_review'.
        If batch_filter == 'batch_1', prioritizes Batch 1 definitive candidates.
        """
        for r in self.records:
            cid = r.get("case_id")
            status = (r.get("review_status") or "pending_review").strip().lower()
            if status == "pending_review":
                if batch_filter == "batch_1":
                    if cid in self.batch_1_ids:
                        return self.get_case_view(cid)
                else:
                    return self.get_case_view(cid)

        # If batch_1 has no pending but overall does
        if batch_filter == "batch_1":
            for r in self.records:
                status = (r.get("review_status") or "pending_review").strip().lower()
                if status == "pending_review":
                    return self.get_case_view(r.get("case_id"))

        return None

    def get_case_view(self, case_id: str) -> Dict[str, Any]:
        """
        Retrieves a complete view of a case: metadata, source judgment text,
        extracted operative order candidate, and review state.
        """
        record = self.records_by_id.get(case_id)
        if not record:
            raise KeyError(f"Case ID '{case_id}' not found in candidate review records.")

        source = self.source_cases.get(case_id, {})
        judgment_text = source.get("judgmentText", "")

        # Extract concluding tail (final 3,000 characters) for quick operative inspection
        tail_chars = 3000
        concluding_tail = judgment_text[-tail_chars:] if len(judgment_text) > tail_chars else judgment_text

        # Evaluate risk assessment
        risk = self.risk_prioritizer.assess_case_risk(record, judgment_text)

        return {
            "case_id": case_id,
            "case_title": record.get("case_title") or source.get("caseTitle", "Untitled"),
            "court": record.get("court") or source.get("court", "Unknown Court"),
            "decision_date": record.get("decision_date") or source.get("judgmentDate", "Unknown Date"),
            "proceeding_type": record.get("proceeding_type", "unknown"),
            "category": source.get("category", "General Law"),
            "legal_provisions": source.get("legalProvisions", []),
            "procedural_role": record.get("procedural_role", "unresolved"),
            "is_batch_1": case_id in self.batch_1_ids,
            "machine_candidate": {
                "original_disposition": record.get("original_disposition"),
                "normalized_disposition": record.get("normalized_disposition"),
                "successful_party": record.get("successful_party"),
                "extracted_phrase": record.get("original_disposition_phrase"),
                "matched_text": record.get("matched_text"),
                "parser_confidence": float(record.get("parser_confidence", 0.0)),
                "recommended_action": record.get("recommended_action"),
                "ambiguity_reason": record.get("ambiguity_reason")
            },
            "risk_assessment": risk,
            "risk_tier": risk["tier"],
            "risk_tier_label": risk["label"],
            "risk_flags": risk["flags"],
            "recommended_review_mode": risk["recommended_review_mode"],
            "judgment_text_length": len(judgment_text),
            "concluding_tail": concluding_tail,
            "operative_order_excerpt": concluding_tail,
            "full_judgment_text": judgment_text,
            "current_review": {
                "review_status": record.get("review_status", "pending_review"),
                "human_approved_label": record.get("human_approved_label", ""),
                "human_successful_party": record.get("human_successful_party", ""),
                "human_notes": record.get("human_notes", ""),
                "reviewer_reference": record.get("reviewer_reference", ""),
                "evidence_reference": record.get("evidence_reference", ""),
                "audit_history": record.get("audit_history", [])
            }
        }

    def get_batch_view(
        self,
        batch_size: int = 5,
        tier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves a batch of pending cases (up to batch_size, default 5)
        filtered by risk tier or prioritized across tiers (Tier 1 -> Tier 2 -> Tier 3 -> Tier 4).
        Enriches each case with operative order excerpts, risk warnings, and machine predictions.
        """
        tier_normalized = None
        if tier:
            t = str(tier).strip().lower()
            if t in ["1", "tier1", "tier_1"]:
                tier_normalized = RiskTier.TIER_1_DEFINITIVE_MERITS
            elif t in ["2", "tier2", "tier_2"]:
                tier_normalized = RiskTier.TIER_2_MODERATE_RISK_BAIL_DIRECTIVES
            elif t in ["3", "tier3", "tier_3"]:
                tier_normalized = RiskTier.TIER_3_HIGH_RISK_PROCEDURAL
            elif t in ["4", "tier4", "tier_4"]:
                tier_normalized = RiskTier.TIER_4_CRITICAL_DEFERRED
            elif t in RiskTier.LABELS:
                tier_normalized = t

        prioritized = self.risk_prioritizer.get_prioritized_pending_queue(
            self.records,
            self.source_cases,
            tier_filter=tier_normalized
        )

        selected = prioritized[:batch_size]
        batch: List[Dict[str, Any]] = []
        for r in selected:
            cid = r["case_id"]
            view = self.get_case_view(cid)
            batch.append(view)

        return batch

    def _validate_decision_payload(self, decision: Dict[str, Any]) -> None:
        """
        Validates an individual decision payload without modifying state.
        Raises AnnotationValidationError on any validation discrepancy.
        """
        if not isinstance(decision, dict):
            raise AnnotationValidationError("Each decision payload must be a dictionary.")

        case_id = decision.get("case_id")
        if not case_id or case_id not in self.records_by_id:
            raise AnnotationValidationError(f"Invalid or missing case_id: '{case_id}'.")

        record = self.records_by_id[case_id]
        action = str(decision.get("action", "")).strip().lower()

        if action not in ["accept", "correct", "reject", "uncertain", "defer"]:
            raise AnnotationValidationError(
                f"Unsupported action '{action}' for case '{case_id}'. Permitted: accept, correct, reject, uncertain, defer."
            )

        evidence = str(decision.get("evidence", "")).strip()
        notes = str(decision.get("notes", "")).strip()

        if action == "accept":
            candidate_disp = record.get("normalized_disposition") or record.get("original_disposition")
            candidate_party = record.get("successful_party")

            final_disp = decision.get("disposition") or candidate_disp
            final_party = decision.get("successful_party") or candidate_party

            if not final_disp or final_disp not in VALID_DISPOSITIONS:
                raise AnnotationValidationError(f"Invalid candidate disposition '{final_disp}' for accept on {case_id}.")
            if final_disp in ["unknown", "unknown_truncated_text", "interlocutory_reference", "ambiguous"]:
                raise AnnotationValidationError(
                    f"Cannot 'accept' provisional class '{final_disp}' as approved for {case_id}. Use 'correct' or 'uncertain'."
                )
            if not final_party or final_party not in VALID_SUCCESSFUL_PARTIES:
                raise AnnotationValidationError(f"Invalid successful_party '{final_party}' for case {case_id}.")
            if not evidence or len(evidence) < 5:
                raise AnnotationValidationError(f"Evidence quote from judgment text (at least 5 chars) is mandatory for accept on {case_id}.")

        elif action == "correct":
            disposition = decision.get("disposition")
            successful_party = decision.get("successful_party")
            if not disposition or disposition not in VALID_DISPOSITIONS:
                raise AnnotationValidationError(f"Disposition '{disposition}' must be one of {VALID_DISPOSITIONS} for {case_id}.")
            if not successful_party or successful_party not in VALID_SUCCESSFUL_PARTIES:
                raise AnnotationValidationError(f"Successful party '{successful_party}' must be one of {VALID_SUCCESSFUL_PARTIES} for {case_id}.")
            if not evidence or len(evidence) < 5:
                raise AnnotationValidationError(f"Evidence quote (at least 5 chars) is mandatory for correction on {case_id}.")
            if not notes or len(notes) < 5:
                raise AnnotationValidationError(f"Justification notes (at least 5 chars) are required for correction on {case_id}.")

        elif action == "reject":
            if not notes or len(notes) < 5:
                raise AnnotationValidationError(f"Rejection reason (at least 5 chars in notes) is required for {case_id}.")

        elif action in ["uncertain", "defer"]:
            pass

    def _apply_review_decision(
        self,
        case_id: str,
        action: str,
        reviewer_id: str,
        disposition: Optional[str] = None,
        successful_party: Optional[str] = None,
        evidence: str = "",
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Applies a validated review decision to in-memory state and records the audit event.
        Does not invoke self._save() directly to allow atomic batch updates.
        """
        record = self.records_by_id[case_id]
        action = action.strip().lower()
        old_status = record.get("review_status", "pending_review")
        timestamp = datetime.now(timezone.utc).isoformat()

        if action == "accept":
            candidate_disp = record.get("normalized_disposition") or record.get("original_disposition")
            candidate_party = record.get("successful_party")
            final_disp = disposition or candidate_disp
            final_party = successful_party or candidate_party

            record["human_approved_label"] = final_disp
            record["human_successful_party"] = final_party
            record["human_notes"] = notes.strip() or f"Accepted machine candidate '{final_disp}'."
            record["evidence_reference"] = evidence.strip()
            record["reviewer_reference"] = reviewer_id.strip()
            record["review_status"] = "approved"

        elif action == "correct":
            record["human_approved_label"] = disposition
            record["human_successful_party"] = successful_party
            record["human_notes"] = notes.strip()
            record["evidence_reference"] = evidence.strip()
            record["reviewer_reference"] = reviewer_id.strip()
            record["review_status"] = "corrected"

        elif action == "reject":
            record["human_approved_label"] = "rejected"
            record["human_successful_party"] = "unresolved"
            record["human_notes"] = notes.strip()
            record["evidence_reference"] = evidence.strip() or "Extractor false-positive"
            record["reviewer_reference"] = reviewer_id.strip()
            record["review_status"] = "rejected"

        elif action in ["uncertain", "defer"]:
            record["human_approved_label"] = "uncertain"
            record["human_successful_party"] = "unresolved"
            record["human_notes"] = notes.strip() or "Marked uncertain/deferred pending full text."
            record["evidence_reference"] = evidence.strip() or "Truncated or ambiguous holding"
            record["reviewer_reference"] = reviewer_id.strip()
            record["review_status"] = "deferred_needs_full_text" if action == "defer" else "uncertain"

        audit_event = {
            "timestamp": timestamp,
            "action": action,
            "reviewer_id": reviewer_id.strip(),
            "previous_status": old_status,
            "new_status": record["review_status"],
            "disposition": record["human_approved_label"],
            "successful_party": record["human_successful_party"],
            "notes": record["human_notes"],
            "evidence": record["evidence_reference"]
        }
        record.setdefault("audit_history", []).append(audit_event)
        return record

    def submit_review(
        self,
        case_id: str,
        action: str,
        reviewer_id: str,
        disposition: Optional[str] = None,
        successful_party: Optional[str] = None,
        evidence: str = "",
        notes: str = "",
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Submits a primary review decision for an individual case.
        Requires explicit confirmation (confirm=True) to commit.
        """
        if not confirm:
            raise ConfirmationRequiredError(
                "Explicit confirmation required: pass confirm=True to commit this annotation."
            )

        if not reviewer_id or len(reviewer_id.strip()) < 2:
            raise AnnotationValidationError("Valid reviewer_id (at least 2 characters) is required.")

        decision = {
            "case_id": case_id,
            "action": action,
            "disposition": disposition,
            "successful_party": successful_party,
            "evidence": evidence,
            "notes": notes,
        }
        self._validate_decision_payload(decision)
        record = self._apply_review_decision(
            case_id=case_id,
            action=action,
            reviewer_id=reviewer_id,
            disposition=disposition,
            successful_party=successful_party,
            evidence=evidence,
            notes=notes,
        )
        self._save()
        return record

    def submit_batch_reviews(
        self,
        batch_decisions: List[Dict[str, Any]],
        reviewer_id: str,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Submits decisions for an entire batch of cases atomically.
        Guarantees:
        1. confirm=True is strictly required.
        2. Non-empty list of individual decisions with valid case_id, action, and evidence.
        3. Pre-validates ALL decisions in the batch before applying changes (fail-fast, zero partial writes).
        4. No bulk auto-approval: every item requires an individual explicit decision.
        5. Preserves independent audit history for every case.
        """
        if not confirm:
            raise ConfirmationRequiredError(
                "Explicit confirmation required: pass confirm=True to commit this batch."
            )

        if not reviewer_id or len(reviewer_id.strip()) < 2:
            raise AnnotationValidationError("Valid reviewer_id (at least 2 characters) is required.")

        if not batch_decisions or not isinstance(batch_decisions, list):
            raise AnnotationValidationError("batch_decisions must be a non-empty list of decisions.")

        # Ensure no duplicate case IDs within the same batch submission
        seen_case_ids: Set[str] = set()
        for d in batch_decisions:
            cid = d.get("case_id")
            if cid in seen_case_ids:
                raise AnnotationValidationError(f"Duplicate case_id '{cid}' in batch_decisions.")
            seen_case_ids.add(cid)
            self._validate_decision_payload(d)

        results: List[Dict[str, Any]] = []
        for d in batch_decisions:
            rec = self._apply_review_decision(
                case_id=d["case_id"],
                action=d["action"],
                reviewer_id=reviewer_id,
                disposition=d.get("disposition"),
                successful_party=d.get("successful_party"),
                evidence=d.get("evidence", ""),
                notes=d.get("notes", ""),
            )
            results.append(rec)

        self._save()
        return {
            "committed_count": len(results),
            "reviewer_id": reviewer_id.strip(),
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def submit_second_review(
        self,
        case_id: str,
        second_reviewer_id: str,
        disposition: str,
        successful_party: str,
        evidence: str = "",
        notes: str = "",
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Submits an independent second review for cross-validation.
        If second reviewer disagrees with primary reviewer, flags case as 'disputed'.
        """
        if not confirm:
            raise ConfirmationRequiredError("Explicit confirmation required: pass confirm=True.")

        if not second_reviewer_id or len(second_reviewer_id.strip()) < 2:
            raise AnnotationValidationError("Valid second_reviewer_id required.")

        record = self.records_by_id.get(case_id)
        if not record:
            raise KeyError(f"Case ID '{case_id}' not found.")

        if disposition not in VALID_DISPOSITIONS:
            raise AnnotationValidationError(f"Invalid disposition '{disposition}'.")
        if successful_party not in VALID_SUCCESSFUL_PARTIES:
            raise AnnotationValidationError(f"Invalid successful_party '{successful_party}'.")

        primary_disp = record.get("human_approved_label")
        primary_party = record.get("human_successful_party")
        primary_reviewer = record.get("reviewer_reference")

        if second_reviewer_id == primary_reviewer:
            raise AnnotationValidationError("Second reviewer must be distinct from primary reviewer.")

        record["second_reviewer_id"] = second_reviewer_id.strip()
        record["second_reviewer_disposition"] = disposition
        record["second_reviewer_party"] = successful_party
        record["second_reviewer_notes"] = notes.strip()

        old_status = record.get("review_status", "pending_review")
        timestamp = datetime.now(timezone.utc).isoformat()

        # Check for consensus vs dispute
        if primary_disp and (primary_disp != disposition or primary_party != successful_party):
            record["review_status"] = "disputed"
            record["ambiguity_reason"] = (
                f"Dispute between {primary_reviewer} ({primary_disp}, {primary_party}) and "
                f"{second_reviewer_id} ({disposition}, {successful_party}). Requires lead adjudication."
            )
        else:
            record["review_status"] = "approved"

        audit_event = {
            "timestamp": timestamp,
            "action": "second_review",
            "reviewer_id": second_reviewer_id.strip(),
            "previous_status": old_status,
            "new_status": record["review_status"],
            "disposition": disposition,
            "successful_party": successful_party,
            "notes": notes.strip(),
            "dispute_detected": record["review_status"] == "disputed"
        }
        record.setdefault("audit_history", []).append(audit_event)

        self._save()
        return record

    def adjudicate_dispute(
        self,
        case_id: str,
        adjudicator_id: str,
        adjudicated_disposition: str,
        adjudicated_party: str,
        adjudication_notes: str,
        confirm: bool = False
    ) -> Dict[str, Any]:
        """
        Resolves a disputed review between conflicting annotators through senior adjudication.
        """
        if not confirm:
            raise ConfirmationRequiredError("Explicit confirmation required: pass confirm=True.")

        if not adjudicator_id or len(adjudicator_id.strip()) < 2:
            raise AnnotationValidationError("Valid adjudicator_id required.")

        record = self.records_by_id.get(case_id)
        if not record:
            raise KeyError(f"Case ID '{case_id}' not found.")

        if adjudicated_disposition not in VALID_DISPOSITIONS:
            raise AnnotationValidationError(f"Invalid disposition '{adjudicated_disposition}'.")
        if adjudicated_party not in VALID_SUCCESSFUL_PARTIES:
            raise AnnotationValidationError(f"Invalid party '{adjudicated_party}'.")
        if not adjudication_notes or len(adjudication_notes.strip()) < 10:
            raise AnnotationValidationError("Detailed adjudication ruling (at least 10 chars) is required.")

        old_status = record.get("review_status")
        timestamp = datetime.now(timezone.utc).isoformat()

        record["adjudicator_id"] = adjudicator_id.strip()
        record["adjudicated_disposition"] = adjudicated_disposition
        record["adjudicated_party"] = adjudicated_party
        record["adjudication_notes"] = adjudication_notes.strip()
        record["human_approved_label"] = adjudicated_disposition
        record["human_successful_party"] = adjudicated_party
        record["human_notes"] = f"[ADJUDICATED] {adjudication_notes.strip()}"
        record["review_status"] = "adjudicated_approved"

        audit_event = {
            "timestamp": timestamp,
            "action": "adjudicate",
            "adjudicator_id": adjudicator_id.strip(),
            "previous_status": old_status,
            "new_status": "adjudicated_approved",
            "adjudicated_disposition": adjudicated_disposition,
            "adjudicated_party": adjudicated_party,
            "notes": adjudication_notes.strip()
        }
        record.setdefault("audit_history", []).append(audit_event)

        self._save()
        return record

    def check_training_readiness(
        self,
        min_total_verified: int = 30,
        min_minority_samples: int = 5
    ) -> Dict[str, Any]:
        """
        Feature 4.14: Dual-Model Training Gatekeeper.
        Independently checks whether the human-reviewed corpus satisfies empirical ML training
        prerequisites for both supervised tasks:
          - Model A: Judicial Disposition (merits-eligible only)
          - Model B: Successful Party (substantive-party victories only)

        Overall statistical training is unlocked ONLY when both models independently pass.
        Procedural exclusions (remanded, infructuous, none_procedural, unresolved) are strictly
        excluded from training datasets and from global / minority sample thresholds.
        """
        dashboard = self.get_progress_dashboard()
        total_verified = dashboard["total_verified"]

        # Only evaluate records with approved, corrected, or adjudicated review status
        verified_records = [
            r for r in self.records
            if (r.get("review_status") or "").strip().lower() in ["approved", "corrected", "adjudicated_approved"]
        ]

        # -------------------------------------------------------------
        # 1. Evaluate Model A — Judicial Disposition (Merits-Only)
        # -------------------------------------------------------------
        model_a_eligible_dist: Dict[str, int] = {}
        model_a_excluded_dist: Dict[str, int] = {}
        model_a_eligible_count = 0
        model_a_excluded_count = 0

        for r in verified_records:
            disp = (r.get("human_approved_label") or "").strip()
            if not disp:
                continue
            if disp in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS:
                model_a_eligible_dist[disp] = model_a_eligible_dist.get(disp, 0) + 1
                model_a_eligible_count += 1
            else:
                model_a_excluded_dist[disp] = model_a_excluded_dist.get(disp, 0) + 1
                model_a_excluded_count += 1

        model_a_blockers: List[str] = []
        is_model_a_ready = True

        if model_a_eligible_count < min_total_verified:
            is_model_a_ready = False
            model_a_blockers.append(
                f"Model A (Judicial Disposition) insufficient eligible records: {model_a_eligible_count} verified merits samples (minimum {min_total_verified} required)."
            )

        if len(model_a_eligible_dist) < 2:
            is_model_a_ready = False
            model_a_blockers.append(
                f"Model A (Judicial Disposition) fewer than 2 distinct eligible classes represented. Currently found: {list(model_a_eligible_dist.keys())}."
            )
            min_a_class_count = min(model_a_eligible_dist.values()) if model_a_eligible_dist else 0
        else:
            min_a_class_count = min(model_a_eligible_dist.values())
            if min_a_class_count < min_minority_samples:
                is_model_a_ready = False
                model_a_blockers.append(
                    f"Model A (Judicial Disposition) minority class representation is {min_a_class_count} (minimum {min_minority_samples} required)."
                )

        model_a_status = {
            "name": "Model A — Judicial Disposition",
            "target": "judicial_disposition",
            "is_training_eligible": is_model_a_ready,
            "eligible_count": model_a_eligible_count,
            "minimum_required": min_total_verified,
            "min_minority_samples": min_minority_samples,
            "minority_class_count": min_a_class_count,
            "verified_classes_count": len(model_a_eligible_dist),
            "class_distribution": model_a_eligible_dist,
            "excluded_count": model_a_excluded_count,
            "excluded_distribution": model_a_excluded_dist,
            "blockers": model_a_blockers,
        }

        # -------------------------------------------------------------
        # 2. Evaluate Model B — Successful Party (Substantive-Only)
        # -------------------------------------------------------------
        model_b_eligible_dist: Dict[str, int] = {}
        model_b_excluded_dist: Dict[str, int] = {}
        model_b_eligible_count = 0
        model_b_excluded_count = 0

        for r in verified_records:
            party = (r.get("human_successful_party") or "").strip()
            if not party:
                continue
            if party in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES:
                model_b_eligible_dist[party] = model_b_eligible_dist.get(party, 0) + 1
                model_b_eligible_count += 1
            else:
                model_b_excluded_dist[party] = model_b_excluded_dist.get(party, 0) + 1
                model_b_excluded_count += 1

        model_b_blockers: List[str] = []
        is_model_b_ready = True

        if model_b_eligible_count < min_total_verified:
            is_model_b_ready = False
            model_b_blockers.append(
                f"Model B (Successful Party) insufficient eligible records: {model_b_eligible_count} verified substantive samples (minimum {min_total_verified} required)."
            )

        if len(model_b_eligible_dist) < 2:
            is_model_b_ready = False
            model_b_blockers.append(
                f"Model B (Successful Party) fewer than 2 distinct eligible classes represented. Currently found: {list(model_b_eligible_dist.keys())}."
            )
            min_b_class_count = min(model_b_eligible_dist.values()) if model_b_eligible_dist else 0
        else:
            min_b_class_count = min(model_b_eligible_dist.values())
            if min_b_class_count < min_minority_samples:
                is_model_b_ready = False
                model_b_blockers.append(
                    f"Model B (Successful Party) minority class representation is {min_b_class_count} (minimum {min_minority_samples} required)."
                )

        model_b_status = {
            "name": "Model B — Successful Party",
            "target": "successful_party",
            "is_training_eligible": is_model_b_ready,
            "eligible_count": model_b_eligible_count,
            "minimum_required": min_total_verified,
            "min_minority_samples": min_minority_samples,
            "minority_class_count": min_b_class_count,
            "verified_classes_count": len(model_b_eligible_dist),
            "class_distribution": model_b_eligible_dist,
            "excluded_count": model_b_excluded_count,
            "excluded_distribution": model_b_excluded_dist,
            "blockers": model_b_blockers,
        }

        # -------------------------------------------------------------
        # 3. Overall Gatekeeper Decision
        # -------------------------------------------------------------
        is_overall_ready = is_model_a_ready and is_model_b_ready
        combined_blockers = model_a_blockers + model_b_blockers

        return {
            "is_training_eligible": is_overall_ready,
            "total_verified_count": total_verified,
            "minimum_required": min_total_verified,
            "min_minority_samples": min_minority_samples,
            "model_a": model_a_status,
            "model_b": model_b_status,
            "model_a_disposition": model_a_status,
            "model_b_successful_party": model_b_status,
            # Backward-compatible fields
            "verified_classes_count": len(model_a_eligible_dist),
            "class_distribution": model_a_eligible_dist,
            "remaining_pending": dashboard["pending"],
            "blockers": combined_blockers,
            "recommended_mode": "statistical_verified" if is_overall_ready else "qualitative_research_mode"
        }

    def get_eligible_training_records(self, target: str = "model_a") -> List[Dict[str, Any]]:
        """
        Feature 4.14: Returns only verified records eligible for training the requested model target:
          - target in ["model_a", "disposition"]: records with human_approved_label in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS
          - target in ["model_b", "successful_party"]: records with human_successful_party in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES
        Excludes pending, uncertain, rejected, and non-trainable procedural annotations.
        """
        verified = [
            r for r in self.records
            if (r.get("review_status") or "").strip().lower() in ["approved", "corrected", "adjudicated_approved"]
        ]
        target_norm = target.strip().lower()
        if target_norm in ["model_a", "disposition", "judicial_disposition"]:
            return [
                r for r in verified
                if (r.get("human_approved_label") or "").strip() in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS
            ]
        elif target_norm in ["model_b", "successful_party", "party"]:
            return [
                r for r in verified
                if (r.get("human_successful_party") or "").strip() in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES
            ]
        else:
            raise ValueError(f"Unknown target '{target}'. Permitted: 'model_a' ('disposition') or 'model_b' ('successful_party').")

    def _save(self):
        """
        Persists updated records to outcome_label_candidates_v2.json and outcome_label_review_v2.csv.
        """
        # 1. Save JSON
        json_data = {
            "metadata": {
                "batch_name": "Master Human Review Queue (150 Cases)",
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "record_count": len(self.records),
                "review_status": "in_progress",
                "protocol_reference": "ml-service/app/prediction/outcome_annotation_guidelines.md"
            },
            "records": self.records
        }
        with open(self.candidates_json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        # 2. Save CSV
        csv_fields = [
            "case_id",
            "case_title",
            "court",
            "decision_date",
            "proceeding_type",
            "original_disposition",
            "normalized_disposition",
            "successful_party",
            "original_disposition_phrase",
            "matched_text",
            "source_start_offset",
            "source_end_offset",
            "procedural_role",
            "parser_confidence",
            "recommended_action",
            "evidence_reference",
            "human_approved_label",
            "human_successful_party",
            "human_notes",
            "reviewer_reference",
            "review_status",
            "ambiguity_reason"
        ]

        with open(self.review_csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
            writer.writeheader()
            for r in self.records:
                writer.writerow(r)
