"""
Tests for Feature 4.11 — Outcome Annotation Batch 1.3 Staging Integrity

Verifies:
1. Existence and structure of batch_1_3_staged.json and batch_1_3_review.csv.
2. Exact byte-for-byte evidence substring matching in source judgment text.
3. Zero ellipses or editorial insertions in evidence quotes.
4. Schema validation through OutcomeAnnotationSessionManager.
5. Strict zero-commit verification: 11 verified cases and 139 pending cases preserved.
6. Source dataset SHA-256 cryptographic integrity.
"""

import sys
import json
import csv
import hashlib
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    VALID_DISPOSITIONS,
    VALID_SUCCESSFUL_PARTIES,
    KNOWN_SOURCE_HASHES,
)
STAGING_JSON = BASE_DIR / "app" / "datasets" / "review_batches" / "batch_1_3_staged.json"
REVIEW_CSV = BASE_DIR / "app" / "datasets" / "review_batches" / "batch_1_3_review.csv"
SOURCE_JSON = BASE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"
CANDIDATES_JSON = BASE_DIR / "app" / "datasets" / "outcome_label_candidates_v2.json"
REVIEW_CSV_FILE = BASE_DIR / "app" / "datasets" / "outcome_label_review_v2.csv"

@pytest.fixture(scope="module")
def session():
    return OutcomeAnnotationSessionManager()

@pytest.fixture(scope="module")
def staged_data():
    assert STAGING_JSON.exists(), f"Staged JSON file does not exist: {STAGING_JSON}"
    with open(STAGING_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture(scope="module")
def source_cases():
    assert SOURCE_JSON.exists(), f"Source JSON file does not exist: {SOURCE_JSON}"
    with open(SOURCE_JSON, "r", encoding="utf-8") as f:
        return {c["id"]: c for c in json.load(f)}

def test_staged_json_structure(staged_data):
    """Verify batch metadata and record count."""
    assert staged_data["batch_id"] == "batch_1_3"
    assert staged_data["status"] == "staged_for_review"
    assert staged_data["total_staged"] == 5
    assert len(staged_data["records"]) == 5

def test_review_csv_matches_json(staged_data):
    """Verify batch_1_3_review.csv exists and has identical 5 records."""
    assert REVIEW_CSV.exists(), f"Review CSV file does not exist: {REVIEW_CSV}"
    with open(REVIEW_CSV, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 5

    csv_ids = [r["case_id"] for r in reader]
    json_ids = [r["case_id"] for r in staged_data["records"]]
    assert csv_ids == json_ids

def test_expected_case_ids(staged_data):
    """Verify the 5 exact candidate cases staged for Batch 1.3."""
    expected_ids = [
        "OIL-SC-2006_INSC_699",
        "OIL-SC-2010_INSC_109",
        "OIL-AHC-UPHC020034182022",
        "OIL-DHC-DLHC015857912015",
        "OIL-SC-1992_INSC_350"
    ]
    actual_ids = [r["case_id"] for r in staged_data["records"]]
    assert actual_ids == expected_ids

def test_evidence_substring_exact_match(staged_data, source_cases):
    """Verify every evidence quotation is an exact substring of the primary judgment text."""
    for record in staged_data["records"]:
        cid = record["case_id"]
        ev = record["evidence"]
        src = source_cases.get(cid)
        assert src is not None, f"Source case {cid} not found!"
        
        # Substring check
        text = src["judgmentText"]
        idx = text.find(ev)
        assert idx != -1, f"Evidence for {cid} is not an exact substring of judgmentText!"
        assert idx == record["source_char_offset"], f"Offset mismatch for {cid}: {idx} != {record['source_char_offset']}"
        assert len(ev) == record["source_char_length"], f"Length mismatch for {cid}"

        # No ellipses check
        assert "..." not in ev, f"Evidence for {cid} contains forbidden ellipses!"

def test_schema_validity(session, staged_data):
    """Verify decision schemas pass OutcomeAnnotationSessionManager validation."""
    for record in staged_data["records"]:
        payload = {
            "case_id": record["case_id"],
            "action": record["action"],
            "disposition": record["disposition"],
            "successful_party": record["successful_party"],
            "evidence": record["evidence"],
            "notes": record["notes"]
        }
        session._validate_decision_payload(payload)
        assert record["disposition"] in VALID_DISPOSITIONS
        assert record["successful_party"] in VALID_SUCCESSFUL_PARTIES

def test_target_independence(staged_data):
    """Verify disposition and party success are independently assigned."""
    pairs = [(r["disposition"], r["successful_party"]) for r in staged_data["records"]]
    # In Batch 1.3:
    # (appeal_allowed, accused)
    # (appeal_dismissed, state_prosecution)
    # (appeal_allowed, accused)
    # (petition_allowed, petitioner)
    # (appeal_dismissed, respondent)
    assert ("appeal_allowed", "accused") in pairs
    assert ("appeal_dismissed", "state_prosecution") in pairs
    assert ("petition_allowed", "petitioner") in pairs
    assert ("appeal_dismissed", "respondent") in pairs

def test_zero_commit_guarantee(session):
    """Verify candidate queue and review CSV were NOT modified by staging."""
    dashboard = session.get_progress_dashboard()
    assert dashboard["total_verified"] == 11, f"Expected 11 verified, found {dashboard['total_verified']}"
    assert dashboard["pending"] == 139, f"Expected 139 pending, found {dashboard['pending']}"

    # Check that staged cases remain pending_review in the master candidates file
    with open(CANDIDATES_JSON, "r", encoding="utf-8") as f:
        master_records = {r["case_id"]: r for r in json.load(f)["records"]}

    for cid in [
        "OIL-SC-2006_INSC_699",
        "OIL-SC-2010_INSC_109",
        "OIL-AHC-UPHC020034182022",
        "OIL-DHC-DLHC015857912015",
        "OIL-SC-1992_INSC_350"
    ]:
        rec = master_records.get(cid)
        assert rec is not None
        assert rec["review_status"] == "pending_review", f"Case {cid} was prematurely modified to {rec['review_status']}"
        assert rec.get("human_approved_label") == ""
        assert rec.get("human_successful_party") == ""

def test_source_datasets_sha256_integrity(session):
    """Verify that source datasets have not been altered."""
    integrity = session.verify_source_integrity()
    for fname, ok in integrity.items():
        assert ok, f"Cryptographic integrity failed for {fname}"
