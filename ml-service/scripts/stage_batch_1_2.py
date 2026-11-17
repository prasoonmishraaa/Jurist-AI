"""
Stage Batch 1.2 Annotations for Human Review (Two-Phase Protocol)
Feature 4.10.1 — Batch 1.2 Final Review Adjustments

Guarantees:
1. Validates the five next pending Tier 1 cases with Feature 4.10.1 adjustments:
   - OIL-SC-2016_INSC_467: appeal_allowed, successful_party: unresolved (civil statutory authority appeal)
   - OIL-SC-1998_INSC_267: appeal_dismissed, successful_party: respondent (civil service appeal against State)
   - Preserves OIL-SC-2000_INSC_110, OIL-SC-1973_INSC_247, OIL-SC-1979_INSC_85 unchanged.
2. Verifies exact byte-for-byte substring matches in primary source judgments.
3. Validates decision schemas against OutcomeAnnotationSessionManager._validate_decision_payload.
4. Stages the payloads in a persistent batch review staging file.
5. DOES NOT commit or modify outcome_label_candidates_v2.json or outcome_label_review_v2.csv.
6. Verifies database dashboard counts remain exactly 6 verified and 144 pending.
"""

import sys
import json
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

def stage_batch_1_2():
    print("=" * 80)
    print("STAGE BATCH 1.2: FEATURE 4.10.1 FINAL REVIEW ADJUSTMENTS")
    print("=" * 80)

    session = OutcomeAnnotationSessionManager()

    # Step 1: Pre-audit baseline state
    dash_before = session.get_progress_dashboard()
    print("\n[PRE-AUDIT] Dashboard State Before Staging:")
    print(f"  Total Candidates:    {dash_before['total_candidates']}")
    print(f"  Total Verified:      {dash_before['total_verified']} (Approved: {dash_before['approved']}, Corrected: {dash_before['corrected']})")
    print(f"  Total Pending:       {dash_before['pending']}")
    print(f"  Tier 1 Progress:     {dash_before['risk_tier_progress']['tier_1']['verified']} verified, {dash_before['risk_tier_progress']['tier_1']['pending']} pending")

    assert dash_before["total_verified"] == 6, f"Expected 6 verified, got {dash_before['total_verified']}"
    assert dash_before["pending"] == 144, f"Expected 144 pending, got {dash_before['pending']}"
    assert dash_before["risk_tier_progress"]["tier_1"]["verified"] == 6, "Expected 6 verified in Tier 1"
    assert dash_before["risk_tier_progress"]["tier_1"]["pending"] == 29, "Expected 29 pending in Tier 1"

    # Step 2: Fetch next 5 pending Tier 1 cases
    batch_view = session.get_batch_view(batch_size=5, tier="1")
    retrieved_ids = [c["case_id"] for c in batch_view]
    expected_ids = [
        "OIL-SC-2000_INSC_110",
        "OIL-SC-2016_INSC_467",
        "OIL-SC-1973_INSC_247",
        "OIL-SC-1979_INSC_85",
        "OIL-SC-1998_INSC_267"
    ]
    print(f"\n[RETRIEVAL] Retrieved 5 Tier 1 Cases:")
    for idx, cid in enumerate(retrieved_ids, 1):
        print(f"  Case {idx}: {cid}")
    assert retrieved_ids == expected_ids, f"Mismatch in retrieved Tier 1 queue: {retrieved_ids} != {expected_ids}"

    # Step 3: Define proposed human review decisions with Feature 4.10.1 adjustments
    proposed_decisions = [
        {
            "case_id": "OIL-SC-2000_INSC_110",
            "case_title": "M. ARUL JOTHI AND ANR. versus LAJJA BAL (DECEASED) AND ANR.",
            "court": "Supreme Court of India",
            "decision_date": "2000-02-29",
            "procedural_role": "appellant (tenants)",
            "action": "accept",
            "disposition": "appeal_dismissed",
            "successful_party": "respondent",
            "evidence": (
                "In view of what we have concluded ano the said decision which squarely apply, we have no hesitation to hold that courts below have rightly decreed the suit for eviction as against the appellant and change of user of the business by the appellant's from radios, cycles, fans, clocks and· steel furniture to grocery business is in contradiction to the specific term of the agreement. Thus such tenant would be covered by Section 10(2)(ii)(b). Hence the appellant is liable for eviction which the courts below have rightly decreed. This appeal accordingly fails and is dismissed. Costs on the parties.-\n\n"
                "Heard learned counsel for the parties. Tenant may vacate the premises by or before 31st Dec. 2000 subject to the usual undertaking within six weeks from today"
            ),
            "notes": "Tenant civil appeal dismissed; concurrent eviction decrees on ground of unauthorized change of user affirmed. Landlord/respondent succeeds; tenant granted time until 31.12.2000 to vacate.",
            "ambiguity": "None. Complete judgment text (30,331 chars). Operative order clearly affirms eviction and dismisses appeal."
        },
        {
            "case_id": "OIL-SC-2016_INSC_467",
            "case_title": "GREATER NOLDA IND. DEV. AUTHORITY versus SAVJTRI MOHAN (DEAD) THROUGH LRS. & ORS.",
            "court": "Supreme Court of India",
            "decision_date": "2016-06-29",
            "procedural_role": "appellant (statutory industrial development authority)",
            "action": "accept",
            "disposition": "appeal_allowed",
            "successful_party": "unresolved",
            "evidence": (
                "18. In view of the above, we allow this appeal, set aside the impugned judgment and direct disposal of the writ petitions of the respondents in terms of the judgment of this Court in Savitri Devi (supra). There will be no order as to costs.\n\n"
                "B Appeal allowed."
            ),
            "notes": "Civil statutory-authority appeal allowed; High Court judgment quashing land acquisition notifications set aside. Because this is a civil statutory-authority appeal and not a criminal prosecution, and the current taxonomy lacks a dedicated government-authority category, successful_party is categorized as 'unresolved' rather than forcing an inaccurate 'state_prosecution' label.",
            "ambiguity": "Taxonomy boundary: Civil statutory-authority appeal lacks dedicated government-authority party category; classified as unresolved."
        },
        {
            "case_id": "OIL-SC-1973_INSC_247",
            "case_title": "SK. IBRAHIM versus STATE OF WEST BENGAL AND ORS.",
            "court": "Supreme Court of India",
            "decision_date": "1973-12-19",
            "procedural_role": "petitioner (detenu)",
            "action": "accept",
            "disposition": "petition_dismissed",
            "successful_party": "respondent",
            "evidence": (
                "Where, however, as in the present case the requisite details of the activity for which the order for detention was made.. have been conveyed to the detenu B at1d he is not shown to have been prejudiced or handicapped in making an effective representation, the argument about the vague,. ness of grounds of detention must plainly be held to be not tenable.\n\n"
                "The petition consequently fails and is dismissed. S.B.W. Petition dismisJed. c"
            ),
            "notes": "Habeas corpus writ petition under MISA challenging preventive detention dismissed; grounds held not vague and representation disposed without undue delay. State of West Bengal/respondent succeeds.",
            "ambiguity": "None. Complete judgment text (13,878 chars). Concluding sentence clearly dismisses writ petition."
        },
        {
            "case_id": "OIL-SC-1979_INSC_85",
            "case_title": "N. KRISHNAMMAL versus R. EKAMBARAM & ORS.",
            "court": "Supreme Court of India",
            "decision_date": "1979-04-16",
            "procedural_role": "appellant / plaintiff (widow of son of testator)",
            "action": "accept",
            "disposition": "appeal_allowed",
            "successful_party": "petitioner",
            "evidence": (
                "For the foregoing reasons, we allow this appeal, set aside the judgment of the High Court and pass a preliminary decree for parti-tion and separate possession in favour of the plaintiff with respect to her l/3rd share in the snit property. In the circumstances of the case, the parties are left to pay and bear !heir own costs.\n\nP.B.R.\n\n[SECTION] ## Appeal allowed."
            ),
            "notes": "Civil appeal allowed; High Court judgment set aside and preliminary decree for partition and separate possession of 1/3rd share passed in favour of plaintiff-appellant widow.",
            "ambiguity": "Date reconciliation: Authoritative decision date is 1979-04-16 (confirmed in judgment text and dataset metadata)."
        },
        {
            "case_id": "OIL-SC-1998_INSC_267",
            "case_title": "HARI RAM GUPTA (DEAD) THROUGH L.R. KASTURI DEVI versus STATE OF UTTAR PRADESH",
            "court": "Supreme Court of India",
            "decision_date": "1998-07-22",
            "procedural_role": "appellant (retiree / legal representative)",
            "action": "accept",
            "disposition": "appeal_dismissed",
            "successful_party": "respondent",
            "evidence": (
                "This being the position the appellant having superannuated prior to the C Rule corning into force cannot claim the right to pension under the Rules with the help of the decision of this Court in Nakara (supra) and further in view of our conclusion that the Rules do not have any retrospective operation the relief sought for by the appellant to get pension under the Rules cannot be granted.\n\nD In the premises, as aforesaid, the appeal fails and is dismissed. But in the circumstances there will no order as to costs.\n\nv.s.s.\n\nAppeal dismissed."
            ),
            "notes": "Service pension civil appeal dismissed; 1981 Retirement Benefit Rules held non-retrospective. Retiree superannuated prior to rules held ineligible for pension. State of Uttar Pradesh succeeds as the respondent in civil proceedings.",
            "ambiguity": "None. Complete judgment text (24,518 chars). Operative concluding paragraph dismisses appeal."
        }
    ]

    # Step 4: Strict Pre-validation of Evidence Substrings & Decision Schemas
    print("\n[VALIDATION] Validating Proposed Payloads & Substring Evidence:")
    source_path = ML_SERVICE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"
    with open(source_path, "r", encoding="utf-8") as f:
        source_data = {c["id"]: c for c in json.load(f)}

    staged_payloads = []
    for d in proposed_decisions:
        cid = d["case_id"]
        ev = d["evidence"]

        # 1. Exact substring check against source judgment text
        src_case = source_data.get(cid)
        assert src_case is not None, f"Source case {cid} not found!"
        src_text = src_case["judgmentText"]
        idx = src_text.find(ev)
        assert idx != -1, f"Evidence for {cid} is NOT an exact substring of source text!"
        print(f"  [OK] {cid}: Exact substring match at offset {idx} ({len(ev)} chars)")

        # 2. No ellipses check
        assert "..." not in ev, f"Evidence for {cid} contains editorial ellipses!"

        # 3. Payload validation check
        payload = {
            "case_id": cid,
            "action": d["action"],
            "disposition": d["disposition"],
            "successful_party": d["successful_party"],
            "evidence": ev,
            "notes": d["notes"]
        }
        session._validate_decision_payload(payload)
        staged_payloads.append({
            **payload,
            "case_title": d["case_title"],
            "court": d["court"],
            "decision_date": d["decision_date"],
            "procedural_role": d["procedural_role"],
            "ambiguity_notes": d["ambiguity"],
            "source_char_offset": idx,
            "source_char_length": len(ev),
            "staged_at": datetime.now(timezone.utc).isoformat(),
            "status": "staged_pending_human_authorization"
        })

    # Step 5: Save staging JSON file
    staging_file = ML_SERVICE_DIR / "app" / "datasets" / "review_batches" / "batch_1_2_staged.json"
    staging_metadata = {
        "batch_id": "batch_1_2",
        "batch_name": "Tier 1 Pending Merits - Sub-Batch 1.2 (Adjusted)",
        "staged_at": datetime.now(timezone.utc).isoformat(),
        "total_staged": len(staged_payloads),
        "status": "staged_for_review",
        "reviewer_designate": "SNR-LEGAL-NLP-01",
        "records": staged_payloads
    }
    with open(staging_file, "w", encoding="utf-8") as f:
        json.dump(staging_metadata, f, indent=2, ensure_ascii=False)
    print(f"\n[STAGING] Staged {len(staged_payloads)} cases to {staging_file.resolve()}")

    # Step 6: Post-audit verification — ensure database stores were NOT committed
    session_after = OutcomeAnnotationSessionManager()
    dash_after = session_after.get_progress_dashboard()

    print("\n[POST-AUDIT] Verifying Database Counts Remain Unchanged (No Commit):")
    print(f"  Verified Count:    {dash_after['total_verified']} (Expected: 6)")
    print(f"  Pending Count:     {dash_after['pending']} (Expected: 144)")
    assert dash_after["total_verified"] == 6, "UNAUTHORIZED WRITE: Total verified changed!"
    assert dash_after["pending"] == 144, "UNAUTHORIZED WRITE: Total pending changed!"

    # Step 7: Cryptographic hash verification of source datasets
    integrity = session_after.verify_source_integrity()
    print("\n[POST-AUDIT] Source Integrity Check (Cryptographic SHA-256):")
    for fname, ok in integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok, f"Integrity failed for {fname}"

    print("\n" + "=" * 80)
    print("BATCH 1.2 ADJUSTMENT STAGING VERIFICATION COMPLETE — ZERO COMMITS PERFORMED")
    print("=" * 80)

if __name__ == "__main__":
    stage_batch_1_2()
