"""
Execute the Authorized Atomic Commit of Batch 1.3 Annotations
Feature 4.11.2 — Authorized Atomic Commit of Batch 1.3

Reviewer ID: SNR-LEGAL-NLP-01

Strict verification checks:
1. Revalidate all 5 case IDs and staged decisions from batch_1_3_staged.json.
2. Confirm the party and disposition assignments:
   - OIL-SC-2006_INSC_699: appeal_allowed, successful_party: accused (with OCR notes)
   - OIL-SC-2010_INSC_109: appeal_dismissed, successful_party: state_prosecution
   - OIL-AHC-UPHC020034182022: appeal_allowed, successful_party: accused (with extraction notes)
   - OIL-DHC-DLHC015857912015: petition_allowed, successful_party: petitioner
   - OIL-SC-1992_INSC_350: appeal_dismissed, successful_party: respondent (with civil classification)
3. Verify all 5 evidence quotations are exact byte-for-byte substrings of open_india_law_sample_150.json.
4. Verify all 11 previously approved annotations and their audit histories remain intact.
5. Verify source dataset cryptographic SHA-256 hashes before and after commit.
6. Commit the 5 decisions atomically via OutcomeAnnotationSessionManager.submit_batch_reviews(confirm=True).
7. Re-audit live database stores, CSV/JSON synchronization, dashboard counts, and training gatekeeper status.
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
    KNOWN_SOURCE_HASHES,
)

PREVIOUS_ELEVEN_COMMITTED_IDS = [
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
]

def main():
    print("=" * 80)
    print("BATCH 1.3 AUTHORIZED ATOMIC COMMIT EXECUTION")
    print("Reviewer ID: SNR-LEGAL-NLP-01")
    print("=" * 80)

    session = OutcomeAnnotationSessionManager()

    # Step 1: Pre-check source dataset hashes
    print("\n[PRE-CHECK 1] Verifying Cryptographic Source Integrity:")
    pre_integrity = session.verify_source_integrity()
    for fname, ok in pre_integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok, f"Integrity check failed for {fname}"

    # Step 2: Pre-check the 11 existing approved cases
    print("\n[PRE-CHECK 2] Verifying 11 Existing Approved Annotations:")
    for cid in PREVIOUS_ELEVEN_COMMITTED_IDS:
        c_view = session.get_case_view(cid)
        rev = c_view["current_review"]
        status = rev["review_status"]
        label = rev["human_approved_label"]
        party = rev["human_successful_party"]
        reviewer = rev["reviewer_reference"]
        history_len = len(rev["audit_history"])
        print(f"  - {cid}: status={status}, label={label}, party={party}, reviewer={reviewer}, audit_events={history_len}")
        assert status in ["approved", "corrected"], f"Expected approved/corrected status for {cid}"
        assert reviewer == "SNR-LEGAL-NLP-01", f"Expected reviewer SNR-LEGAL-NLP-01 for {cid}"
        assert history_len >= 1, f"Audit history missing for {cid}"

    # Step 3: Load and validate staged Batch 1.3 file
    staging_file = ML_SERVICE_DIR / "app" / "datasets" / "review_batches" / "batch_1_3_staged.json"
    assert staging_file.exists(), f"Staging file not found: {staging_file}"
    with open(staging_file, "r", encoding="utf-8") as f:
        staged_data = json.load(f)

    staged_records = staged_data["records"]
    assert len(staged_records) == 5, f"Expected 5 staged records, got {len(staged_records)}"
    print(f"\n[PRE-CHECK 3] Loaded {len(staged_records)} staged records from batch_1_3_staged.json")

    # Step 4: Verify specific party assignments and notes
    print("\n[PRE-CHECK 4] Verifying Target Labels and Requirements:")
    expected_targets = {
        "OIL-SC-2006_INSC_699": {
            "disposition": "appeal_allowed",
            "successful_party": "accused",
            "notes_extra": "[OCR Uncertainty Note: Misread 'B' as '8' in 'Section 3048' (referring to Section 304B IPC); margin markers 'after F examination' and 'D.G. G' noted.]"
        },
        "OIL-SC-2010_INSC_109": {
            "disposition": "appeal_dismissed",
            "successful_party": "state_prosecution",
            "notes_extra": "[Conviction under Section 304 Part II IPC affirmed; State of Assam succeeds as prosecuting authority; bail cancelled and surrender ordered.]"
        },
        "OIL-AHC-UPHC020034182022": {
            "disposition": "appeal_allowed",
            "successful_party": "accused",
            "notes_extra": "[Extraction Note: Statutory Criminal Appeal No. 188 of 2022 under Section 14-A(2) SC/ST Act arising out of Bail Appln 3016/2021 in FIR 450/2021 u/s 302 IPC. PDF ligature 'sufÏcient' (ffi) and compressed spacing noted. Order dated 24.11.2021 set aside and accused appellants enlarged on bail.]"
        },
        "OIL-DHC-DLHC015857912015": {
            "disposition": "petition_allowed",
            "successful_party": "petitioner",
            "notes_extra": "[Criminal Misc Petition under Section 482 Cr.P.C. allowed; FIR No. 174/2013 u/s 498A/406 IPC quashed pursuant to settlement. Accused petitioners succeed in High Court.]"
        },
        "OIL-SC-1992_INSC_350": {
            "disposition": "appeal_dismissed",
            "successful_party": "respondent",
            "notes_extra": "[Proceeding Type: civil_appellate_proceeding. Civil commercial challenge to price increase of steel coils; Open India Law criminal_appeal tag corrected. Respondents Union of India and SAIL succeed with costs.]"
        },
    }

    # Step 5: Verify exact evidence substrings against open_india_law_sample_150.json
    print("\n[PRE-CHECK 5] Substring Verification in Source Judgments:")
    source_file = ML_SERVICE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"
    with open(source_file, "r", encoding="utf-8") as f:
        source_judgments = {c["id"]: c for c in json.load(f)}

    batch_decisions = []
    for rec in staged_records:
        cid = rec["case_id"]
        ev = rec["evidence"]
        src_case = source_judgments[cid]
        src_text = src_case["judgmentText"]
        idx = src_text.find(ev)
        assert idx != -1, f"Evidence for {cid} not found verbatim in source judgment!"
        assert "..." not in ev, f"Evidence for {cid} contains prohibited ellipses!"
        print(f"  - {cid}: Exact match at character offset {idx} ({len(ev)} chars)")

        tgt = expected_targets[cid]
        assert rec["disposition"] == tgt["disposition"], f"Disposition mismatch for {cid}"
        assert rec["successful_party"] == tgt["successful_party"], f"Party mismatch for {cid}"

        # Combine detailed review notes with extraction and OCR preservation notes
        full_notes = rec["notes"].strip() + " " + tgt["notes_extra"]

        batch_decisions.append({
            "case_id": cid,
            "action": rec["action"],
            "disposition": rec["disposition"],
            "successful_party": rec["successful_party"],
            "evidence": ev,
            "notes": full_notes,
        })

    # Step 6: Execute the atomic commit
    print("\n[COMMIT] Executing Atomic Batch Commit via submit_batch_reviews (confirm=True)...")
    commit_res = session.submit_batch_reviews(
        batch_decisions=batch_decisions,
        reviewer_id="SNR-LEGAL-NLP-01",
        confirm=True
    )
    print(f"Commit Result: {commit_res['committed_count']} cases atomically committed.")

    # Step 6b: Explicitly preserve proceeding_type in master records
    bms_rec = session.records_by_id["OIL-SC-1992_INSC_350"]
    bms_rec["proceeding_type"] = "civil_appellate_proceeding"

    ramakant_rec = session.records_by_id["OIL-AHC-UPHC020034182022"]
    ramakant_rec["proceeding_type"] = "criminal_appeal"

    govadia_rec = session.records_by_id["OIL-SC-2006_INSC_699"]
    govadia_rec["proceeding_type"] = "criminal_appeal"

    nadeem_rec = session.records_by_id["OIL-DHC-DLHC015857912015"]
    nadeem_rec["proceeding_type"] = "criminal_misc_petition_482"

    mannan_rec = session.records_by_id["OIL-SC-2010_INSC_109"]
    mannan_rec["proceeding_type"] = "criminal_appeal"

    session._save()
    print("Explicitly synchronized proceeding types in master stores.")

    # Step 7: Reload session and re-verify database state
    session_post = OutcomeAnnotationSessionManager()
    dash = session_post.get_progress_dashboard()

    print("\n" + "=" * 80)
    print("UPDATED POST-COMMIT ANNOTATION DASHBOARD")
    print("=" * 80)
    print(f"Total Candidates:         {dash['total_candidates']}")
    print(f"Total Verified:           {dash['total_verified']} / 150 (Progress: {dash['total_verified']/150*100:.1f}%)")
    print(f"  - Approved:             {dash['approved']}")
    print(f"  - Corrected:            {dash['corrected']}")
    print(f"Pending Review:           {dash['pending']}")
    print(f"Batch 1 Definitive Total: {dash['batch_1_progress']['total']} (Verified: {dash['batch_1_progress']['verified']}, Pending: {dash['batch_1_progress']['pending']})")

    assert dash["total_verified"] == 16, f"Expected 16 verified, got {dash['total_verified']}"
    assert dash["approved"] == 15, f"Expected 15 approved, got {dash['approved']}"
    assert dash["corrected"] == 1, f"Expected 1 corrected, got {dash['corrected']}"
    assert dash["pending"] == 134, f"Expected 134 pending, got {dash['pending']}"

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

    assert dash["risk_tier_progress"]["tier_1"]["verified"] == 16, "Tier 1 verified count must be 16"
    assert dash["risk_tier_progress"]["tier_1"]["pending"] == 19, "Tier 1 pending count must be 19"

    # Step 8: Verify audit history for all 16 committed cases
    print("\n[VERIFICATION] Audit Trail Verification for All 16 Verified Cases:")
    all_sixteen_ids = PREVIOUS_ELEVEN_COMMITTED_IDS + [d["case_id"] for d in batch_decisions]
    for cid in all_sixteen_ids:
        cv = session_post.get_case_view(cid)
        rev = cv["current_review"]
        last_audit = rev["audit_history"][-1]
        print(f"  {cid}:")
        print(f"    Status:     {rev['review_status']}")
        print(f"    Dispos:     {rev['human_approved_label']}")
        print(f"    Party:      {rev['human_successful_party']}")
        print(f"    Reviewer:   {rev['reviewer_reference']}")
        print(f"    Timestamp:  {last_audit['timestamp']}")
        print(f"    Notes:      {last_audit['notes'][:80]}...")

    # Step 9: Re-verify cryptographic hashes of source datasets
    print("\n[POST-CHECK] Cryptographic Source Integrity:")
    post_integrity = session_post.verify_source_integrity()
    for fname, ok in post_integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok, f"Integrity failed for {fname}"

    # Step 10: Verify training readiness gatekeeper
    readiness = session_post.check_training_readiness(min_total_verified=30)
    print(f"\n[TRAINING READINESS GATEKEEPER]")
    print(f"  Eligible for Training: {readiness['is_training_eligible']}")
    print(f"  Current Verified:      {readiness['total_verified_count']} / {readiness['minimum_required']}")
    print(f"  Mode:                  {readiness['recommended_mode']}")
    print(f"  Blockers:              {readiness['blockers']}")
    assert not readiness["is_training_eligible"], "Training must remain blocked!"
    assert readiness["recommended_mode"] == "qualitative_research_mode", "qualitative_research_mode must remain active!"

    # Step 11: Verify CSV and JSON synchronization
    print("\n[CSV / JSON SYNCHRONIZATION]")
    csv_file = ML_SERVICE_DIR / "app" / "datasets" / "outcome_label_review_v2.csv"
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 150, f"Expected 150 CSV rows, got {len(reader)}"
    csv_by_id = {r["case_id"]: r for r in reader}
    for cid in all_sixteen_ids:
        c_row = csv_by_id[cid]
        j_rec = session_post.records_by_id[cid]
        assert c_row["human_approved_label"] == j_rec["human_approved_label"]
        assert c_row["human_successful_party"] == j_rec["human_successful_party"]
        assert c_row["review_status"] == j_rec["review_status"]
        assert c_row["proceeding_type"] == j_rec["proceeding_type"]
    print("  CSV and JSON records match 100% across all 16 verified cases.")

    print("\n" + "=" * 80)
    print("FEATURE 4.11.2 ATOMIC COMMIT SUCCESSFUL — 16 TOTAL CASES VERIFIED")
    print("=" * 80)

if __name__ == "__main__":
    main()
