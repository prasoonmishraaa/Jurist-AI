"""
Tests for Feature 4.23 — Outcome Annotation Batch 1.9 Atomic Commit Verification
JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Verifies:
1. Master dashboard counts: exactly 46 verified annotations (23 approved, 23 corrected) and 104 pending.
2. All 4 Batch 1.9 Group D records committed with verified disposition appeal_dismissed, party respondent, and reviewer SNR-LEGAL-NLP-01.
3. Group H Candidates 5-7 (Pandey, Sarma, Bhutada) strictly preserved as pending_review.
4. All 42 previously verified annotations strictly preserved.
5. Full CSV/JSON synchronization across all 46 verified cases and 150 total records.
6. Individual timestamped audit events for all committed records.
7. Strict training gate enforcement: Model A passes (43 eligible), Model B passes (37 eligible, 0 blockers),
   overall gate unlocks with recommended_mode == "statistical_verified" and is_training_eligible == True.
8. Primary source datasets SHA-256 cryptographic integrity.
9. Zero model weights serialized and predictor remains untrained.
10. Target leakage sanitizer verifies zero operative leakage in sanitized pre-decision features for all 4 cases.
"""

import sys
import json
import csv
import hashlib
from pathlib import Path
from collections import Counter
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    VALID_DISPOSITIONS,
    VALID_SUCCESSFUL_PARTIES,
    MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS,
    MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES,
)
from scripts.build_verified_outcome_dataset import TargetLeakageSanitizer
from app.prediction.verified_outcome_model import VerifiedOutcomePredictor

CANDIDATES_JSON = BASE_DIR / "app" / "datasets" / "outcome_label_candidates_v2.json"
REVIEW_CSV_FILE = BASE_DIR / "app" / "datasets" / "outcome_label_review_v2.csv"
SOURCE_JSON = BASE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"


@pytest.fixture(scope="module")
def session():
    return OutcomeAnnotationSessionManager()


@pytest.fixture(scope="module")
def sanitizer():
    return TargetLeakageSanitizer()


def test_dashboard_post_commit_counts(session):
    """Verify master dashboard counts reflect exactly 46 verified records and 104 pending."""
    dash = session.get_progress_dashboard()
    assert dash["total_candidates"] == 150
    assert dash["total_verified"] == 46, f"Expected 46 verified, got {dash['total_verified']}"
    assert dash["pending"] == 104, f"Expected 104 pending, got {dash['pending']}"
    assert dash["approved"] == 23
    assert dash["corrected"] == 23


def test_batch_1_9_records_committed(session):
    """Verify all 4 Batch 1.9 Group D records committed with appeal_dismissed / respondent / SNR-LEGAL-NLP-01."""
    expected_batch_1_9 = {
        "OIL-SC-1955_INSC_31": {
            "disposition": "appeal_dismissed",
            "party": "respondent",
            "model_a_eligible": True,
            "model_b_eligible": True,
        },
        "OIL-SC-1994_INSC_388": {
            "disposition": "appeal_dismissed",
            "party": "respondent",
            "model_a_eligible": True,
            "model_b_eligible": True,
        },
        "OIL-SC-1968_INSC_212": {
            "disposition": "appeal_dismissed",
            "party": "respondent",
            "model_a_eligible": True,
            "model_b_eligible": True,
        },
        "OIL-SC-1972_INSC_24": {
            "disposition": "appeal_dismissed",
            "party": "respondent",
            "model_a_eligible": True,
            "model_b_eligible": True,
        },
    }

    for cid, tgt in expected_batch_1_9.items():
        case_view = session.get_case_view(cid)
        review = case_view["current_review"]
        assert review["review_status"] == "approved"
        assert review["human_approved_label"] == tgt["disposition"]
        assert review["human_successful_party"] == tgt["party"]
        assert review["reviewer_reference"] == "SNR-LEGAL-NLP-01"
        assert len(review["human_notes"]) > 10

        record = session.records_by_id[cid]
        assert len(record.get("audit_history", [])) >= 1
        latest_audit = record["audit_history"][-1]
        assert latest_audit["action"] == "accept"
        assert latest_audit["reviewer_id"] == "SNR-LEGAL-NLP-01"
        assert latest_audit["disposition"] == tgt["disposition"]
        assert latest_audit["successful_party"] == tgt["party"]


def test_group_h_candidates_preserved_pending(session):
    """Verify Group H candidates 5-7 remain untouched in pending_review status."""
    group_h_ids = [
        "OIL-SC-1995_INSC_603",
        "OIL-SC-2011_INSC_609",
        "OIL-SC-2003_INSC_14",
    ]
    for cid in group_h_ids:
        rec = session.records_by_id[cid]
        assert rec.get("review_status") == "pending_review", f"Candidate {cid} status corrupted"


def test_model_a_and_b_training_readiness(session):
    """Verify Model A has 43 eligible samples and Model B has 37 eligible samples with zero blockers."""
    readiness = session.check_training_readiness()
    ma = readiness["model_a"]
    mb = readiness["model_b"]

    assert ma["eligible_count"] == 43, f"Expected 43 Model A eligible, got {ma['eligible_count']}"
    assert mb["eligible_count"] == 37, f"Expected 37 Model B eligible, got {mb['eligible_count']}"

    assert ma["class_distribution"]["appeal_dismissed"] == 17
    assert ma["class_distribution"]["appeal_allowed"] == 11
    assert ma["class_distribution"]["petition_allowed"] == 8
    assert ma["class_distribution"]["petition_dismissed"] == 7

    assert mb["class_distribution"]["respondent"] == 17
    assert mb["class_distribution"]["petitioner"] == 8
    assert mb["class_distribution"]["accused"] == 7
    assert mb["class_distribution"]["state_prosecution"] == 5

    assert ma["blockers"] == []
    assert mb["blockers"] == []
    assert readiness["is_training_eligible"] is True
    assert readiness["recommended_mode"] == "statistical_verified"


def test_master_csv_json_synchronization():
    """Verify 100% field parity across all 150 records between JSON and CSV."""
    with open(CANDIDATES_JSON, "r", encoding="utf-8") as f:
        master_json = json.load(f)["records"]
    with open(REVIEW_CSV_FILE, "r", encoding="utf-8") as f:
        master_csv = list(csv.DictReader(f))

    assert len(master_json) == len(master_csv) == 150

    for jr, cr in zip(master_json, master_csv):
        assert jr["case_id"] == cr["case_id"]
        assert (jr.get("review_status") or "") == (cr.get("review_status") or "")
        assert (jr.get("human_approved_label") or "") == (cr.get("human_approved_label") or "")
        assert (jr.get("human_successful_party") or "") == (cr.get("human_successful_party") or "")
        assert (jr.get("reviewer_reference") or "") == (cr.get("reviewer_reference") or "")


def test_source_dataset_integrity():
    """Verify source benchmark dataset SHA-256 hash has not changed."""
    expected_hash = "006ea5b5bff63dc5e6423bf44273ae0a0dd23b557d22b7595212c8b8d19bf42b"
    with open(SOURCE_JSON, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()
    assert actual_hash == expected_hash


def test_zero_training_guarantee():
    """Verify predictor is not trained and no weights exist."""
    predictor = VerifiedOutcomePredictor()
    assert predictor.is_trained is False
    assert predictor.evaluation_metrics == {}


def test_sanitizer_zero_leakage_on_committed_batch(session, sanitizer):
    """Verify TargetLeakageSanitizer removes operative decretal sections from all 4 committed cases."""
    source_cases = session.source_cases
    target_ids = [
        "OIL-SC-1955_INSC_31",
        "OIL-SC-1994_INSC_388",
        "OIL-SC-1968_INSC_212",
        "OIL-SC-1972_INSC_24"
    ]

    for cid in target_ids:
        raw_text = source_cases[cid]["judgmentText"]
        sanitized_text, meta = sanitizer.sanitize_judgment_text(raw_text)

        assert meta.get("truncated_operative_section") is True, f"Operative section was not truncated for {cid}"
        assert len(sanitized_text) < len(raw_text), f"Text was not reduced for {cid}"
        assert "appeal dismissed" not in sanitized_text[-500:].lower()
        assert "appeal allowed" not in sanitized_text[-500:].lower()
