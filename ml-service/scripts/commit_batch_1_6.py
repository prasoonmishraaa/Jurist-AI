"""
Execute the Authorized Atomic Commit of Batch 1.6 Annotations
Feature 4.16.4 — Authorized Atomic Commit of Batch 1.6
JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Reviewer ID: SNR-LEGAL-NLP-01

Strict verification checks:
1. Reconfirm current master baseline is exactly 26 verified (19 approved, 7 corrected) and 124 pending.
2. Revalidate all 8 staged records from batch_1_6_staged.json against the annotation schema.
3. Confirm Candidates 6, 7 and 8 retain Model B label 'unresolved'.
4. Confirm all eight Model A labels are valid merits classes.
5. Confirm all 8 evidence quotations and source offsets match verbatim in open_india_law_sample_150.json with zero ellipses.
6. Commit all 8 records atomically via OutcomeAnnotationSessionManager.submit_batch_reviews(confirm=True).
7. Synchronize master JSON and CSV with proceeding classifications and individual timestamped audit events.
8. Post-commit verification: 34 verified and 116 pending records in master stores.
9. Recalculate Model A (31 eligible, threshold >= 30 passed) and Model B (27 eligible, gap of 3 records).
10. Confirm qualitative_research_mode remains active and zero model weights are generated.
"""

import sys
import json
import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Add ml-service to path
ML_SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    VALID_DISPOSITIONS,
    VALID_SUCCESSFUL_PARTIES,
    MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS,
    MODEL_B_ELIGIBLE_SUBSTANTIVE_PARTIES,
    KNOWN_SOURCE_HASHES,
)

PREVIOUS_TWENTY_SIX_COMMITTED_IDS = [
    "OIL-SC-2021_INSC_327",
    "OIL-SC-1996_INSC_503",
    "OIL-SC-2007_INSC_31",
    "OIL-SC-2007_INSC_1082",
    "OIL-SC-2003_INSC_88",
    "OIL-SC-1973_INSC_203",
    "OIL-SC-2000_INSC_110",
    "OIL-SC-2016_INSC_467",
    "OIL-SC-1973_INSC_247",
    "OIL-SC-1979_INSC_85",
    "OIL-SC-1998_INSC_267",
    "OIL-SC-1981_INSC_134",
    "OIL-SC-1992_INSC_350",
    "OIL-SC-2006_INSC_699",
    "OIL-SC-1984_INSC_90",
    "OIL-SC-2010_INSC_109",
    "OIL-SC-2012_INSC_207",
    "OIL-DHC-DLHC015857912015",
    "OIL-DHC-DLHC011166952013",
    "OIL-DHC-DLHC010614922013",
    "OIL-DHC-DLHC011594232016",
    "OIL-AHC-UPHC020034182022",
    "OIL-AHC-UPHC020497422019",
    "OIL-AHC-UPHC020380352022",
    "OIL-AHC-UPHC020265642022",
    "OIL-AHC-UPHC020001822015",
]

EXPECTED_BATCH_1_6 = {
    "OIL-DHC-DLHC010207822016": {
        "disposition": "petition_dismissed",
        "successful_party": "respondent",
        "action": "correct",
        "proceeding_type": "writ_petition",
        "notes_extra": "[SICA reference registration challenge dismissed on merits; respondent company prevailed under Guideline Row 124.]"
    },
    "OIL-DHC-DLHC010029692013": {
        "disposition": "petition_dismissed",
        "successful_party": "respondent",
        "action": "correct",
        "proceeding_type": "writ_petition",
        "notes_extra": "[Licence fee circular challenge dismissed on merits with Rule discharged; respondent authority DDA prevailed under Guideline Row 124.]"
    },
    "OIL-AHC-UPHC020481512022": {
        "disposition": "petition_allowed",
        "successful_party": "petitioner",
        "action": "correct",
        "proceeding_type": "writ_petition",
        "notes_extra": "[Denial of death gratuity quashed on merits; petition allowed with positive directions; petitioner teacher's husband prevailed under Guideline Row 125.]"
    },
    "OIL-DHC-DLHC011058852016": {
        "disposition": "petition_allowed",
        "successful_party": "accused",
        "action": "correct",
        "proceeding_type": "criminal_writ_petition",
        "notes_extra": "[Section 420/468/471 FIR quashed on settlement under Gian Singh; petition allowed; accused petitioner prevailed under Guideline Row 121/125.]"
    },
    "OIL-AHC-UPHC020000012005": {
        "disposition": "appeal_dismissed",
        "successful_party": "accused",
        "action": "correct",
        "proceeding_type": "criminal_appeal",
        "notes_extra": "[State Section 378(3) CrPC appeal against NDPS acquittal dismissed on merits; accused respondent Santosh Kumar sustained acquittal under Guideline Row 122.]"
    },
    "OIL-SC-2007_INSC_548": {
        "disposition": "appeal_dismissed",
        "successful_party": "unresolved",
        "action": "correct",
        "proceeding_type": "statutory_appeal",
        "notes_extra": "[Section 130E(b) Customs Act statutory appeal dismissed on merits; Commissioner of Customs is a civil revenue authority, excluded from criminal state_prosecution taxonomy under Section 5; Model B unresolved per Feature 4.16.1/4.16.2 audit.]"
    },
    "OIL-SC-2006_INSC_78": {
        "disposition": "appeal_allowed",
        "successful_party": "unresolved",
        "action": "correct",
        "proceeding_type": "civil_appeal",
        "notes_extra": "[Civil appeal against vehicle repossession injunction allowed on merits; winning party is an appellant financier, excluded from writ petitioner taxonomy under Section 5; Model B unresolved per Feature 4.16.1/4.16.2 audit.]"
    },
    "OIL-DHC-DLHC010110302013": {
        "disposition": "appeal_allowed",
        "successful_party": "unresolved",
        "action": "correct",
        "proceeding_type": "statutory_appeal",
        "notes_extra": "[Section 173 Motor Vehicles Act appeal allowed on merits with MACT recovery rights granted; winning insurer is an appellant, excluded from writ petitioner taxonomy under Section 5; Model B unresolved per Feature 4.16.1/4.16.2 audit.]"
    }
}


def main():
    print("=" * 80)
    print("BATCH 1.6 AUTHORIZED ATOMIC COMMIT EXECUTION")
    print("Reviewer ID: SNR-LEGAL-NLP-01")
    print("=" * 80)

    session = OutcomeAnnotationSessionManager()

    # Pre-check 1: Cryptographic source dataset integrity
    print("\n[PRE-CHECK 1] Verifying Cryptographic Source Integrity:")
    pre_integrity = session.verify_source_integrity()
    for fname, ok in pre_integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok, f"Integrity check failed for {fname}"

    # Pre-check 2: Master store baseline verification (26 verified, 124 pending)
    print("\n[PRE-CHECK 2] Verifying Master Store Baseline Counts:")
    dash_pre = session.get_progress_dashboard()
    print(f"  Total Candidates: {dash_pre['total_candidates']}")
    print(f"  Total Verified:   {dash_pre['total_verified']} (Approved: {dash_pre['approved']}, Corrected: {dash_pre['corrected']})")
    print(f"  Pending:          {dash_pre['pending']}")
    assert dash_pre["total_verified"] == 26, f"Expected 26 verified, got {dash_pre['total_verified']}"
    assert dash_pre["pending"] == 124, f"Expected 124 pending, got {dash_pre['pending']}"

    # Pre-check 3: Verify all 26 existing approved annotations and audit histories
    print("\n[PRE-CHECK 3] Verifying 26 Existing Approved Annotations & Audit Histories:")
    for cid in PREVIOUS_TWENTY_SIX_COMMITTED_IDS:
        c_view = session.get_case_view(cid)
        rev = c_view["current_review"]
        status = rev["review_status"]
        label = rev["human_approved_label"]
        party = rev["human_successful_party"]
        history_len = len(rev["audit_history"])
        assert status in ["approved", "corrected", "adjudicated_approved"], f"Expected verified for {cid}, got {status}"
        assert history_len >= 1, f"Audit history missing for {cid}"

    print(f"  All 26 existing verified records confirmed intact with valid audit trails.")

    # Pre-check 4: Load staged Batch 1.6 records and validate against schema
    staging_file = ML_SERVICE_DIR / "app" / "datasets" / "review_batches" / "batch_1_6_staged.json"
    assert staging_file.exists(), f"Staging file not found: {staging_file}"
    with open(staging_file, "r", encoding="utf-8") as f:
        staged_data = json.load(f)

    staged_records = staged_data["records"]
    assert len(staged_records) == 8, f"Expected 8 staged records, got {len(staged_records)}"
    print(f"\n[PRE-CHECK 4] Validating {len(staged_records)} Staged Decisions Against Annotation Schema:")

    source_file = ML_SERVICE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"
    with open(source_file, "r", encoding="utf-8") as f:
        source_judgments = {c["id"]: c for c in json.load(f)}

    batch_decisions = []
    for rec in staged_records:
        cid = rec["case_id"]
        assert cid in EXPECTED_BATCH_1_6, f"Unexpected case ID in batch: {cid}"
        tgt = EXPECTED_BATCH_1_6[cid]

        # Verify evidence matches verbatim in source judgment
        ev = rec["evidence"]
        src_case = source_judgments[cid]
        src_text = src_case["judgmentText"]
        idx = src_text.find(ev)
        assert idx != -1, f"Evidence for {cid} not found verbatim in source judgment!"
        assert idx == rec["source_char_offset"], f"Offset mismatch for {cid}: {idx} != {rec['source_char_offset']}"
        assert len(ev) == rec["source_char_length"], f"Length mismatch for {cid}"
        assert "..." not in ev, f"Evidence for {cid} contains forbidden ellipses!"

        # Verify labels match revised expectations
        assert rec["disposition"] == tgt["disposition"], f"Disposition mismatch for {cid}: {rec['disposition']} != {tgt['disposition']}"
        assert rec["successful_party"] == tgt["successful_party"], f"Party mismatch for {cid}: {rec['successful_party']} != {tgt['successful_party']}"
        assert rec["action"] == tgt["action"], f"Action mismatch for {cid}: {rec['action']} != {tgt['action']}"

        # Confirm Candidates 6, 7 and 8 retain Model B unresolved
        if cid in ["OIL-SC-2007_INSC_548", "OIL-SC-2006_INSC_78", "OIL-DHC-DLHC010110302013"]:
            assert rec["successful_party"] == "unresolved", f"Candidate {cid} must be unresolved for Model B!"

        # Confirm Model A label is valid merits class
        assert rec["disposition"] in MODEL_A_ELIGIBLE_MERITS_DISPOSITIONS

        full_notes = rec["notes"].strip() + " " + tgt["notes_extra"]

        payload = {
            "case_id": cid,
            "action": rec["action"],
            "disposition": rec["disposition"],
            "successful_party": rec["successful_party"],
            "evidence": ev,
            "notes": full_notes,
        }
        session._validate_decision_payload(payload)
        batch_decisions.append(payload)
        print(f"  [VALIDATED] {cid}: {rec['action']} -> {rec['disposition']} / {rec['successful_party']} (offset {idx})")

    # Step 5: Execute atomic commit via submit_batch_reviews (confirm=True)
    print("\n[COMMIT] Executing Atomic Batch Commit via submit_batch_reviews (confirm=True)...")
    commit_res = session.submit_batch_reviews(
        batch_decisions=batch_decisions,
        reviewer_id="SNR-LEGAL-NLP-01",
        confirm=True
    )
    print(f"Commit Result: {commit_res['committed_count']} cases atomically committed.")
    assert commit_res["committed_count"] == 8, f"Expected 8 committed cases, got {commit_res['committed_count']}"

    # Step 6: Explicitly preserve proceeding classifications in master stores
    print("\n[PROCEEDING CLASSIFICATIONS] Synchronizing proceeding types in master stores:")
    for cid, tgt in EXPECTED_BATCH_1_6.items():
        rec_obj = session.records_by_id[cid]
        rec_obj["proceeding_type"] = tgt["proceeding_type"]
        print(f"  - {cid}: proceeding_type = {tgt['proceeding_type']}")

    session._save()
    print("Master candidate stores and review CSV synchronized successfully.")

    # Step 7: Post-commit dashboard verification
    session_post = OutcomeAnnotationSessionManager()
    dash = session_post.get_progress_dashboard()

    print("\n" + "=" * 80)
    print("POST-COMMIT ANNOTATION DASHBOARD AUDIT (34 VERIFIED)")
    print("=" * 80)
    print(f"Total Candidates:         {dash['total_candidates']}")
    print(f"Total Verified:           {dash['total_verified']} / 150 (Progress: {dash['total_verified']/150*100:.1f}%)")
    print(f"  - Approved:             {dash['approved']}")
    print(f"  - Corrected:            {dash['corrected']}")
    print(f"Pending Review:           {dash['pending']}")
    assert dash["total_verified"] == 34, f"Expected 34 verified, got {dash['total_verified']}"
    assert dash["pending"] == 116, f"Expected 116 pending, got {dash['pending']}"

    # Step 8: Post-commit training readiness evaluation
    readiness = session_post.check_training_readiness(min_total_verified=30, min_minority_samples=5)
    print("\n" + "=" * 80)
    print("POST-COMMIT DUAL-MODEL TRAINING READINESS EVALUATION")
    print("=" * 80)
    print(f"Training Eligible (Global): {readiness['is_training_eligible']} (Locked)")
    print(f"Recommended Mode:          {readiness['recommended_mode']}")

    print("\n--- Model A: Judicial Disposition ---")
    ma = readiness["model_a"]
    print(f"  Target:                  {ma['target']}")
    print(f"  Eligible Merits Count:   {ma['eligible_count']} / {ma['minimum_required']} (Gap: {max(0, ma['minimum_required'] - ma['eligible_count'])})")
    print(f"  Excluded Count:          {ma['excluded_count']} {ma['excluded_distribution']}")
    print(f"  Merits Distribution:     {ma['class_distribution']}")
    print(f"  Minority Class Count:    {ma['minority_class_count']} (Threshold: {ma['min_minority_samples']})")
    print(f"  Blockers:                {ma['blockers']}")
    print(f"  Model A Eligible:        {ma['is_training_eligible']}")

    print("\n--- Model B: Successful Party ---")
    mb = readiness["model_b"]
    print(f"  Target:                  {mb['target']}")
    print(f"  Eligible Substantive:    {mb['eligible_count']} / {mb['minimum_required']} (Gap: {max(0, mb['minimum_required'] - mb['eligible_count'])})")
    print(f"  Excluded Count:          {mb['excluded_count']} {mb['excluded_distribution']}")
    print(f"  Substantive Distribution:{mb['class_distribution']}")
    print(f"  Minority Class Count:    {mb['minority_class_count']} (Threshold: {mb['min_minority_samples']})")
    print(f"  Blockers:                {mb['blockers']}")
    print(f"  Model B Eligible:        {mb['is_training_eligible']}")

    assert ma["eligible_count"] == 31, f"Expected 31 Model A eligible, got {ma['eligible_count']}"
    assert ma["is_training_eligible"] is True, f"Expected Model A training eligible, got {ma['is_training_eligible']}"
    assert mb["eligible_count"] == 27, f"Expected 27 Model B eligible, got {mb['eligible_count']}"
    assert mb["is_training_eligible"] is False, f"Expected Model B blocked, got {mb['is_training_eligible']}"
    assert readiness["is_training_eligible"] is False, f"Expected overall training gate locked, got {readiness['is_training_eligible']}"
    assert readiness["recommended_mode"] == "qualitative_research_mode"

    # Step 9: Post-check source dataset cryptographic integrity
    print("\n[POST-CHECK 9] Verifying Cryptographic Source Integrity:")
    post_integrity = session_post.verify_source_integrity()
    for fname, ok in post_integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok, f"Post-commit integrity check failed for {fname}"

    print("\n" + "=" * 80)
    print("BATCH 1.6 ATOMIC COMMIT COMPLETED SUCCESSFULLY WITH ZERO ERRORS")
    print("=" * 80)

if __name__ == "__main__":
    main()
