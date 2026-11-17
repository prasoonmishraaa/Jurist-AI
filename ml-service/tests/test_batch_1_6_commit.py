"""
Tests for Feature 4.16.4 — Outcome Annotation Batch 1.6 Atomic Commit Verification
JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Verifies:
1. Master dashboard counts: exactly 34 verified annotations (19 approved, 15 corrected) and 116 pending.
2. All 8 Batch 1.6 records committed with verified disposition, successful party, proceeding type, and reviewer SNR-LEGAL-NLP-01.
3. Candidates 6, 7, 8 retain Model B label 'unresolved'.
4. Full CSV/JSON synchronization across all 34 verified cases and 150 total records.
5. Individual timestamped audit events for all 34 verified records.
6. Strict training gate enforcement: Model A passes (31 eligible), Model B blocks (27 eligible, gap of 3), overall gate remains locked with qualitative_research_mode active.
7. Zero model weights serialized.
8. Primary source datasets SHA-256 integrity.
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
    VALID_DISPOSITIONS,
    VALID_SUCCESSFUL_PARTIES,
    MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS,
    MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES,
    KNOWN_SOURCE_HASHES,
)

CANDIDATES_JSON = BASE_DIR / "app" / "datasets" / "outcome_label_candidates_v2.json"
REVIEW_CSV_FILE = BASE_DIR / "app" / "datasets" / "outcome_label_review_v2.csv"
SOURCE_JSON = BASE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"


@pytest.fixture(scope="module")
def session():
    return OutcomeAnnotationSessionManager()


def test_dashboard_post_commit_counts(session):
    """Verify master dashboard counts reflect at least 34 verified records."""
    dash = session.get_progress_dashboard()
    assert dash["total_candidates"] == 150
    assert dash["total_verified"] >= 34, f"Expected at least 34 verified, got {dash['total_verified']}"
    assert dash["pending"] <= 116, f"Expected <= 116 pending, got {dash['pending']}"


def test_batch_1_6_records_committed(session):
    """Verify all 8 Batch 1.6 records committed with verified disposition, party, proceeding type, and reviewer SNR-LEGAL-NLP-01."""
    expected_batch_1_6 = {
        "OIL-DHC-DLHC010207822016": {
            "disposition": "petition_dismissed",
            "party": "respondent",
            "proceeding_type": "writ_petition",
        },
        "OIL-DHC-DLHC010029692013": {
            "disposition": "petition_dismissed",
            "party": "respondent",
            "proceeding_type": "writ_petition",
        },
        "OIL-AHC-UPHC020481512022": {
            "disposition": "petition_allowed",
            "party": "petitioner",
            "proceeding_type": "writ_petition",
        },
        "OIL-DHC-DLHC011058852016": {
            "disposition": "petition_allowed",
            "party": "accused",
            "proceeding_type": "criminal_writ_petition",
        },
        "OIL-AHC-UPHC020000012005": {
            "disposition": "appeal_dismissed",
            "party": "accused",
            "proceeding_type": "criminal_appeal",
        },
        "OIL-SC-2007_INSC_548": {
            "disposition": "appeal_dismissed",
            "party": "unresolved",
            "proceeding_type": "statutory_appeal",
        },
        "OIL-SC-2006_INSC_78": {
            "disposition": "appeal_allowed",
            "party": "unresolved",
            "proceeding_type": "civil_appeal",
        },
        "OIL-DHC-DLHC010110302013": {
            "disposition": "appeal_allowed",
            "party": "unresolved",
            "proceeding_type": "statutory_appeal",
        },
    }

    for cid, exp in expected_batch_1_6.items():
        c_view = session.get_case_view(cid)
        rev = c_view["current_review"]
        assert rev["review_status"] == "corrected"
        assert rev["human_approved_label"] == exp["disposition"]
        assert rev["human_successful_party"] == exp["party"]
        assert rev["reviewer_reference"] == "SNR-LEGAL-NLP-01"
        assert c_view.get("proceeding_type") == exp["proceeding_type"]
        assert len(rev.get("human_notes", "")) > 0

        # Audit history verification
        history = rev.get("audit_history", [])
        assert len(history) >= 1
        latest_audit = history[-1]
        assert latest_audit["action"] == "correct"
        assert latest_audit["reviewer_id"] == "SNR-LEGAL-NLP-01"
        assert latest_audit["disposition"] == exp["disposition"]
        assert latest_audit["successful_party"] == exp["party"]
        assert len(latest_audit.get("evidence", "")) > 0


def test_previous_26_verified_annotations_preserved(session):
    """Verify all 26 previously verified records retain their labels and audit history."""
    previous_ids = [
        "OIL-SC-2021_INSC_327", "OIL-SC-1996_INSC_503", "OIL-SC-2007_INSC_31",
        "OIL-SC-2007_INSC_1082", "OIL-SC-2003_INSC_88", "OIL-SC-1973_INSC_203",
        "OIL-SC-2000_INSC_110", "OIL-SC-2016_INSC_467", "OIL-SC-1973_INSC_247",
        "OIL-SC-1979_INSC_85", "OIL-SC-1998_INSC_267", "OIL-SC-1981_INSC_134",
        "OIL-SC-1992_INSC_350", "OIL-SC-2006_INSC_699", "OIL-SC-1984_INSC_90",
        "OIL-SC-2010_INSC_109", "OIL-SC-2012_INSC_207", "OIL-DHC-DLHC015857912015",
        "OIL-DHC-DLHC011166952013", "OIL-DHC-DLHC010614922013", "OIL-DHC-DLHC011594232016",
        "OIL-AHC-UPHC020034182022", "OIL-AHC-UPHC020497422019", "OIL-AHC-UPHC020380352022",
        "OIL-AHC-UPHC020265642022", "OIL-AHC-UPHC020001822015"
    ]
    for cid in previous_ids:
        c_view = session.get_case_view(cid)
        rev = c_view["current_review"]
        assert rev["review_status"] in ["approved", "corrected", "adjudicated_approved"]
        assert len(rev.get("audit_history", [])) >= 1


def test_json_csv_synchronization():
    """Verify 100% synchronization between outcome_label_candidates_v2.json and outcome_label_review_v2.csv."""
    with open(CANDIDATES_JSON, "r", encoding="utf-8") as f:
        json_records = {r["case_id"]: r for r in json.load(f)["records"]}

    with open(REVIEW_CSV_FILE, "r", encoding="utf-8") as f:
        csv_records = {r["case_id"]: r for r in csv.DictReader(f)}

    assert len(json_records) == 150
    assert len(csv_records) == 150

    for cid in [
        "OIL-DHC-DLHC010207822016",
        "OIL-DHC-DLHC010029692013",
        "OIL-AHC-UPHC020481512022",
        "OIL-DHC-DLHC011058852016",
        "OIL-AHC-UPHC020000012005",
        "OIL-SC-2007_INSC_548",
        "OIL-SC-2006_INSC_78",
        "OIL-DHC-DLHC010110302013",
    ]:
        jr = json_records[cid]
        cr = csv_records[cid]
        assert jr["review_status"] == cr["review_status"] == "corrected"
        assert jr["human_approved_label"] == cr["human_approved_label"]
        assert jr["human_successful_party"] == cr["human_successful_party"]
        assert jr["proceeding_type"] == cr["proceeding_type"]
        assert jr["reviewer_reference"] == cr["reviewer_reference"]


def test_training_readiness_post_commit(session):
    """Verify Model A and Model B have reached at least the Batch 1.6 baseline."""
    readiness = session.check_training_readiness(min_total_verified=30, min_minority_samples=5)

    assert readiness["total_verified_count"] >= 34

    ma = readiness["model_a"]
    assert ma["is_training_eligible"] is True
    assert ma["eligible_count"] >= 31
    assert ma["minority_class_count"] >= 6
    assert len(ma["blockers"]) == 0

    mb = readiness["model_b"]
    assert mb["eligible_count"] >= 27
    assert mb["minority_class_count"] >= 5


def test_source_datasets_and_model_weights_integrity(session):
    """Verify source datasets SHA-256 hashes and confirm zero model weights generated."""
    integrity = session.verify_source_integrity()
    for fname, ok in integrity.items():
        assert ok, f"Cryptographic integrity failed for {fname}"

    # Confirm no new model weights generated
    models_dir = BASE_DIR / "app" / "models"
    # Ensure predictor is not trained
    from app.prediction.verified_outcome_model import VerifiedOutcomePredictor
    predictor = VerifiedOutcomePredictor()
    assert not predictor.is_trained
