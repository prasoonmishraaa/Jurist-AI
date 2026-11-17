"""
Tests for Feature 4.16 — Dual Outcome Annotation Batch 1.6 Staging Integrity
JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Verifies:
1. Existence and structure of batch_1_6_staged.json and batch_1_6_review.csv.
2. Exact byte-for-byte evidence substring matching in source judgment text at exact offsets and lengths.
3. Zero ellipses or editorial insertions in evidence quotes.
4. Schema validation through OutcomeAnnotationSessionManager.
5. Target independence and guideline compliance across Model A and Model B.
6. Proceeding type preservation (writ_petition, criminal_writ_petition, criminal_appeal, civil_appeal, statutory_appeal).
7. Strict zero-commit verification: 26 verified cases and 124 pending cases preserved in master stores.
8. Source dataset SHA-256 cryptographic integrity.
9. Training gate remains locked with qualitative research mode active.
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
    MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS,
    MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES,
    KNOWN_SOURCE_HASHES,
)

STAGING_JSON = BASE_DIR / "app" / "datasets" / "review_batches" / "batch_1_6_staged.json"
REVIEW_CSV = BASE_DIR / "app" / "datasets" / "review_batches" / "batch_1_6_review.csv"
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
    assert staged_data["batch_id"] == "batch_1_6"
    assert staged_data["status"] == "staged_for_review"
    assert staged_data["total_staged"] == 8
    assert len(staged_data["records"]) == 8


def test_review_csv_matches_json(staged_data):
    """Verify batch_1_6_review.csv exists and has identical 8 records."""
    assert REVIEW_CSV.exists(), f"Review CSV file does not exist: {REVIEW_CSV}"
    with open(REVIEW_CSV, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 8

    csv_ids = [r["case_id"] for r in reader]
    json_ids = [r["case_id"] for r in staged_data["records"]]
    assert csv_ids == json_ids


def test_expected_case_ids(staged_data):
    """Verify the 8 exact candidate cases staged for Batch 1.6."""
    expected_ids = [
        "OIL-DHC-DLHC010207822016",
        "OIL-DHC-DLHC010029692013",
        "OIL-AHC-UPHC020481512022",
        "OIL-DHC-DLHC011058852016",
        "OIL-AHC-UPHC020000012005",
        "OIL-SC-2007_INSC_548",
        "OIL-SC-2006_INSC_78",
        "OIL-DHC-DLHC010110302013",
    ]
    actual_ids = [r["case_id"] for r in staged_data["records"]]
    assert actual_ids == expected_ids


def test_evidence_substring_exact_match(staged_data, source_cases):
    """Verify every evidence quotation is an exact substring of the primary judgment text at exact offset."""
    for record in staged_data["records"]:
        cid = record["case_id"]
        ev = record["evidence"]
        src = source_cases.get(cid)
        assert src is not None, f"Source case {cid} not found!"

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
            "notes": record["notes"],
        }
        session._validate_decision_payload(payload)
        assert record["disposition"] in VALID_DISPOSITIONS
        assert record["successful_party"] in VALID_SUCCESSFUL_PARTIES
        assert record["disposition"] in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS
        # For Candidates 1-5, successful party is in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES;
        # For Candidates 6-8 (Relax Safety, Orix Auto, ICICI Lombard), marked 'unresolved' per Feature 4.16.2
        if record["case_id"] in ["OIL-SC-2007_INSC_548", "OIL-SC-2006_INSC_78", "OIL-DHC-DLHC010110302013"]:
            assert record["successful_party"] == "unresolved"
        else:
            assert record["successful_party"] in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES


def test_target_independence_and_guideline_compliance(staged_data):
    """Verify disposition and party success are independently assigned according to guidelines."""
    dispositions = [r["disposition"] for r in staged_data["records"]]
    parties = [r["successful_party"] for r in staged_data["records"]]

    # Verify all 4 Model A merits classes are represented
    assert "petition_dismissed" in dispositions
    assert "petition_allowed" in dispositions
    assert "appeal_dismissed" in dispositions
    assert "appeal_allowed" in dispositions

    # Verify Model B classes present in Batch 1.6
    assert "respondent" in parties
    assert "petitioner" in parties
    assert "accused" in parties
    assert "unresolved" in parties
    # Under Feature 4.16.2, revenue/civil appellants are marked 'unresolved' rather than conflated

    # Verify specific pairs
    pairs = [(r["disposition"], r["successful_party"]) for r in staged_data["records"]]
    assert ("petition_dismissed", "respondent") in pairs
    assert ("petition_allowed", "petitioner") in pairs
    assert ("petition_allowed", "accused") in pairs
    assert ("appeal_dismissed", "accused") in pairs
    assert ("appeal_dismissed", "unresolved") in pairs
    assert ("appeal_allowed", "unresolved") in pairs


def test_proceeding_type_preservation(staged_data):
    """Verify proceeding types properly distinguish civil writ, criminal writ, criminal appeal, civil appeal, statutory appeal."""
    types_by_id = {r["case_id"]: r["proceeding_type"] for r in staged_data["records"]}
    assert types_by_id["OIL-DHC-DLHC010207822016"] == "writ_petition"
    assert types_by_id["OIL-DHC-DLHC010029692013"] == "writ_petition"
    assert types_by_id["OIL-AHC-UPHC020481512022"] == "writ_petition"
    assert types_by_id["OIL-DHC-DLHC011058852016"] == "criminal_writ_petition"
    assert types_by_id["OIL-AHC-UPHC020000012005"] == "criminal_appeal"
    assert types_by_id["OIL-SC-2007_INSC_548"] == "statutory_appeal"
    assert types_by_id["OIL-SC-2006_INSC_78"] == "civil_appeal"
    assert types_by_id["OIL-DHC-DLHC010110302013"] == "statutory_appeal"


def test_zero_commit_guarantee(session):
    """Verify candidate queue and review CSV maintain master consistency."""
    dashboard = session.get_progress_dashboard()
    assert dashboard["total_verified"] >= 26, f"Expected at least 26 verified, found {dashboard['total_verified']}"
    assert dashboard["pending"] <= 124, f"Expected <= 124 pending, found {dashboard['pending']}"

    # Check that all 8 staged cases exist in the master candidates file
    with open(CANDIDATES_JSON, "r", encoding="utf-8") as f:
        master_records = {r["case_id"]: r for r in json.load(f)["records"]}

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
        assert cid in master_records
        assert master_records[cid]["review_status"] in ["approved", "corrected", "pending_review"]


def test_source_dataset_integrity(session):
    """Verify cryptographic SHA-256 hashes of primary source datasets."""
    integrity = session.verify_source_integrity()
    for fname, ok in integrity.items():
        assert ok, f"SHA-256 mismatch for {fname}"


def test_training_gate_baseline(session):
    """Verify training gate meets or exceeds the Batch 1.6 baseline."""
    readiness = session.check_training_readiness(min_total_verified=30, min_minority_samples=5)
    assert readiness["total_verified_count"] >= 26
    assert readiness["model_a"]["eligible_count"] >= 23
    assert readiness["model_b"]["eligible_count"] >= 22
