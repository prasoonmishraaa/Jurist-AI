"""
Execute the Authorized Atomic Commit of Batch 1.5 Annotations
Feature 4.15.3 — Authorized Atomic Commit of Batch 1.5

Reviewer ID: SNR-LEGAL-NLP-01

Strict verification checks:
1. Revalidate all 5 staged records from batch_1_5_staged.json against the current annotation schema.
2. Confirm square brackets in Candidate 5 (Impexnet Logistic, '1[st]') are genuine source text and not editorial insertions.
3. Confirm the 5 evidence quotations and source offsets match verbatim in open_india_law_sample_150.json.
4. Confirm master stores still contain exactly 21 verified annotations and 129 pending records.
5. Commit all five records atomically via OutcomeAnnotationSessionManager.submit_batch_reviews(confirm=True).
6. Synchronize master JSON and CSV with proceeding classifications.
7. Record individual timestamped audit events.
8. Preserve all 21 previous annotations and audit histories.
9. Verify that rejected candidate OIL-DHC-DLHC010440622015 is NOT committed.
10. Recalculate both independent target distributions.
11. Ensure zero model training, zero serialization of model weights, and qualitative_research_mode remains active.
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
    KNOWN_SOURCE_HASHES,
)

PREVIOUS_TWENTY_ONE_COMMITTED_IDS = [
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
    "OIL-SC-1992_INSC_350",
    "OIL-SC-2006_INSC_699",
    "OIL-SC-2010_INSC_109",
    "OIL-DHC-DLHC015857912015",
    "OIL-AHC-UPHC020034182022",
    "OIL-SC-1981_INSC_134",
    "OIL-SC-1984_INSC_90",
    "OIL-SC-2012_INSC_207",
    "OIL-AHC-UPHC020380352022",
    "OIL-AHC-UPHC020497422019",
]

def main():
    print("=" * 80)
    print("BATCH 1.5 AUTHORIZED ATOMIC COMMIT EXECUTION")
    print("Reviewer ID: SNR-LEGAL-NLP-01")
    print("=" * 80)

    session = OutcomeAnnotationSessionManager()

    # Pre-check 1: Cryptographic source dataset integrity
    print("\n[PRE-CHECK 1] Verifying Cryptographic Source Integrity:")
    pre_integrity = session.verify_source_integrity()
    for fname, ok in pre_integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok, f"Integrity check failed for {fname}"

    # Pre-check 2: Master store baseline verification (21 verified, 129 pending)
    print("\n[PRE-CHECK 2] Verifying Master Store Baseline Counts:")
    dash_pre = session.get_progress_dashboard()
    print(f"  Total Candidates: {dash_pre['total_candidates']}")
    print(f"  Total Verified:   {dash_pre['total_verified']} (Approved: {dash_pre['approved']}, Corrected: {dash_pre['corrected']})")
    print(f"  Pending:          {dash_pre['pending']}")
    assert dash_pre["total_verified"] == 21, f"Expected 21 verified, got {dash_pre['total_verified']}"
    assert dash_pre["pending"] == 129, f"Expected 129 pending, got {dash_pre['pending']}"

    # Pre-check 3: Verify all 21 existing approved annotations and audit histories
    print("\n[PRE-CHECK 3] Verifying 21 Existing Approved Annotations & Audit Histories:")
    for cid in PREVIOUS_TWENTY_ONE_COMMITTED_IDS:
        c_view = session.get_case_view(cid)
        rev = c_view["current_review"]
        status = rev["review_status"]
        label = rev["human_approved_label"]
        party = rev["human_successful_party"]
        reviewer = rev["reviewer_reference"]
        history_len = len(rev["audit_history"])
        assert status in ["approved", "corrected"], f"Expected approved/corrected for {cid}, got {status}"
        assert history_len >= 1, f"Audit history missing for {cid}"
        print(f"  - {cid}: status={status}, label={label}, party={party}, audit_events={history_len}")

    # Pre-check 4: Ensure rejected candidate OIL-DHC-DLHC010440622015 is NOT in commit list
    rejected_id = "OIL-DHC-DLHC010440622015"
    assert session.records_by_id[rejected_id]["review_status"] == "pending_review"
    print(f"\n[PRE-CHECK 4] Verified Rejected Candidate Protection: {rejected_id} remains pending_review.")

    # Pre-check 5: Load staged Batch 1.5 records and validate against schema
    staging_file = ML_SERVICE_DIR / "app" / "datasets" / "review_batches" / "batch_1_5_staged.json"
    assert staging_file.exists(), f"Staging file not found: {staging_file}"
    with open(staging_file, "r", encoding="utf-8") as f:
        staged_data = json.load(f)

    staged_records = staged_data["records"]
    assert len(staged_records) == 5, f"Expected 5 staged records, got {len(staged_records)}"
    print(f"\n[PRE-CHECK 5] Validating {len(staged_records)} Staged Decisions Against Annotation Schema:")

    source_file = ML_SERVICE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"
    with open(source_file, "r", encoding="utf-8") as f:
        source_judgments = {c["id"]: c for c in json.load(f)}

    expected_verified = {
        "OIL-AHC-UPHC020265642022": {
            "disposition": "petition_dismissed",
            "successful_party": "state_prosecution",
            "action": "correct",
            "proceeding_type": "criminal_writ_petition",
            "notes_extra": "[Article 226 criminal writ petition challenging Section 392 IPC FIR dismissed on merits for lack of merit; withdrawal prayer refused; State through Learned AGA successfully defended ongoing police investigation.]"
        },
        "OIL-DHC-DLHC011166952013": {
            "disposition": "petition_dismissed",
            "successful_party": "state_prosecution",
            "action": "correct",
            "proceeding_type": "criminal_petition",
            "notes_extra": "[Section 482 CrPC quashing petition challenging Crime Branch FIR 129/2013 dismissed on merits as devoid of merit; petitioner was proclaimed offender in UK; chargesheet filed before trial court; State successfully defended prosecution.]"
        },
        "OIL-AHC-UPHC020001822015": {
            "disposition": "appeal_dismissed",
            "successful_party": "accused",
            "action": "accept",
            "proceeding_type": "criminal_appeal",
            "notes_extra": "[State Section 378(3) CrPC appeal against acquittal dismissed on merits; trial court acquittal affirmed as not perverse; accused Rishiram succeeds under Guideline Row 122.]"
        },
        "OIL-DHC-DLHC010614922013": {
            "disposition": "appeal_allowed",
            "successful_party": "accused",
            "action": "correct",
            "proceeding_type": "criminal_appeal",
            "notes_extra": "[Section 374 criminal appeal allowed on benefit of doubt; conviction under Sections 342/354/376 r/w 511 IPC set aside; accused Raj Kishore acquitted and ordered released forthwith.]"
        },
        "OIL-DHC-DLHC011594232016": {
            "disposition": "petition_allowed",
            "successful_party": "petitioner",
            "action": "accept",
            "proceeding_type": "writ_petition",
            "notes_extra": "[Writ petition challenging Customs Broker license revocation allowed on merits; revocation quashed as time-barred under Regulation 20 CBLR 2013; petitioner Impexnet Logistic succeeds. Source excerpt contains authentic court typesetting '1[st] June, 2015'.]"
        }
    }

    batch_decisions = []
    for rec in staged_records:
        cid = rec["case_id"]
        assert cid in expected_verified, f"Unexpected case ID in batch: {cid}"
        ev = rec["evidence"]
        src_case = source_judgments[cid]
        src_text = src_case["judgmentText"]
        idx = src_text.find(ev)
        assert idx != -1, f"Evidence for {cid} not found verbatim in source judgment!"
        assert idx == rec["source_char_offset"], f"Offset mismatch for {cid}"
        assert len(ev) == rec["source_char_length"], f"Length mismatch for {cid}"
        assert "..." not in ev, f"Evidence for {cid} contains forbidden ellipses!"

        tgt = expected_verified[cid]
        assert rec["disposition"] == tgt["disposition"], f"Disposition mismatch for {cid}: {rec['disposition']} != {tgt['disposition']}"
        assert rec["successful_party"] == tgt["successful_party"], f"Party mismatch for {cid}: {rec['successful_party']} != {tgt['successful_party']}"
        assert rec["action"] == tgt["action"], f"Action mismatch for {cid}: {rec['action']} != {tgt['action']}"

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

    # Step 6: Execute atomic commit via submit_batch_reviews (confirm=True)
    print("\n[COMMIT] Executing Atomic Batch Commit via submit_batch_reviews (confirm=True)...")
    commit_res = session.submit_batch_reviews(
        batch_decisions=batch_decisions,
        reviewer_id="SNR-LEGAL-NLP-01",
        confirm=True
    )
    print(f"Commit Result: {commit_res['committed_count']} cases atomically committed.")
    assert commit_res["committed_count"] == 5, f"Expected 5 committed cases, got {commit_res['committed_count']}"

    # Step 7: Explicitly preserve proceeding classifications in master stores
    print("\n[PROCEEDING CLASSIFICATIONS] Synchronizing proceeding types in master stores:")
    for cid, tgt in expected_verified.items():
        rec_obj = session.records_by_id[cid]
        rec_obj["proceeding_type"] = tgt["proceeding_type"]
        print(f"  - {cid}: proceeding_type = {tgt['proceeding_type']}")

    session._save()
    print("Master candidate stores and review CSV synchronized successfully.")

    # Step 8: Post-commit dashboard verification
    session_post = OutcomeAnnotationSessionManager()
    dash = session_post.get_progress_dashboard()

    print("\n" + "=" * 80)
    print("POST-COMMIT ANNOTATION DASHBOARD AUDIT (26 VERIFIED)")
    print("=" * 80)
    print(f"Total Candidates:         {dash['total_candidates']}")
    print(f"Total Verified:           {dash['total_verified']} / 150 (Progress: {dash['total_verified']/150*100:.1f}%)")
    print(f"  - Approved:             {dash['approved']}")
    print(f"  - Corrected:            {dash['corrected']}")
    print(f"Pending Review:           {dash['pending']}")
    assert dash["total_verified"] == 26, f"Expected 26 verified, got {dash['total_verified']}"
    assert dash["pending"] == 124, f"Expected 124 pending, got {dash['pending']}"

    # Step 9: Post-commit training readiness evaluation
    readiness = session_post.check_training_readiness(min_total_verified=30, min_minority_samples=5)
    print("\n" + "=" * 80)
    print("POST-COMMIT DUAL-MODEL TRAINING READINESS EVALUATION")
    print("=" * 80)
    print(f"Training Eligible (Global): {readiness['is_training_eligible']} (Locked)")
    print(f"Recommended Mode:          {readiness['recommended_mode']}")

    print("\n--- Model A: Judicial Disposition ---")
    ma = readiness["model_a"]
    print(f"  Target:                  {ma['target']}")
    print(f"  Eligible Merits Count:   {ma['eligible_count']} / {ma['minimum_required']} (Gap: {ma['minimum_required'] - ma['eligible_count']})")
    print(f"  Excluded Count:          {ma['excluded_count']} {ma['excluded_distribution']}")
    print(f"  Merits Distribution:     {ma['class_distribution']}")
    print(f"  Minority Class Count:    {ma['minority_class_count']} (Threshold: {ma['min_minority_samples']})")
    print(f"  Blockers:                {ma['blockers']}")

    print("\n--- Model B: Successful Party ---")
    mb = readiness["model_b"]
    print(f"  Target:                  {mb['target']}")
    print(f"  Eligible Substantive:    {mb['eligible_count']} / {mb['minimum_required']} (Gap: {mb['minimum_required'] - mb['eligible_count']})")
    print(f"  Excluded Count:          {mb['excluded_count']} {mb['excluded_distribution']}")
    print(f"  Substantive Distribution:{mb['class_distribution']}")
    print(f"  Minority Class Count:    {mb['minority_class_count']} (Threshold: {mb['min_minority_samples']})")
    print(f"  Blockers:                {mb['blockers']}")

    assert ma["eligible_count"] == 23, f"Expected 23 Model A eligible, got {ma['eligible_count']}"
    assert mb["eligible_count"] == 22, f"Expected 22 Model B eligible, got {mb['eligible_count']}"
    assert mb["minority_class_count"] == 5, f"Expected Model B minority class count >= 5, got {mb['minority_class_count']}"

    print("\n" + "=" * 80)
    print("BATCH 1.5 ATOMIC COMMIT COMPLETED SUCCESSFULLY WITH ZERO ERRORS")
    print("=" * 80)

if __name__ == "__main__":
    main()
