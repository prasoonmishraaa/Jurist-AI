"""
Unit and Integration Tests for Feature 4.5: Interactive Human-Reviewed Judicial Outcome Annotation
JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Tests:
1. Session Loading & Dashboard: Loading queue, batch categorization, and initial pending status.
2. Accept Candidate: Verifies transition to 'approved', evidence validation, confirmation requirement.
3. Correct Candidate: Verifies custom disposition, party success validation, and audit recording.
4. Reject Candidate: Verifies transition to 'rejected' with mandatory justification notes.
5. Uncertain / Deferred: Verifies handling of truncated/ambiguous cases without training eligibility.
6. Resume Functionality: get_next_pending skips reviewed cases and respects batch prioritization.
7. Provenance & Audit Trail: Preserves audit history with timestamps, reviewer IDs, and status transitions.
8. Two-Reviewer Disagreement & Adjudication: Detects consensus vs dispute, tests lead adjudication.
9. Training Readiness Integration: Validates that only approved/adjudicated records count toward ML readiness.
10. Source Dataset Hash Integrity: Verifies open_india_law_sample_150.json and indian_judgments.json SHA-256 hashes.
"""

import os
import sys
import json
import csv
import copy
import shutil
import tempfile
import unittest
from pathlib import Path

# Ensure ml-service root is in sys.path
ML_SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ML_SERVICE_DIR)

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    VALID_DISPOSITIONS,
    VALID_SUCCESSFUL_PARTIES,
    AnnotationValidationError,
    ConfirmationRequiredError,
    KNOWN_SOURCE_HASHES,
)
from scripts.build_verified_outcome_dataset import (
    VerifiedOutcomeDatasetBuilder,
    InsufficientApprovedLabelsError
)


class TestOutcomeAnnotationSession(unittest.TestCase):
    """Tests the outcome annotation session manager using isolated temporary workspaces."""

    def setUp(self):
        # Create a temporary workspace to isolate write actions from real production queue
        self.tmp_dir = tempfile.mkdtemp()
        self.datasets_dir = Path(ML_SERVICE_DIR) / "app" / "datasets"

        # Copy candidate and review files into temporary directory
        self.tmp_cand_json = Path(self.tmp_dir) / "outcome_label_candidates_v2.json"
        self.tmp_review_csv = Path(self.tmp_dir) / "outcome_label_review_v2.csv"
        self.tmp_source_json = self.datasets_dir / "open_india_law_sample_150.json"

        shutil.copy(self.datasets_dir / "outcome_label_candidates_v2.json", self.tmp_cand_json)
        shutil.copy(self.datasets_dir / "outcome_label_review_v2.csv", self.tmp_review_csv)

        # Copy review_batches directory
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

    def test_initial_dashboard_state(self):
        dash = self.session.get_progress_dashboard()
        self.assertEqual(dash["total_candidates"], 150)
        self.assertEqual(dash["batch_1_definitive_candidates"], 99)
        # 34 cases verified in master queue; remaining 116 pending
        self.assertEqual(dash["total_verified"], 34)
        self.assertEqual(dash["pending"], 116)
        self.assertEqual(dash["approved"], 19)
        self.assertEqual(dash["corrected"], 15)
        self.assertEqual(dash["adjudicated_approved"], 0)
        self.assertEqual(dash["rejected"], 0)
        self.assertEqual(dash["disputed"], 0)
        self.assertEqual(dash["remaining_candidates"], 116)
        self.assertEqual(len(dash["verified_disposition_distribution"]), 6)
        self.assertEqual(dash["verified_disposition_distribution"].get("appeal_allowed"), 9)
        self.assertEqual(dash["verified_disposition_distribution"].get("appeal_dismissed"), 9)
        self.assertEqual(dash["verified_disposition_distribution"].get("remanded"), 2)
        self.assertEqual(dash["verified_disposition_distribution"].get("petition_allowed"), 7)
        self.assertEqual(dash["verified_disposition_distribution"].get("petition_dismissed"), 6)
        self.assertEqual(dash["verified_disposition_distribution"].get("dismissed_as_infructuous"), 1)

    def test_resume_and_batch_1_prioritization(self):
        # First pending in Batch 1 should be returned
        case = self.session.get_next_pending(batch_filter="batch_1")
        self.assertIsNotNone(case)
        self.assertTrue(case["is_batch_1"])
        self.assertIn("machine_candidate", case)
        self.assertIn("concluding_tail", case)
        self.assertEqual(case["current_review"]["review_status"], "pending_review")

    def test_accept_candidate_requires_confirmation(self):
        case = self.session.get_next_pending(batch_filter="batch_1")
        case_id = case["case_id"]

        # Calling without confirm=True must fail
        with self.assertRaises(ConfirmationRequiredError):
            self.session.submit_review(
                case_id=case_id,
                action="accept",
                reviewer_id="REV-01",
                evidence="Operative order confirmed in para 21",
                confirm=False
            )

    def test_accept_candidate_workflow(self):
        # Pick the next pending definitive case from Batch 1
        case = self.session.get_next_pending(batch_filter="batch_1")
        self.assertIsNotNone(case)
        case_id = case["case_id"]
        cand_disp = case["machine_candidate"]["normalized_disposition"]
        cand_party = case["machine_candidate"]["successful_party"]
        if cand_party in ["unresolved", "unknown"]:
            cand_party = "respondent"

        updated = self.session.submit_review(
            case_id=case_id,
            action="accept",
            reviewer_id="REV-LEGAL-01",
            evidence="The appeal is accordingly allowed and the judgment of the High Court set aside.",
            notes="Appeal allowed on merits.",
            disposition=cand_disp,
            successful_party=cand_party,
            confirm=True
        )

        self.assertEqual(updated["review_status"], "approved")
        self.assertEqual(updated["human_approved_label"], cand_disp)
        self.assertEqual(updated["reviewer_reference"], "REV-LEGAL-01")
        self.assertGreaterEqual(len(updated["audit_history"]), 1)
        self.assertEqual(updated["audit_history"][-1]["action"], "accept")

        # Verify dashboard update: 34 baseline + 1 newly approved = 35
        dash = self.session.get_progress_dashboard()
        self.assertEqual(dash["total_verified"], 35)
        self.assertEqual(dash["approved"], 20)
        self.assertEqual(dash["pending"], 115)

    def test_correct_candidate_workflow(self):
        case = self.session.get_next_pending(batch_filter="batch_1")
        case_id = case["case_id"]
        updated = self.session.submit_review(
            case_id=case_id,
            action="correct",
            reviewer_id="REV-SENIOR-02",
            disposition="partly_allowed",
            successful_party="unresolved",
            evidence="Sentence modified from 10 years to 5 years under Section 304 Part I",
            notes="Partial relief granted modifying sentence; not a complete allowance.",
            confirm=True
        )

        self.assertEqual(updated["review_status"], "corrected")
        self.assertEqual(updated["human_approved_label"], "partly_allowed")
        self.assertEqual(updated["human_successful_party"], "unresolved")
        self.assertGreaterEqual(len(updated["audit_history"]), 1)

    def test_reject_candidate_workflow(self):
        case_id = "OIL-SC-2021_INSC_327"
        updated = self.session.submit_review(
            case_id=case_id,
            action="reject",
            reviewer_id="REV-AUDITOR",
            notes="Machine extractor quoted historical trial court decree, not High Court order.",
            confirm=True
        )

        self.assertEqual(updated["review_status"], "rejected")
        self.assertEqual(updated["human_approved_label"], "rejected")
        self.assertEqual(updated["human_successful_party"], "unresolved")

        dash = self.session.get_progress_dashboard()
        self.assertEqual(dash["rejected"], 1)
        self.assertEqual(dash["total_verified"], 33)  # 34 baseline minus 1 rejected = 33 verified training samples

    def test_uncertain_and_deferral_workflow(self):
        case_id = "OIL-SC-2016_INSC_1151"  # Truncated case
        updated = self.session.submit_review(
            case_id=case_id,
            action="defer",
            reviewer_id="REV-LEGAL-01",
            notes="Judgment truncated at character 40,000; concluding order missing.",
            confirm=True
        )

        self.assertEqual(updated["review_status"], "deferred_needs_full_text")
        dash = self.session.get_progress_dashboard()
        self.assertEqual(dash["deferred"], 1)
        # Total verified remains 34 because baseline verified cases remain untouched
        self.assertEqual(dash["total_verified"], 34)

    def test_validation_errors(self):
        case_id = "OIL-SC-2021_INSC_327"

        # Empty reviewer ID
        with self.assertRaises(AnnotationValidationError):
            self.session.submit_review(case_id=case_id, action="accept", reviewer_id="", confirm=True)

        # Invalid disposition class
        with self.assertRaises(AnnotationValidationError):
            self.session.submit_review(
                case_id=case_id, action="correct", reviewer_id="REV-01",
                disposition="totally_won", successful_party="accused",
                evidence="valid evidence quote", notes="valid notes", confirm=True
            )

        # Invalid party
        with self.assertRaises(AnnotationValidationError):
            self.session.submit_review(
                case_id=case_id, action="correct", reviewer_id="REV-01",
                disposition="appeal_allowed", successful_party="judge",
                evidence="valid evidence quote", notes="valid notes", confirm=True
            )

    def test_two_reviewer_disagreement_and_lead_adjudication(self):
        case_id = "OIL-SC-2021_INSC_327"

        # 1. Primary Reviewer approves as appeal_allowed
        self.session.submit_review(
            case_id=case_id,
            action="accept",
            reviewer_id="REV-PRIMARY",
            disposition="appeal_allowed",
            successful_party="state_prosecution",
            evidence="Order 21 sets aside High Court ruling and allows appeal.",
            notes="State appeal allowed.",
            confirm=True
        )

        # 2. Second Reviewer disagrees, arguing partly_allowed
        record = self.session.submit_second_review(
            case_id=case_id,
            second_reviewer_id="REV-SECONDARY",
            disposition="partly_allowed",
            successful_party="unresolved",
            notes="Costs were not granted and only transfer portion was allowed.",
            confirm=True
        )

        # Case must transition to disputed
        self.assertEqual(record["review_status"], "disputed")
        self.assertIn("Dispute between", record["ambiguity_reason"])

        dash = self.session.get_progress_dashboard()
        self.assertEqual(dash["disputed"], 1)

        # 3. Same reviewer cannot be second reviewer
        with self.assertRaises(AnnotationValidationError):
            self.session.submit_second_review(
                case_id=case_id,
                second_reviewer_id="REV-PRIMARY",  # Duplicate reviewer
                disposition="appeal_allowed",
                successful_party="state_prosecution",
                confirm=True
            )

        # 4. Lead Adjudicator resolves dispute
        adjudicated = self.session.adjudicate_dispute(
            case_id=case_id,
            adjudicator_id="HON-LEAD-ADJUDICATOR",
            adjudicated_disposition="appeal_allowed",
            adjudicated_party="state_prosecution",
            adjudication_notes="High court judgment was set aside in its entirety; appeal was fully allowed.",
            confirm=True
        )

        self.assertEqual(adjudicated["review_status"], "adjudicated_approved")
        self.assertEqual(adjudicated["human_approved_label"], "appeal_allowed")
        self.assertEqual(adjudicated["human_successful_party"], "state_prosecution")
        self.assertIn("[ADJUDICATED]", adjudicated["human_notes"])

        dash_after = self.session.get_progress_dashboard()
        self.assertEqual(dash_after["adjudicated_approved"], 1)
        self.assertEqual(dash_after["disputed"], 0)
        self.assertEqual(dash_after["total_verified"], 34)

    def test_training_readiness_checks(self):
        readiness = self.session.check_training_readiness(min_total_verified=30)
        self.assertFalse(readiness["is_training_eligible"])
        self.assertEqual(readiness["recommended_mode"], "qualitative_research_mode")
        self.assertTrue(any("insufficient eligible records" in b.lower() for b in readiness["blockers"]))

    def test_dashboard_tracks_successful_party_and_reviewer_progress(self):
        # Review a case and verify party and reviewer progress tracking
        case_id = "OIL-SC-2021_INSC_327"
        self.session.submit_review(
            case_id=case_id,
            action="accept",
            reviewer_id="REV-LEGAL-01",
            evidence="Operative order confirmed in para 21",
            notes="State appeal allowed.",
            confirm=True
        )

        dash = self.session.get_progress_dashboard()
        self.assertEqual(dash["successful_party_distribution"].get("state_prosecution"), 5)
        self.assertIn("REV-LEGAL-01", dash["reviewer_wise_progress"])
        self.assertEqual(dash["reviewer_wise_progress"]["REV-LEGAL-01"]["approved"], 1)
        self.assertEqual(dash["reviewer_wise_progress"]["REV-LEGAL-01"]["total"], 1)

    def test_batch_plan_partitioning_into_sub_batches_of_five(self):
        b1_records = [r for r in self.session.records if r.get("case_id") in self.session.batch_1_ids]
        self.assertEqual(len(b1_records), 99)
        batch_size = 5
        num_sub_batches = ((len(b1_records) - 1) // batch_size) + 1
        self.assertEqual(num_sub_batches, 20)  # 19 of 5 + 1 of 4

        # First sub-batch has 5 cases
        sub_batch_1 = b1_records[0:5]
        self.assertEqual(len(sub_batch_1), 5)
        self.assertEqual(sub_batch_1[0]["case_id"], "OIL-SC-2021_INSC_327")

        # Last sub-batch has 4 cases
        sub_batch_20 = b1_records[95:99]
        self.assertEqual(len(sub_batch_20), 4)

    def test_live_source_hashes_unaltered(self):
        live_session = OutcomeAnnotationSessionManager()
        integrity = live_session.verify_source_integrity()
        self.assertTrue(integrity["open_india_law_sample_150.json"])
        self.assertTrue(integrity["indian_judgments.json"])


class TestTrainingReadinessIntegration(unittest.TestCase):
    """Verifies that pending and rejected records are excluded from training datasets."""

    def test_builder_excludes_unapproved_and_rejected(self):
        builder = VerifiedOutcomeDatasetBuilder()
        manifest = builder.build_dataset(allow_empty_manifest=True)
        self.assertFalse(manifest["is_training_eligible"])
        # Under dual-model gatekeeper, Model B has 27 substantive records (below minimum threshold of 30)
        self.assertEqual(manifest["human_approved_found"], 27)
        self.assertEqual(len(manifest["records"]), 0)


if __name__ == "__main__":
    unittest.main()
