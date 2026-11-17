"""
Unit Tests for Open India Law Sampling & Staging Pipeline
Jurist AI — Precedent Retrieval Expansion
"""

import os
import sys
import unittest
import json

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ML_SERVICE_DIR = os.path.dirname(CURRENT_DIR)
if ML_SERVICE_DIR not in sys.path:
    sys.path.insert(0, ML_SERVICE_DIR)

from scripts.sample_open_india_law import (
    reconstruct_judgment_from_chunks,
    is_duplicate_of_landmark,
    infer_legal_category,
    validate_staged_dataset,
    filter_chunk_by_keywords,
    normalize_title_for_comparison
)


class TestOpenIndiaLawSampling(unittest.TestCase):

    def setUp(self):
        self.mock_landmark_corpus = [
            {
                "id": "SC-2023-001",
                "caseTitle": "Pankaj Bansal v. Union of India and Ors.",
                "court": "Supreme Court of India"
            },
            {
                "id": "SC-2014-004",
                "caseTitle": "Arnesh Kumar v. State of Bihar and Anr.",
                "court": "Supreme Court of India"
            }
        ]

    def test_chunk_reconstruction_complete(self):
        chunks = [
            {
                "case_id": "TEST_001",
                "chunk_index": 0,
                "total_chunks": 2,
                "text_original": "The petitioner filed a petition under Section 482 of CrPC seeking quashing of the FIR.",
                "title": "ABC v. State of Delhi",
                "court_key": "delhi_hc",
                "case_number": "Crl. M.C. 101/2023",
                "citation": "2023 DHC 100",
                "year": 2023,
                "is_judgment": True,
                "pdf_url": "https://delhihighcourt.nic.in/pdf/test.pdf"
            },
            {
                "case_id": "TEST_001",
                "chunk_index": 1,
                "total_chunks": 2,
                "text_original": "Having regard to the settlement between the parties under Section 498A IPC, the proceedings are quashed.",
                "section_type": "judgement"
            }
        ]
        record = reconstruct_judgment_from_chunks(chunks, min_text_length=50)
        self.assertIsNotNone(record)
        self.assertEqual(record["id"], "OIL-DHC-TEST_001")
        self.assertEqual(record["court"], "High Court of Delhi")
        self.assertIn("Section 482", record["judgmentText"])
        self.assertIn("Section 498A", record["judgmentText"])
        self.assertIsNone(record["outcome"])  # Must not fabricate outcome
        self.assertFalse(record["officialSourceVerified"])

    def test_chunk_reconstruction_incomplete_dropped(self):
        chunks = [
            {
                "case_id": "TEST_002",
                "chunk_index": 0,
                "total_chunks": 3,  # Missing chunks 1 and 2
                "text_original": "Initial facts of the case...",
                "title": "Incomplete Case v. State"
            }
        ]
        record = reconstruct_judgment_from_chunks(chunks)
        self.assertIsNone(record, "Incomplete multi-chunk case must be dropped")

    def test_chunk_reconstruction_unordered_sorted(self):
        # Chunks provided out of order (index 1 before index 0)
        chunks = [
            {
                "case_id": "TEST_003",
                "chunk_index": 1,
                "total_chunks": 2,
                "text_original": "Consequent part of judgment detailing the final order and directions.",
                "section_type": "order"
            },
            {
                "case_id": "TEST_003",
                "chunk_index": 0,
                "total_chunks": 2,
                "text_original": "Initial part: This is a criminal appeal regarding Section 439 CrPC bail.",
                "title": "Accused v. State of UP",
                "court_key": "allahabad_hc",
                "case_number": "Crl. Bail 404/2022",
                "year": 2022
            }
        ]
        record = reconstruct_judgment_from_chunks(chunks, min_text_length=50)
        self.assertIsNotNone(record)
        # Verify index 0 appears before index 1 in concatenated judgmentText
        pos0 = record["judgmentText"].find("Initial part")
        pos1 = record["judgmentText"].find("Consequent part")
        self.assertTrue(pos0 < pos1, "Chunks must be concatenated in ascending chunk_index order")

    def test_deduplication_detects_existing_landmark(self):
        # Should flag duplicate of Pankaj Bansal
        is_dup = is_duplicate_of_landmark("Pankaj Bansal v. Union of India", self.mock_landmark_corpus)
        self.assertTrue(is_dup)

        # Should flag duplicate of Arnesh Kumar
        is_dup2 = is_duplicate_of_landmark("Arnesh Kumar v. State of Bihar", self.mock_landmark_corpus)
        self.assertTrue(is_dup2)

        # Should NOT flag an unrepresented case
        is_dup3 = is_duplicate_of_landmark("State of Maharashtra v. Sanjay Nirupam", self.mock_landmark_corpus)
        self.assertFalse(is_dup3)

    def test_keyword_filtering(self):
        self.assertTrue(filter_chunk_by_keywords("The accused sought anticipatory bail under section 438."))
        self.assertTrue(filter_chunk_by_keywords("Police failed to serve written grounds of arrest."))
        self.assertTrue(filter_chunk_by_keywords("Cheque dishonour complaint filed under Section 138."))
        self.assertFalse(filter_chunk_by_keywords("Routine lease dispute regarding commercial property rent."))

    def test_category_inference(self):
        cat1 = infer_legal_category("Accused charged with murder under Section 302 IPC", ["Section 302, Indian Penal Code"])
        self.assertEqual(cat1, "Criminal Law")

        cat2 = infer_legal_category("Notice issued regarding bounced cheque under Section 138", ["Section 138, Negotiable Instruments Act"])
        self.assertEqual(cat2, "Banking & Cheque Dishonour")

        cat3 = infer_legal_category("Violation of fundamental right under Article 21", ["Article 21 of Constitution of India"])
        self.assertEqual(cat3, "Constitutional Law")

    def test_validate_staged_dataset_catches_issues(self):
        # Valid records
        valid_records = [
            {
                "id": "OIL-SC-001",
                "caseTitle": "Test Case v. State",
                "court": "Supreme Court of India",
                "judgmentDate": "2023-01-01",
                "caseIdentifier": "Crl. A. 1/2023",
                "citation": "2023 INSC 1",
                "category": "Criminal Law",
                "legalProvisions": ["Section 439, CrPC"],
                "summary": "Bail granted.",
                "judgmentText": "Detailed judgment text explaining reasoning...",
                "article141Status": "Binding nationwide.",
                "outcome": None
            }
        ]
        report = validate_staged_dataset(valid_records, self.mock_landmark_corpus)
        self.assertTrue(report["isValidationPassed"])
        self.assertEqual(report["fabricatedOutcomesDetected"], 0)

        # Fabricated outcome record
        invalid_outcome_record = dict(valid_records[0])
        invalid_outcome_record["id"] = "OIL-SC-002"
        invalid_outcome_record["outcome"] = "Allowed"  # Fabricated!
        bad_report = validate_staged_dataset([invalid_outcome_record], self.mock_landmark_corpus)
        self.assertFalse(bad_report["isValidationPassed"])
        self.assertEqual(bad_report["fabricatedOutcomesDetected"], 1)


if __name__ == "__main__":
    unittest.main()
