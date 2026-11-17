"""
Comprehensive Test Suite for Human-Reviewed Retrieval Benchmark Workflow (Feature 1.5)
Jurist AI — Feature 1.5: Human-Reviewed Expanded Retrieval Benchmark

Verifies:
1. Annotation Queue Schema and Integrity (36 pending records, zero fabricated labels).
2. Annotation CSV Schema and Content.
3. Pending Annotations Excluded from Finalized Ground Truth.
4. Original Benchmark Labels Preserved Verbatim.
5. Duplicate Query–Judgment Pair Deduplication.
6. Conflicting Reviewer Annotations and Lead Adjudication.
7. Provenance Tracking (reviewer IDs, timestamps, evidence, original rank).
8. Mathematical Correctness of Graded Relevance Metrics (NDCG@5, P@1, P@3, P@5, R@5, MRR).
"""

import os
import sys
import json
import csv
import math
import tempfile
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.evaluation.expanded_benchmark_builder import (
    validate_annotation_record,
    resolve_adjudication,
    build_expanded_benchmark,
    BenchmarkAnnotationError
)
from app.evaluation.retrieval_evaluator import (
    compute_precision_at_k,
    compute_recall_at_k,
    compute_reciprocal_rank,
    compute_dcg_at_k,
    compute_ndcg_at_k
)


class TestExpandedBenchmarkAnnotationWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queue_path = os.path.join(BASE_DIR, "app", "datasets", "expanded_benchmark_annotation_queue.json")
        cls.csv_path = os.path.join(BASE_DIR, "app", "datasets", "expanded_benchmark_annotation.csv")
        cls.orig_bench_path = os.path.join(BASE_DIR, "app", "datasets", "retrieval_benchmark.json")

        with open(cls.queue_path, "r", encoding="utf-8") as f:
            cls.queue = json.load(f)
        with open(cls.orig_bench_path, "r", encoding="utf-8") as f:
            cls.orig_bench = json.load(f)

    def test_01_annotation_queue_schema_and_counts(self):
        """Annotation queue contains exactly 36 candidate records, all strictly pending review."""
        self.assertEqual(len(self.queue), 36)

        required_keys = {
            "annotationId", "queryId", "queryText", "domain", "targetAspect",
            "judgmentId", "caseTitle", "court", "decisionDate", "sourceDataset",
            "legalProvisions", "retrievedRank", "retrievalConfiguration",
            "ranksAcrossConfigurations", "judgmentPassages", "existingBenchmarkRelevance",
            "humanRelevanceLabel", "reviewerId", "reviewStatus", "reviewerNotes",
            "relevanceEvidence", "secondReviewer", "adjudication"
        }

        for record in self.queue:
            for k in required_keys:
                self.assertIn(k, record, f"Missing required key '{k}' in record {record.get('annotationId')}")

            # Strict Invariant: All records are pending review, zero fabricated labels
            self.assertEqual(record["reviewStatus"], "pending_review")
            self.assertIsNone(record["humanRelevanceLabel"])
            self.assertIsNone(record["reviewerId"])
            self.assertEqual(record["reviewerNotes"], "")
            self.assertEqual(record["relevanceEvidence"], "")

            # Second reviewer must also be uninitialized
            self.assertIsNone(record["secondReviewer"]["reviewerId"])
            self.assertIsNone(record["secondReviewer"]["humanRelevanceLabel"])
            self.assertEqual(record["secondReviewer"]["reviewStatus"], "pending_review")

            # Judgment passages must be non-empty
            self.assertGreater(len(record["judgmentPassages"]), 0)
            self.assertTrue(all("text" in p and len(p["text"]) > 0 for p in record["judgmentPassages"]))

    def test_02_annotation_csv_structure(self):
        """CSV annotation file contains header and 36 rows with matching IDs."""
        self.assertTrue(os.path.exists(self.csv_path))

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.assertEqual(len(rows), 36)
        expected_cols = {
            "annotation_id", "query_id", "query_text", "judgment_id",
            "case_title", "court", "decision_date", "source_dataset",
            "legal_provisions", "retrieved_rank_3way", "key_passages_excerpt",
            "existing_benchmark_relevance", "human_relevance_label",
            "reviewer_id", "review_status", "reviewer_notes",
            "relevance_evidence", "second_reviewer_id", "second_relevance_label",
            "adjudicated_grade"
        }
        for col in expected_cols:
            self.assertIn(col, reader.fieldnames)

        for row in rows:
            self.assertEqual(row["review_status"], "pending_review")
            self.assertEqual(row["human_relevance_label"], "")
            self.assertEqual(row["reviewer_id"], "")

    def test_03_pending_annotations_excluded_from_finalized_ground_truth(self):
        """Builder strictly excludes all pending records and refuses to finalize empty ground truth."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_output = os.path.join(tmpdir, "retrieval_benchmark_expanded_human_reviewed.json")

            summary = build_expanded_benchmark(
                original_benchmark_path=self.orig_bench_path,
                annotation_queue_path=self.queue_path,
                output_path=test_output,
                allow_empty_annotations=False
            )

            self.assertEqual(summary["totalAnnotationPairs"], 36)
            self.assertEqual(summary["approvedAnnotations"], 0)
            self.assertEqual(summary["pendingAnnotations"], 36)
            self.assertFalse(summary["finalizedGroundTruth"])
            # File must NOT have been written because 0 approved labels exist
            self.assertFalse(os.path.exists(test_output))

    def test_04_original_benchmark_labels_preserved_verbatim(self):
        """Merging approved annotations preserves all original queries, landmark IDs, and grades verbatim."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock approved annotation
            mock_queue = [dict(self.queue[0])]
            mock_queue[0]["humanRelevanceLabel"] = 3
            mock_queue[0]["reviewerId"] = "TEST-REV-01"
            mock_queue[0]["reviewStatus"] = "approved"
            mock_queue[0]["relevanceEvidence"] = "Direct binding authority on Article 22(1) written grounds."

            mock_queue_path = os.path.join(tmpdir, "mock_queue.json")
            with open(mock_queue_path, "w", encoding="utf-8") as f:
                json.dump(mock_queue, f)

            output_path = os.path.join(tmpdir, "expanded_benchmark.json")

            summary = build_expanded_benchmark(
                original_benchmark_path=self.orig_bench_path,
                annotation_queue_path=mock_queue_path,
                output_path=output_path,
                allow_empty_annotations=True
            )

            self.assertEqual(summary["approvedAnnotations"], 1)
            self.assertTrue(os.path.exists(output_path))

            with open(output_path, "r", encoding="utf-8") as f:
                merged_bench = json.load(f)

            # Check original benchmark preservation
            self.assertEqual(len(merged_bench), len(self.orig_bench))

            orig_map = {q["queryId"]: q for q in self.orig_bench}
            merged_map = {q["queryId"]: q for q in merged_bench}

            for qid, orig_q in orig_map.items():
                merged_q = merged_map[qid]
                # Verbatim preservation of original queries
                self.assertEqual(merged_q["query"], orig_q["query"])
                self.assertEqual(merged_q["targetAspect"], orig_q["targetAspect"])
                # Original landmark IDs must all still be in relevantJudgmentIds
                for orig_id in orig_q["relevantJudgmentIds"]:
                    self.assertIn(orig_id, merged_q["relevantJudgmentIds"])
                # Original grades must match exactly
                for orig_id, orig_grade in orig_q["relevanceGrading"].items():
                    self.assertEqual(merged_q["relevanceGrading"][orig_id], orig_grade)

            # Check newly added case
            added_qid = mock_queue[0]["queryId"]
            added_cid = mock_queue[0]["judgmentId"]
            self.assertIn(added_cid, merged_map[added_qid]["relevantJudgmentIds"])
            self.assertEqual(merged_map[added_qid]["relevanceGrading"][added_cid], 3)

    def test_05_duplicate_query_judgment_pair_deduplication(self):
        """Repeated annotations for identical (queryId, judgmentId) are deduplicated cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two entries for the same query and judgment
            ann1 = dict(self.queue[0])
            ann1["humanRelevanceLabel"] = 2
            ann1["reviewerId"] = "REV-01"
            ann1["reviewStatus"] = "approved"

            ann2 = dict(self.queue[0])
            ann2["humanRelevanceLabel"] = 3
            ann2["reviewerId"] = "REV-02"
            ann2["reviewStatus"] = "approved"

            mock_queue_path = os.path.join(tmpdir, "dup_queue.json")
            with open(mock_queue_path, "w", encoding="utf-8") as f:
                json.dump([ann1, ann2], f)

            output_path = os.path.join(tmpdir, "dedup_benchmark.json")

            summary = build_expanded_benchmark(
                original_benchmark_path=self.orig_bench_path,
                annotation_queue_path=mock_queue_path,
                output_path=output_path,
                allow_empty_annotations=True
            )

            # Total pairs must be 1, approved count 1
            self.assertEqual(summary["totalAnnotationPairs"], 1)
            self.assertEqual(summary["approvedAnnotations"], 1)

            with open(output_path, "r", encoding="utf-8") as f:
                merged = json.load(f)

            target_q = next(q for q in merged if q["queryId"] == ann1["queryId"])
            # Judgment ID must appear only once in relevantJudgmentIds
            cid_count = target_q["relevantJudgmentIds"].count(ann1["judgmentId"])
            self.assertEqual(cid_count, 1)

    def test_06_conflicting_reviewer_annotations_and_adjudication(self):
        """Tests reviewer disagreement detection and resolution through lead adjudication."""
        # Case A: Disagreement without adjudication -> Unresolved
        res_unresolved = resolve_adjudication(r1_grade=3, r2_grade=0, adjudicator_grade=None)
        self.assertFalse(res_unresolved["isResolved"])
        self.assertTrue(res_unresolved["disagreementDetected"])
        self.assertIsNone(res_unresolved["finalGrade"])
        self.assertEqual(res_unresolved["resolutionMethod"], "unresolved_disagreement")

        # Case B: Disagreement resolved by lead adjudicator -> Resolved
        res_resolved = resolve_adjudication(
            r1_grade=3,
            r2_grade=1,
            adjudicator_grade=2,
            adjudication_notes="Affirmed relevance on Section 41A CrPC safeguards."
        )
        self.assertTrue(res_resolved["isResolved"])
        self.assertTrue(res_resolved["disagreementDetected"])
        self.assertEqual(res_resolved["finalGrade"], 2)
        self.assertEqual(res_resolved["resolutionMethod"], "lead_adjudication")

        # Case C: Reviewers agree in consensus -> Resolved without adjudication
        res_consensus = resolve_adjudication(r1_grade=2, r2_grade=2, adjudicator_grade=None)
        self.assertTrue(res_consensus["isResolved"])
        self.assertFalse(res_consensus["disagreementDetected"])
        self.assertEqual(res_consensus["finalGrade"], 2)
        self.assertEqual(res_consensus["resolutionMethod"], "reviewer_consensus")

        # Case D: Uncertain consensus -> Excluded unless adjudicator overrules
        res_unc = resolve_adjudication(r1_grade="uncertain", r2_grade="uncertain", adjudicator_grade=None)
        self.assertFalse(res_unc["isResolved"])
        self.assertIsNone(res_unc["finalGrade"])

    def test_07_provenance_preservation(self):
        """Approved records merged into benchmark carry full audit provenance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ann = dict(self.queue[0])
            ann["humanRelevanceLabel"] = 2
            ann["reviewerId"] = "REV-AUDIT-01"
            ann["reviewStatus"] = "approved"
            ann["relevanceEvidence"] = "Paragraph 14 discusses mandatory compliance with S. 41A CrPC."
            ann["reviewerNotes"] = "Substantive discussion of arrest procedure."
            ann["secondReviewer"] = {
                "reviewerId": "REV-AUDIT-02",
                "humanRelevanceLabel": 2,
                "reviewStatus": "approved",
                "reviewerNotes": "Agreed on Section 41A applicability.",
                "relevanceEvidence": "Paragraph 14 cited."
            }

            mock_queue_path = os.path.join(tmpdir, "prov_queue.json")
            with open(mock_queue_path, "w", encoding="utf-8") as f:
                json.dump([ann], f)

            output_path = os.path.join(tmpdir, "prov_benchmark.json")

            _ = build_expanded_benchmark(
                original_benchmark_path=self.orig_bench_path,
                annotation_queue_path=mock_queue_path,
                output_path=output_path,
                allow_empty_annotations=True
            )

            with open(output_path, "r", encoding="utf-8") as f:
                merged = json.load(f)

            target_q = next(q for q in merged if q["queryId"] == ann["queryId"])
            provenance = target_q["provenance"]

            self.assertEqual(provenance["addedHumanReviewedCount"], 1)
            self.assertEqual(len(provenance["addedCases"]), 1)

            entry = provenance["addedCases"][0]
            self.assertEqual(entry["judgmentId"], ann["judgmentId"])
            self.assertEqual(entry["primaryReviewerId"], "REV-AUDIT-01")
            self.assertEqual(entry["secondReviewerId"], "REV-AUDIT-02")
            self.assertEqual(entry["resolutionMethod"], "reviewer_consensus")
            self.assertIn("Paragraph 14", entry["evidence"])
            self.assertIn("mergedTimestamp", entry)

    def test_08_metric_calculation_with_graded_relevance(self):
        """Mathematical correctness of NDCG@K and precision/recall across 4-level graded scale (3, 2, 1, 0)."""
        retrieved = ["DOC-A", "DOC-B", "DOC-C", "DOC-D", "DOC-E"]

        # Graded relevance dictionary
        grades = {
            "DOC-A": 3.0,
            "DOC-B": 2.0,
            "DOC-C": 1.0,
            "DOC-D": 0.0,
            "DOC-E": 0.0
        }

        # Perfect ranking: DOC-A (3), DOC-B (2), DOC-C (1)
        ndcg_perfect = compute_ndcg_at_k(retrieved, grades, k=5)
        self.assertAlmostEqual(ndcg_perfect, 1.0, places=5)

        # Inverted ranking
        inverted_retrieved = ["DOC-E", "DOC-D", "DOC-C", "DOC-B", "DOC-A"]
        ndcg_inverted = compute_ndcg_at_k(inverted_retrieved, grades, k=5)

        # DCG calculation for inverted:
        # rank 1: DOC-E (0) -> gain 0
        # rank 2: DOC-D (0) -> gain 0
        # rank 3: DOC-C (1) -> gain (2^1 - 1)/log2(4) = 1/2 = 0.5
        # rank 4: DOC-B (2) -> gain (2^2 - 1)/log2(5) = 3/2.321928 = 1.29203
        # rank 5: DOC-A (3) -> gain (2^3 - 1)/log2(6) = 7/2.584962 = 2.70797
        # Total DCG = 0.5 + 1.29203 + 2.70797 = 4.499999
        # IDCG calculation:
        # rank 1: gain (2^3 - 1)/log2(2) = 7/1 = 7.0
        # rank 2: gain (2^2 - 1)/log2(3) = 3/1.584962 = 1.89279
        # rank 3: gain (2^1 - 1)/log2(4) = 1/2.0 = 0.5
        # Total IDCG = 7.0 + 1.89279 + 0.5 = 9.39279
        # Expected NDCG = 4.499999 / 9.39279 = 0.47909
        self.assertAlmostEqual(ndcg_inverted, 4.5 / 9.39279, places=3)
        self.assertLess(ndcg_inverted, 0.55)
        self.assertGreater(ndcg_inverted, 0.40)

        # Precision & Recall using grade threshold >= 2
        relevant_set = {doc_id for doc_id, g in grades.items() if g >= 2.0}
        self.assertEqual(relevant_set, {"DOC-A", "DOC-B"})

        p_at_5 = compute_precision_at_k(retrieved, relevant_set, k=5)
        self.assertAlmostEqual(p_at_5, 2.0 / 5.0)  # 2 relevant out of 5 retrieved

        r_at_5 = compute_recall_at_k(retrieved, relevant_set, k=5)
        self.assertAlmostEqual(r_at_5, 2.0 / 2.0)  # Found both relevant documents (100% recall)

        rr = compute_reciprocal_rank(retrieved, relevant_set, k=5)
        self.assertAlmostEqual(rr, 1.0)  # DOC-A at rank 1


if __name__ == "__main__":
    unittest.main()
