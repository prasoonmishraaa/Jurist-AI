"""
Unit and Integration Tests for Feature 4.4: Verified-Label Legal Outcome Prediction Pipeline
JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Tests:
1. Target Leakage Sanitizer: Stripping operative headings, disposition phrases, and forbidden fields.
2. Approved-Only Gatekeeper: Inclusion of approved records, strict exclusion of pending, uncertain, rejected records.
3. Case-Level Lineage & Grouping: Grouping connected cases to prevent split leakage.
4. Insufficient-Label Safeguards: Refusal to train a statistical model when human-approved labels < threshold.
5. Fallback Behavior: Returning qualitative research mode with transparent audit counts and disclaimers.
6. Pipeline Execution & Evaluation on Valid Data: Training Scikit-learn Pipeline on mock verified data,
   verifying group isolation, balanced class handling, and evaluation metrics.
7. Model Serialization & Loading: Joblib persistence and loading.
8. API Alignment: Response schema and qualitative mode compatibility.
"""

import os
import sys
import re
import json
import tempfile
import shutil
import unittest
from pathlib import Path
import numpy as np

# Ensure ml-service root is in sys.path
ML_SERVICE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ML_SERVICE_DIR)

from scripts.build_verified_outcome_dataset import (
    TargetLeakageSanitizer,
    OutcomeDataAuditor,
    VerifiedOutcomeDatasetBuilder,
    InsufficientApprovedLabelsError
)
from app.prediction.verified_outcome_model import (
    VerifiedOutcomePredictor,
    InsufficientVerifiedDataError
)


class TestTargetLeakageSanitizer(unittest.TestCase):
    """Verifies that operative orders, disposition phrases, and forbidden fields are stripped."""

    def setUp(self):
        self.sanitizer = TargetLeakageSanitizer()

    def test_strip_operative_order_heading(self):
        text = (
            "The petitioner approached this Court under Article 226 alleging illegal detention. "
            "The respondent State filed an affidavit stating compliance with arrest guidelines. "
            "Heard both sides at length on fundamental rights under Article 21.\n\n"
            "ORDER:\n"
            "In view of the above findings, the petition is hereby allowed and the detenue is ordered to be released."
        )
        sanitized, meta = self.sanitizer.sanitize_judgment_text(text)
        self.assertTrue(meta["truncated_operative_section"])
        self.assertNotIn("ORDER:", sanitized)
        self.assertNotIn("petition is hereby allowed", sanitized)
        self.assertIn("The petitioner approached this Court", sanitized)

    def test_strip_disposition_phrases(self):
        text = (
            "The prosecution examined 12 witnesses regarding the recovery of stolen goods. "
            "In the result, the appeal is allowed and the conviction is set aside."
        )
        sanitized, meta = self.sanitizer.sanitize_judgment_text(text)
        self.assertNotIn("appeal is allowed", sanitized.lower())
        self.assertNotIn("conviction is set aside", sanitized.lower())
        self.assertIn("[DISPOSITION_REDACTED]", sanitized)

    def test_bare_terminal_dispositions_redacted(self):
        """Bare terminal verdicts (e.g. 'Appeals dismissed.', 'Petition allowed:') must be stripped."""
        text = (
            "Arguments were heard on Section 138 of the Negotiable Instruments Act. "
            "The cheque was issued in discharge of a legally enforceable debt.\n\n"
            "D N.J.\n\nAppeals dismissed."
        )
        sanitized, meta = self.sanitizer.sanitize_judgment_text(text)
        self.assertNotIn("Appeals dismissed", sanitized)
        self.assertIn("Negotiable Instruments Act", sanitized)

    def test_intervening_adverbs_and_compound_clauses(self):
        """Intervening adverbs like 'therefore fails and is hereby dismissed' must be redacted."""
        text = (
            "The testimony of the eyewitness was cogent and corroborated by medical evidence. "
            "The appeal therefore fails and is hereby dismissed. The appellant shall surrender to his bail bonds."
        )
        sanitized, meta = self.sanitizer.sanitize_judgment_text(text)
        self.assertNotIn("appeal therefore fails", sanitized.lower())
        self.assertNotIn("is hereby dismissed", sanitized.lower())
        self.assertIn("[DISPOSITION_REDACTED]", sanitized)

    def test_first_person_active_voice_judicial_phrases(self):
        """First-person judicial actions like 'we dismiss the appeals' or 'we set aside' must be redacted."""
        text = (
            "The private concerns followed standard disciplinary procedures. "
            "In these circumstances, we dismiss the appeals without any order as to costs."
        )
        sanitized, meta = self.sanitizer.sanitize_judgment_text(text)
        self.assertNotIn("we dismiss the appeals", sanitized.lower())
        self.assertIn("disciplinary procedures", sanitized)

    def test_decree_and_order_reversal_phrases(self):
        """Reversal phrases like 'The same are set aside' or 'order of detention is set aside' must be redacted."""
        text = (
            "The orders of the High Court granting back wages were arbitrary. "
            "The same are set aside and the appeal is allowed."
        )
        sanitized, meta = self.sanitizer.sanitize_judgment_text(text)
        self.assertNotIn("the same are set aside", sanitized.lower())
        self.assertNotIn("appeal is allowed", sanitized.lower())

    def test_scraper_kanoon_suffixes(self):
        """Kanoon scraper artifacts like '[SECTION] ## Appeal allowed.' must be cleanly stripped."""
        text = (
            "Costs are quantified at Rs. 25,000 for the appellants.\n\n"
            "RP.\n\n[SECTION] ## Appeal allowed."
        )
        sanitized, meta = self.sanitizer.sanitize_judgment_text(text)
        self.assertNotIn("[SECTION]", sanitized)
        self.assertNotIn("## Appeal allowed", sanitized)

    def test_older_judgments_without_headings_concluding_transition(self):
        """Unheaded older judgments must truncate at concluding operative transition paragraph."""
        padding = "Detailed analysis of evidence and legal contentions.\n" * 25
        concluding_order = (
            "For the foregoing reasons, we do not differ from the view taken by the High Court "
            "in maintaining the conviction of the appellant. The appeal therefore fails and is hereby dismissed. "
            "The appellant is on bail. He shall surrender to his bail bonds."
        )
        full_text = padding + concluding_order
        sanitized, meta = self.sanitizer.sanitize_judgment_text(full_text)
        self.assertTrue(meta["truncated_operative_section"])
        self.assertNotIn("maintaining the conviction of the appellant", sanitized)
        self.assertNotIn("is hereby dismissed", sanitized)
        self.assertIn("Detailed analysis of evidence", sanitized)

    def test_negative_examples_preserve_factual_and_procedural_narratives(self):
        """Pre-decision facts, counsel arguments, precedent citations and statutory text must be preserved."""
        factual_text = (
            "The appellant was convicted by the Sessions Court under Section 302 IPC. "
            "The appellant filed an appeal before the High Court, but that appeal was dismissed by the High Court on 12.01.2018. "
            "Mr. Rohatgi, learned Senior Counsel for the respondent, argued that the appeal ought to be dismissed "
            "as no substantial question of law was formulated. "
            "Under Section 100 of the Code of Civil Procedure, an appeal lies only on a substantial question of law. "
            "In State of Haryana v. Bhajan Lal, this Court held that extraordinary powers under Article 226 must be sparingly used."
        )
        sanitized, meta = self.sanitizer.sanitize_judgment_text(factual_text)
        # Factual and legal core must remain preserved
        self.assertIn("Sessions Court under Section 302 IPC", sanitized)
        self.assertIn("Mr. Rohatgi", sanitized)
        self.assertIn("Section 100 of the Code of Civil Procedure", sanitized)
        self.assertIn("Bhajan Lal", sanitized)
        self.assertIn("Article 226", sanitized)

    def test_zero_leakage_on_all_150_live_judgments(self):
        """Sanitizing all 150 live corpus judgments must result in zero residual target outcome leaks."""
        oil_path = Path(ML_SERVICE_DIR) / "app" / "datasets" / "open_india_law_sample_150.json"
        with open(oil_path, "r", encoding="utf-8") as f:
            cases = json.load(f)

        leakage_patterns = [
            re.compile(r"(?:^|\n|\.\s+)(?:Appeals?|Petitions?)\s+(?:allowed|dismissed|disposed\s+of)\s*[\.:]?", re.IGNORECASE),
            re.compile(r"\bwe\s+(?:hereby\s+|accordingly\s+|therefore\s+)?(?:allow|dismiss|partly\s+allow|set\s+aside|quash)\b", re.IGNORECASE),
            re.compile(r"\bappeal\s+therefore\s+fails\s+and\s+is\s+hereby\s+dismissed\b", re.IGNORECASE),
            re.compile(r"\bset\s+aside\s+(?:the\s+)?(?:ihe\s+)?order\s+of\s+detention\b", re.IGNORECASE),
            re.compile(r"\[SECTION\]\s*##", re.IGNORECASE),
        ]

        total_leaks = 0
        for c in cases:
            text = c.get("judgmentText", "")
            sanitized, _ = self.sanitizer.sanitize_judgment_text(text)
            for rx in leakage_patterns:
                if rx.search(sanitized):
                    total_leaks += 1

        self.assertEqual(total_leaks, 0, f"Found {total_leaks} residual outcome leaks across 150 judgments!")

    def test_extract_pre_decision_features_excludes_forbidden_fields(self):
        raw_case = {
            "id": "OIL-TEST-001",
            "caseTitle": "Ram Kumar v. State of U.P.",
            "court": "Supreme Court of India",
            "judgmentDate": "2023-05-15",
            "category": "Criminal Law",
            "legalProvisions": ["Section 302 IPC", "Section 439 CrPC"],
            "summary": "The Supreme Court allowed the appeal and acquitted the appellant.",  # Forbidden
            "outcome": "Allowed",  # Forbidden
            "outcomeRationale": "Prosecution failed to establish chain of custody.",  # Forbidden
            "article141Status": "Binding precedent",  # Forbidden
            "judgmentText": (
                "The appellant was convicted under Section 302 IPC by the Sessions Court. "
                "The High Court affirmed the conviction. The appellant contends lack of eye-witnesses.\n\n"
                "FINAL ORDER:\nThe appeal is allowed and conviction is quashed."
            )
        }
        features = self.sanitizer.extract_pre_decision_features(raw_case)

        # Factual composite must not contain forbidden outcome fields
        composite = features["factual_composite"]
        self.assertNotIn("The Supreme Court allowed the appeal and acquitted", composite)
        self.assertNotIn("Prosecution failed to establish chain of custody", composite)
        self.assertNotIn("FINAL ORDER", composite)
        self.assertNotIn("conviction is quashed", composite)
        self.assertIn("Ram Kumar v. State of U.P.", composite)
        self.assertIn("Section 302 IPC", composite)


class TestApprovedOnlyGatekeeper(unittest.TestCase):
    """Verifies that only human-approved annotations can enter training datasets."""

    def setUp(self):
        self.auditor = OutcomeDataAuditor()
        self.builder = VerifiedOutcomeDatasetBuilder()

    def test_live_dataset_audit_reflects_truth(self):
        audit = self.auditor.audit_all()
        self.assertEqual(audit["candidate_records_count"], 150)
        # 46 cases verified (Case 1 + 5 from Batch 1.1 + 5 from Batch 1.2 + 5 from Batch 1.3 + 5 from Batch 1.4 + 5 from Batch 1.5 + 8 from Batch 1.6 + 3 from Batch 1.7 + 5 from Batch 1.8 + 4 from Batch 1.9); remaining 104 are pending
        self.assertEqual(audit["human_approved_count"], 46)
        self.assertEqual(audit["pending_review_count"], 104)
        self.assertEqual(len(audit["verified_class_distribution"]), 6)
        self.assertEqual(audit["verified_class_distribution"].get("appeal_allowed"), 11)
        self.assertEqual(audit["verified_class_distribution"].get("appeal_dismissed"), 17)
        self.assertEqual(audit["verified_class_distribution"].get("remanded"), 2)
        self.assertEqual(audit["verified_class_distribution"].get("petition_allowed"), 8)
        self.assertEqual(audit["verified_class_distribution"].get("petition_dismissed"), 7)
        self.assertEqual(audit["verified_class_distribution"].get("dismissed_as_infructuous"), 1)
        self.assertGreaterEqual(audit["cases_with_sufficient_pre_decision_text"], 140)

    def test_builder_refuses_to_generate_dataset_when_unapproved(self):
        # When required minimum samples exceed verified records (e.g. min 50 required), builder refuses
        manifest = self.builder.build_dataset(allow_empty_manifest=True, min_approved_required=50)
        self.assertEqual(manifest["dataset_status"], "unfinalized_pending_human_review")
        self.assertFalse(manifest["is_training_eligible"])
        self.assertEqual(len(manifest["records"]), 0)
        self.assertIn("missing_requirements", manifest)

    def test_builder_raises_error_if_empty_not_allowed(self):
        with self.assertRaises(InsufficientApprovedLabelsError):
            self.builder.build_dataset(allow_empty_manifest=False, min_approved_required=50)

    def test_duplicate_case_grouping(self):
        audit = self.auditor.audit_all()
        related = audit["duplicate_or_related_cases"]
        self.assertTrue(any("OIL-DHC-DLHC010440622015" in grp for grp in related))
        self.assertTrue(any("OIL-DHC-DLHC012615072014" in grp for grp in related))


class TestVerifiedOutcomePredictorSafety(unittest.TestCase):
    """Tests ML safety guardrails and qualitative fallback when verified data is missing."""

    def setUp(self):
        self.predictor = VerifiedOutcomePredictor()

    def test_training_fails_safely_on_unverified_dataset(self):
        builder = VerifiedOutcomeDatasetBuilder()
        # Simulated ineligible manifest (e.g. required threshold 50)
        manifest = builder.build_dataset(allow_empty_manifest=True, min_approved_required=50)

        with self.assertRaises(InsufficientVerifiedDataError):
            self.predictor.train_and_evaluate(manifest, raise_if_ineligible=True)

        self.assertFalse(self.predictor.is_trained)
        self.assertFalse(self.predictor.safeguard_status["eligible"])

    def test_predict_outcome_falls_back_to_qualitative_mode(self):
        query = "Appellant challenges order of detention passed under National Security Act without grounds communicated."
        pred = self.predictor.predict_outcome(query)

        self.assertEqual(pred["status"], "qualitative_research_mode")
        self.assertEqual(pred["predictionMode"], "qualitative_research")
        self.assertEqual(pred["estimatedOutcome"], "Structured Doctrinal & Authority Assessment")
        self.assertIsNone(pred["confidenceScore"])
        self.assertEqual(pred["confidenceLevel"], "Informational")
        self.assertIn("verifiedDataStatus", pred)
        self.assertEqual(pred["verifiedDataStatus"]["humanApprovedRecords"], 0)
        self.assertEqual(pred["verifiedDataStatus"]["candidateRecords"], 150)
        self.assertFalse(pred["verifiedDataStatus"]["statisticalModelTrained"])
        self.assertIn("disclaimer", pred)

    def test_short_input_returns_insufficient_input(self):
        pred = self.predictor.predict_outcome("bail plea")
        self.assertEqual(pred["status"], "insufficient_input")


class TestVerifiedPipelineOnValidatedData(unittest.TestCase):
    """Tests the Scikit-learn Pipeline and GroupShuffleSplit on mock verified data."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.predictor = VerifiedOutcomePredictor(model_dir=self.tmp_dir)

        # Create 40 mock cases with 2 classes and connected group IDs
        records = []
        for i in range(20):
            records.append({
                "case_id": f"VERIFIED-{i:03d}",
                "case_group_id": f"GROUP-{i // 2:03d}",  # 2 cases per group
                "factual_composite": f"Bail application filed under Section 439 CrPC. Accused has clean antecedent and no prior conviction. Custodial interrogation complete for subject {i}.",
                "verified_label": "bail_granted"
            })
        for i in range(20, 40):
            records.append({
                "case_id": f"VERIFIED-{i:03d}",
                "case_group_id": f"GROUP-{i // 2:03d}",
                "factual_composite": f"Bail application under Section 439 CrPC. Accused is habitual offender facing multiple charges under NDPS Act. Flight risk established for subject {i}.",
                "verified_label": "bail_rejected"
            })

        self.mock_dataset = {
            "builder_version": "v4.4.0-test",
            "is_training_eligible": True,
            "records": records
        }

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_pipeline_trains_and_evaluates_with_group_isolation(self):
        metrics = self.predictor.train_and_evaluate(self.mock_dataset, test_size=0.25, random_state=42)

        self.assertTrue(self.predictor.is_trained)
        self.assertIn("testAccuracy", metrics)
        self.assertIn("testBalancedAccuracy", metrics)
        self.assertIn("testMacroF1", metrics)
        self.assertIn("confusionMatrix", metrics)
        self.assertTrue(metrics["caseLevelGroupIsolationVerified"])
        self.assertGreaterEqual(metrics["testAccuracy"], 0.70)

        # Predict using trained pipeline
        pred = self.predictor.predict_outcome(
            "Applicant applies for regular bail. First-time offender with no criminal history and charge-sheet filed.",
            max_similarity=0.45
        )
        self.assertEqual(pred["status"], "validated_estimate")
        self.assertEqual(pred["predictionMode"], "statistical_verified")
        self.assertIn(pred["estimatedOutcome"], ["bail_granted", "bail_rejected"])
        self.assertIn("probabilities", pred)
        self.assertIn("disclaimer", pred)

    def test_model_serialization_and_reloading(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            predictor = VerifiedOutcomePredictor(model_dir=tmp_dir)
            predictor.train_and_evaluate(self.mock_dataset, test_size=0.25, random_state=42)

            # Reload into a fresh instance
            fresh_predictor = VerifiedOutcomePredictor(model_dir=tmp_dir)
            loaded = fresh_predictor.load_model()
            self.assertTrue(loaded)
            self.assertTrue(fresh_predictor.is_trained)
            self.assertEqual(fresh_predictor.classes_, predictor.classes_)

            pred = fresh_predictor.predict_outcome("Applicant with severe criminal history seeking bail.")
            self.assertEqual(pred["status"], "validated_estimate")


if __name__ == "__main__":
    unittest.main()
