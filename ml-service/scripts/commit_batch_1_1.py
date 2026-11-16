"""
Script to execute the atomic commit of Batch 1.1 annotations under reviewer SNR-LEGAL-NLP-01.
Strict pre-validation checks:
1. Remove scraped Kanoon suffix '[SECTION] ## Appeal allowed.' from Case 3 evidence.
2. Ensure Case 4 evidence is exact contiguous quotation without ellipses.
3. Verify all 5 evidence strings are exact byte-for-byte substrings of source text.
4. Verify Case 1 (OIL-SC-2021_INSC_327) is preserved.
5. Verify source dataset cryptographic hashes before and after.
"""

import sys
import json
from pathlib import Path

# Add ml-service to sys.path
ML_SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from app.prediction.outcome_annotation_session import OutcomeAnnotationSessionManager

def main():
    print("=" * 70)
    print("BATCH 1.1 ATOMIC COMMIT EXECUTION")
    print("Reviewer ID: SNR-LEGAL-NLP-01")
    print("=" * 70)

    session = OutcomeAnnotationSessionManager()

    # Step 1: Verify source dataset hashes before commit
    pre_integrity = session.verify_source_integrity()
    print("\n[PRE-CHECK] Verifying source dataset integrity...")
    for fname, ok in pre_integrity.items():
        print(f"  {fname}: {'OK' if ok else 'FAILED'}")
        if not ok:
            raise RuntimeError(f"Integrity check failed for {fname}")

    # Step 2: Verify Case 1 state
    case_1 = session.get_case_view("OIL-SC-2021_INSC_327")
    c1_rev = case_1["current_review"]
    print(f"\n[PRE-CHECK] Case 1 (OIL-SC-2021_INSC_327):")
    print(f"  Status: {c1_rev['review_status']}")
    print(f"  Disposition: {c1_rev['human_approved_label']}")
    print(f"  Reviewer: {c1_rev['reviewer_reference']}")
    assert c1_rev["review_status"] == "approved"
    assert c1_rev["reviewer_reference"] == "SNR-LEGAL-NLP-01"

    # Step 3: Define Batch 1.1 decisions
    batch_decisions = [
        {
            "case_id": "OIL-SC-1996_INSC_503",
            "action": "accept",
            "disposition": "appeal_dismissed",
            "successful_party": "state_prosecution",
            "evidence": "For the foregoing reasons, we do not differ from the view taken by the High Court in maintaining the conviction of the appellant. The appeal therefore fails and is hereby dismissed. The appellant is on bail. He shall surrender to his bail bonds.",
            "notes": "The appellant was directed to surrender to his bail bonds."
        },
        {
            "case_id": "OIL-SC-2007_INSC_31",
            "action": "correct",
            "disposition": "remanded",
            "successful_party": "none_procedural",
            "evidence": "we are of the opinion that the impugned judgment cannot be sustained and this should be set aside and the matter be remitted to the High Court for consideration of the Second Appeal afresh after formulating an appropriate substantial question of law arising, if any. The appeal is allowed.",
            "notes": "Do not classify this as a substantive merits victory merely because the formal order says the appeal is allowed."
        },
        {
            "case_id": "OIL-SC-2007_INSC_1082",
            "action": "accept",
            "disposition": "appeal_allowed",
            "successful_party": "petitioner",
            "evidence": "For the reasons aforementioned the impugned judgment cannot be c sustained. The appeal is allowed. We, however, before taking any punitive action against the contemnors at this stage, would like to issue a direction upon them to fully implement the orders of this Court as modified by this Court on the same terms as was done in the case of employees similarly D situated. In facts and circumstances of the case the appellants shall also be entitled to costs which we quantify at Rs. 25,000/-.",
            "notes": "Resolve the previously unresolved successful-party field."
        },
        {
            "case_id": "OIL-SC-2003_INSC_88",
            "action": "accept",
            "disposition": "appeal_dismissed",
            "successful_party": "respondent",
            "evidence": "In these circumstances, we dismiss the appeals without ariy order as to costs.\n\nD N.J.\n\nAppeals dismissed.",
            "notes": "Confirm the complete concluding operative order is present in the source text before staging. Resolve the previously unresolved successful-party field."
        },
        {
            "case_id": "OIL-SC-1973_INSC_203",
            "action": "accept",
            "disposition": "petition_allowed",
            "successful_party": "petitioner",
            "evidence": "For these reasons we set aside ihe order of detention. We had ear· lier directed on the conclusion of the arguments that the petitioner be set at liberty forthwith.",
            "notes": "Habeas corpus petition allowed; preventive detention quashed."
        }
    ]

    # Pre-validation 1: Case 3 must not contain scraped header
    case_3_ev = batch_decisions[2]["evidence"]
    assert "[SECTION]" not in case_3_ev, "Case 3 evidence must not contain '[SECTION]'"
    assert "## Appeal allowed." not in case_3_ev, "Case 3 evidence must not contain '## Appeal allowed.'"
    print("\n[VALIDATION] Case 3 scraped header check: PASSED (no '[SECTION]' or '## Appeal allowed.')")

    # Pre-validation 2: Case 4 must not contain ellipses
    case_4_ev = batch_decisions[3]["evidence"]
    assert "..." not in case_4_ev, "Case 4 evidence must not contain ellipses"
    print("[VALIDATION] Case 4 contiguous text check: PASSED (no ellipses)")

    # Pre-validation 3: Exact match in source judgment text
    print("[VALIDATION] Substring verification against source judgments:")
    for d in batch_decisions:
        cid = d["case_id"]
        source_text = session.source_cases[cid]["judgmentText"]
        ev = d["evidence"]
        assert ev in source_text, f"Evidence for {cid} not found verbatim in source text!"
        print(f"  - {cid}: Verbatim match confirmed ({len(ev)} chars)")

    # Step 4: Submit batch atomically
    print("\n[COMMIT] Submitting batch reviews atomically with confirm=True...")
    res = session.submit_batch_reviews(
        batch_decisions=batch_decisions,
        reviewer_id="SNR-LEGAL-NLP-01",
        confirm=True
    )
    print(f"Commit result: {res['committed_count']} cases committed.")

    # Step 5: Reload and verify database state
    session_post = OutcomeAnnotationSessionManager()
    dash = session_post.get_progress_dashboard()

    print("\n" + "=" * 70)
    print("UPDATED ANNOTATION DASHBOARD")
    print("=" * 70)
    print(f"Total Candidates:         {dash['total_candidates']}")
    print(f"Approved:                 {dash['approved']}")
    print(f"Corrected:                {dash['corrected']}")
    print(f"Total Verified:           {dash['total_verified']} / 150 (Progress: {dash['total_verified']/150*100:.1f}%)")
    print(f"Pending Review:           {dash['pending']}")
    print(f"Batch 1 Progress:         {dash['batch_1_progress']['verified']} / {dash['batch_1_progress']['total']} ({dash['batch_1_progress']['percent_complete']}%)")

    print("\nVerified Class Distribution:")
    for disp, cnt in dash["verified_disposition_distribution"].items():
        print(f"  {disp:25s}: {cnt}")

    print("\nSuccessful Party Distribution:")
    for party, cnt in dash["successful_party_distribution"].items():
        print(f"  {party:25s}: {cnt}")

    print("\nReviewer-Wise Progress:")
    for rev, stats in dash["reviewer_wise_progress"].items():
        print(f"  {rev:25s}: total={stats['total']}, approved={stats['approved']}, corrected={stats['corrected']}")

    print("\nRisk Tier Progress:")
    for t_key, t_info in dash["risk_tier_progress"].items():
        print(f"  {t_info['label']:35s}: verified={t_info['verified']}, pending={t_info['pending']}, total={t_info['total']}")

    # Step 6: Verify Case 1 preservation
    c1_post = session_post.get_case_view("OIL-SC-2021_INSC_327")
    assert c1_post["current_review"]["review_status"] == "approved"
    assert c1_post["current_review"]["reviewer_reference"] == "SNR-LEGAL-NLP-01"
    assert len(c1_post["current_review"]["audit_history"]) >= 1
    print("\n[VERIFICATION] Case 1 (OIL-SC-2021_INSC_327) preserved with intact audit history: CONFIRMED")

    # Step 7: Verify all 5 committed cases
    print("\n[VERIFICATION] Audit Trail for Committed Batch 1.1 Cases:")
    for d in batch_decisions:
        cid = d["case_id"]
        cv = session_post.get_case_view(cid)
        rev = cv["current_review"]
        last_audit = rev["audit_history"][-1]
        print(f"  {cid}:")
        print(f"    Status:           {rev['review_status']}")
        print(f"    Dispos:           {rev['human_approved_label']}")
        print(f"    Party:            {rev['human_successful_party']}")
        print(f"    Reviewer:         {rev['reviewer_reference']}")
        print(f"    Audit Action:     {last_audit['action']}")
        print(f"    Audit Timestamp:  {last_audit['timestamp']}")
        print(f"    Audit Notes:      {last_audit['notes']}")

    # Step 8: Verify source integrity again
    post_integrity = session_post.verify_source_integrity()
    print("\n[POST-CHECK] Cryptographic SHA-256 integrity of source datasets:")
    for fname, ok in post_integrity.items():
        print(f"  {fname}: {'UNTOUCHED / MATCHES CANONICAL' if ok else 'FAILED'}")
        assert ok, f"Integrity failed for {fname}"

    # Step 9: Training readiness check
    readiness = session_post.check_training_readiness(min_total_verified=30)
    print(f"\n[TRAINING READINESS]")
    print(f"  Eligible: {readiness['is_training_eligible']}")
    print(f"  Mode:     {readiness['recommended_mode']}")
    print(f"  Blockers: {readiness['blockers']}")

    print("\n" + "=" * 70)
    print("BATCH 1.1 ATOMIC COMMIT SUCCESSFUL")
    print("=" * 70)

if __name__ == "__main__":
    main()
