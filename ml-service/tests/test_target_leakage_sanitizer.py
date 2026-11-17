"""
Unit and Regression Tests for Feature 4.16.2 — Target Leakage Sanitizer Hardening
JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Verifies:
1. Vulnerability 1: Plural forms in IOCL (OIL-DHC-DLHC010029692013) 'petitions fail and are dismissed'.
2. Vulnerability 2: OCR concatenations in Santosh Kumar (OIL-AHC-UPHC020000012005) 'appealalso does not survive'.
3. Vulnerability 3: Anticipatory outcome in Atul Shukla (OIL-AHC-UPHC020481512022) 'instant writ petition also deserves to be allowed'.
4. Vulnerability 4: Tribunal negative finding reversal in ICICI Lombard (OIL-DHC-DLHC010110302013).
5. Existing sanitized cases across batches (Varun Dutta, Pegasus Assets, Manish Azad, Relax Safety, Orix Auto).
6. Symmetric sanitization across both allowed and dismissed outcomes.
7. Symmetric sanitization across civil and criminal proceedings.
8. False-positive protection: Lower-court historical narratives and precedent citations are preserved.
9. Auxiliary field isolation: Evidence excerpts and human notes never enter training features.
10. Target isolation and group-aware train/test separation.
"""

import sys
import json
import re
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.build_verified_outcome_dataset import (
    TargetLeakageSanitizer,
    MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS,
    MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES,
)

SOURCE_JSON = BASE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"
BATCH_1_6_JSON = BASE_DIR / "app" / "datasets" / "review_batches" / "batch_1_6_staged.json"


@pytest.fixture(scope="module")
def sanitizer():
    return TargetLeakageSanitizer()


@pytest.fixture(scope="module")
def source_cases():
    assert SOURCE_JSON.exists(), f"Source JSON file missing: {SOURCE_JSON}"
    with open(SOURCE_JSON, "r", encoding="utf-8") as f:
        return {c["id"]: c for c in json.load(f)}


@pytest.fixture(scope="module")
def staged_batch_1_6():
    assert BATCH_1_6_JSON.exists(), f"Batch 1.6 staged JSON missing: {BATCH_1_6_JSON}"
    with open(BATCH_1_6_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


# ==============================================================================
# 1. The Four Feature 4.16.1 Target Leakage Vulnerabilities
# ==============================================================================

def test_vulnerability_1_plural_petitions_fail_iocl(sanitizer, source_cases):
    """
    Case 1: OIL-DHC-DLHC010029692013 (Indian Oil Corporation Ltd v. DDA).
    Vulnerability: Plural phrase 'Resultantly, the petitions fail and are dismissed; Rule discharged...'.
    Must truncate operative section and strip all outcome phrases.
    """
    case = source_cases.get("OIL-DHC-DLHC010029692013")
    assert case is not None
    raw_text = case["judgmentText"]

    clean_text, meta = sanitizer.sanitize_judgment_text(raw_text)

    # 1. Must be truncated at concluding operative transition
    assert meta["truncated_operative_section"] is True
    assert meta["sanitized_length"] < meta["original_length"]

    # 2. Operative holding must NOT appear in sanitized text
    assert "petitions fail and are dismissed" not in clean_text
    assert "Rule discharged" not in clean_text
    assert "however no costs" not in clean_text

    # 3. Substantive pre-decision facts and arguments must be preserved
    assert "indian oil corporation" in clean_text.lower()
    assert "licence fee" in clean_text.lower()
    assert len(clean_text) >= 30000, f"Expected substantial pre-decision text, got {len(clean_text)}"


def test_vulnerability_2_ocr_concatenations_santosh_kumar(sanitizer, source_cases):
    """
    Case 2: OIL-AHC-UPHC020000012005 (State of U.P. v. Santosh Kumar).
    Vulnerability: OCR-concatenated words 'toappeal' and 'appealalso does not survive and the same stands dismissed'.
    Must truncate operative dismissal section and eliminate residual leakage.
    """
    case = source_cases.get("OIL-AHC-UPHC020000012005")
    assert case is not None
    raw_text = case["judgmentText"]

    clean_text, meta = sanitizer.sanitize_judgment_text(raw_text)

    # 1. Must truncate at operative transition
    assert meta["truncated_operative_section"] is True
    assert meta["sanitized_length"] < meta["original_length"]

    # 2. Conjoined words and operative order must NOT appear
    assert "appealalso" not in clean_text
    assert "does not survive and the same stands dismissed" not in clean_text
    assert "application for leave toappeal lacks merit" not in clean_text

    # 3. Substantive evidentiary analysis must be preserved
    assert "Santosh Kumar" in clean_text or "accused" in clean_text.lower()
    assert "trial court" in clean_text.lower()
    assert len(clean_text) >= 18000, f"Expected substantial text, got {len(clean_text)}"


def test_vulnerability_3_anticipatory_outcome_atul_shukla(sanitizer, source_cases):
    """
    Case 3: OIL-AHC-UPHC020481512022 (Atul Kumar Shukla v. State of U.P.).
    Vulnerability: Anticipatory outcome phrase 'the instant writ petition also deserves to be allowed'
    followed by 'Consequently, the Writ Petition is allowed...'.
    Must truncate at anticipatory transition and scrub decretal orders.
    """
    case = source_cases.get("OIL-AHC-UPHC020481512022")
    assert case is not None
    raw_text = case["judgmentText"]

    clean_text, meta = sanitizer.sanitize_judgment_text(raw_text)

    # 1. Must truncate at anticipatory transition
    assert meta["truncated_operative_section"] is True

    # 2. Anticipatory statement and final operative decree must NOT appear
    assert "deserves to be allowed" not in clean_text
    assert "Consequently, the Writ Petition is allowed" not in clean_text
    assert "Writ Petition is allowed" not in clean_text
    assert "within a period of four weeks" not in clean_text

    # 3. Factual core (petitioner's wife passed away, assistant teacher, gratuity claim) must be preserved
    assert "Atul Kumar Shukla" in clean_text
    assert "Assistant Teacher" in clean_text
    assert "gratuity" in clean_text.lower()
    assert len(clean_text) >= 1500


def test_vulnerability_4_decretal_tribunal_finding_icici_lombard(sanitizer, source_cases):
    """
    Case 4: OIL-DHC-DLHC010110302013 (ICICI Lombard GIC Ltd v. Subhash & Ors.).
    Vulnerability: Decretal reversal 'Thus, the appeal is allowed' and
    'The negative finding recorded by the Tribunal in the impugned judgment denying recovery rights to the insurance company is set aside'.
    Must truncate at decretal transition and scrub reversal phrasing.
    """
    case = source_cases.get("OIL-DHC-DLHC010110302013")
    assert case is not None
    raw_text = case["judgmentText"]

    clean_text, meta = sanitizer.sanitize_judgment_text(raw_text)

    # 1. Must truncate at decretal transition
    assert meta["truncated_operative_section"] is True

    # 2. Decretal holding and Tribunal reversal must NOT appear
    assert "Thus, the appeal is allowed" not in clean_text
    assert "appeal is allowed" not in clean_text
    assert "negative finding recorded by the Tribunal" not in clean_text
    assert "denying recovery rights to the insurance company is set aside" not in clean_text

    # 3. Substantive motor accident case law (Sohan Lal Passi, Kamla, Lehru) must be preserved
    assert "icici lombard" in clean_text.lower()
    assert "Sohan Lal Passi" in clean_text
    assert len(clean_text) >= 8000


# ==============================================================================
# 2. Historical & Cross-Batch Sanitization Integrity
# ==============================================================================

def test_batch_1_6_candidates_sanitization(sanitizer, source_cases, staged_batch_1_6):
    """Verify that all 8 Batch 1.6 candidates have zero evidence quotation leakage."""
    for record in staged_batch_1_6["records"]:
        cid = record["case_id"]
        raw = source_cases.get(cid)
        assert raw is not None, f"Candidate {cid} not in source cases!"

        clean_text, meta = sanitizer.sanitize_judgment_text(raw["judgmentText"])
        ev = record["evidence"]

        # Exact evidence quotation must never be in clean text
        assert ev not in clean_text, f"Evidence leaked for candidate {cid}!"
        # Pre-decision text must remain non-empty and substantial
        assert meta["sanitized_length"] > 0
        assert meta["sanitized_length"] <= meta["original_length"]


def test_varun_dutta_batch_1_5_replacement_sanitization(sanitizer, source_cases):
    """Verify OIL-DHC-DLHC011166952013 (Varun Dutta v. State & Anr) from Batch 1.5."""
    case = source_cases.get("OIL-DHC-DLHC011166952013")
    assert case is not None
    raw_text = case["judgmentText"]

    clean_text, meta = sanitizer.sanitize_judgment_text(raw_text)
    assert meta["truncated_operative_section"] is True
    assert "petition is dismissed" not in clean_text.lower()
    assert "varun dutta" in clean_text.lower()


# ==============================================================================
# 3. Disposition Class & Proceeding Type Symmetry
# ==============================================================================

def test_allowed_and_dismissed_disposition_symmetry(sanitizer):
    """Verify sanitizer handles both allowed and dismissed outcomes symmetrically."""
    text_allowed = (
        "The respondent employer terminated the workman without inquiry. "
        "The Labour Court upheld the termination erroneously. "
        "Heard both sides on Section 25F of the Industrial Disputes Act.\n\n"
        "ORDER:\n"
        "The writ petition is hereby allowed and the award of the Labour Court is quashed."
    )
    clean_allowed, meta_allowed = sanitizer.sanitize_judgment_text(text_allowed)
    assert "writ petition is hereby allowed" not in clean_allowed.lower()
    assert "quashed" not in clean_allowed.lower()
    assert "Industrial Disputes Act" in clean_allowed

    text_dismissed = (
        "The petitioner assails the order of forfeiture of property under SAFEMA. "
        "The competent authority issued notice and recorded adequate reasons. "
        "Heard learned counsel on the nexus between the detenu and the acquired assets.\n\n"
        "FINAL ORDER:\n"
        "The appeal is accordingly dismissed and the impugned order is confirmed."
    )
    clean_dismissed, meta_dismissed = sanitizer.sanitize_judgment_text(text_dismissed)
    assert "appeal is accordingly dismissed" not in clean_dismissed.lower()
    assert "impugned order is confirmed" not in clean_dismissed.lower()
    assert "competent authority" in clean_dismissed


def test_civil_and_criminal_proceedings_coverage(sanitizer):
    """Verify coverage of both civil decretal and criminal penal/bail adjudications."""
    criminal_bail_text = (
        "The applicant is in custody since 10.01.2023 in Crime No. 45/2023 under Section 376 IPC. "
        "The prosecutrix did not support the prosecution story in her statement under Section 164 CrPC. "
        "Learned A.G.A. opposed the bail prayer.\n\n"
        "ORDER:\n"
        "Let the applicant be released on bail on furnishing a personal bond of Rs. 50,000/-."
    )
    clean_crim, meta_crim = sanitizer.sanitize_judgment_text(criminal_bail_text)
    assert "released on bail" not in clean_crim.lower()
    assert "furnishing a personal bond" not in clean_crim.lower()
    assert "Section 164 CrPC" in clean_crim

    civil_decree_text = (
        "The appellant instituted a suit for specific performance of agreement to sell. "
        "The trial court found readiness and willingness proved. "
        "The First Appellate Court reversed the finding arbitrarily.\n\n"
        "ORDER OF THE COURT:\n"
        "The appeal is allowed. The judgment and decree of the High Court is set aside and that of the trial court is restored."
    )
    clean_civ, meta_civ = sanitizer.sanitize_judgment_text(civil_decree_text)
    assert "appeal is allowed" not in clean_civ.lower()
    assert "decree of the high court is set aside" not in clean_civ.lower()
    assert "specific performance" in clean_civ


# ==============================================================================
# 4. False-Positive Protection: Narrative & Legal Reasoning Integrity
# ==============================================================================

def test_false_positive_protection_predecision_narratives(sanitizer):
    """
    Ensure citations of lower-court outcomes or counsel arguments in the factual narrative
    do NOT trigger premature truncation.
    """
    narrative = (
        "The appellant was prosecuted for murder. The trial court dismissed the application for discharge "
        "by order dated 15.03.2018. Subsequently, the High Court allowed the revision in part. "
        "Mr. Salve, learned Senior Counsel, argued that the learned Single Judge allowed the petition "
        "without considering the statutory exception under Section 300 IPC. "
        "In Ram Kumar v. State, this Court dismissed a similar appeal observing that circumstantial evidence "
        "must form a complete chain without lacunae. "
        "We have carefully examined the testimonies of PW-1 and PW-2 regarding the recovery of weapon.\n\n"
        "ORDER:\n"
        "For the reasons recorded above, this criminal appeal is hereby dismissed."
    )
    clean, meta = sanitizer.sanitize_judgment_text(narrative)

    # Historical lower court citations must be PRESERVED in the narrative
    assert "trial court dismissed the application for discharge" in clean
    assert "High Court allowed the revision in part" in clean
    assert "learned Single Judge allowed the petition" in clean
    assert "Ram Kumar v. State" in clean
    assert "PW-1 and PW-2" in clean

    # Only the concluding operative holding is removed
    assert "criminal appeal is hereby dismissed" not in clean.lower()


# ==============================================================================
# 5. Auxiliary Field Isolation in Pre-Decision Feature Extraction
# ==============================================================================

def test_auxiliary_fields_never_enter_training_features(sanitizer):
    """
    Verify extract_pre_decision_features strictly omits auxiliary annotation fields:
    evidence, human_notes, notes, review_notes, reviewer_reference, etc.
    """
    raw_case = {
        "id": "OIL-TEST-LEAKAGE-01",
        "caseTitle": "State of Maharashtra v. Suresh",
        "court": "Supreme Court of India",
        "judgmentDate": "2024-01-15",
        "category": "Criminal Law",
        "legalProvisions": ["Section 302 IPC", "Section 313 CrPC"],
        "judgmentText": (
            "The prosecution alleged circumstantial evidence against the accused. "
            "PW-3 testified regarding the last seen theory. Forensic reports were inconclusive.\n\n"
            "ORDER:\nThe appeal is dismissed and the conviction is affirmed."
        ),
        # Auxiliary / Forbidden fields that MUST NOT leak
        "evidence": "The appeal is dismissed and the conviction is affirmed.",
        "evidence_offset_start": 180,
        "evidence_offset_end": 235,
        "human_notes": "Reviewer confirmed acquittal affirmation; successful party is accused.",
        "notes": "Internal annotation note: clear merits dismissal.",
        "reviewer_reference": "SNR-LEGAL-NLP-01",
        "human_approved_label": "appeal_dismissed",
        "human_successful_party": "accused",
        "outcome": "Dismissed",
        "summary": "The Supreme Court dismissed the appeal affirming the conviction.",
    }

    features = sanitizer.extract_pre_decision_features(raw_case)

    # 1. Output dict keys check
    allowed_keys = {
        "case_id",
        "case_title",
        "court",
        "decision_date",
        "category",
        "legal_provisions",
        "sanitized_pre_decision_text",
        "factual_composite",
        "sanitization_diagnostics",
    }
    for k in features.keys():
        assert k in allowed_keys, f"Unexpected key in pre-decision features: {k}"

    # 2. Strict content inspection: Forbidden field values must NEVER appear in features
    composite = features["factual_composite"]
    pre_text = features["sanitized_pre_decision_text"]

    for forbidden_val in [
        raw_case["evidence"],
        raw_case["human_notes"],
        raw_case["notes"],
        raw_case["reviewer_reference"],
        raw_case["summary"],
    ]:
        assert forbidden_val not in composite, f"Forbidden field value leaked into factual_composite: {forbidden_val}"
        assert forbidden_val not in pre_text, f"Forbidden field value leaked into sanitized_pre_decision_text: {forbidden_val}"

    # 3. Operative order must be absent
    assert "appeal is dismissed" not in pre_text.lower()
    assert "conviction is affirmed" not in pre_text.lower()


# ==============================================================================
# Feature 4.17.1 — Batch 1.7 Sanitizer Hardening Regression Suite
# ==============================================================================

def test_feature_4_17_1_candidate_1_south_mcd(sanitizer, source_cases):
    """
    Candidate 1: OIL-DHC-DLHC012541422014 (South MCD v. Gakko Bunka Education Society).
    Verifies detection of 'For the above reasons' and stripping of appeal dismissal,
    cost award, and refund directions to the respondent.
    """
    case = source_cases.get("OIL-DHC-DLHC012541422014")
    assert case is not None
    raw_text = case["judgmentText"]

    clean_text, meta = sanitizer.sanitize_judgment_text(raw_text)

    # 1. Truncated at operative section boundary
    assert meta["truncated_operative_section"] is True
    assert meta["sanitized_length"] < meta["original_length"]

    # 2. Operative holding and party directions must NOT survive
    assert "For the above reasons" not in clean_text
    assert "the appeal is dismissed" not in clean_text.lower()
    assert "appellant shall pay costs" not in clean_text.lower()
    assert "quantified @ rs.50,000" not in clean_text.lower()
    assert "amount shall also be refunded" not in clean_text.lower()

    # 3. Substantive pre-decision reasoning and facts preserved
    assert "embassy of japan" in clean_text.lower()
    assert "far charges" in clean_text.lower()
    assert "notification dated 17.07.2012" in clean_text.lower()
    assert len(clean_text) >= 5500


def test_feature_4_17_1_candidate_5_brijesh_kumar_shukla(sanitizer, source_cases):
    """
    Candidate 5: OIL-DHC-DLHC011406392016 (HC Brijesh Kumar Shukla v. Union of India).
    Verifies detection and truncation of paragraph 4 'In view of the above, the impugned Movement order...
    is quashed and set aside', fresh movement order directions, and paragraph 5 compound disposal.
    """
    case = source_cases.get("OIL-DHC-DLHC011406392016")
    assert case is not None
    raw_text = case["judgmentText"]

    clean_text, meta = sanitizer.sanitize_judgment_text(raw_text)

    # 1. Truncated at paragraph 4 boundary
    assert meta["truncated_operative_section"] is True
    assert meta["sanitized_length"] < meta["original_length"]

    # 2. Operative directions must NOT survive
    assert "impugned Movement order" not in clean_text
    assert "quashed and set aside" not in clean_text.lower()
    assert "freshmovement order" not in clean_text.lower()
    assert "posting the petitioner to 32 battalion" not in clean_text.lower()
    assert "petition and the application are disposed of" not in clean_text.lower()

    # 3. Substantive pre-decision factual narrative preserved
    assert "head constable" in clean_text.lower()
    assert "mentally retarded son" in clean_text.lower()
    assert "medical facilities" in clean_text.lower()
    assert len(clean_text) >= 1400


def test_feature_4_17_1_candidate_2_ramkarandas(sanitizer, source_cases):
    """Candidate 2: OIL-SC-1964_INSC_260 — Zero leakage confirmation."""
    case = source_cases.get("OIL-SC-1964_INSC_260")
    assert case is not None
    clean_text, meta = sanitizer.sanitize_judgment_text(case["judgmentText"])
    assert meta["truncated_operative_section"] is True
    assert "in the result this appeal fails" not in clean_text.lower()
    assert "dismissed with costs" not in clean_text.lower()
    assert len(clean_text) >= 17000


def test_feature_4_17_1_candidate_3_chockalinga(sanitizer, source_cases):
    """Candidate 3: OIL-SC-1968_INSC_212 — Zero leakage confirmation."""
    case = source_cases.get("OIL-SC-1968_INSC_212")
    assert case is not None
    clean_text, meta = sanitizer.sanitize_judgment_text(case["judgmentText"])
    assert meta["truncated_operative_section"] is True
    assert "in the result this appeal fails" not in clean_text.lower()
    assert "appeal dismissed" not in clean_text.lower()
    assert len(clean_text) >= 16000


def test_feature_4_17_1_candidate_4_chigurupati(sanitizer, source_cases):
    """Candidate 4: OIL-SC-1972_INSC_24 — Zero leakage confirmation."""
    case = source_cases.get("OIL-SC-1972_INSC_24")
    assert case is not None
    clean_text, meta = sanitizer.sanitize_judgment_text(case["judgmentText"])
    assert meta["truncated_operative_section"] is True
    assert "in the result this appeal fails" not in clean_text.lower()
    assert "appeal dismissed" not in clean_text.lower()
    assert len(clean_text) >= 29000


def test_feature_4_17_1_cost_and_refund_directions_scrubbing(sanitizer):
    """Verify cost awards and refund directions are scrubbed even in unheaded text."""
    synthetic_tail = (
        "The arguments of the appellant were considered on merits.\n\n"
        "The appellant shall pay costs quantified @ Rs.75,000/- to the respondent within six weeks.\n"
        "The amount shall also be refunded with 6% interest."
    )
    clean_text, meta = sanitizer.sanitize_judgment_text(synthetic_tail)
    assert "appellant shall pay costs" not in clean_text.lower()
    assert "quantified @ rs.75,000" not in clean_text.lower()
    assert "amount shall also be refunded" not in clean_text.lower()
    assert "[DISPOSITION_REDACTED]" in clean_text


def test_feature_4_17_1_administrative_order_quashing_scrubbing(sanitizer):
    """Verify administrative/transfer orders and fresh order mandates are scrubbed."""
    synthetic_tail = (
        "The petitioner presented evidence of arbitrary administrative action.\n\n"
        "The impugned transfer order dated 15.03.2021 is hereby quashed and set aside.\n"
        "The respondents shall issue a fresh posting order within two weeks.\n"
        "The petition and the application are disposed of."
    )
    clean_text, meta = sanitizer.sanitize_judgment_text(synthetic_tail)
    assert "impugned transfer order" not in clean_text.lower()
    assert "quashed and set aside" not in clean_text.lower()
    assert "fresh posting order" not in clean_text.lower()
    assert "petition and the application are disposed of" not in clean_text.lower()


def test_feature_4_17_1_pre_decision_legal_vocabulary_preserved(sanitizer):
    """
    Verify false-positive protection: Legitimate discussion of prior appeals,
    historical dismissals, statutory wording, and legal arguments are NOT aggressively removed.
    """
    pre_decision_text = (
        "The trial court previously dismissed the suit for default, which was later set aside. "
        "The appellant argued that under Section 96 CPC an appeal lies from every original decree. "
        "The respondent contended that the statutory appeal was barred by limitation. "
        "We have examined the precedent where a similar petition was allowed by the High Court."
    )
    clean_text, meta = sanitizer.sanitize_judgment_text(pre_decision_text)
    # The factual narrative and legal arguments must remain intact
    assert "Section 96 CPC an appeal lies" in clean_text
    assert "statutory appeal was barred by limitation" in clean_text
    assert "petition was allowed by the High Court" in clean_text
    assert len(clean_text) >= len(pre_decision_text) * 0.95

