"""
Unit & Integration Tests for Interactive Human Annotation Session & Safeguards (Feature 1.5A)
Jurist AI — Feature 1.5A: Interactive Human Annotation & Review

Verifies:
1. Resuming annotation progress and finding next pending candidate.
2. Preventing accidental overwrites with audit trail history.
3. Rejecting invalid relevance grades.
4. Reviewer identity and minimum evidence validation.
5. Preserving pending review status on unannotated records.
6. Two-way synchronization between JSON queue and CSV file.
7. Second reviewer support and disagreement adjudication safeguards.
8. Ground-truth builder isolation and original benchmark integrity.
"""

import os
import sys
import json
import csv
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.evaluation.annotation_session import (
    AnnotationSessionManager,
    AnnotationValidationError,
    OverwriteProtectionError
)
from app.evaluation.expanded_benchmark_builder import build_expanded_benchmark


class TestInteractiveAnnotationSession(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory with a clean copy of queue and csv
        self.tmpdir = tempfile.TemporaryDirectory()
        src_queue = os.path.join(BASE_DIR, "app", "datasets", "expanded_benchmark_annotation_queue.json")
        src_csv = os.path.join(BASE_DIR, "app", "datasets", "expanded_benchmark_annotation.csv")
        self.orig_bench_path = os.path.join(BASE_DIR, "app", "datasets", "retrieval_benchmark.json")

        self.test_queue_path = os.path.join(self.tmpdir.name, "test_queue.json")
        self.test_csv_path = os.path.join(self.tmpdir.name, "test_queue.csv")

        with open(src_queue, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(self.test_queue_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        self.manager = AnnotationSessionManager(
            queue_path=self.test_queue_path,
            csv_path=self.test_csv_path
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_01_resuming_annotation_progress(self):
        """Manager accurately tracks progress and advances nextPendingIndex upon submission."""
        p_initial = self.manager.get_progress()
        self.assertEqual(p_initial["totalCandidates"], 36)
        self.assertEqual(p_initial["reviewedCandidates"], 0)
        self.assertEqual(p_initial["pendingCandidates"], 36)
        self.assertEqual(p_initial["nextPendingIndex"], 0)

        # Submit first candidate
        cand0 = self.manager.get_candidate(0)
        self.manager.submit_annotation(
            annotation_id=cand0["annotationId"],
            reviewer_id="REV-01",
            grade=3,
            evidence="Paragraph 12 explicitly invalidates arrest without written grounds."
        )

        p_after = self.manager.get_progress()
        self.assertEqual(p_after["reviewedCandidates"], 1)
        self.assertEqual(p_after["pendingCandidates"], 35)
        self.assertEqual(p_after["nextPendingIndex"], 1)
        self.assertAlmostEqual(p_after["percentComplete"], 2.8, places=1)

    def test_02_preventing_accidental_overwrites(self):
        """Accidental overwriting of approved candidates is blocked; explicit overwrite logs audit history."""
        cand0 = self.manager.get_candidate(0)
        self.manager.submit_annotation(
            annotation_id=cand0["annotationId"],
            reviewer_id="REV-ORIG",
            grade=2,
            evidence="Paragraph 14 discusses general Article 21 and Section 41A principles."
        )

        # Attempt to overwrite without allow_overwrite
        with self.assertRaises(OverwriteProtectionError):
            self.manager.submit_annotation(
                annotation_id=cand0["annotationId"],
                reviewer_id="REV-CORRECT",
                grade=3,
                evidence="Reassessed: Paragraph 12 is direct holding.",
                allow_overwrite=False
            )

        # Overwrite with explicit allow_overwrite=True
        res = self.manager.submit_annotation(
            annotation_id=cand0["annotationId"],
            reviewer_id="REV-CORRECT",
            grade=3,
            evidence="Reassessed: Paragraph 12 is direct holding on Article 22(1).",
            allow_overwrite=True
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["assignedGrade"], 3)

        updated_cand = self.manager.get_candidate_by_id(cand0["annotationId"])
        self.assertEqual(updated_cand["humanRelevanceLabel"], 3)
        self.assertEqual(updated_cand["reviewerId"], "REV-CORRECT")
        self.assertIn("auditHistory", updated_cand)
        self.assertEqual(len(updated_cand["auditHistory"]), 1)
        self.assertEqual(updated_cand["auditHistory"][0]["previousGrade"], 2)
        self.assertEqual(updated_cand["auditHistory"][0]["previousReviewerId"], "REV-ORIG")

    def test_03_invalid_grade_rejection(self):
        """Invalid grades (e.g. 4, -1, 'plausible', None) are rejected with validation errors."""
        cand0 = self.manager.get_candidate(0)
        invalid_grades = [4, -1, 5, "plausible", "maybe", 99, ""]

        for bad_grade in invalid_grades:
            with self.assertRaises(AnnotationValidationError):
                self.manager.submit_annotation(
                    annotation_id=cand0["annotationId"],
                    reviewer_id="REV-01",
                    grade=bad_grade,
                    evidence="Some text explaining reasons."
                )

        # Valid grades must succeed
        valid_inputs = [(3, 3), (2, 2), (1, 1), (0, 0), ("u", "uncertain"), ("uncertain", "uncertain")]
        for input_val, expected_val in valid_inputs:
            res = self.manager.submit_annotation(
                annotation_id=cand0["annotationId"],
                reviewer_id="REV-01",
                grade=input_val,
                evidence="Sufficient textual justification from judgment." if expected_val in {2, 3} else "General notes",
                allow_overwrite=True
            )
            self.assertEqual(res["assignedGrade"], expected_val)

    def test_04_reviewer_identity_and_evidence_validation(self):
        """Rejects submissions missing reviewer ID or lacking required textual evidence for relevant grades."""
        cand0 = self.manager.get_candidate(0)

        # Missing reviewer ID
        with self.assertRaises(AnnotationValidationError):
            self.manager.submit_annotation(
                annotation_id=cand0["annotationId"],
                reviewer_id="",
                grade=3,
                evidence="Paragraph 12 shows direct violation."
            )

        # Grade 3 with trivial evidence (< 15 chars)
        with self.assertRaises(AnnotationValidationError):
            self.manager.submit_annotation(
                annotation_id=cand0["annotationId"],
                reviewer_id="REV-01",
                grade=3,
                evidence="short"
            )

        # Grade 0 allows brief note
        res = self.manager.submit_annotation(
            annotation_id=cand0["annotationId"],
            reviewer_id="REV-01",
            grade=0,
            evidence="Irrelevant",
            allow_overwrite=True
        )
        self.assertEqual(res["assignedGrade"], 0)

    def test_05_pending_annotation_preservation(self):
        """All unannotated candidates strictly maintain 'pending_review' and humanRelevanceLabel as None."""
        for c in self.manager.queue:
            if c["annotationId"] != self.manager.queue[0]["annotationId"]:
                self.assertEqual(c["reviewStatus"], "pending_review")
                self.assertIsNone(c["humanRelevanceLabel"])
                self.assertIsNone(c["reviewerId"])

    def test_06_two_way_sync_json_csv(self):
        """Submitting an annotation automatically synchronizes the tabular CSV file."""
        cand0 = self.manager.get_candidate(0)
        self.manager.submit_annotation(
            annotation_id=cand0["annotationId"],
            reviewer_id="REV-SYNC",
            grade=3,
            evidence="Paragraph 12 strictly governs written grounds under Article 22(1)."
        )

        with open(self.test_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        row0 = next(r for r in rows if r["annotation_id"] == cand0["annotationId"])
        self.assertEqual(row0["human_relevance_label"], "3")
        self.assertEqual(row0["reviewer_id"], "REV-SYNC")
        self.assertEqual(row0["review_status"], "approved")
        self.assertIn("Paragraph 12", row0["relevance_evidence"])

    def test_07_second_reviewer_and_adjudication_safeguards(self):
        """Second reviewer disagreement is flagged; excluded from ground truth until adjudicated."""
        cand0 = self.manager.get_candidate(0)

        # Reviewer 1 rates as 3
        self.manager.submit_annotation(
            annotation_id=cand0["annotationId"],
            reviewer_id="REV-01",
            grade=3,
            evidence="Direct ratio on Article 22(1) written grounds of arrest."
        )

        # Reviewer 2 rates as 0
        self.manager.submit_annotation(
            annotation_id=cand0["annotationId"],
            reviewer_id="REV-02",
            grade=0,
            evidence="Matrimonial dispute under S. 498A rather than commercial cheating.",
            is_second_reviewer=True
        )

        rec = self.manager.get_candidate_by_id(cand0["annotationId"])
        self.assertTrue(rec["adjudication"]["disagreementDetected"])
        self.assertEqual(rec["adjudication"]["adjudicationStatus"], "disagreement_pending_lead")

        # Ground truth builder must exclude unresolved disagreement
        out_bench = os.path.join(self.tmpdir.name, "out_bench.json")
        summary = build_expanded_benchmark(
            original_benchmark_path=self.orig_bench_path,
            annotation_queue_path=self.test_queue_path,
            output_path=out_bench,
            allow_empty_annotations=True
        )
        # Disagreement is excluded from approved annotations
        self.assertEqual(summary["approvedAnnotations"], 0)
        self.assertEqual(summary["disagreementsDetected"], 1)

        # Lead Adjudicator steps in and resolves
        self.manager.submit_adjudication(
            annotation_id=cand0["annotationId"],
            adjudicator_id="LEAD-ADJ-01",
            final_grade=1,
            adjudication_notes="Partially relevant background authority on Section 170 custody."
        )

        # Re-run builder: Now resolved with grade 1
        summary2 = build_expanded_benchmark(
            original_benchmark_path=self.orig_bench_path,
            annotation_queue_path=self.test_queue_path,
            output_path=out_bench,
            allow_empty_annotations=True
        )
        self.assertEqual(summary2["approvedAnnotations"], 1)

    def test_08_original_benchmark_integrity(self):
        """Original landmark benchmark file remains completely unmodified."""
        with open(self.orig_bench_path, "r", encoding="utf-8") as f:
            orig_data = json.load(f)

        self.assertEqual(len(orig_data), 15)
        # Confirm landmark ID present in Q01
        self.assertIn("SC-2025-026", orig_data[0]["relevantJudgmentIds"])
        self.assertEqual(orig_data[0]["relevanceGrading"]["SC-2025-026"], 2)


if __name__ == "__main__":
    unittest.main()
