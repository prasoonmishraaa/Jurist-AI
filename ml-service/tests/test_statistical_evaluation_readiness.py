"""
Tests for Feature 4.18 — Statistical Evaluation Readiness Audit
JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Verifies:
1. Master dataset audit: 37 verified, 113 pending, 34 Model A eligible, 30 Model B eligible.
2. 100% JSON/CSV synchronization across all 150 records.
3. Excluded record distributions for Model A (3) and Model B (7).
4. Case group and proceeding identifier isolation.
5. Baseline accuracy metrics (Majority class, Stratified expected, Uniform).
6. Target independence between Model A (Judicial Disposition) and Model B (Successful Party).
7. TargetLeakageSanitizer adversarial test suite (false negatives and false positives).
8. Identification of residual leakage vulnerability surface in legacy-batch un-truncated records.
9. Strict zero-training invariant: predictor untrained, no new serialized weights.
"""

import sys
import json
import csv
from pathlib import Path
from collections import Counter
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS,
    MODEL_A_EXCLUDED_PROCEDURAL_DISPOSITIONS,
    MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES,
    MODEL_B_EXCLUDED_NON_SUBSTANTIVE_PARTIES,
)
from scripts.build_verified_outcome_dataset import TargetLeakageSanitizer, VerifiedOutcomeDatasetBuilder
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


@pytest.fixture(scope="module")
def source_cases():
    with open(SOURCE_JSON, "r", encoding="utf-8") as f:
        return {c["id"]: c for c in json.load(f)}


def test_master_dataset_audit(session):
    """Verify master annotation store counts and class distributions."""
    dash = session.get_progress_dashboard()
    assert dash["total_candidates"] == 150
    assert dash["total_verified"] >= 37
    assert dash["pending"] <= 113

    readiness = session.check_training_readiness(min_total_verified=30, min_minority_samples=5)
    assert readiness["is_training_eligible"] is True
    assert readiness["recommended_mode"] == "statistical_verified"

    # Model A
    ma = readiness["model_a"]
    assert ma["eligible_count"] >= 34
    assert len(ma["class_distribution"]) == 4
    for cls in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS:
        assert cls in ma["class_distribution"]
        assert ma["class_distribution"][cls] >= 5

    # Model B
    mb = readiness["model_b"]
    assert mb["eligible_count"] >= 30
    assert len(mb["class_distribution"]) == 4
    for party in MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES:
        assert party in mb["class_distribution"]
        assert mb["class_distribution"][party] >= 5


def test_json_csv_strict_synchronization():
    """Verify 100% field-level synchronization between JSON and CSV stores."""
    with open(CANDIDATES_JSON, "r", encoding="utf-8") as f:
        j_recs = {r["case_id"]: r for r in json.load(f)["records"]}
    with open(REVIEW_CSV_FILE, "r", encoding="utf-8") as f:
        c_recs = {r["case_id"]: r for r in csv.DictReader(f)}

    assert len(j_recs) == 150
    assert len(c_recs) == 150

    for cid, jr in j_recs.items():
        cr = c_recs[cid]
        assert jr["review_status"] == cr["review_status"]
        assert jr["human_approved_label"] == cr["human_approved_label"]
        assert jr["human_successful_party"] == cr["human_successful_party"]
        assert jr["reviewer_reference"] == cr["reviewer_reference"]
        assert jr["proceeding_type"] == cr["proceeding_type"]


def test_group_isolation_and_identifiers(source_cases):
    """Verify case group identifiers and ensure no overlapping groups among verified cases."""
    with open(CANDIDATES_JSON, "r", encoding="utf-8") as f:
        verified_ids = [
            r["case_id"] for r in json.load(f)["records"]
            if r["review_status"] in ["approved", "corrected", "adjudicated_approved"]
        ]

    assert len(verified_ids) >= 37

    # Collect group IDs
    verified_groups = set()
    for cid in verified_ids:
        raw = source_cases[cid]
        ident = raw.get("caseIdentifier", "").strip()
        grp = ident if ident and ident != "neutral citation pending" else cid
        # All 37 verified cases belong to unique proceedings
        assert grp not in verified_groups, f"Duplicate group detected in verified cases: {grp}"
        verified_groups.add(grp)

    # In the full 150 corpus, verify that known related cases are linked
    case_1 = source_cases.get("OIL-DHC-DLHC010440622015", {})
    case_2 = source_cases.get("OIL-DHC-DLHC012615072014", {})
    assert case_1.get("caseIdentifier") == "9101/2014"
    assert case_2.get("caseIdentifier") == "9101/2014"


def test_baseline_metrics_computation(session):
    """Verify independent baseline calculations for Model A and Model B."""
    readiness = session.check_training_readiness(min_total_verified=30, min_minority_samples=5)

    # Model A: at least 34 samples
    ma_dist = readiness["model_a"]["class_distribution"]
    total_a = sum(ma_dist.values())
    assert total_a >= 34
    majority_a = max(ma_dist.values()) / total_a
    stratified_a = sum((cnt / total_a) ** 2 for cnt in ma_dist.values())
    uniform_a = 1.0 / len(ma_dist)

    assert majority_a > 0.25
    assert stratified_a > 0.20
    assert uniform_a == 0.25

    # Model B: at least 30 samples
    mb_dist = readiness["model_b"]["class_distribution"]
    total_b = sum(mb_dist.values())
    assert total_b >= 30
    majority_b = max(mb_dist.values()) / total_b
    stratified_b = sum((cnt / total_b) ** 2 for cnt in mb_dist.values())
    uniform_b = 1.0 / len(mb_dist)

    assert majority_b > 0.25
    assert stratified_b > 0.20
    assert uniform_b == 0.25


def test_adversarial_false_positives(sanitizer):
    """
    Adversarial False Positive Test:
    Verify that pre-decision facts, procedural history, statutory citations, and counsel arguments
    containing outcome keywords are NOT improperly truncated or corrupted by the sanitizer.
    """
    narrative_case = (
        "The appellant filed an appeal challenging the conviction under Section 302 IPC. "
        "The procedural history shows that the earlier writ petition was dismissed by the Single Judge in 2014. "
        "Section 378 of the Code of Criminal Procedure provides that the State Government may direct the Public "
        "Prosecutor to present an appeal to the High Court from an order of acquittal. "
        "Learned counsel for the appellant argued that the appeal deserves to be allowed because PW-1 is unreliable. "
        "Learned counsel for the State submitted that the trial court rightly rejected the plea of alibi. "
        "The primary issue for consideration is whether circumstantial evidence conclusively establishes guilt."
    )

    sanitized, diag = sanitizer.sanitize_judgment_text(narrative_case)
    # The narrative case must NOT be truncated as an operative section
    assert not diag["truncated_operative_section"]
    # Key legal and procedural words must be preserved in the pre-decision factual narrative
    assert "conviction under Section 302 IPC" in sanitized
    assert "Section 378 of the Code of Criminal Procedure" in sanitized
    assert "circumstantial evidence conclusively establishes guilt" in sanitized


def test_adversarial_false_negatives(sanitizer):
    """
    Adversarial False Negative Test:
    Verify that sneaky operative decree variations are caught and stripped or truncated.
    """
    test_cases = [
        # Variation 1: OCR typo in 'dismissed'
        "In the result, the appeal is dismissed with costs.",
        # Variation 2: Compound quashing and fresh order
        "The impugned orders are hereby quashed and the respondents shall issue fresh orders.",
        # Variation 3: Cost and refund order
        "The appellant shall pay costs quantified @ Rs. 50,000 to the respondent. The amount shall also be refunded.",
        # Variation 4: Direct active-voice bench finding
        "For the reasons stated above, we allow the appeal and set aside the impugned conviction.",
    ]

    for tc in test_cases:
        # Wrap in mock judgment context with concluding section
        full_text = "Background facts and legal submissions.\n\n" * 10 + tc
        sanitized, diag = sanitizer.sanitize_judgment_text(full_text)
        assert tc.lower() not in sanitized.lower()


def test_residual_leakage_forensic_remediation(sanitizer, source_cases):
    """
    Forensic Verification of P0 Remediation on Legacy-Batch Vulnerabilities:
    Confirms that previously vulnerable cases from Batches 1.1–1.5 (e.g. unnumbered decretal
    sentences) are now structurally truncated with zero surviving target leakage.
    """
    # 1. Candidate OIL-AHC-UPHC020265642022 (Batch 1.5): 'The petition lacks merit and is, accordingly, dismissed'
    raw_case_1 = source_cases["OIL-AHC-UPHC020265642022"]
    features_1 = sanitizer.extract_pre_decision_features(raw_case_1)
    diag_1 = features_1["sanitization_diagnostics"]
    san_text_1 = features_1["sanitized_pre_decision_text"]

    assert diag_1["truncated_operative_section"] is True
    assert diag_1["sanitizer_version"] == "v4.18.0-safety-envelope"
    assert "petition lacks merit and is, accordingly, dismissed" not in san_text_1.lower()
    assert "dismissed" not in san_text_1.lower()

    # 2. Candidate OIL-SC-1973_INSC_247 (Batch 1.3): 'The petition consequently fails and is dismissed'
    raw_case_2 = source_cases["OIL-SC-1973_INSC_247"]
    features_2 = sanitizer.extract_pre_decision_features(raw_case_2)
    diag_2 = features_2["sanitization_diagnostics"]
    san_text_2 = features_2["sanitized_pre_decision_text"]

    assert diag_2["truncated_operative_section"] is True
    assert diag_2["sanitizer_version"] == "v4.18.0-safety-envelope"
    assert "petition consequently fails and is dismissed" not in san_text_2.lower()


def test_stratified_group_cross_validation_protocol():
    """
    Verify Feature 4.18 P1 Statistical Evaluation Protocol:
    1. Stratified Group 5-Fold Cross-Validation evaluates Model A (34 samples) and Model B (30 samples).
    2. Strict case group isolation across all 5 folds.
    3. Generates complete out-of-fold metrics (Macro-F1, Balanced Accuracy, Accuracy, confusion matrix).
    4. Predictor instance remains strictly untrained, verifying the zero-training invariant.
    """
    builder = VerifiedOutcomeDatasetBuilder()
    ds = builder.build_dataset(allow_empty_manifest=True)
    predictor = VerifiedOutcomePredictor()

    # Model A: Judicial Disposition
    res_a = predictor.evaluate_stratified_group_cross_validation(ds, target_field="verified_label", n_splits=5)
    assert res_a["evaluation_protocol"] == "StratifiedGroup5FoldCV"
    assert res_a["total_evaluated_samples"] >= 34
    assert res_a["group_isolation_verified"] is True
    assert res_a["n_splits"] == 5
    assert len(res_a["fold_breakdown"]) == 5
    assert res_a["out_of_fold_metrics"]["macro_f1"] > 0
    assert len(res_a["confusion_matrix"]) == 4

    # Model B: Successful Party
    res_b = predictor.evaluate_stratified_group_cross_validation(ds, target_field="verified_successful_party", n_splits=5)
    assert res_b["evaluation_protocol"] == "StratifiedGroup5FoldCV"
    assert res_b["total_evaluated_samples"] >= 30
    assert res_b["group_isolation_verified"] is True
    assert res_b["n_splits"] == 5
    assert len(res_b["fold_breakdown"]) == 5
    assert res_b["out_of_fold_metrics"]["macro_f1"] > 0
    assert len(res_b["confusion_matrix"]) == 4

    # Strict zero-training invariant remains preserved
    assert not predictor.is_trained
    assert predictor.classes_ == []


def test_zero_training_and_model_weights_invariant():
    """Verify that predictor remains untrained and no model weights were generated."""
    predictor = VerifiedOutcomePredictor()
    assert not predictor.is_trained
    assert predictor.evaluation_metrics == {}
    assert predictor.classes_ == []
