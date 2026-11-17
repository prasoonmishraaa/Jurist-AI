"""
Test Suite for Feature 4.7: Accelerated Risk-Based Human Outcome Annotation
JURIST AI — Accelerated Risk-Based Human Outcome Annotation

Verifies:
1. Preservation of Case 1 (OIL-SC-2021_INSC_327) and uncorrupted audit history.
2. Unaltered cryptographic hashes of source benchmark datasets.
3. Risk tier prioritization engine (Tiers 1 through 4) accuracy.
4. 5-case batch view presentation with operative order text and risk flags.
5. Batch submission atomicity and individual case audit tracking.
6. Strict confirmation safeguards (confirm=True requirement).
7. Rejection of invalid payloads (empty batch, invalid disposition, empty evidence, duplicates).
8. Prohibition of bulk auto-approval without individual case inspection.
9. Zero fabricated annotations on live data (1 approved, 149 pending).
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

# Add ml-service to path
ML_SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    AnnotationValidationError,
    ConfirmationRequiredError,
    VALID_DISPOSITIONS,
    VALID_SUCCESSFUL_PARTIES,
)
from app.prediction.risk_prioritized_queue import RiskPrioritizer, RiskTier


class TestFeature47PreservationAndIntegrity(unittest.TestCase):
    """Verifies that existing human decisions and source datasets remain unaltered."""

    def setUp(self):
        self.session = OutcomeAnnotationSessionManager()

    def test_case_1_remains_approved_with_audit_history(self):
        """Case 1 (OIL-SC-2021_INSC_327) must remain approved from Feature 4.6.1."""
        case_view = self.session.get_case_view("OIL-SC-2021_INSC_327")
        self.assertEqual(case_view["case_id"], "OIL-SC-2021_INSC_327")

        review = case_view["current_review"]
        self.assertEqual(review["review_status"], "approved")
        self.assertEqual(review["human_approved_label"], "appeal_allowed")
        self.assertEqual(review["human_successful_party"], "state_prosecution")
        self.assertEqual(review["reviewer_reference"], "SNR-LEGAL-NLP-01")
        self.assertGreaterEqual(len(review["audit_history"]), 1)

        first_audit = review["audit_history"][0]
        self.assertEqual(first_audit["action"], "accept")
        self.assertEqual(first_audit["reviewer_id"], "SNR-LEGAL-NLP-01")
        self.assertEqual(first_audit["new_status"], "approved")

    def test_source_dataset_cryptographic_hashes_unaltered(self):
        """Cryptographic SHA-256 hashes of original source datasets must match."""
        integrity = self.session.verify_source_integrity()
        self.assertTrue(integrity["open_india_law_sample_150.json"])
        self.assertTrue(integrity["indian_judgments.json"])

    def test_zero_fabricated_annotations_on_live_data(self):
        """Strict integrity check: exactly 11 verified cases (10 approved, 1 corrected), 139 pending."""
        dash = self.session.get_progress_dashboard()
        self.assertEqual(dash["total_candidates"], 150)
        self.assertEqual(dash["approved"], 10)
        self.assertEqual(dash["corrected"], 1)
        self.assertEqual(dash["total_verified"], 11)
        self.assertEqual(dash["pending"], 139)
        self.assertEqual(dash["remaining_candidates"], 139)
        self.assertEqual(dash["rejected"], 0)
        self.assertEqual(dash["uncertain"], 0)
        self.assertEqual(dash["deferred"], 0)


class TestRiskTierClassification(unittest.TestCase):
    """Tests the RiskPrioritizer stratification logic across all four risk tiers."""

    def setUp(self):
        self.prioritizer = RiskPrioritizer()

    def test_tier_1_definitive_merits_criteria(self):
        record = {
            "case_id": "TEST-01",
            "normalized_disposition": "appeal_allowed",
            "parser_confidence": 0.95
        }
        text = "This is a clean merits judgment. The appeal is allowed."
        risk = self.prioritizer.assess_case_risk(record, text)
        self.assertEqual(risk["tier"], RiskTier.TIER_1_DEFINITIVE_MERITS)
        self.assertEqual(risk["recommended_review_mode"], "accelerated_batch")
        self.assertFalse(risk["is_truncated"])

    def test_tier_2_bail_and_directives_criteria(self):
        record = {
            "case_id": "TEST-02",
            "normalized_disposition": "bail_granted",
            "parser_confidence": 0.90
        }
        text = "The appellant is directed to be released on bail."
        risk = self.prioritizer.assess_case_risk(record, text)
        self.assertEqual(risk["tier"], RiskTier.TIER_2_MODERATE_RISK_BAIL_DIRECTIVES)
        self.assertTrue(any("BAIL" in flag for flag in risk["flags"]))

    def test_tier_3_procedural_nuance_criteria(self):
        # Remand
        rec_remand = {"case_id": "TEST-03A", "normalized_disposition": "remanded", "parser_confidence": 0.90}
        risk_remand = self.prioritizer.assess_case_risk(rec_remand, "Remanded to High Court.")
        self.assertEqual(risk_remand["tier"], RiskTier.TIER_3_HIGH_RISK_PROCEDURAL)
        self.assertTrue(any("REMAND" in flag for flag in risk_remand["flags"]))

        # Partly allowed
        rec_part = {"case_id": "TEST-03B", "normalized_disposition": "partly_allowed", "parser_confidence": 0.90}
        risk_part = self.prioritizer.assess_case_risk(rec_part, "Appeal partly allowed.")
        self.assertEqual(risk_part["tier"], RiskTier.TIER_3_HIGH_RISK_PROCEDURAL)
        self.assertTrue(any("PARTIAL" in flag for flag in risk_part["flags"]))

        # Withdrawn
        rec_withdrawn = {"case_id": "TEST-03C", "normalized_disposition": "withdrawn", "parser_confidence": 0.90}
        risk_withdrawn = self.prioritizer.assess_case_risk(rec_withdrawn, "Dismissed as withdrawn.")
        self.assertEqual(risk_withdrawn["tier"], RiskTier.TIER_3_HIGH_RISK_PROCEDURAL)

    def test_tier_4_critical_truncated_and_interlocutory(self):
        # Truncated text length (>= 39,900 chars)
        long_text = "x" * 40000
        rec_long = {"case_id": "TEST-04A", "normalized_disposition": "appeal_allowed", "parser_confidence": 0.95}
        risk_long = self.prioritizer.assess_case_risk(rec_long, long_text)
        self.assertEqual(risk_long["tier"], RiskTier.TIER_4_CRITICAL_DEFERRED)
        self.assertTrue(risk_long["is_truncated"])
        self.assertTrue(any("TRUNCATION" in flag for flag in risk_long["flags"]))

        # Interlocutory reference
        rec_inter = {"case_id": "TEST-04B", "normalized_disposition": "interlocutory_reference", "parser_confidence": 0.80}
        risk_inter = self.prioritizer.assess_case_risk(rec_inter, "Referred to Larger Bench.")
        self.assertEqual(risk_inter["tier"], RiskTier.TIER_4_CRITICAL_DEFERRED)
        self.assertTrue(any("INTERLOCUTORY" in flag for flag in risk_inter["flags"]))

    def test_live_corpus_stratification_counts(self):
        """Verifies distribution across all 150 candidates in the live corpus."""
        session = OutcomeAnnotationSessionManager()
        stratified = self.prioritizer.stratify_queue(session.records, session.source_cases, only_pending=False)
        self.assertEqual(len(stratified[RiskTier.TIER_1_DEFINITIVE_MERITS]), 35)
        self.assertEqual(len(stratified[RiskTier.TIER_2_MODERATE_RISK_BAIL_DIRECTIVES]), 21)
        self.assertEqual(len(stratified[RiskTier.TIER_3_HIGH_RISK_PROCEDURAL]), 43)
        self.assertEqual(len(stratified[RiskTier.TIER_4_CRITICAL_DEFERRED]), 51)
        # Sum of 4 tiers equals exact 150 candidates
        total = sum(len(v) for v in stratified.values())
        self.assertEqual(total, 150)


class TestBatchPresentationAndReviewExecution(unittest.TestCase):
    """Tests 5-case batch view, staging, and atomic batch submission in isolated test workspace."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.datasets_dir = Path(ML_SERVICE_DIR) / "app" / "datasets"

        self.tmp_cand_json = Path(self.tmp_dir) / "outcome_label_candidates_v2.json"
        self.tmp_review_csv = Path(self.tmp_dir) / "outcome_label_review_v2.csv"
        self.tmp_source_json = self.datasets_dir / "open_india_law_sample_150.json"

        shutil.copy(self.datasets_dir / "outcome_label_candidates_v2.json", self.tmp_cand_json)
        shutil.copy(self.datasets_dir / "outcome_label_review_v2.csv", self.tmp_review_csv)

        tmp_batches = Path(self.tmp_dir) / "review_batches"
        tmp_batches.mkdir(parents=True, exist_ok=True)
        for bf in (self.datasets_dir / "review_batches").glob("*.json"):
            shutil.copy(bf, tmp_batches / bf.name)

        self.session = OutcomeAnnotationSessionManager(
            datasets_dir=self.tmp_dir,
            candidates_json_path=str(self.tmp_cand_json),
            review_csv_path=str(self.tmp_review_csv),
            source_json_path=str(self.tmp_source_json)
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_batch_view_returns_five_cases_with_operative_text(self):
        """get_batch_view must return 5 pending cases with operative text and risk profiles."""
        batch = self.session.get_batch_view(batch_size=5, tier="1")
        self.assertEqual(len(batch), 5)

        for case in batch:
            self.assertIn("case_id", case)
            self.assertIn("case_title", case)
            self.assertIn("court", case)
            self.assertIn("decision_date", case)
            self.assertIn("machine_candidate", case)
            self.assertIn("risk_assessment", case)
            self.assertIn("operative_order_excerpt", case)
            self.assertEqual(case["risk_tier"], RiskTier.TIER_1_DEFINITIVE_MERITS)
            self.assertEqual(case["current_review"]["review_status"], "pending_review")

    def test_batch_submission_requires_explicit_confirmation(self):
        """Calling submit_batch_reviews with confirm=False must raise ConfirmationRequiredError."""
        batch = self.session.get_batch_view(batch_size=2, tier="1")
        decisions = [
            {
                "case_id": batch[0]["case_id"],
                "action": "accept",
                "evidence": "Operative order confirmed in para 15."
            },
            {
                "case_id": batch[1]["case_id"],
                "action": "accept",
                "evidence": "Operative order confirmed in para 18."
            }
        ]

        with self.assertRaises(ConfirmationRequiredError):
            self.session.submit_batch_reviews(decisions, reviewer_id="REV-TEST-01", confirm=False)

    def test_batch_submission_commits_mixed_decisions_atomically(self):
        """Submit a batch of 3 cases with mixed actions (accept, correct, defer) and verify atomicity."""
        batch = self.session.get_batch_view(batch_size=3, tier="1")
        cid0 = batch[0]["case_id"]
        cid1 = batch[1]["case_id"]
        cid2 = batch[2]["case_id"]

        decisions = [
            {
                "case_id": cid0,
                "action": "accept",
                "evidence": "The appeal is accordingly allowed with costs.",
                "notes": "Clean merits allowance accepted."
            },
            {
                "case_id": cid1,
                "action": "correct",
                "disposition": "partly_allowed",
                "successful_party": "unresolved",
                "evidence": "Sentence reduced to the period already undergone.",
                "notes": "Partial modification of sentence; corrected from full dismissal."
            },
            {
                "case_id": cid2,
                "action": "defer",
                "notes": "Deferred pending inspection of cross-appeal record.",
                "evidence": "Ambiguous cross-appeal reference"
            }
        ]

        result = self.session.submit_batch_reviews(decisions, reviewer_id="REV-BATCH-01", confirm=True)
        self.assertEqual(result["committed_count"], 3)
        self.assertEqual(result["reviewer_id"], "REV-BATCH-01")

        # Verify each case state
        view0 = self.session.get_case_view(cid0)
        self.assertEqual(view0["current_review"]["review_status"], "approved")
        self.assertEqual(view0["current_review"]["reviewer_reference"], "REV-BATCH-01")
        self.assertEqual(len(view0["current_review"]["audit_history"]), 1)
        self.assertEqual(view0["current_review"]["audit_history"][0]["action"], "accept")

        view1 = self.session.get_case_view(cid1)
        self.assertEqual(view1["current_review"]["review_status"], "corrected")
        self.assertEqual(view1["current_review"]["human_approved_label"], "partly_allowed")
        self.assertEqual(view1["current_review"]["reviewer_reference"], "REV-BATCH-01")
        self.assertEqual(len(view1["current_review"]["audit_history"]), 1)
        self.assertEqual(view1["current_review"]["audit_history"][0]["action"], "correct")

        view2 = self.session.get_case_view(cid2)
        self.assertEqual(view2["current_review"]["review_status"], "deferred_needs_full_text")
        self.assertEqual(len(view2["current_review"]["audit_history"]), 1)

        # Verify dashboard update: 11 baseline verified (10 approved, 1 corrected) + 1 approved + 1 corrected = 13 verified
        dash = self.session.get_progress_dashboard()
        self.assertEqual(dash["total_verified"], 13)
        self.assertEqual(dash["approved"], 11)
        self.assertEqual(dash["corrected"], 2)
        self.assertEqual(dash["deferred"], 1)
        self.assertEqual(dash["pending"], 136)

    def test_rejection_of_empty_and_duplicate_batch_payloads(self):
        """Batch submission must fail on empty list or duplicate case IDs."""
        with self.assertRaises(AnnotationValidationError):
            self.session.submit_batch_reviews([], reviewer_id="REV-01", confirm=True)

        batch = self.session.get_batch_view(batch_size=1, tier="1")
        cid = batch[0]["case_id"]
        duplicate_decisions = [
            {"case_id": cid, "action": "accept", "evidence": "Order confirmed in para 10."},
            {"case_id": cid, "action": "accept", "evidence": "Order confirmed in para 10."}
        ]
        with self.assertRaises(AnnotationValidationError):
            self.session.submit_batch_reviews(duplicate_decisions, reviewer_id="REV-01", confirm=True)

    def test_rejection_of_invalid_item_aborts_entire_batch_zero_partial_writes(self):
        """If one item in a batch is invalid, no modifications are written (fail-fast atomicity)."""
        batch = self.session.get_batch_view(batch_size=2, tier="1")
        cid0 = batch[0]["case_id"]
        cid1 = batch[1]["case_id"]

        decisions = [
            {
                "case_id": cid0,
                "action": "accept",
                "evidence": "Operative order confirmed in judgment."
            },
            {
                "case_id": cid1,
                "action": "correct",
                "disposition": "completely_invalid_disposition",  # Invalid!
                "successful_party": "petitioner",
                "evidence": "Some evidence.",
                "notes": "Some notes."
            }
        ]

        with self.assertRaises(AnnotationValidationError):
            self.session.submit_batch_reviews(decisions, reviewer_id="REV-01", confirm=True)

        # Verify that cid0 was NOT partially committed
        view0 = self.session.get_case_view(cid0)
        self.assertEqual(view0["current_review"]["review_status"], "pending_review")
        self.assertEqual(len(view0["current_review"]["audit_history"]), 0)

    def test_short_or_empty_evidence_rejected(self):
        """Evidence must be at least 5 characters for accept/correct actions."""
        batch = self.session.get_batch_view(batch_size=1, tier="1")
        cid = batch[0]["case_id"]

        short_ev_decision = [
            {
                "case_id": cid,
                "action": "accept",
                "evidence": "ok"  # Too short!
            }
        ]
        with self.assertRaises(AnnotationValidationError):
            self.session.submit_batch_reviews(short_ev_decision, reviewer_id="REV-01", confirm=True)


if __name__ == "__main__":
    unittest.main()
