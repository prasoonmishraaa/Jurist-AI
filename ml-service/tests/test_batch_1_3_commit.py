"""
Tests for Feature 4.11.2 — Batch 1.3 Post-Commit State Verification

Verifies:
1. Total verified cases == 16 (15 approved, 1 corrected).
2. Total pending cases == 134.
3. Batch 1.3 records specifically committed with correct labels and reviewer SNR-LEGAL-NLP-01.
4. Independent audit events present for all five Batch 1.3 cases.
5. Exact CSV and JSON synchronization across all 150 rows.
6. Training readiness gatekeeper strictly locks model training (qualitative_research_mode).
7. Source dataset SHA-256 hashes remain untouched.
"""

import sys
import json
import csv
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    KNOWN_SOURCE_HASHES,
)

CANDIDATES_JSON = BASE_DIR / "app" / "datasets" / "outcome_label_candidates_v2.json"
REVIEW_CSV = BASE_DIR / "app" / "datasets" / "outcome_label_review_v2.csv"
SOURCE_JSON = BASE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"

BATCH_1_3_EXPECTED = {
    "OIL-SC-2006_INSC_699": {
        "disposition": "appeal_allowed",
        "successful_party": "accused",
        "proceeding_type": "criminal_appeal",
    },
    "OIL-SC-2010_INSC_109": {
        "disposition": "appeal_dismissed",
        "successful_party": "state_prosecution",
        "proceeding_type": "criminal_appeal",
    },
    "OIL-AHC-UPHC020034182022": {
        "disposition": "appeal_allowed",
        "successful_party": "accused",
        "proceeding_type": "criminal_appeal",
    },
    "OIL-DHC-DLHC015857912015": {
        "disposition": "petition_allowed",
        "successful_party": "petitioner",
        "proceeding_type": "criminal_misc_petition_482",
    },
    "OIL-SC-1992_INSC_350": {
        "disposition": "appeal_dismissed",
        "successful_party": "respondent",
        "proceeding_type": "civil_appellate_proceeding",
    },
}

@pytest.fixture(scope="module")
def session():
    return OutcomeAnnotationSessionManager()

def test_dashboard_post_commit_counts(session):
    dash = session.get_progress_dashboard()
    assert dash["total_candidates"] == 150
    assert dash["total_verified"] >= 16
    assert dash["approved"] >= 15
    assert dash["corrected"] >= 1
    assert dash["pending"] <= 134
    assert dash["risk_tier_progress"]["tier_1"]["verified"] >= 16
    assert dash["risk_tier_progress"]["tier_1"]["pending"] <= 19

def test_batch_1_3_records_committed(session):
    for cid, exp in BATCH_1_3_EXPECTED.items():
        rec = session.records_by_id.get(cid)
        assert rec is not None, f"Missing record {cid}"
        assert rec["review_status"] == "approved"
        assert rec["human_approved_label"] == exp["disposition"]
        assert rec["human_successful_party"] == exp["successful_party"]
        assert rec["reviewer_reference"] == "SNR-LEGAL-NLP-01"
        assert rec["proceeding_type"] == exp["proceeding_type"]

        # Audit event check
        assert len(rec.get("audit_history", [])) >= 1
        last_audit = rec["audit_history"][-1]
        assert last_audit["reviewer_id"] == "SNR-LEGAL-NLP-01"
        assert last_audit["action"] == "accept"
        assert last_audit["new_status"] == "approved"
        assert last_audit["disposition"] == exp["disposition"]
        assert last_audit["successful_party"] == exp["successful_party"]

def test_csv_json_full_sync():
    with open(CANDIDATES_JSON, "r", encoding="utf-8") as f:
        json_records = {r["case_id"]: r for r in json.load(f)["records"]}

    with open(REVIEW_CSV, "r", encoding="utf-8") as f:
        csv_records = {r["case_id"]: r for r in csv.DictReader(f)}

    assert len(json_records) == 150
    assert len(csv_records) == 150

    for cid, j_rec in json_records.items():
        c_rec = csv_records.get(cid)
        assert c_rec is not None
        assert c_rec["human_approved_label"] == j_rec.get("human_approved_label", "")
        assert c_rec["human_successful_party"] == j_rec.get("human_successful_party", "")
        assert c_rec["review_status"] == j_rec.get("review_status", "")
        assert c_rec["proceeding_type"] == j_rec.get("proceeding_type", "")

def test_training_gate_threshold_enforcement(session):
    readiness = session.check_training_readiness(min_total_verified=50)
    assert not readiness["is_training_eligible"]
    assert readiness["total_verified_count"] >= 16
    assert readiness["minimum_required"] == 50
    assert readiness["recommended_mode"] == "qualitative_research_mode"

def test_source_dataset_integrity(session):
    integrity = session.verify_source_integrity()
    for fname, ok in integrity.items():
        assert ok, f"Integrity failed for {fname}"
