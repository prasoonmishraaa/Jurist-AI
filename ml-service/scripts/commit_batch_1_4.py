"""
Execute the Authorized Atomic Commit of Batch 1.4 Annotations
Feature 4.12.3 — Authorized Atomic Commit of Batch 1.4

Reviewer ID: SNR-LEGAL-NLP-01

Strict verification checks:
1. Revalidate all 5 staged records from batch_1_4_staged.json against the current annotation schema.
2. Confirm dismissed_as_infructuous is supported and excluded from merits-model training.
3. Confirm the 5 evidence quotations and source offsets match verbatim in open_india_law_sample_150.json (zero ellipses).
4. Confirm master stores still contain exactly 16 verified annotations and 134 pending records.
5. Commit all five records atomically via OutcomeAnnotationSessionManager.submit_batch_reviews(confirm=True).
6. Synchronize master JSON and CSV with proceeding classifications.
7. Record individual timestamped audit events.
8. Preserve all previous annotations and audit history.
9. Recalculate both independent target distributions.
10. Ensure zero model training, zero serialization of model weights, and qualitative_research_mode remains active.
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

PREVIOUS_SIXTEEN_COMMITTED_IDS = [
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
]

def main():
    print("=" * 80)
    print("BATCH 1.4 AUTHORIZED ATOMIC COMMIT EXECUTION")
    print("Reviewer ID: SNR-LEGAL-NLP-01")
    print("=" * 80)

    session = OutcomeAnnotationSessionManager()

    # Pre-check 1: Cryptographic source dataset integrity
    print("\n[PRE-CHECK 1] Verifying Cryptographic Source Integrity:")
    pre_integrity = session.verify_source_integrity()
    for fname, ok in pre_integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok, f"Integrity check failed for {fname}"

    # Pre-check 2: Master store baseline verification (16 verified, 134 pending)
    print("\n[PRE-CHECK 2] Verifying Master Store Baseline Counts:")
    dash_pre = session.get_progress_dashboard()
    print(f"  Total Candidates: {dash_pre['total_candidates']}")
    print(f"  Total Verified:   {dash_pre['total_verified']} (Approved: {dash_pre['approved']}, Corrected: {dash_pre['corrected']})")
    print(f"  Pending:          {dash_pre['pending']}")
    assert dash_pre["total_verified"] == 16, f"Expected 16 verified, got {dash_pre['total_verified']}"
    assert dash_pre["pending"] == 134, f"Expected 134 pending, got {dash_pre['pending']}"

    # Pre-check 3: Verify all 16 existing approved annotations and audit histories
    print("\n[PRE-CHECK 3] Verifying 16 Existing Approved Annotations & Audit Histories:")
    for cid in PREVIOUS_SIXTEEN_COMMITTED_IDS:
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

    # Pre-check 4: Confirm dismissed_as_infructuous is supported and excluded from merits training
    print("\n[PRE-CHECK 4] Confirming 'dismissed_as_infructuous' Support & Exclusion from Merits Training:")
    assert "dismissed_as_infructuous" in VALID_DISPOSITIONS, "dismissed_as_infructuous must be a valid disposition!"
    assert "none_procedural" in VALID_SUCCESSFUL_PARTIES, "none_procedural must be a valid successful party!"
    guidelines_file = ML_SERVICE_DIR / "app" / "prediction" / "outcome_annotation_guidelines.md"
    with open(guidelines_file, "r", encoding="utf-8") as f:
        g_text = f.read()
    assert "dismissed_as_infructuous" in g_text, "dismissed_as_infructuous missing in guidelines!"
    assert "**No** (Mootness)" in g_text, "dismissed_as_infructuous must be documented as non-trainable (Mootness)!"
    print("  [OK] 'dismissed_as_infructuous' is in VALID_DISPOSITIONS and explicitly excluded from merits training.")

    # Pre-check 5: Load staged Batch 1.4 records and validate against schema
    staging_file = ML_SERVICE_DIR / "app" / "datasets" / "review_batches" / "batch_1_4_staged.json"
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
        "OIL-SC-1981_INSC_134": {
            "disposition": "remanded",
            "successful_party": "none_procedural",
            "action": "correct",
            "proceeding_type": "civil_appellate_proceeding",
            "notes_extra": "[Operative remand direction takes precedence over reporter stamp 'Appeal allowed' under Guideline Mandate 1.2 & §3.5; neither party achieved final merits victory on seniority ranks.]"
        },
        "OIL-SC-1984_INSC_90": {
            "disposition": "petition_allowed",
            "successful_party": "petitioner",
            "action": "accept",
            "proceeding_type": "writ_petition",
            "notes_extra": "[Article 32 writ petitions allowed; retired judges and widows held entitled to revised pensionary benefits under 1976 Act with arrears from 1.10.1974. Petitioners succeed against Union of India.]"
        },
        "OIL-SC-2012_INSC_207": {
            "disposition": "petition_dismissed",
            "successful_party": "respondent",
            "action": "accept",
            "proceeding_type": "special_leave_petition",
            "notes_extra": "[Special Leave Petitions under Article 136 challenging MRTP Commission and Competition Appellate Tribunal orders dismissed on merits with no order as to costs. Respondent authority succeeds.]"
        },
        "OIL-AHC-UPHC020380352022": {
            "disposition": "petition_allowed",
            "successful_party": "accused",
            "action": "correct",
            "proceeding_type": "criminal_misc_petition_482",
            "notes_extra": "[Criminal petition under Section 482 CrPC allowed; trial court order refusing recall set aside and witness P.W.1 recalled for cross-examination by undertrial accused in murder trial. Accused petitioner succeeds.]"
        },
        "OIL-AHC-UPHC020497422019": {
            "disposition": "dismissed_as_infructuous",
            "successful_party": "none_procedural",
            "action": "correct",
            "proceeding_type": "criminal_writ_petition",
            "notes_extra": "[Writ petition challenging Section 366 IPC FIR dismissed as infructuous due to efflux of time under Guideline §3.6.2 and Row 131; interim protection vacated with liberty to take recourse to law. No merits adjudication; party success is none_procedural.]"
        }
    }

    batch_decisions = []
    for rec in staged_records:
        cid = rec["case_id"]
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
    print("POST-COMMIT ANNOTATION DASHBOARD AUDIT (21 VERIFIED)")
    print("=" * 80)
    print(f"Total Candidates:         {dash['total_candidates']}")
    print(f"Total Verified:           {dash['total_verified']} / 150 (Progress: {dash['total_verified']/150*100:.1f}%)")
    print(f"  - Approved:             {dash['approved']}")
    print(f"  - Corrected:            {dash['corrected']}")
    print(f"Pending Review:           {dash['pending']}")
    print(f"Batch 1 Progress:         {dash['batch_1_progress']['verified']} verified, {dash['batch_1_progress']['pending']} pending (Total: {dash['batch_1_progress']['total']})")

    assert dash["total_verified"] == 21, f"Expected 21 verified, got {dash['total_verified']}"
    assert dash["approved"] == 17, f"Expected 17 approved, got {dash['approved']}"
    assert dash["corrected"] == 4, f"Expected 4 corrected, got {dash['corrected']}"
    assert dash["pending"] == 129, f"Expected 129 pending, got {dash['pending']}"

    print("\nVerified Class Distribution (Target A: Disposition):")
    for disp, cnt in sorted(dash["verified_disposition_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {disp:35s}: {cnt}")

    print("\nSuccessful Party Distribution (Target B: Party Success):")
    for party, cnt in sorted(dash["successful_party_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {party:35s}: {cnt}")

    print("\nReviewer-Wise Progress:")
    for rev, stats in dash["reviewer_wise_progress"].items():
        print(f"  {rev:25s}: total={stats['total']}, approved={stats['approved']}, corrected={stats['corrected']}")

    print("\nRisk Tier Progress:")
    for t_key, t_info in dash["risk_tier_progress"].items():
        print(f"  {t_info['label']:40s}: verified={t_info['verified']:2d}, pending={t_info['pending']:2d}, total={t_info['total']:2d}")

    assert dash["risk_tier_progress"]["tier_1"]["verified"] == 21, "Tier 1 verified count must be 21"
    assert dash["risk_tier_progress"]["tier_1"]["pending"] == 14, "Tier 1 pending count must be 14"

    # Step 9: Verify audit trail for all 21 committed cases
    print("\n[VERIFICATION] Audit Trail Verification for All 21 Verified Cases:")
    all_twenty_one_ids = PREVIOUS_SIXTEEN_COMMITTED_IDS + [d["case_id"] for d in batch_decisions]
    for cid in all_twenty_one_ids:
        cv = session_post.get_case_view(cid)
        rev = cv["current_review"]
        last_audit = rev["audit_history"][-1]
        print(f"  {cid}: status={rev['review_status']}, disp={rev['human_approved_label']}, party={rev['human_successful_party']}, reviewer={rev['reviewer_reference']}, timestamp={last_audit['timestamp']}")

    # Step 10: Re-verify cryptographic hashes of source datasets
    print("\n[POST-CHECK] Cryptographic Source Integrity:")
    post_integrity = session_post.verify_source_integrity()
    for fname, ok in post_integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok, f"Integrity failed for {fname}"

    # Step 11: Verify training readiness gatekeeper
    readiness = session_post.check_training_readiness(min_total_verified=30)
    print(f"\n[TRAINING READINESS GATEKEEPER]")
    print(f"  Eligible for Training: {readiness['is_training_eligible']}")
    print(f"  Current Verified:      {readiness['total_verified_count']} / {readiness['minimum_required']}")
    print(f"  Mode:                  {readiness['recommended_mode']}")
    print(f"  Blockers:              {readiness['blockers']}")
    assert not readiness["is_training_eligible"], "Training must remain strictly blocked!"
    assert readiness["recommended_mode"] == "qualitative_research_mode", "qualitative_research_mode must remain active!"

    # Step 12: Verify CSV and JSON synchronization
    print("\n[CSV / JSON SYNCHRONIZATION]")
    csv_file = ML_SERVICE_DIR / "app" / "datasets" / "outcome_label_review_v2.csv"
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 150, f"Expected 150 CSV rows, got {len(reader)}"
    csv_by_id = {r["case_id"]: r for r in reader}
    for cid in all_twenty_one_ids:
        c_row = csv_by_id[cid]
        j_rec = session_post.records_by_id[cid]
        assert c_row["human_approved_label"] == j_rec["human_approved_label"]
        assert c_row["human_successful_party"] == j_rec["human_successful_party"]
        assert c_row["review_status"] == j_rec["review_status"]
        assert c_row["proceeding_type"] == j_rec["proceeding_type"]
    print("  CSV and JSON records match 100% across all 21 verified cases.")

    print("\n" + "=" * 80)
    print("FEATURE 4.12.3 ATOMIC COMMIT SUCCESSFUL — 21 TOTAL CASES VERIFIED")
    print("=" * 80)

if __name__ == "__main__":
    main()
