"""
Feature 4.14: Dual-Model Training Gatekeeper Regression Tests
JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Verifies independent evaluation of:
  - Model A: Judicial Disposition (merits-eligible only)
  - Model B: Successful Party (substantive-party victories only)
Enforces strict safety rules: zero leakage, zero unverified data, decoupled readiness gates.
"""

import os
import sys
import copy
import unittest
from pathlib import Path
from sklearn.model_selection import GroupShuffleSplit

# Ensure ml-service root is in sys.path
ML_SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ML_SERVICE_DIR)

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS,
    MODEL_A_EXCLUDED_PROCEDURAL_DISPOSITIONS,
    MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES,
    MODEL_B_EXCLUDED_NON_SUBSTANTIVE_PARTIES,
)
from scripts.build_verified_outcome_dataset import (
    TargetLeakageSanitizer,
    VerifiedOutcomeDatasetBuilder,
)
from app.prediction.verified_outcome_model import (
    VerifiedOutcomePredictor,
    InsufficientVerifiedDataError,
)


class TestDualModelTrainingGatekeeper(unittest.TestCase):
    """Regression test suite for Feature 4.14 Dual-Model Training Gatekeeper."""

    def setUp(self):
        self.session = OutcomeAnnotationSessionManager()
        self.sanitizer = TargetLeakageSanitizer()

    def test_live_corpus_dual_model_baseline_counts(self):
        """Verify baseline counts across Model A and Model B in the current 37-case verified corpus."""
        readiness = self.session.check_training_readiness(min_total_verified=30, min_minority_samples=5)

        # Global stats: both models pass thresholds!
        self.assertTrue(readiness["is_training_eligible"])
        self.assertEqual(readiness["total_verified_count"], 37)
        self.assertEqual(readiness["recommended_mode"], "statistical_verified")

        # Model A stats (34 eligible, threshold >= 30 passed)
        model_a = readiness["model_a"]
        self.assertEqual(model_a["name"], "Model A — Judicial Disposition")
        self.assertTrue(model_a["is_training_eligible"])
        self.assertEqual(model_a["eligible_count"], 34)
        self.assertEqual(model_a["excluded_count"], 3)
        self.assertEqual(model_a["class_distribution"], {
            "appeal_allowed": 9,
            "appeal_dismissed": 11,
            "petition_allowed": 8,
            "petition_dismissed": 6,
        })
        self.assertEqual(model_a["excluded_distribution"], {
            "remanded": 2,
            "dismissed_as_infructuous": 1,
        })
        self.assertEqual(model_a["minority_class_count"], 6)  # petition_dismissed: 6 (threshold >= 5 satisfied)

        # Model B stats (30 eligible, threshold >= 30 passed!)
        model_b = readiness["model_b"]
        self.assertEqual(model_b["name"], "Model B — Successful Party")
        self.assertTrue(model_b["is_training_eligible"])
        self.assertEqual(model_b["eligible_count"], 30)
        self.assertEqual(model_b["excluded_count"], 7)
        self.assertEqual(model_b["class_distribution"], {
            "respondent": 10,
            "petitioner": 8,
            "accused": 7,
            "state_prosecution": 5,
        })
        self.assertEqual(model_b["excluded_distribution"], {
            "none_procedural": 3,
            "unresolved": 4,
        })
        self.assertEqual(model_b["minority_class_count"], 5)  # state_prosecution: 5 (threshold >= 5 satisfied)

    def test_one_procedural_class_with_count_one_does_not_block_model_a_minority_threshold(self):
        """
        Verify that a procedural class with count 1 (e.g. dismissed_as_infructuous)
        does not block Model A's minority representation threshold.
        """
        # Create a mock session where merits classes each have >= 5 samples,
        # but one procedural record has count 1.
        mock_session = copy.deepcopy(self.session)
        mock_records = []

        # 30 merits records (all >= 5 samples per class)
        merits_specs = [
            ("appeal_allowed", "accused", 10),
            ("appeal_dismissed", "respondent", 10),
            ("petition_allowed", "petitioner", 5),
            ("petition_dismissed", "respondent", 5),
        ]
        case_idx = 1
        for disp, party, count in merits_specs:
            for _ in range(count):
                mock_records.append({
                    "case_id": f"MOCK-CASE-{case_idx}",
                    "review_status": "approved",
                    "human_approved_label": disp,
                    "human_successful_party": party,
                })
                case_idx += 1

        # Add 1 procedural record with count 1
        mock_records.append({
            "case_id": "MOCK-CASE-PROCEDURAL-1",
            "review_status": "approved",
            "human_approved_label": "dismissed_as_infructuous",
            "human_successful_party": "none_procedural",
        })

        mock_session.records = mock_records
        readiness = mock_session.check_training_readiness(min_total_verified=30, min_minority_samples=5)

        # Model A should pass its minority threshold because dismissed_as_infructuous is excluded!
        model_a = readiness["model_a"]
        self.assertEqual(model_a["eligible_count"], 30)
        self.assertEqual(model_a["excluded_count"], 1)
        self.assertEqual(model_a["minority_class_count"], 5)  # min of 10, 10, 5, 5 is 5
        self.assertTrue(model_a["is_training_eligible"])
        self.assertEqual(len(model_a["blockers"]), 0)

    def test_remanded_and_infructuous_cases_excluded_from_model_a_training(self):
        """Verify remanded and infructuous cases are strictly excluded from Model A training."""
        readiness = self.session.check_training_readiness(min_total_verified=30, min_minority_samples=5)
        model_a = readiness["model_a"]

        # Neither remanded nor infructuous appears in class_distribution
        self.assertNotIn("remanded", model_a["class_distribution"])
        self.assertNotIn("dismissed_as_infructuous", model_a["class_distribution"])

        # Both appear in excluded_distribution
        self.assertEqual(model_a["excluded_distribution"].get("remanded"), 2)
        self.assertEqual(model_a["excluded_distribution"].get("dismissed_as_infructuous"), 1)

        # Extracted eligible records for Model A
        eligible_a = self.session.get_eligible_training_records(target="model_a")
        self.assertEqual(len(eligible_a), 34)
        for r in eligible_a:
            self.assertIn(r["human_approved_label"], MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS)
            self.assertNotIn(r["human_approved_label"], ["remanded", "dismissed_as_infructuous"])

    def test_none_procedural_and_unresolved_excluded_from_model_b_training(self):
        """Verify none_procedural and unresolved are strictly excluded from Model B training."""
        readiness = self.session.check_training_readiness(min_total_verified=30, min_minority_samples=5)
        model_b = readiness["model_b"]

        # Neither none_procedural nor unresolved appears in class_distribution
        self.assertNotIn("none_procedural", model_b["class_distribution"])
        self.assertNotIn("unresolved", model_b["class_distribution"])

        # Both appear in excluded_distribution
        self.assertEqual(model_b["excluded_distribution"].get("none_procedural"), 3)
        self.assertEqual(model_b["excluded_distribution"].get("unresolved"), 4)

        # Extracted eligible records for Model B
        eligible_b = self.session.get_eligible_training_records(target="model_b")
        self.assertEqual(len(eligible_b), 30)
        for r in eligible_b:
            self.assertIn(r["human_successful_party"], MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES)
            self.assertNotIn(r["human_successful_party"], ["none_procedural", "unresolved"])

    def test_model_b_insufficient_class_representation_blocks_overall_readiness_independently(self):
        """Verify that insufficient representation in Model B blocks overall readiness independently."""
        mock_session = copy.deepcopy(self.session)
        mock_records = []

        # Model A satisfies all criteria: 32 merits records with all classes >= 5
        # Model B: respondent=15, petitioner=14, state_prosecution=3 (minority < 5!)
        a_classes = ["appeal_allowed", "appeal_dismissed", "petition_allowed", "petition_dismissed"]
        for idx in range(32):
            disp = a_classes[idx % 4]
            if idx < 15:
                party = "respondent"
            elif idx < 29:
                party = "petitioner"
            else:
                party = "state_prosecution"  # only 3 samples!
            mock_records.append({
                "case_id": f"MOCK-{idx}",
                "review_status": "approved",
                "human_approved_label": disp,
                "human_successful_party": party,
            })

        mock_session.records = mock_records
        readiness = mock_session.check_training_readiness(min_total_verified=30, min_minority_samples=5)

        # Model A passes (32 samples, min class 8 >= 5)
        self.assertTrue(readiness["model_a"]["is_training_eligible"])

        # Model B fails (state_prosecution has only 3 samples, min required 5)
        self.assertFalse(readiness["model_b"]["is_training_eligible"])
        self.assertIn("Model B (Successful Party) minority class representation is 3", readiness["model_b"]["blockers"][0])

        # Overall readiness MUST be false
        self.assertFalse(readiness["is_training_eligible"])
        self.assertEqual(readiness["recommended_mode"], "qualitative_research_mode")

    def test_model_a_passing_while_model_b_fails_keeps_overall_readiness_false(self):
        """When Model A passes and Model B fails, overall readiness is false."""
        mock_session = copy.deepcopy(self.session)
        mock_records = []

        # Model A: 32 samples (8 of each class) -> PASSES
        # Model B: only 20 samples -> FAILS on count
        a_classes = ["appeal_allowed", "appeal_dismissed", "petition_allowed", "petition_dismissed"]
        for idx in range(32):
            disp = a_classes[idx % 4]
            party = "respondent" if idx < 20 else "none_procedural"  # 12 none_procedural excluded!
            mock_records.append({
                "case_id": f"MOCK-{idx}",
                "review_status": "approved",
                "human_approved_label": disp,
                "human_successful_party": party,
            })

        mock_session.records = mock_records
        readiness = mock_session.check_training_readiness(min_total_verified=30, min_minority_samples=5)

        self.assertTrue(readiness["model_a"]["is_training_eligible"])
        self.assertFalse(readiness["model_b"]["is_training_eligible"])
        self.assertEqual(readiness["model_b"]["eligible_count"], 20)
        self.assertFalse(readiness["is_training_eligible"])
        self.assertEqual(readiness["recommended_mode"], "qualitative_research_mode")

    def test_model_b_passing_while_model_a_fails_keeps_overall_readiness_false(self):
        """When Model B passes and Model A fails, overall readiness is false."""
        mock_session = copy.deepcopy(self.session)
        mock_records = []

        # Model B: 32 samples (8 of each class) -> PASSES
        # Model A: only 20 samples (12 remanded excluded) -> FAILS on count
        b_classes = ["respondent", "petitioner", "state_prosecution", "accused"]
        for idx in range(32):
            party = b_classes[idx % 4]
            disp = "appeal_allowed" if idx < 20 else "remanded"  # 12 remanded excluded!
            mock_records.append({
                "case_id": f"MOCK-{idx}",
                "review_status": "approved",
                "human_approved_label": disp,
                "human_successful_party": party,
            })

        mock_session.records = mock_records
        readiness = mock_session.check_training_readiness(min_total_verified=30, min_minority_samples=5)

        self.assertFalse(readiness["model_a"]["is_training_eligible"])
        self.assertTrue(readiness["model_b"]["is_training_eligible"])
        self.assertEqual(readiness["model_a"]["eligible_count"], 20)
        self.assertFalse(readiness["is_training_eligible"])
        self.assertEqual(readiness["recommended_mode"], "qualitative_research_mode")

    def test_both_models_passing_is_necessary_for_overall_readiness(self):
        """Only when BOTH models satisfy all gates does overall readiness become True."""
        mock_session = copy.deepcopy(self.session)
        mock_records = []

        # 32 cases where both Model A and Model B have 8 samples in each of 4 classes
        a_classes = ["appeal_allowed", "appeal_dismissed", "petition_allowed", "petition_dismissed"]
        b_classes = ["respondent", "petitioner", "state_prosecution", "accused"]

        for idx in range(32):
            mock_records.append({
                "case_id": f"MOCK-{idx}",
                "review_status": "approved",
                "human_approved_label": a_classes[idx % 4],
                "human_successful_party": b_classes[idx % 4],
            })

        mock_session.records = mock_records
        readiness = mock_session.check_training_readiness(min_total_verified=30, min_minority_samples=5)

        self.assertTrue(readiness["model_a"]["is_training_eligible"])
        self.assertTrue(readiness["model_b"]["is_training_eligible"])
        self.assertTrue(readiness["is_training_eligible"])
        self.assertEqual(readiness["recommended_mode"], "statistical_verified")
        self.assertEqual(len(readiness["blockers"]), 0)

    def test_pending_annotations_never_enter_either_dataset(self):
        """Verify that pending annotations (review_status == pending_review) are strictly excluded."""
        readiness = self.session.check_training_readiness(min_total_verified=30, min_minority_samples=5)

        # 113 pending cases
        self.assertEqual(readiness["remaining_pending"], 113)

        # Sum of eligible and excluded equals exactly 37 (verified records) for both models
        total_a = readiness["model_a"]["eligible_count"] + readiness["model_a"]["excluded_count"]
        total_b = readiness["model_b"]["eligible_count"] + readiness["model_b"]["excluded_count"]
        self.assertEqual(total_a, 37)
        self.assertEqual(total_b, 37)

        # Ensure no pending record is in eligible training records
        records_a = self.session.get_eligible_training_records("model_a")
        records_b = self.session.get_eligible_training_records("model_b")
        for r in records_a + records_b:
            self.assertIn(r.get("review_status"), ["approved", "corrected", "adjudicated_approved"])
            self.assertNotEqual(r.get("review_status"), "pending_review")

    def test_group_aware_splitting_and_leakage_protections_remain_intact(self):
        """Verify TargetLeakageSanitizer and GroupShuffleSplit isolation across proceedings."""
        # 1. Target Leakage Sanitizer verification
        text = (
            "Arguments were heard regarding fundamental rights under Article 21. "
            "The petitioner challenged the preventive detention order.\n\n"
            "ORDER OF THE COURT:\n"
            "The appeal is allowed and the appellant is set at liberty forthwith."
        )
        sanitized, meta = self.sanitizer.sanitize_judgment_text(text)
        self.assertTrue(meta["truncated_operative_section"])
        self.assertNotIn("ORDER OF THE COURT", sanitized)
        self.assertNotIn("appeal is allowed", sanitized.lower())
        self.assertIn("The petitioner challenged the preventive detention order", sanitized)

        # 2. GroupShuffleSplit isolation verification
        mock_texts = [f"Text for proceeding {i}" for i in range(20)]
        mock_labels = ["appeal_allowed" if i % 2 == 0 else "appeal_dismissed" for i in range(20)]
        # Related proceedings share groups (e.g. connected appeals)
        mock_groups = [f"GROUP_{i // 2}" for i in range(20)]  # 10 groups of 2

        gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
        train_idx, test_idx = next(gss.split(mock_texts, mock_labels, groups=mock_groups))

        train_groups = set(mock_groups[i] for i in train_idx)
        test_groups = set(mock_groups[i] for i in test_idx)
        overlap = train_groups.intersection(test_groups)

        self.assertEqual(len(overlap), 0, f"Case group leakage across train/test splits: {overlap}")
        self.assertGreater(len(train_idx), 0)
        self.assertGreater(len(test_idx), 0)


if __name__ == "__main__":
    unittest.main()
