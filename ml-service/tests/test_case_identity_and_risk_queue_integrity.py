"""
Regression Test Suite for Feature 4.7.1: Case Identity and Risk Queue Integrity Audit
JURIST AI — Case Identity and Risk Queue Integrity Audit

Verifies:
1. Strict 1-to-1 identity mapping between source dataset, candidates JSON, review CSV, and batch files.
2. Case title, court, and judgment date consistency across all 150 records.
3. Specific resolution and verification of OIL-SC-1996_INSC_503 (RAM NATH MAHTO versus STATE OF BIHAR).
4. Text association and concluding operative-order integrity.
5. Exact risk-tier partition counts: Tier 1 (35), Tier 2 (21), Tier 3 (43), Tier 4 (51) totaling 150.
6. Zero duplicate case IDs across risk tiers (disjoint partition).
7. Preservation of Case 1 (OIL-SC-2021_INSC_327) approved state and audit trail.
8. Unaltered cryptographic SHA-256 integrity of source datasets.
"""

import sys
import json
import csv
import unittest
from pathlib import Path
from collections import Counter

# Add ml-service to path
ML_SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    KNOWN_SOURCE_HASHES,
)
from app.prediction.risk_prioritized_queue import RiskPrioritizer, RiskTier


class TestCaseIdentityAndRiskQueueIntegrity(unittest.TestCase):
    """Rigorous audit test cases for all 150 case records and risk queues."""

    def setUp(self):
        self.datasets_dir = ML_SERVICE_DIR / "app" / "datasets"
        self.session = OutcomeAnnotationSessionManager()

        # Load raw files directly
        with open(self.datasets_dir / "open_india_law_sample_150.json", "r", encoding="utf-8") as f:
            self.source_cases = json.load(f)
        self.source_by_id = {c["id"]: c for c in self.source_cases}

        with open(self.datasets_dir / "outcome_label_candidates_v2.json", "r", encoding="utf-8") as f:
            self.cands_json = json.load(f).get("records", [])
        self.cands_by_id = {c["case_id"]: c for c in self.cands_json}

        with open(self.datasets_dir / "outcome_label_review_v2.csv", "r", encoding="utf-8") as f:
            self.csv_rows = list(csv.DictReader(f))
        self.csv_by_id = {c["case_id"]: c for c in self.csv_rows}

    def test_case_id_source_record_identity_consistency(self):
        """All 150 case IDs must exist identically without missing or extra records."""
        self.assertEqual(len(self.source_cases), 150)
        self.assertEqual(len(self.cands_json), 150)
        self.assertEqual(len(self.csv_rows), 150)

        source_ids = set(self.source_by_id.keys())
        cand_ids = set(self.cands_by_id.keys())
        csv_ids = set(self.csv_by_id.keys())

        self.assertEqual(len(source_ids), 150)
        self.assertEqual(source_ids, cand_ids)
        self.assertEqual(source_ids, csv_ids)

        # Check for zero duplicate IDs
        source_id_counts = Counter(c["id"] for c in self.source_cases)
        cand_id_counts = Counter(c["case_id"] for c in self.cands_json)
        csv_id_counts = Counter(c["case_id"] for c in self.csv_rows)

        self.assertTrue(all(cnt == 1 for cnt in source_id_counts.values()))
        self.assertTrue(all(cnt == 1 for cnt in cand_id_counts.values()))
        self.assertTrue(all(cnt == 1 for cnt in csv_id_counts.values()))

    def test_case_title_and_date_consistency_across_all_150_records(self):
        """Case title, court, and judgment date must match exactly across all datasets."""
        for cid, source_case in self.source_by_id.items():
            cand_case = self.cands_by_id[cid]
            csv_case = self.csv_by_id[cid]

            s_title = source_case["caseTitle"].strip()
            c_title = cand_case["case_title"].strip()
            r_title = csv_case["case_title"].strip()
            self.assertEqual(s_title, c_title, f"Title mismatch in candidates JSON for {cid}")
            self.assertEqual(s_title, r_title, f"Title mismatch in review CSV for {cid}")

            s_date = source_case["judgmentDate"].strip()
            c_date = cand_case["decision_date"].strip()
            r_date = csv_case["decision_date"].strip()
            self.assertEqual(s_date, c_date, f"Date mismatch in candidates JSON for {cid}")
            self.assertEqual(s_date, r_date, f"Date mismatch in review CSV for {cid}")

            s_court = source_case["court"].strip()
            c_court = cand_case["court"].strip()
            r_court = csv_case["court"].strip()
            self.assertEqual(s_court, c_court, f"Court mismatch in candidates JSON for {cid}")
            self.assertEqual(s_court, r_court, f"Court mismatch in review CSV for {cid}")

    def test_specific_identity_of_case_1996_insc_503(self):
        """Case OIL-SC-1996_INSC_503 must consistently resolve to RAM NATH MAHTO versus STATE OF BIHAR."""
        cid = "OIL-SC-1996_INSC_503"
        source = self.source_by_id[cid]
        cand = self.cands_by_id[cid]
        csv_row = self.csv_by_id[cid]
        case_view = self.session.get_case_view(cid)

        expected_title = "RAM NATH MAHTO versus STATE OF BIHAR"
        expected_date = "1996-04-10"
        expected_court = "Supreme Court of India"
        expected_role = "accused"

        self.assertEqual(source["caseTitle"], expected_title)
        self.assertEqual(cand["case_title"], expected_title)
        self.assertEqual(csv_row["case_title"], expected_title)
        self.assertEqual(case_view["case_title"], expected_title)

        self.assertEqual(source["judgmentDate"], expected_date)
        self.assertEqual(cand["decision_date"], expected_date)
        self.assertEqual(csv_row["decision_date"], expected_date)
        self.assertEqual(case_view["decision_date"], expected_date)

        self.assertEqual(source["court"], expected_court)
        self.assertEqual(case_view["court"], expected_court)
        self.assertEqual(case_view["procedural_role"], expected_role)

        # Check operative holding in tail
        tail = case_view["operative_order_excerpt"]
        self.assertIn("maintaining the conviction of the appellant", tail)
        self.assertIn("The appeal therefore fails and is hereby dismissed", tail)
        self.assertIn("Appeal dismissed", tail)

    def test_review_batches_inventory_consistency(self):
        """All records in review_batches/ must match source records."""
        batch_dir = self.datasets_dir / "review_batches"
        total_batch_recs = 0

        for bfile in ["batch_1_definitive_candidates.json", "batch_2_ambiguous_candidates.json", "batch_3_unknown_candidates.json"]:
            bpath = batch_dir / bfile
            self.assertTrue(bpath.exists(), f"Missing batch file: {bfile}")
            with open(bpath, "r", encoding="utf-8") as f:
                bdata = json.load(f)
            recs = bdata.get("records", bdata.get("candidates", []))
            total_batch_recs += len(recs)

            for r in recs:
                cid = r["case_id"]
                self.assertIn(cid, self.source_by_id)
                self.assertEqual(r["case_title"], self.source_by_id[cid]["caseTitle"])
                self.assertEqual(r["decision_date"], self.source_by_id[cid]["judgmentDate"])
                self.assertEqual(r["court"], self.source_by_id[cid]["court"])

        self.assertEqual(total_batch_recs, 150)

    def test_risk_tier_exact_partition_counts_and_disjointness(self):
        """Risk tiers must partition all 150 cases disjointly into 35, 21, 43, 51."""
        stratified = self.session.risk_prioritizer.stratify_queue(
            self.session.records, self.session.source_cases, only_pending=False
        )

        tier_1 = stratified[RiskTier.TIER_1_DEFINITIVE_MERITS]
        tier_2 = stratified[RiskTier.TIER_2_MODERATE_RISK_BAIL_DIRECTIVES]
        tier_3 = stratified[RiskTier.TIER_3_HIGH_RISK_PROCEDURAL]
        tier_4 = stratified[RiskTier.TIER_4_CRITICAL_DEFERRED]

        self.assertEqual(len(tier_1), 35)
        self.assertEqual(len(tier_2), 21)
        self.assertEqual(len(tier_3), 43)
        self.assertEqual(len(tier_4), 51)
        self.assertEqual(len(tier_1) + len(tier_2) + len(tier_3) + len(tier_4), 150)

        # Check pairwise disjointness
        s1 = set(r["case_id"] for r in tier_1)
        s2 = set(r["case_id"] for r in tier_2)
        s3 = set(r["case_id"] for r in tier_3)
        s4 = set(r["case_id"] for r in tier_4)

        self.assertEqual(len(s1 & s2), 0)
        self.assertEqual(len(s1 & s3), 0)
        self.assertEqual(len(s1 & s4), 0)
        self.assertEqual(len(s2 & s3), 0)
        self.assertEqual(len(s2 & s4), 0)
        self.assertEqual(len(s3 & s4), 0)

        self.assertEqual(s1 | s2 | s3 | s4, set(self.source_by_id.keys()))

    def test_get_batch_view_data_fidelity(self):
        """get_batch_view must return cases with 100% fidelity to source text and metadata."""
        for tier_num, tier_key in [("1", "tier_1"), ("2", "tier_2"), ("3", "tier_3"), ("4", "tier_4")]:
            batch = self.session.get_batch_view(batch_size=5, tier=tier_num)
            self.assertGreater(len(batch), 0)
            for case in batch:
                cid = case["case_id"]
                source = self.source_by_id[cid]

                self.assertEqual(case["case_title"], source["caseTitle"])
                self.assertEqual(case["decision_date"], source["judgmentDate"])
                self.assertEqual(case["court"], source["court"])
                self.assertEqual(case["full_judgment_text"], source["judgmentText"])
                self.assertTrue(case["operative_order_excerpt"].endswith(source["judgmentText"][-len(case["operative_order_excerpt"]):]))
                self.assertEqual(case["risk_tier"], tier_key)

    def test_preservation_of_case_1_approved_state(self):
        """Case 1 (OIL-SC-2021_INSC_327) must remain approved with intact audit history."""
        case_view = self.session.get_case_view("OIL-SC-2021_INSC_327")
        self.assertEqual(case_view["case_title"], "THE STATE OF UTTAR PRADESH & ORS. versus DR. MANOJ KUMAR SHARMA")
        self.assertEqual(case_view["decision_date"], "2021-07-09")
        self.assertEqual(case_view["court"], "Supreme Court of India")

        rev = case_view["current_review"]
        self.assertEqual(rev["review_status"], "approved")
        self.assertEqual(rev["human_approved_label"], "appeal_allowed")
        self.assertEqual(rev["human_successful_party"], "state_prosecution")
        self.assertEqual(rev["reviewer_reference"], "SNR-LEGAL-NLP-01")
        self.assertIn("wholly unjustified, unwarranted, arbitrary and illegal", rev["evidence_reference"])

        self.assertGreaterEqual(len(rev["audit_history"]), 1)
        audit_event = rev["audit_history"][0]
        self.assertEqual(audit_event["action"], "accept")
        self.assertEqual(audit_event["reviewer_id"], "SNR-LEGAL-NLP-01")
        self.assertEqual(audit_event["new_status"], "approved")

        # Confirm Case 1, Batch 1.1 (5 cases), and Batch 1.2 (5 cases) are verified; remaining 139 records are strictly pending_review
        expected_verified_ids = {
            "OIL-SC-2021_INSC_327",
            "OIL-SC-1996_INSC_503",
            "OIL-SC-2007_INSC_31",
            "OIL-SC-2007_INSC_1082",
            "OIL-SC-2003_INSC_88",
            "OIL-SC-1973_INSC_203",
            "OIL-SC-2000_INSC_110",
            "OIL-SC-2016_INSC_467",
            "OIL-SC-1973_INSC_247",
            "OIL-SC-1979_INSC_85",
            "OIL-SC-1998_INSC_267",
        }
        actual_verified = [
            r["case_id"] for r in self.session.records
            if r.get("review_status") in ["approved", "corrected", "adjudicated_approved"]
        ]
        self.assertEqual(set(actual_verified), expected_verified_ids)

        other_non_pending = [
            r["case_id"] for r in self.session.records
            if r["case_id"] not in expected_verified_ids and r.get("review_status") != "pending_review"
        ]
        self.assertEqual(len(other_non_pending), 0, f"Unexpected non-pending cases found: {other_non_pending}")

    def test_specific_identity_of_case_1_and_source_text_evidence_match(self):
        """Case 1 (OIL-SC-2021_INSC_327) title, date, court, and paragraph 21 evidence must match."""
        cid = "OIL-SC-2021_INSC_327"
        source = self.source_by_id[cid]
        cand = self.cands_by_id[cid]
        csv_row = self.csv_by_id[cid]
        case_view = self.session.get_case_view(cid)

        expected_title = "THE STATE OF UTTAR PRADESH & ORS. versus DR. MANOJ KUMAR SHARMA"
        expected_date = "2021-07-09"
        expected_court = "Supreme Court of India"

        self.assertEqual(source["caseTitle"], expected_title)
        self.assertEqual(cand["case_title"], expected_title)
        self.assertEqual(csv_row["case_title"], expected_title)
        self.assertEqual(case_view["case_title"], expected_title)

        self.assertEqual(source["judgmentDate"], expected_date)
        self.assertEqual(cand["decision_date"], expected_date)
        self.assertEqual(csv_row["decision_date"], expected_date)
        self.assertEqual(case_view["decision_date"], expected_date)

        self.assertEqual(source["court"], expected_court)
        self.assertEqual(case_view["court"], expected_court)

        # Verify paragraph 21 operative order in judgment text
        jtext = source["judgmentText"]
        self.assertIn("21. The writ petitioner was posted at Badaun.", jtext)
        self.assertIn("wholly unjustified, unwarranted, arbitrary and illegal", jtext)
        self.assertIn("The same are set aside and the appeal is allowed", jtext)

    def test_source_dataset_cryptographic_hashes_unaltered(self):
        """Original source datasets must have exact unaltered SHA-256 hashes."""
        integrity = self.session.verify_source_integrity()
        self.assertTrue(integrity["open_india_law_sample_150.json"])
        self.assertTrue(integrity["indian_judgments.json"])


if __name__ == "__main__":
    unittest.main()
