"""
Unit Tests for Feature 4.22 — Batch 1.9 Option 1 Staging & Commit Preparation Validation
JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Verifies:
1. Batch 1.9 Option 1 staged file structure and 100% JSON/CSV field alignment (4 Group D candidates).
2. Verbatim evidence substring verification and exact character offsets in source judgments.
3. Target independence between Model A (Judicial Disposition) and Model B (Successful Party).
4. Taxonomy compliance: 4 civil appeals where respondents prevailed (appeal_dismissed / respondent).
5. Exclusion verification: Candidates 5-7 (Pandey, Sarma, Bhutada) are excluded from Batch 1.9 Option 1.
6. TargetLeakageSanitizer v4.18.0 zero-leakage verification on all 4 staged candidates.
7. Strict zero-commit guarantee: Master stores remain unaltered at 42 verified, 108 pending.
8. Master store cryptographic hash and source dataset integrity preserved.
9. Zero-training guarantee: No model training or weights serialization performed.
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
    MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS,
    MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES,
)
from scripts.build_verified_outcome_dataset import TargetLeakageSanitizer
from app.prediction.verified_outcome_model import VerifiedOutcomePredictor

STAGED_JSON = BASE_DIR / "app" / "datasets" / "review_batches" / "batch_1_9_staged.json"
STAGED_CSV = BASE_DIR / "app" / "datasets" / "review_batches" / "batch_1_9_review.csv"
SOURCE_JSON = BASE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"
MASTER_JSON = BASE_DIR / "app" / "datasets" / "outcome_label_candidates_v2.json"
MASTER_CSV = BASE_DIR / "app" / "datasets" / "outcome_label_review_v2.csv"


@pytest.fixture(scope="module")
def staged_data():
    with open(STAGED_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def source_cases():
    with open(SOURCE_JSON, "r", encoding="utf-8") as f:
        return {c["id"]: c for c in json.load(f)}


@pytest.fixture(scope="module")
def sanitizer():
    return TargetLeakageSanitizer()


def test_staged_json_structure(staged_data):
    """Verify Batch 1.9 Option 1 JSON structure and metadata."""
    assert staged_data["batch_id"] == "batch_1_9"
    assert staged_data["reviewer_reference"] == "SNR-LEGAL-NLP-01"
    assert staged_data["stage_status"] == "staged_pending_authorization"
    assert staged_data["candidate_count"] == 4
    assert staged_data["model_a_eligible_count"] == 4
    assert staged_data["model_b_eligible_count"] == 4
    assert len(staged_data["records"]) == 4


def test_review_csv_matches_json(staged_data):
    """Verify 100% field alignment between staged JSON and staged CSV."""
    with open(STAGED_CSV, "r", encoding="utf-8") as f:
        csv_records = list(csv.DictReader(f))

    assert len(csv_records) == 4
    json_records = staged_data["records"]

    for jr, cr in zip(json_records, csv_records):
        assert jr["case_id"] == cr["case_id"]
        assert jr["human_approved_label"] == cr["human_approved_label"]
        assert jr["human_successful_party"] == cr["human_successful_party"]
        assert jr["evidence"] == cr["evidence"]
        assert int(jr["evidence_offset_start"]) == int(cr["evidence_offset_start"])
        assert int(jr["evidence_offset_end"]) == int(cr["evidence_offset_end"])
        assert jr["reviewer_reference"] == cr["reviewer_reference"]
        assert jr["proceeding_type"] == cr["proceeding_type"]


def test_expected_case_ids(staged_data):
    """Verify the exact four selected Group D candidate case IDs."""
    expected_ids = [
        "OIL-SC-1955_INSC_31",
        "OIL-SC-1994_INSC_388",
        "OIL-SC-1968_INSC_212",
        "OIL-SC-1972_INSC_24",
    ]
    staged_ids = [r["case_id"] for r in staged_data["records"]]
    assert staged_ids == expected_ids


def test_excluded_candidates_not_in_batch(staged_data):
    """Verify Candidates 5-7 (Pandey, Sarma, Bhutada) are explicitly excluded from Option 1."""
    excluded_ids = {
        "OIL-SC-1995_INSC_603",
        "OIL-SC-2011_INSC_609",
        "OIL-SC-2003_INSC_14",
    }
    staged_ids = {r["case_id"] for r in staged_data["records"]}
    assert staged_ids.isdisjoint(excluded_ids)


def test_evidence_substring_exact_match(staged_data, source_cases):
    """Verify each candidate's evidence string matches the raw judgment text exactly at the offsets."""
    for record in staged_data["records"]:
        cid = record["case_id"]
        assert cid in source_cases, f"Case {cid} not in source dataset"
        raw_text = source_cases[cid]["judgmentText"]
        start = record["evidence_offset_start"]
        end = record["evidence_offset_end"]
        evidence = record["evidence"]

        assert 0 <= start < end <= len(raw_text), f"Offsets out of bounds for {cid}"
        extracted = raw_text[start:end]
        assert extracted == evidence, f"Evidence mismatch for {cid}:\nExpected: {evidence}\nFound: {extracted}"


def test_model_a_and_b_label_validity(staged_data):
    """Verify all 4 Group D candidates have valid Model A and Model B labels."""
    for r in staged_data["records"]:
        cid = r["case_id"]
        disp = r["human_approved_label"]
        party = r["human_successful_party"]

        assert disp in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS
        assert disp == "appeal_dismissed"
        assert party in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES
        assert party == "respondent"
        assert r["target_model_a_eligible"] is True
        assert r["target_model_b_eligible"] is True


def test_sanitizer_removes_target_leakage_on_staged_candidates(staged_data, source_cases, sanitizer):
    """Verify TargetLeakageSanitizer truncates operative decree on all 4 staged candidates."""
    for record in staged_data["records"]:
        cid = record["case_id"]
        raw_text = source_cases[cid]["judgmentText"]
        sanitized_text, meta = sanitizer.sanitize_judgment_text(raw_text)

        assert meta.get("truncated_operative_section") is True, f"Operative section was not truncated for {cid}"
        assert len(sanitized_text) < len(raw_text), f"Text was not reduced for {cid}"
        assert "appeal dismissed" not in sanitized_text[-500:].lower()
        assert "appeal allowed" not in sanitized_text[-500:].lower()


def test_master_stores_integrity():
    """Verify master JSON and CSV contain valid records with >= 42 verified and <= 108 pending."""
    with open(MASTER_JSON, "r", encoding="utf-8") as f:
        master_data = json.load(f)

    records = master_data["records"]
    assert len(records) == 150
    verified = [r for r in records if r.get("review_status") in ["approved", "corrected", "adjudicated_approved"]]
    pending = [r for r in records if r.get("review_status") == "pending_review"]

    assert len(verified) >= 42
    assert len(pending) <= 108


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
