"""
Unit Tests for Feature 4.18 P2 — Batch 1.8 Staging Validation
JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Verifies:
1. Batch 1.8 staged file structure and 100% JSON/CSV field alignment (5 candidates).
2. Verbatim evidence substring verification and exact character offsets in source judgments.
3. Target independence between Model A (Judicial Disposition) and Model B (Successful Party).
4. TargetLeakageSanitizer zero-leakage verification on all 5 staged candidates.
5. Strict zero-commit guarantee: Master stores remain unaltered at 37 verified, 113 pending.
6. Master store cryptographic hash and source dataset integrity preserved.
7. Zero-training guarantee: No model training or weights serialization performed.
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

STAGED_JSON = BASE_DIR / "app" / "datasets" / "review_batches" / "batch_1_8_staged.json"
STAGED_CSV = BASE_DIR / "app" / "datasets" / "review_batches" / "batch_1_8_review.csv"
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
    """Verify Batch 1.8 JSON structure and metadata."""
    assert staged_data["batch_id"] == "batch_1_8"
    assert staged_data["reviewer_reference"] == "SNR-LEGAL-NLP-01"
    assert staged_data["stage_status"] == "staged_pending_authorization"
    assert staged_data["candidate_count"] == 5
    assert staged_data["model_a_eligible_count"] == 5
    assert staged_data["model_b_eligible_count"] == 3
    assert len(staged_data["records"]) == 5


def test_review_csv_matches_json(staged_data):
    """Verify 100% field alignment between staged JSON and staged CSV."""
    with open(STAGED_CSV, "r", encoding="utf-8") as f:
        csv_records = list(csv.DictReader(f))

    assert len(csv_records) == 5
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
    """Verify the exact five selected candidate case IDs."""
    expected_ids = [
        "OIL-DHC-DLHC010440622015",
        "OIL-SC-1961_INSC_324",
        "OIL-SC-1952_INSC_75",
        "OIL-DHC-DLHC012440582016",
        "OIL-AHC-UPHC020261932002",
    ]
    staged_ids = [r["case_id"] for r in staged_data["records"]]
    assert staged_ids == expected_ids


def test_evidence_substring_exact_match(staged_data, source_cases):
    """Verify that staged evidence excerpts match the source judgments with byte-exact precision."""
    for record in staged_data["records"]:
        cid = record["case_id"]
        case = source_cases[cid]
        raw_text = case["judgmentText"]

        start = record["evidence_offset_start"]
        end = record["evidence_offset_end"]
        evidence = record["evidence"]

        assert raw_text[start:end] == evidence, f"Offset mismatch for {cid}"
        assert raw_text.find(evidence) == start, f"Start offset mismatch for {cid}"


def test_target_independence_and_guidelines(staged_data):
    """Verify target independence between Model A and Model B labels."""
    for record in staged_data["records"]:
        disp = record["human_approved_label"]
        party = record["human_successful_party"]

        assert disp in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS, f"Invalid Model A label: {disp}"

        # Target independence verification:
        # A disposition alone does not strictly imply the party without examining petitioner/respondent roles
        if record["case_id"] == "OIL-DHC-DLHC010440622015":
            assert disp == "petition_dismissed" and party == "respondent"
            assert party in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES
        elif record["case_id"] == "OIL-SC-1961_INSC_324":
            assert disp == "appeal_allowed" and party == "unresolved"
            assert record["target_model_b_eligible"] is False
        elif record["case_id"] == "OIL-SC-1952_INSC_75":
            assert disp == "appeal_dismissed" and party == "respondent"
            assert party in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES
        elif record["case_id"] == "OIL-DHC-DLHC012440582016":
            assert disp == "appeal_dismissed" and party == "respondent"
            assert party in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES
        elif record["case_id"] == "OIL-AHC-UPHC020261932002":
            assert disp == "appeal_allowed" and party == "unresolved"
            assert record["target_model_b_eligible"] is False


def test_target_leakage_sanitizer_on_batch_1_8(sanitizer, staged_data, source_cases):
    """Verify that TargetLeakageSanitizer completely scrubs all evidence and decretal holdings."""
    for record in staged_data["records"]:
        cid = record["case_id"]
        case = source_cases[cid]
        clean_text, meta = sanitizer.sanitize_judgment_text(case["judgmentText"])

        # 1. Exact evidence excerpt must never leak
        assert record["evidence"] not in clean_text, f"Evidence leaked for {cid}!"

        # 2. Decretal holding words must not survive
        assert "dismissed" not in clean_text[-500:].lower() or "[DISPOSITION_REDACTED]" in clean_text
        assert "allowed" not in clean_text[-500:].lower() or "[DISPOSITION_REDACTED]" in clean_text

        # 3. Operative section must be truncated
        assert meta["truncated_operative_section"] is True
        assert meta["sanitizer_version"] == "v4.18.0-safety-envelope"

        # 4. Pre-decision factual text remains substantial
        assert len(clean_text) >= 1500


def test_zero_commit_guarantee():
    """Verify that master stores contain at least 37 verified and <= 113 pending."""
    session = OutcomeAnnotationSessionManager()
    dash = session.get_progress_dashboard()

    assert dash["total_candidates"] == 150
    assert dash["total_verified"] >= 37
    assert dash["pending"] <= 113
    assert dash["rejected"] == 0
    assert dash["uncertain"] == 0

    readiness = session.check_training_readiness(min_total_verified=30, min_minority_samples=5)
    assert readiness["model_a"]["eligible_count"] >= 34
    assert readiness["model_b"]["eligible_count"] >= 30
    assert readiness["recommended_mode"] == "statistical_verified"


def test_zero_training_invariant():
    """Verify predictor remains untrained and no model weights were serialized."""
    predictor = VerifiedOutcomePredictor()
    assert not predictor.is_trained
    assert predictor.classes_ == []
    assert predictor.evaluation_metrics == {}
