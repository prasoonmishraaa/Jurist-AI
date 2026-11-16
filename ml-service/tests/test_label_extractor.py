"""
Unit Tests for Judicial Disposition Extraction Engine
JURIST AI — Feature 4.2: Outcome Prediction Improvement
"""

import os
import sys
import json
import tempfile
import unittest

# Ensure ml-service root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ML_SERVICE_DIR = os.path.dirname(CURRENT_DIR)
if ML_SERVICE_DIR not in sys.path:
    sys.path.insert(0, ML_SERVICE_DIR)

from app.prediction.label_extractor import (
    JudicialDispositionExtractor,
    DispositionCandidate,
    VALID_DISPOSITIONS,
)


class TestJudicialDispositionExtractor(unittest.TestCase):
    """Comprehensive test suite for conservative judicial disposition extraction."""

    def setUp(self):
        self.extractor = JudicialDispositionExtractor(concluding_window_size=2500)

    def test_appeal_allowed(self):
        """Tests definitive detection of appeal allowed in concluding text."""
        synthetic_text = (
            "We have heard learned counsel for the parties at length. "
            "The High Court fell into error in refusing to quash the order. "
            "In the result, the appeal is allowed and the judgment of the High Court is set aside."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-APP-001",
            metadata={"caseTitle": "Ramesh Kumar v. State of Punjab", "court": "Supreme Court of India"}
        )
        self.assertEqual(candidate.candidate_disposition, "appeal_allowed")
        self.assertEqual(candidate.review_status, "pending_review")
        self.assertGreaterEqual(candidate.extraction_confidence, 0.85)
        self.assertIn("appeal is allowed", candidate.original_disposition_phrase.lower())
        self.assertEqual(candidate.party_role, "accused")
        self.assertEqual(candidate.party_success, "favorable_to_accused")

    def test_appeal_dismissed(self):
        """Tests definitive detection of appeal dismissed in concluding text."""
        synthetic_text = (
            "We find no infirmity in the concurrent findings of fact recorded below. "
            "Consequently, the appeal fails and is dismissed with costs."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-APP-002",
            metadata={"caseTitle": "Suresh v. State of Maharashtra", "court": "Supreme Court of India"}
        )
        self.assertEqual(candidate.candidate_disposition, "appeal_dismissed")
        self.assertIn("dismissed", candidate.original_disposition_phrase.lower())
        self.assertEqual(candidate.party_role, "accused")
        self.assertEqual(candidate.party_success, "unfavorable_to_accused")

    def test_state_appeal_dismissed_favorable_to_accused(self):
        """Tests that State's appeal being dismissed is recognized as favorable to the accused."""
        synthetic_text = (
            "The view taken by the trial judge while acquitting the respondent was reasonably possible. "
            "We dismiss the appeal."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-APP-003",
            metadata={"caseTitle": "State of U.P. versus Vikram Singh", "court": "Supreme Court of India"}
        )
        self.assertEqual(candidate.candidate_disposition, "appeal_dismissed")
        self.assertEqual(candidate.party_role, "State/prosecution")
        self.assertEqual(candidate.party_success, "favorable_to_accused")

    def test_bail_granted(self):
        """Tests detection of bail granted in criminal proceedings."""
        synthetic_text = (
            "Considering the period of incarceration undergone by the applicant, "
            "let the applicant be released on bail on furnishing a personal bond of Rs. 50,000/-."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-BAIL-001",
            metadata={"caseTitle": "Aman v. State of NCT of Delhi", "court": "High Court of Delhi"}
        )
        self.assertEqual(candidate.candidate_disposition, "bail_granted")
        self.assertEqual(candidate.party_role, "applicant/accused")
        self.assertEqual(candidate.party_success, "favorable_to_accused")

    def test_bail_rejected(self):
        """Tests detection of bail rejection."""
        synthetic_text = (
            "Looking into the gravity of the allegations and previous criminal history, "
            "this Court does not consider it to be a fit case for enlarging the accused on bail. "
            "This bail application is thus rejected."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-BAIL-002",
            metadata={"caseTitle": "Babbey v. State of U.P.", "court": "High Court of Allahabad"}
        )
        self.assertEqual(candidate.candidate_disposition, "bail_rejected")
        self.assertEqual(candidate.party_role, "applicant/accused")
        self.assertEqual(candidate.party_success, "unfavorable_to_accused")

    def test_proceedings_quashed(self):
        """Tests detection of Section 482 proceedings quashed."""
        synthetic_text = (
            "The dispute between the parties having been amicably settled, "
            "FIR No. 101/2021 and the criminal proceedings emanating therefrom are hereby quashed."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-QUASH-001",
            metadata={"caseTitle": "Mohd Nadeem & Ors v. State", "court": "High Court of Delhi"}
        )
        self.assertEqual(candidate.candidate_disposition, "proceedings_quashed")
        self.assertEqual(candidate.party_role, "accused")
        self.assertEqual(candidate.party_success, "favorable_to_accused")

    def test_conviction_set_aside(self):
        """Tests detection of conviction set aside / acquittal."""
        synthetic_text = (
            "The prosecution has failed to establish the chain of circumstantial evidence beyond doubt. "
            "The judgment of conviction is set aside and the appellant is acquitted of all charges."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-CONV-001",
            metadata={"caseTitle": "Anil Kumar v. State of Rajasthan", "court": "Supreme Court of India"}
        )
        self.assertEqual(candidate.candidate_disposition, "conviction_set_aside")
        self.assertEqual(candidate.party_role, "accused")
        self.assertEqual(candidate.party_success, "favorable_to_accused")

    def test_partly_allowed(self):
        """Tests detection of partly allowed appeal/petition."""
        synthetic_text = (
            "The conviction under Section 302 IPC cannot be sustained, but the offence falls under Section 304 Part I. "
            "The appeal is partly allowed to the aforesaid extent."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-PART-001",
            metadata={"caseTitle": "Dinesh v. State of M.P.", "court": "Supreme Court of India"}
        )
        self.assertEqual(candidate.candidate_disposition, "partly_allowed")
        self.assertIn("partly allowed", candidate.original_disposition_phrase.lower())
        self.assertEqual(candidate.party_success, "unresolved")

    def test_remanded(self):
        """Tests detection of remand orders back to subordinate court."""
        synthetic_text = (
            "Since the High Court decided the issue without considering the statutory bar, "
            "the impugned order is set aside and the matter is remanded back to the High Court for fresh disposal."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-REMAND-001",
            metadata={"caseTitle": "ABC Corp v. Union of India", "court": "Supreme Court of India"}
        )
        self.assertEqual(candidate.candidate_disposition, "remanded")
        self.assertIn("remand", candidate.original_disposition_phrase.lower())

    def test_withdrawn(self):
        """Tests detection of petitions dismissed as withdrawn."""
        synthetic_text = (
            "Learned counsel for the petitioner submits that the grievance has been redressed. "
            "Accordingly, the writ petition is dismissed as withdrawn."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-WITHDRAW-001",
            metadata={"caseTitle": "Kishan Lal v. Commissioner of Police", "court": "High Court of Delhi"}
        )
        self.assertEqual(candidate.candidate_disposition, "withdrawn")
        self.assertIn("withdrawn", candidate.original_disposition_phrase.lower())

    def test_disposed_with_directions(self):
        """Tests detection of final disposal with observations or as infructuous."""
        synthetic_text = (
            "With the aforesaid observations and directions, the writ petition is finally disposed of."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-DISP-001",
            metadata={"caseTitle": "Sufiya v. State of U.P.", "court": "High Court of Allahabad"}
        )
        self.assertEqual(candidate.candidate_disposition, "disposed_with_directions")

    def test_ambiguous_contradictory_language(self):
        """Tests that conflicting operative orders result in ambiguous category."""
        synthetic_text = (
            "Regarding Criminal Appeal No. 10, the appeal is allowed. "
            "However, regarding Criminal Appeal No. 11, the appeal is dismissed."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-AMBIG-001",
            metadata={"caseTitle": "Co-Appellants v. State", "court": "Supreme Court of India"}
        )
        self.assertEqual(candidate.candidate_disposition, "ambiguous")
        self.assertIn("Contradictory orders detected", candidate.ambiguity_reason)
        self.assertEqual(candidate.review_status, "pending_review")

    def test_no_detectable_disposition_unknown(self):
        """Tests that texts lacking concluding operative rulings return unknown."""
        synthetic_text = (
            "The jurisprudence of preventive detention requires careful constitutional balance. "
            "Fundamental rights under Part III must be safeguarded."
        )
        candidate = self.extractor.extract_from_text(
            synthetic_text,
            case_id="TEST-UNK-001",
            metadata={"caseTitle": "Academic Case v. State", "court": "Supreme Court of India"}
        )
        self.assertEqual(candidate.candidate_disposition, "unknown")
        self.assertEqual(candidate.extraction_confidence, 0.0)
        self.assertIn("No definitive concluding", candidate.ambiguity_reason)

    def test_negation_and_quoted_historical_statements(self):
        """Tests that negated phrases or historical recitals are not treated as operative orders."""
        # Case A: Negation ("cannot be allowed")
        negated_text = (
            "The submissions made by the appellant lack substance. "
            "The prayer for relief cannot be allowed. The appeal is dismissed."
        )
        candidate_neg = self.extractor.extract_from_text(
            negated_text,
            case_id="TEST-NEG-001",
            metadata={"caseTitle": "Applicant v. State", "court": "High Court"}
        )
        self.assertEqual(candidate_neg.candidate_disposition, "appeal_dismissed")

        # Case B: Historical recital earlier in concluding paragraph
        historical_text = (
            "The appellant contended that the trial court erroneously dismissed the appeal. "
            "Having reviewed the records, the judgment of conviction is set aside."
        )
        candidate_hist = self.extractor.extract_from_text(
            historical_text,
            case_id="TEST-HIST-001",
            metadata={"caseTitle": "Dev v. State", "court": "Supreme Court"}
        )
        self.assertEqual(candidate_hist.candidate_disposition, "conviction_set_aside")

    def test_multiple_chunks_from_same_judgment(self):
        """Tests sequential reassembly of multi-chunk cases prior to extraction."""
        chunks = [
            {
                "case_id": "CHUNK-CASE-001",
                "chunk_index": 1,
                "total_chunks": 3,
                "text_original": "Having examined the evidence of PW-1 and PW-2, the prosecution case collapses.",
            },
            {
                "case_id": "CHUNK-CASE-001",
                "chunk_index": 2,
                "total_chunks": 3,
                "text_original": "Accordingly, the appeal is allowed and the appellant is directed to be released forthwith.",
            },
            {
                "case_id": "CHUNK-CASE-001",
                "chunk_index": 0,
                "total_chunks": 3,
                "text_original": "This appeal arises out of a judgment of conviction rendered by the Sessions Judge.",
                "caseTitle": "Vikram v. State of Haryana",
                "court": "Supreme Court of India",
                "judgmentDate": "2023-05-10"
            }
        ]
        reconstructed, meta = self.extractor.reconstruct_and_group_records(chunks)
        self.assertEqual(meta["unique_judgments"], 1)
        self.assertEqual(meta["reconstructed_count"], 1)
        self.assertTrue(meta["chunked_input_detected"])

        case = reconstructed[0]
        self.assertTrue(case["judgmentText"].startswith("This appeal arises"))
        self.assertTrue(case["judgmentText"].endswith("released forthwith."))

        candidate = self.extractor.extract_from_text(case["judgmentText"], case_id=case["id"], metadata=case)
        self.assertEqual(candidate.candidate_disposition, "appeal_allowed")

    def test_missing_or_invalid_case_identifiers(self):
        """Tests handling of missing or null case identifiers."""
        records_with_invalid_ids = [
            {"id": "", "judgmentText": "The appeal is allowed."},
            {"case_id": None, "judgmentText": "The appeal is dismissed."},
            {"id": "VALID-001", "judgmentText": "The writ petition is dismissed."}
        ]
        reconstructed, meta = self.extractor.reconstruct_and_group_records(records_with_invalid_ids)
        self.assertEqual(meta["missing_id_count"], 2)
        self.assertEqual(len(reconstructed), 1)
        self.assertEqual(reconstructed[0]["id"], "VALID-001")

    def test_export_preservation_and_csv_generation(self):
        """Tests that JSON and CSV exports generate valid review formats with safety backups."""
        synthetic_records = [
            {
                "id": "SYNTH-001",
                "caseTitle": "A v. State",
                "court": "Supreme Court of India",
                "judgmentDate": "2022-01-01",
                "category": "Criminal Law",
                "judgmentText": "The appeal is allowed."
            },
            {
                "id": "SYNTH-002",
                "caseTitle": "B v. State",
                "court": "High Court of Delhi",
                "judgmentDate": "2022-02-01",
                "category": "Criminal Law",
                "judgmentText": "Writ petition is dismissed."
            }
        ]
        candidates, summary = self.extractor.process_dataset(synthetic_records)
        self.assertEqual(len(candidates), 2)

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = os.path.join(tmpdir, "candidates.json")
            csv_path = os.path.join(tmpdir, "review.csv")

            self.extractor.export_candidates_to_json(candidates, json_path, metadata=summary)
            self.extractor.export_candidates_to_csv(candidates, csv_path)

            self.assertTrue(os.path.exists(json_path))
            self.assertTrue(os.path.exists(csv_path))

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertIn("metadata", data)
            self.assertEqual(len(data["candidates"]), 2)
            self.assertEqual(data["candidates"][0]["review_status"], "pending_review")

            # Verify backup behavior on overwrite
            self.extractor.export_candidates_to_json(candidates, json_path, metadata=summary)
            backup_files = [f for f in os.listdir(tmpdir) if f.startswith("candidates.json.") and f.endswith(".bak")]
            self.assertEqual(len(backup_files), 1)

    def test_human_review_batches_integrity(self):
        """Feature 4.3: Verifies that human review batches partition all 150 cases with pending status."""
        datasets_dir = os.path.join(ML_SERVICE_DIR, "app", "datasets")
        batches_dir = os.path.join(datasets_dir, "review_batches")

        b1_csv = os.path.join(batches_dir, "batch_1_definitive_candidates.csv")
        b2_csv = os.path.join(batches_dir, "batch_2_ambiguous_candidates.csv")
        b3_csv = os.path.join(batches_dir, "batch_3_unknown_candidates.csv")
        guidelines_path = os.path.join(ML_SERVICE_DIR, "app", "prediction", "outcome_annotation_guidelines.md")

        self.assertTrue(os.path.exists(b1_csv), "Batch 1 CSV must exist")
        self.assertTrue(os.path.exists(b2_csv), "Batch 2 CSV must exist")
        self.assertTrue(os.path.exists(b3_csv), "Batch 3 CSV must exist")
        self.assertTrue(os.path.exists(guidelines_path), "Annotation guidelines markdown must exist")

        import csv
        with open(b1_csv, "r", encoding="utf-8") as f:
            b1 = list(csv.DictReader(f))
        with open(b2_csv, "r", encoding="utf-8") as f:
            b2 = list(csv.DictReader(f))
        with open(b3_csv, "r", encoding="utf-8") as f:
            b3 = list(csv.DictReader(f))

        self.assertEqual(len(b1), 99, "Batch 1 must contain exactly 99 definitive candidates")
        self.assertEqual(len(b2), 1, "Batch 2 must contain exactly 1 ambiguous candidate")
        self.assertEqual(len(b3), 50, "Batch 3 must contain exactly 50 unknown candidates")
        self.assertEqual(len(b1) + len(b2) + len(b3), 150, "Batches must sum to 150 unique cases")

        all_cases = b1 + b2 + b3
        for r in all_cases:
            self.assertEqual(r["review_status"], "pending_review", "Initial review status must be pending_review")
            self.assertEqual(r["human_approved_label"], "", "Human approved label must be blank before review")
            self.assertIn("recommended_action", r)
            self.assertTrue(len(r["recommended_action"]) > 0)



if __name__ == "__main__":
    unittest.main()
