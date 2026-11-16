"""
Execute the Authorized Atomic Commit of Batch 1.2 Annotations
Feature 4.10.2 — Authorized Atomic Commit of Batch 1.2

Reviewer ID: SNR-LEGAL-NLP-01

Strict verification checks:
1. Revalidate all 5 case IDs and staged decisions from batch_1_2_staged.json.
2. Confirm the two successful-party corrections:
   - OIL-SC-2016_INSC_467: unresolved
   - OIL-SC-1998_INSC_267: respondent
3. Verify all 5 evidence quotations are exact byte-for-byte substrings of open_india_law_sample_150.json.
4. Verify all 6 previously approved annotations and their audit histories remain intact.
5. Verify source dataset cryptographic SHA-256 hashes before and after commit.
6. Commit the 5 decisions atomically via OutcomeAnnotationSessionManager.submit_batch_reviews(confirm=True).
7. Re-audit live database stores, CSV/JSON synchronization, dashboard counts, and training gatekeeper status.
"""

import sys
import json
import hashlib
from pathlib import Path

# Add ml-service to path
ML_SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    KNOWN_SOURCE_HASHES,
)

PREVIOUS_SIX_COMMITTED_IDS = [
    "OIL-SC-2021_INSC_327",
    "OIL-SC-1996_INSC_503",
    "OIL-SC-2007_INSC_31",
    "OIL-SC-2007_INSC_1082",
    "OIL-SC-2003_INSC_88",
    "OIL-SC-1973_INSC_203",
]

def main():
    print("=" * 80)
    print("BATCH 1.2 AUTHORIZED ATOMIC COMMIT EXECUTION")
    print("Reviewer ID: SNR-LEGAL-NLP-01")
    print("=" * 80)

    session = OutcomeAnnotationSessionManager()

    # Step 1: Pre-check source dataset hashes
    print("\n[PRE-CHECK 1] Verifying Cryptographic Source Integrity:")
    pre_integrity = session.verify_source_integrity()
    for fname, ok in pre_integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok, f"Integrity check failed for {fname}"

    # Step 2: Pre-check the 6 existing approved cases
    print("\n[PRE-CHECK 2] Verifying 6 Existing Approved Annotations:")
    for cid in PREVIOUS_SIX_COMMITTED_IDS:
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

    # Step 3: Load and validate staged Batch 1.2 file
    staging_file = ML_SERVICE_DIR / "app" / "datasets" / "review_batches" / "batch_1_2_staged.json"
    assert staging_file.exists(), f"Staging file not found: {staging_file}"
    with open(staging_file, "r", encoding="utf-8") as f:
        staged_data = json.load(f)

    staged_records = staged_data["records"]
    assert len(staged_records) == 5, f"Expected 5 staged records, got {len(staged_records)}"
    print(f"\n[PRE-CHECK 3] Loaded {len(staged_records)} staged records from batch_1_2_staged.json")

    # Step 4: Verify specific party assignments
    print("\n[PRE-CHECK 4] Verifying Target Successful-Party Corrections:")
    party_checks = {
        "OIL-SC-2016_INSC_467": "unresolved",
        "OIL-SC-1998_INSC_267": "respondent",
        "OIL-SC-2000_INSC_110": "respondent",
        "OIL-SC-1973_INSC_247": "respondent",
        "OIL-SC-1979_INSC_85": "petitioner",
    }
    for rec in staged_records:
        cid = rec["case_id"]
        expected_party = party_checks[cid]
        actual_party = rec["successful_party"]
        print(f"  - {cid}: party={actual_party} (expected: {expected_party})")
        assert actual_party == expected_party, f"Party mismatch for {cid}: {actual_party} != {expected_party}"

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

        batch_decisions.append({
            "case_id": cid,
            "action": rec["action"],
            "disposition": rec["disposition"],
            "successful_party": rec["successful_party"],
            "evidence": ev,
            "notes": rec["notes"],
        })

    # Step 6: Execute the atomic commit
    print("\n[COMMIT] Executing Atomic Batch Commit via submit_batch_reviews (confirm=True)...")
    commit_res = session.submit_batch_reviews(
        batch_decisions=batch_decisions,
        reviewer_id="SNR-LEGAL-NLP-01",
        confirm=True
    )
    print(f"Commit Result: {commit_res['committed_count']} cases atomically committed.")

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

    assert dash["total_verified"] == 11, f"Expected 11 verified, got {dash['total_verified']}"
    assert dash["approved"] == 10, f"Expected 10 approved, got {dash['approved']}"
    assert dash["corrected"] == 1, f"Expected 1 corrected, got {dash['corrected']}"
    assert dash["pending"] == 139, f"Expected 139 pending, got {dash['pending']}"

    print("\nVerified Class Distribution:")
    for disp, cnt in sorted(dash["verified_disposition_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {disp:35s}: {cnt}")

    print("\nSuccessful Party Distribution:")
    for party, cnt in sorted(dash["successful_party_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {party:35s}: {cnt}")

    print("\nReviewer-Wise Progress:")
    for rev, stats in dash["reviewer_wise_progress"].items():
        print(f"  {rev:25s}: total={stats['total']}, approved={stats['approved']}, corrected={stats['corrected']}")

    print("\nRisk Tier Progress:")
    for t_key, t_info in dash["risk_tier_progress"].items():
        print(f"  {t_info['label']:40s}: verified={t_info['verified']:2d}, pending={t_info['pending']:2d}, total={t_info['total']:2d}")

    assert dash["risk_tier_progress"]["tier_1"]["verified"] == 11, "Tier 1 verified count must be 11"
    assert dash["risk_tier_progress"]["tier_1"]["pending"] == 24, "Tier 1 pending count must be 24"

    # Step 8: Verify audit history for all 11 committed cases
    print("\n[VERIFICATION] Audit Trail Verification for All 11 Verified Cases:")
    all_eleven_ids = PREVIOUS_SIX_COMMITTED_IDS + [d["case_id"] for d in batch_decisions]
    for cid in all_eleven_ids:
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

    print("\n" + "=" * 80)
    print("FEATURE 4.10.2 ATOMIC COMMIT SUCCESSFUL — 11 TOTAL CASES VERIFIED")
    print("=" * 80)

if __name__ == "__main__":
    main()
