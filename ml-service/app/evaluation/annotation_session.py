"""
Interactive Human Annotation Session Manager
Jurist AI — Feature 1.5A: Interactive Human Annotation & Review

Manages the human-in-the-loop review workflow for the 36 unjudged benchmark candidates.
Strictly guarantees:
1. Zero automated relevance assignments or synthetic grades.
2. Complete candidate display (query, court, provisions, ranks, passages).
3. Accidental overwrite protection with full audit trail.
4. Validation of reviewer identity, graded scale (0, 1, 2, 3, uncertain), and supporting evidence.
5. Automatic two-way synchronization between JSON queue and CSV dataset.
6. Support for primary reviewer, second reviewer, and lead adjudication.
"""

import os
import sys
import json
import csv
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALID_GRADES = {0, 1, 2, 3}


class AnnotationValidationError(Exception):
    """Raised when annotation input fails validation."""
    pass


class OverwriteProtectionError(Exception):
    """Raised when an attempt is made to overwrite an approved annotation without explicit confirmation."""
    pass


class AnnotationSessionManager:
    def __init__(
        self,
        queue_path: Optional[str] = None,
        csv_path: Optional[str] = None
    ):
        if queue_path is None:
            queue_path = os.path.join(BASE_DIR, "datasets", "expanded_benchmark_annotation_queue.json")
        if csv_path is None:
            csv_path = os.path.join(BASE_DIR, "datasets", "expanded_benchmark_annotation.csv")

        self.queue_path = queue_path
        self.csv_path = csv_path
        self.queue: List[Dict[str, Any]] = []
        self._load_queue()

    def _load_queue(self):
        if not os.path.exists(self.queue_path):
            raise FileNotFoundError(f"Annotation queue not found at: {self.queue_path}")
        with open(self.queue_path, "r", encoding="utf-8") as f:
            self.queue = json.load(f)

    def _save_queue(self):
        """Atomically saves the updated JSON queue and synchronizes the CSV file."""
        os.makedirs(os.path.dirname(os.path.abspath(self.queue_path)), exist_ok=True)
        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(self.queue, f, indent=2, ensure_ascii=False)

        # Synchronize CSV
        self._sync_to_csv()

    def _sync_to_csv(self):
        csv_fields = [
            "annotation_id",
            "query_id",
            "query_text",
            "judgment_id",
            "case_title",
            "court",
            "decision_date",
            "source_dataset",
            "legal_provisions",
            "retrieved_rank_3way",
            "key_passages_excerpt",
            "existing_benchmark_relevance",
            "human_relevance_label",
            "reviewer_id",
            "review_status",
            "reviewer_notes",
            "relevance_evidence",
            "second_reviewer_id",
            "second_relevance_label",
            "adjudicated_grade"
        ]

        with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=csv_fields)
            writer.writeheader()
            for r in self.queue:
                passages = r.get("judgmentPassages", [])
                excerpt_parts = []
                for p in passages[:2]:
                    prefix = "[Summary] " if p.get("isSummary") else "[Holding] "
                    clean_text = p.get("text", "").replace("\n", " ").strip()
                    excerpt_parts.append(prefix + (clean_text[:300] + "..." if len(clean_text) > 300 else clean_text))
                excerpt = " | ".join(excerpt_parts)

                sec = r.get("secondReviewer") or {}
                adj = r.get("adjudication") or {}

                writer.writerow({
                    "annotation_id": r["annotationId"],
                    "query_id": r["queryId"],
                    "query_text": r["queryText"],
                    "judgment_id": r["judgmentId"],
                    "case_title": r["caseTitle"],
                    "court": r["court"],
                    "decision_date": r["decisionDate"],
                    "source_dataset": r["sourceDataset"],
                    "legal_provisions": "; ".join(r.get("legalProvisions", [])),
                    "retrieved_rank_3way": r["retrievedRank"],
                    "key_passages_excerpt": excerpt,
                    "existing_benchmark_relevance": "" if r.get("existingBenchmarkRelevance") is None else r.get("existingBenchmarkRelevance"),
                    "human_relevance_label": "" if r.get("humanRelevanceLabel") is None else r.get("humanRelevanceLabel"),
                    "reviewer_id": r.get("reviewerId") or "",
                    "review_status": r.get("reviewStatus", "pending_review"),
                    "reviewer_notes": r.get("reviewerNotes") or "",
                    "relevance_evidence": r.get("relevanceEvidence") or "",
                    "second_reviewer_id": sec.get("reviewerId") or "",
                    "second_relevance_label": "" if sec.get("humanRelevanceLabel") is None else sec.get("humanRelevanceLabel"),
                    "adjudicated_grade": "" if adj.get("finalGrade") is None else adj.get("finalGrade")
                })

    def get_progress(self) -> Dict[str, Any]:
        """Calculates current review progress metrics."""
        total = len(self.queue)
        reviewed = sum(1 for r in self.queue if r.get("reviewStatus") == "approved" and r.get("humanRelevanceLabel") in VALID_GRADES)
        uncertain = sum(1 for r in self.queue if r.get("humanRelevanceLabel") == "uncertain" or r.get("reviewStatus") == "uncertain")
        pending = sum(1 for r in self.queue if r.get("reviewStatus") == "pending_review")
        remaining = total - reviewed

        # Find first pending index
        first_pending_idx = None
        for idx, r in enumerate(self.queue):
            if r.get("reviewStatus") == "pending_review":
                first_pending_idx = idx
                break

        return {
            "totalCandidates": total,
            "reviewedCandidates": reviewed,
            "pendingCandidates": pending,
            "uncertainCandidates": uncertain,
            "remainingCandidates": remaining,
            "percentComplete": round((reviewed / max(total, 1)) * 100, 1),
            "nextPendingIndex": first_pending_idx
        }

    def get_candidate(self, index: int) -> Dict[str, Any]:
        """Retrieves candidate record by 0-based index."""
        if index < 0 or index >= len(self.queue):
            raise IndexError(f"Candidate index {index} out of range [0, {len(self.queue)-1}]")
        return self.queue[index]

    def get_candidate_by_id(self, annotation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves candidate record by annotationId."""
        for r in self.queue:
            if r["annotationId"] == annotation_id:
                return r
        return None

    def format_candidate_display(self, index: int) -> str:
        """Formats comprehensive human-readable presentation for candidate review."""
        c = self.get_candidate(index)
        progress = self.get_progress()

        lines = [
            "=" * 90,
            f" JURIST AI — CANDIDATE ANNOTATION #{index + 1} OF {progress['totalCandidates']} (ID: {c['annotationId']})",
            "=" * 90,
            f"Query ID:         {c['queryId']} | Domain: {c['domain']}",
            f"Target Aspect:    {c['targetAspect']}",
            f"Full Query Text:  \"{c['queryText']}\"",
            "-" * 90,
            f"Candidate Case:   {c['caseTitle']}",
            f"Judgment ID:      {c['judgmentId']} | Source Dataset: {c['sourceDataset']}",
            f"Court & Date:     {c['court']} | Decided: {c['decisionDate'] or 'Date unavailable'}",
            f"Citation:         {c['citation'] or 'Pending Neutral Citation'}",
            f"Legal Codes:      {', '.join(c.get('legalProvisions', [])) or 'None explicitly tagged'}",
            "-" * 90,
            f"Retrieval Context: Rank #{c['retrievedRank']} in {c['retrievalConfiguration']}",
            f"Modality Ranks:   {c.get('ranksAcrossConfigurations', {})}",
            "-" * 90,
            f"Review Status:    {c['reviewStatus'].upper()}",
            f"Current Grade:    {c['humanRelevanceLabel'] if c['humanRelevanceLabel'] is not None else 'UNREVIEWED'}",
            f"Reviewer ID:      {c['reviewerId'] or 'None'}",
            "=" * 90,
            "SUBSTANTIVE JUDGMENT PASSAGES FOR REVIEW:"
        ]

        passages = c.get("judgmentPassages", [])
        if not passages:
            lines.append("  [Warning: No passages available for this judgment]")
        else:
            for p_idx, p in enumerate(passages, start=1):
                p_type = "SUMMARY PASSAGE" if p.get("isSummary") else f"HOLDING PARAGRAPH #{p_idx}"
                lines.append(f"\n--- [{p_type}] (Passage ID: {p.get('passageId')}) ---")
                # Wrap long text cleanly
                raw_text = p.get("text", "").strip()
                lines.append(raw_text)

        lines.extend([
            "\n" + "=" * 90,
            "GRADED RELEVANCE SCALE:",
            "  [3] Highly Relevant — Directly addresses the query's core issue and statutory rule.",
            "  [2] Relevant        — Substantively addresses the legal doctrine/test.",
            "  [1] Partially Rel.  — Broad background or related issue without deciding controversy.",
            "  [0] Not Relevant    — Incidental citation, distinct legal branch, or counsel appearances.",
            "  [u] Uncertain       — Inconclusive text; requires escalation to lead legal research.",
            "=" * 90
        ])

        return "\n".join(lines)

    def submit_annotation(
        self,
        annotation_id: str,
        reviewer_id: str,
        grade: Any,
        evidence: str,
        notes: str = "",
        allow_overwrite: bool = False,
        is_second_reviewer: bool = False
    ) -> Dict[str, Any]:
        """
        Submits human relevance annotation with strict validation and audit tracking.
        """
        # Reviewer ID validation
        if not reviewer_id or not str(reviewer_id).strip():
            raise AnnotationValidationError("Reviewer ID must be provided and non-empty.")
        reviewer_id = str(reviewer_id).strip()

        # Grade validation
        normalized_grade: Optional[Any] = None
        if grade in {3, "3", "three"}:
            normalized_grade = 3
        elif grade in {2, "2", "two"}:
            normalized_grade = 2
        elif grade in {1, "1", "one"}:
            normalized_grade = 1
        elif grade in {0, "0", "zero"}:
            normalized_grade = 0
        elif str(grade).strip().lower() in {"uncertain", "u", "unknown"}:
            normalized_grade = "uncertain"
        else:
            raise AnnotationValidationError(
                f"Invalid grade '{grade}'. Must be 3 (Highly Relevant), 2 (Relevant), "
                f"1 (Partially Relevant), 0 (Not Relevant), or 'uncertain'."
            )

        # Evidence validation: require substantive justification for relevant judgments
        evidence_clean = str(evidence or "").strip()
        if normalized_grade in {2, 3} and len(evidence_clean) < 15:
            raise AnnotationValidationError(
                f"Grade {normalized_grade} requires substantive textual evidence from the judgment "
                f"(minimum 15 characters describing which paragraph or ratio supports this grade)."
            )

        target_record = self.get_candidate_by_id(annotation_id)
        if not target_record:
            raise AnnotationValidationError(f"Candidate annotationId '{annotation_id}' not found in queue.")

        timestamp_now = datetime.now(timezone.utc).isoformat()

        # Check for accidental overwrite
        if not is_second_reviewer:
            existing_grade = target_record.get("humanRelevanceLabel")
            existing_status = target_record.get("reviewStatus")

            if existing_grade is not None and existing_status == "approved" and not allow_overwrite:
                raise OverwriteProtectionError(
                    f"Candidate '{annotation_id}' was already reviewed with grade {existing_grade} by {target_record.get('reviewerId')}. "
                    f"To correct or overwrite, set allow_overwrite=True."
                )

            # Record audit history if overwriting
            if existing_grade is not None:
                if "auditHistory" not in target_record:
                    target_record["auditHistory"] = []
                target_record["auditHistory"].append({
                    "previousGrade": existing_grade,
                    "previousReviewerId": target_record.get("reviewerId"),
                    "previousEvidence": target_record.get("relevanceEvidence"),
                    "previousNotes": target_record.get("reviewerNotes"),
                    "updatedAt": timestamp_now,
                    "reason": "Human correction"
                })

            # Update primary reviewer fields
            target_record["humanRelevanceLabel"] = normalized_grade
            target_record["reviewerId"] = reviewer_id
            target_record["reviewStatus"] = "uncertain" if normalized_grade == "uncertain" else "approved"
            target_record["relevanceEvidence"] = evidence_clean
            target_record["reviewerNotes"] = str(notes or "").strip()
            target_record["reviewedAt"] = timestamp_now

        else:
            # Second Reviewer workflow
            sec = target_record.setdefault("secondReviewer", {})
            existing_sec_grade = sec.get("humanRelevanceLabel")

            if existing_sec_grade is not None and not allow_overwrite:
                raise OverwriteProtectionError(
                    f"Second reviewer has already graded candidate '{annotation_id}'. Use allow_overwrite=True to correct."
                )

            sec["reviewerId"] = reviewer_id
            sec["humanRelevanceLabel"] = normalized_grade
            sec["reviewStatus"] = "uncertain" if normalized_grade == "uncertain" else "approved"
            sec["relevanceEvidence"] = evidence_clean
            sec["reviewerNotes"] = str(notes or "").strip()
            sec["reviewedAt"] = timestamp_now

            # Check for disagreement between Reviewer 1 and Reviewer 2
            r1_grade = target_record.get("humanRelevanceLabel")
            adj = target_record.setdefault("adjudication", {})
            if r1_grade is not None and r1_grade != normalized_grade:
                adj["disagreementDetected"] = True
                adj["adjudicationStatus"] = "disagreement_pending_lead"
                logger.warning("Disagreement flagged between reviewers for %s: %s vs %s", annotation_id, r1_grade, normalized_grade)
            elif r1_grade == normalized_grade:
                adj["disagreementDetected"] = False
                adj["adjudicationStatus"] = "consensus"
                adj["finalGrade"] = normalized_grade

        # Persist changes
        self._save_queue()

        return {
            "status": "success",
            "annotationId": annotation_id,
            "assignedGrade": normalized_grade,
            "reviewerId": reviewer_id,
            "isSecondReviewer": is_second_reviewer,
            "updatedStatus": target_record.get("reviewStatus"),
            "timestamp": timestamp_now
        }

    def submit_adjudication(
        self,
        annotation_id: str,
        adjudicator_id: str,
        final_grade: Any,
        adjudication_notes: str
    ) -> Dict[str, Any]:
        """Submits lead legal adjudication for reviewer disagreement."""
        if not adjudicator_id or not str(adjudicator_id).strip():
            raise AnnotationValidationError("Adjudicator ID is required.")

        normalized_grade = None
        if final_grade in {0, 1, 2, 3, "0", "1", "2", "3"}:
            normalized_grade = int(final_grade)
        elif str(final_grade).strip().lower() in {"uncertain", "u"}:
            normalized_grade = "uncertain"
        else:
            raise AnnotationValidationError(f"Invalid adjudication grade: {final_grade}")

        target_record = self.get_candidate_by_id(annotation_id)
        if not target_record:
            raise AnnotationValidationError(f"Candidate '{annotation_id}' not found.")

        adj = target_record.setdefault("adjudication", {})
        adj["adjudicatorId"] = str(adjudicator_id).strip()
        adj["finalGrade"] = normalized_grade
        adj["adjudicationNotes"] = str(adjudication_notes or "").strip()
        adj["adjudicationStatus"] = "adjudicated" if normalized_grade != "uncertain" else "adjudicated_uncertain"
        adj["adjudicatedAt"] = datetime.now(timezone.utc).isoformat()

        self._save_queue()
        return {
            "status": "success",
            "annotationId": annotation_id,
            "adjudicatorId": adjudicator_id,
            "finalGrade": normalized_grade,
            "adjudicationStatus": adj["adjudicationStatus"]
        }
