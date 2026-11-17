"""
Tests for Feature 4.12 / 4.12.2 — Dual Outcome Annotation Batch 1.4 Staging Integrity

Verifies:
1. Existence and structure of batch_1_4_staged.json and batch_1_4_review.csv.
2. Exact byte-for-byte evidence substring matching in source judgment text.
3. Zero ellipses or editorial insertions in evidence quotes.
4. Schema validation through OutcomeAnnotationSessionManager.
5. Strict zero-commit verification: 16 verified cases and 134 pending cases preserved.
6. Source dataset SHA-256 cryptographic integrity.
7. Correct guidelines-aligned labels:
   - OIL-SC-1981_INSC_134: remanded, none_procedural (remand takes precedence over reporter stamp)
   - OIL-SC-1984_INSC_90: petition_allowed, petitioner
   - OIL-SC-2012_INSC_207: petition_dismissed, respondent
   - OIL-AHC-UPHC020380352022: petition_allowed, accused
   - OIL-AHC-UPHC020497422019: dismissed_as_infructuous, none_procedural (guidelines §3.6.2 & row 131)
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

STAGING_JSON = BASE_DIR / "app" / "datasets" / "review_batches" / "batch_1_4_staged.json"
REVIEW_CSV = BASE_DIR / "app" / "datasets" / "review_batches" / "batch_1_4_review.csv"
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
    assert staged_data["batch_id"] == "batch_1_4"
    assert staged_data["status"] == "staged_for_review"
    assert staged_data["total_staged"] == 5
    assert len(staged_data["records"]) == 5

def test_review_csv_matches_json(staged_data):
    """Verify batch_1_4_review.csv exists and has identical 5 records."""
    assert REVIEW_CSV.exists(), f"Review CSV file does not exist: {REVIEW_CSV}"
    with open(REVIEW_CSV, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 5

    csv_ids = [r["case_id"] for r in reader]
    json_ids = [r["case_id"] for r in staged_data["records"]]
    assert csv_ids == json_ids

def test_expected_case_ids(staged_data):
    """Verify the 5 exact candidate cases staged for Batch 1.4."""
    expected_ids = [
        "OIL-SC-1981_INSC_134",
        "OIL-SC-1984_INSC_90",
        "OIL-SC-2012_INSC_207",
        "OIL-AHC-UPHC020380352022",
        "OIL-AHC-UPHC020497422019"
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

def test_target_independence_and_guideline_compliance(staged_data):
    """Verify disposition and party success are independently assigned according to guidelines."""
    pairs = [(r["disposition"], r["successful_party"]) for r in staged_data["records"]]
    dispositions = {r["disposition"] for r in staged_data["records"]}
    parties = {r["successful_party"] for r in staged_data["records"]}

    # Verify dispositions
    assert "remanded" in dispositions
    assert "petition_allowed" in dispositions
    assert "petition_dismissed" in dispositions
    assert "dismissed_as_infructuous" in dispositions

    # Verify successful parties
    assert "none_procedural" in parties
    assert "petitioner" in parties
    assert "respondent" in parties
    assert "accused" in parties

    # Verify exact pairs complying with legal guidelines
    assert ("remanded", "none_procedural") in pairs
    assert ("petition_allowed", "petitioner") in pairs
    assert ("petition_dismissed", "respondent") in pairs
    assert ("petition_allowed", "accused") in pairs
    assert ("dismissed_as_infructuous", "none_procedural") in pairs

def test_proceeding_type_preservation(staged_data):
    """Verify proceeding types properly distinguish civil appeals, writ petitions, and criminal petitions."""
    types_by_id = {r["case_id"]: r["proceeding_type"] for r in staged_data["records"]}
    assert types_by_id["OIL-SC-1981_INSC_134"] == "civil_appellate_proceeding"
    assert types_by_id["OIL-SC-1984_INSC_90"] == "writ_petition"
    assert types_by_id["OIL-SC-2012_INSC_207"] == "special_leave_petition"
    assert types_by_id["OIL-AHC-UPHC020380352022"] == "criminal_misc_petition_482"
    assert types_by_id["OIL-AHC-UPHC020497422019"] == "criminal_writ_petition"

def test_zero_commit_guarantee(session):
    """Verify candidate queue and review CSV were NOT modified by staging."""
    dashboard = session.get_progress_dashboard()
    assert dashboard["total_verified"] == 16, f"Expected 16 verified, found {dashboard['total_verified']}"
    assert dashboard["pending"] == 134, f"Expected 134 pending, found {dashboard['pending']}"

    # Check that staged cases remain pending_review in the master candidates file
    with open(CANDIDATES_JSON, "r", encoding="utf-8") as f:
        master_records = {r["case_id"]: r for r in json.load(f)["records"]}

    for cid in [
        "OIL-SC-1981_INSC_134",
        "OIL-SC-1984_INSC_90",
        "OIL-SC-2012_INSC_207",
        "OIL-AHC-UPHC020380352022",
        "OIL-AHC-UPHC020497422019"
    ]:
        rec = master_records.get(cid)
        assert rec is not None
        assert rec["review_status"] == "pending_review", f"Case {cid} was prematurely modified to {rec['review_status']}"
        assert rec.get("human_approved_label") == ""
        assert rec.get("human_successful_party") == ""

def test_source_dataset_integrity(session):
    """Verify cryptographic SHA-256 hashes of primary source datasets are intact."""
    integrity = session.verify_source_integrity()
    for filename, is_valid in integrity.items():
        assert is_valid, f"SHA-256 hash mismatch for {filename}!"
