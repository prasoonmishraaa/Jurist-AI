"""
Stage Batch 1.4 Annotations for Human Review (Two-Phase Protocol)
Feature 4.12 / 4.12.2 — Pre-Commit Final Review of Batch 1.4 Staged Annotations

Guarantees:
1. Stages five Tier 1 candidate judgments with legally verified, guidelines-aligned labels:
   - OIL-SC-1981_INSC_134: remanded, successful_party: none_procedural (Supreme Court Civil Seniority Appeal; operative remand takes precedence over reporter stamp)
   - OIL-SC-1984_INSC_90: petition_allowed, successful_party: petitioner (Supreme Court Article 32 Constitutional Writ Petition)
   - OIL-SC-2012_INSC_207: petition_dismissed, successful_party: respondent (Supreme Court Special Leave Petition dismissed on merits)
   - OIL-AHC-UPHC020380352022: petition_allowed, successful_party: accused (Allahabad High Court Criminal Petition u/s 482 CrPC allowed)
   - OIL-AHC-UPHC020497422019: dismissed_as_infructuous, successful_party: none_procedural (Allahabad High Court Criminal Misc Writ Petition dismissed as infructuous)
2. Verifies exact byte-for-byte substring matches in primary source judgments (open_india_law_sample_150.json).
3. Validates decision schemas against OutcomeAnnotationSessionManager._validate_decision_payload.
4. Generates batch_1_4_staged.json and batch_1_4_review.csv in review_batches/.
5. DOES NOT commit or modify outcome_label_candidates_v2.json or outcome_label_review_v2.csv (STAGING ONLY).
6. Verifies database dashboard counts remain strictly 16 verified and 134 pending.
7. Cryptographically verifies SHA-256 source integrity.
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

def stage_batch_1_4():
    print("=" * 80)
    print("STAGE BATCH 1.4: FEATURE 4.12.2 FINAL ANNOTATION REVIEW (REFINED LABELS)")
    print("=" * 80)

    session = OutcomeAnnotationSessionManager()

    # Step 1: Pre-audit baseline state
    dash_before = session.get_progress_dashboard()
    print("\n[PRE-AUDIT] Dashboard State Before Staging:")
    print(f"  Total Candidates:    {dash_before['total_candidates']}")
    print(f"  Total Verified:      {dash_before['total_verified']} (Approved: {dash_before['approved']}, Corrected: {dash_before['corrected']})")
    print(f"  Total Pending:       {dash_before['pending']}")
    print(f"  Tier 1 Progress:     {dash_before['risk_tier_progress']['tier_1']['verified']} verified, {dash_before['risk_tier_progress']['tier_1']['pending']} pending")

    assert dash_before["total_verified"] == 16, f"Expected 16 verified, got {dash_before['total_verified']}"
    assert dash_before["pending"] == 134, f"Expected 134 pending, got {dash_before['pending']}"
    assert dash_before["risk_tier_progress"]["tier_1"]["verified"] == 16, "Expected 16 verified in Tier 1"
    assert dash_before["risk_tier_progress"]["tier_1"]["pending"] == 19, "Expected 19 pending in Tier 1"

    # Step 2: Define candidate records for Batch 1.4
    proposed_candidates = [
        {
            "case_id": "OIL-SC-1981_INSC_134",
            "case_title": "B.R. RAMABHADRIAH versus SECRETARY, FOOD & AGRICULTURE DEPARTMENT ANDHRA PRADESH & ORS.",
            "court": "Supreme Court of India",
            "decision_date": "1981-07-30",
            "proceeding_type": "civil_appellate_proceeding",
            "procedural_role": "appellant (writ petitioner / forest officer)",
            "action": "correct",
            "disposition": "remanded",
            "successful_party": "none_procedural",
            "evidence": (
                "Accordingly, we set aside the judgment of the Division Bench and remand the writ appeal to the High Court for fresh disposal in accordance with law. The parties will bear their respective costs in this appeal.\n\n"
                "[SECTION] ## N.V.K.\n\n"
                "Appeal allowed"
            ),
            "disposition_rationale": "Supreme Court set aside the Division Bench judgment of the High Court and expressly remanded the writ appeal to the High Court for fresh disposal on the merits of inter-se seniority. Under Project Quality Guideline 1.2 and Section 3.5, the operative judicial direction takes absolute precedence over editorial headnotes or trailing reporter stamps ('Appeal allowed'). Substantive disposition is remanded.",
            "party_success_rationale": "Because the appellate court remitted the proceeding to the High Court for fresh adjudication on merits rather than finally deciding seniority ranks, neither party secured a definitive substantive victory; party success is classified as none_procedural under Section 3.5 and Row 130 of the verified taxonomy.",
            "ocr_uncertainty": "Contains OCR misread in body text ('respoodent' for 'respondent', 'Forest Depertment') and includes reporter section markers '[SECTION] ## N.V.K.' and trailing reporter stamp 'Appeal allowed' with margin column letters 'A', 'B', 'c'. Full text length is 12,395 chars with zero truncation.",
            "ambiguity": "Open India Law metadata cataloged this case under 'Criminal Law' (dataset classification anomaly). Substantively it is a civil service seniority dispute under Article 226/136; proceeding type is accurately preserved as civil_appellate_proceeding. Substantive disposition is remanded rather than definitive merit allowance."
        },
        {
            "case_id": "OIL-SC-1984_INSC_90",
            "case_title": "N.L. ABHYANKAR AND OTHERS ETC. versus UNION OF INDIA",
            "court": "Supreme Court of India",
            "decision_date": "1984-04-24",
            "proceeding_type": "writ_petition",
            "procedural_role": "petitioner (retired High Court Judge / legal heirs)",
            "action": "accept",
            "disposition": "petition_allowed",
            "successful_party": "petitioner",
            "evidence": (
                "The family pension due to the_ widows will b,e calculated unper the provisions_ of the 1976 Amending Act and paid to them. Ad· hoc ·paymenis made, ifany, will be adjusted while making such pay·· _; ments. The writ petitions are disppsed of accordingly. What we_ · have· said a!iout pensionary benefits does not llPPIY to payn:tent of . gratuity. .,\n\n"
                "c\n\n"
                ",\n\n"
                "D\n\n"
                "E\n\n"
                "F\n\n"
                "N.V.K.\n\n"
                "Petition allowed."
            ),
            "disposition_rationale": "Supreme Court allowed Article 32 writ petitions challenging discriminatory cut-off dates for pension benefits of retired High Court and Supreme Court judges under the 1976 Amendment Act; concluding order explicitly directs payment of pensionary arrears and concludes with 'Petition allowed.'",
            "party_success_rationale": "Petitioners (retired judges, widows and legal heirs) succeeded against Union of India in obtaining full entitlement to amended pensionary benefits and arrears with effect from 1.10.1974.",
            "ocr_uncertainty": "Contains significant OCR noise from historical SCR volume scanning: 'b,e', 'unper', 'provisions_', 'paymenis', 'ifany', 'pay·· _; ments', 'disppsed', 'a!iout', 'llPPIY', 'payn:tent', and reporter line markers 'c', ',', 'D', 'E', 'F', 'N.V.K.'. Text length is 3,849 chars with zero truncation.",
            "ambiguity": "Body text notes 'The writ petitions are disppsed of accordingly' after specific relief grant, while terminal reporter stamp confirms 'Petition allowed.' Substantive disposition is petition_allowed."
        },
        {
            "case_id": "OIL-SC-2012_INSC_207",
            "case_title": "M/S. A.B.N.A. AND ORS. versus THE MANAGING DIRECTOR, M/S. U.P.S.I.D.C. LIMITED, KANPUR & ANR.",
            "court": "Supreme Court of India",
            "decision_date": "2012-05-08",
            "proceeding_type": "special_leave_petition",
            "procedural_role": "petitioner (industrial plot allottee)",
            "action": "accept",
            "disposition": "petition_dismissed",
            "successful_party": "respondent",
            "evidence": (
                "8. In the result, we do not find any merit in these Special Leave Petitions and accordingly we decline to grant special G leave to the petitioners to appeal against the order dated 04.03.2009 of the MRTP Commission and the order dated 05.01.2010 of the Competition Appellate Tribunal. The Special Leave Petitions are dismissed with no order as to costs.\n\n"
                "K.K.T. Special Leave Petitions dismissed."
            ),
            "disposition_rationale": "Supreme Court found no merit in Special Leave Petitions challenging interim orders of the MRTP Commission and Competition Appellate Tribunal; paragraph 8 and terminal order explicitly state: 'The Special Leave Petitions are dismissed with no order as to costs. K.K.T. Special Leave Petitions dismissed.'",
            "party_success_rationale": "Respondents (Managing Director, U.P.S.I.D.C. Limited and related authority) successfully defended against the petition; leave to appeal was denied and the petitions were dismissed in their entirety on merits.",
            "ocr_uncertainty": "Contains reporter artifact 'special G leave' (letter G indicating column position) and reporter initials 'K.K.T.' followed by column marker 'H'. Length is 14,564 chars with zero truncation.",
            "ambiguity": "Cataloged in Open India Law under 'Criminal Law' (dataset classification anomaly). Substantively a commercial/regulatory matter concerning industrial plot allotment under MRTP Act. Proceeding type is preserved as special_leave_petition; successful party is respondent."
        },
        {
            "case_id": "OIL-AHC-UPHC020380352022",
            "case_title": "/4457/2022 of INDRESH PRATAP SINGH ALIAS PIDHAI Vs STATE OF U.P. THRU. PRIN. SECY. HOME, LKO. AND ANOTHER",
            "court": "High Court of Judicature at Allahabad",
            "decision_date": "2022-07-13",
            "proceeding_type": "criminal_misc_petition_482",
            "procedural_role": "petitioner (accused applicant in judicial custody)",
            "action": "correct",
            "disposition": "petition_allowed",
            "successful_party": "accused",
            "evidence": (
                "3.  Considering  the  aforesaid  submission  and  also  taking  intoconsideration provisions of Section 311 Cr.P.C., impugned order dated01.07.2022 is set aside. The petition is allowed. Trial Court is directedto recall P.W.1 on the date fixed by the trial Court and the petitionershall have liberty to cross examine the witness on the said date only.However, the petitioner is put to cost of Rs.10,000/- which shall bedeposited by him before the trial Court within a period of 7 days fromtoday. Said cost shall be paid to P.W.-1 on the date fixed when he isrecalled for cross examination by the present petitioner."
            ),
            "disposition_rationale": "High Court exercised inherent jurisdiction under Section 482 Cr.P.C. to set aside trial court order refusing recall of prosecution witness P.W.1; paragraph 3 explicitly directs: 'impugned order dated 01.07.2022 is set aside. The petition is allowed.'",
            "party_success_rationale": "Accused applicant (Indresh Pratap Singh, undertrial in custody in Case Crime No. 176 of 2019 under Section 302/34 IPC) succeeded in securing the recall of witness P.W.1 for cross-examination, achieving substantive relief against the trial court's order.",
            "ocr_uncertainty": "Contains character-fusion artifacts from electronic PDF extraction: 'intoconsideration', 'dated01.07.2022', 'directedto', 'petitionershall', 'only.However', 'bedeposited', 'fromtoday', 'isrecalled'. Total length is 1,774 characters with complete text intact.",
            "ambiguity": "Relief granted subject to payment of Rs. 10,000 cost to P.W.1. Setting aside of trial court order and granting recall of witness constitutes substantive success for the accused petitioner."
        },
        {
            "case_id": "OIL-AHC-UPHC020497422019",
            "case_title": "CRLP/32689/2019 of SMT.MADHURI DWIVEDI and ORS. Vs STATE OF U.P.THRU.PRIN.SECY.HOME and ORS.",
            "court": "High Court of Judicature at Allahabad",
            "decision_date": "2022-03-15",
            "proceeding_type": "criminal_writ_petition",
            "procedural_role": "petitioners (accused relatives named in Section 366 IPC FIR)",
            "action": "correct",
            "disposition": "dismissed_as_infructuous",
            "successful_party": "none_procedural",
            "evidence": (
                "It appears that by efflux of time, the instant writ petition hasbecome infructuous.\n\n"
                "Accordingly,  the  present  writ  petition  is  dismissed  asinfructuous.\n\n"
                "Interim order, if any, stands vacated.\n\n"
                "However, it is open for the petitioner to move an appropriateapplication  within  two  months  from  today,  if  the  mattersurvives.\n\n"
                "It  is  made  clear  that  if  any  consequential  proceedings  areinitiated in pursuance of the impugned FIR, the parties are atliberty to take recourse to law."
            ),
            "disposition_rationale": "Under Project Quality Guidelines Section 3.6.2 and Row 131, when a cause of action lapses by efflux of time and the court orders dismissal as infructuous, the required normalized disposition is dismissed_as_infructuous (not petition_dismissed). Operative order expressly holds: 'It appears that by efflux of time, the instant writ petition hasbecome infructuous. Accordingly, the present writ petition is dismissed asinfructuous.'",
            "party_success_rationale": "Dismissal due to mootness/efflux of time and vacation of interim protection does not constitute an adjudication on merits or a substantive victory for the State prosecution. The court expressly preserved the petitioner's liberty to revive the petition within two months if the matter survives. Under Section 3.6.2 and Row 131 of the guidelines, party success is none_procedural.",
            "ocr_uncertainty": "Contains PDF text concatenation artifacts: 'hasbecome', 'asinfructuous', 'appropriateapplication', 'mattersurvives', 'areinitiated', 'atliberty'. Total text length is 1,476 characters with complete text and sign-offs intact.",
            "ambiguity": "The dismissal terminates the writ proceeding procedurally without adjudicating the legality of the Section 366 IPC FIR on the merits. Both parties are left at liberty to take recourse to law. Classified as dismissed_as_infructuous and none_procedural."
        }
    ]

    # Step 3: Strict Substring Validation & Schema Checking
    print("\n[VALIDATION] Validating Proposed Payloads & Substring Evidence:")
    source_path = ML_SERVICE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"
    with open(source_path, "r", encoding="utf-8") as f:
        source_data = {c["id"]: c for c in json.load(f)}

    staged_payloads = []
    for d in proposed_candidates:
        cid = d["case_id"]
        ev = d["evidence"]

        # 1. Exact substring check
        src_case = source_data.get(cid)
        assert src_case is not None, f"Source case {cid} not found in open_india_law_sample_150.json!"
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
            "notes": d["disposition_rationale"] + " " + d["party_success_rationale"]
        }
        session._validate_decision_payload(payload)

        staged_payloads.append({
            **payload,
            "case_title": d["case_title"],
            "court": d["court"],
            "decision_date": d["decision_date"],
            "proceeding_type": d["proceeding_type"],
            "procedural_role": d["procedural_role"],
            "disposition_rationale": d["disposition_rationale"],
            "party_success_rationale": d["party_success_rationale"],
            "ocr_uncertainty": d["ocr_uncertainty"],
            "ambiguity_notes": d["ambiguity"],
            "source_char_offset": idx,
            "source_char_length": len(ev),
            "staged_at": datetime.now(timezone.utc).isoformat(),
            "status": "staged_pending_human_authorization"
        })

    # Step 4: Write batch_1_4_staged.json
    review_batches_dir = ML_SERVICE_DIR / "app" / "datasets" / "review_batches"
    review_batches_dir.mkdir(parents=True, exist_ok=True)
    staging_file = review_batches_dir / "batch_1_4_staged.json"

    staging_metadata = {
        "batch_id": "batch_1_4",
        "batch_name": "Tier 1 Pending Judgments - Sub-Batch 1.4 (Dual Outcome Final Review)",
        "staged_at": datetime.now(timezone.utc).isoformat(),
        "total_staged": len(staged_payloads),
        "status": "staged_for_review",
        "reviewer_designate": "SNR-LEGAL-NLP-01",
        "records": staged_payloads
    }
    with open(staging_file, "w", encoding="utf-8") as f:
        json.dump(staging_metadata, f, indent=2, ensure_ascii=False)
    print(f"\n[STAGING] Wrote JSON staging file to: {staging_file.resolve()}")

    # Step 5: Write batch_1_4_review.csv
    csv_file = review_batches_dir / "batch_1_4_review.csv"
    csv_fieldnames = [
        "case_id",
        "case_title",
        "court",
        "decision_date",
        "proceeding_type",
        "procedural_role",
        "proposed_disposition",
        "proposed_successful_party",
        "source_char_offset",
        "source_char_length",
        "exact_evidence_excerpt",
        "disposition_rationale",
        "party_success_rationale",
        "ocr_extraction_uncertainty",
        "legal_review_ambiguity",
        "review_status"
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fieldnames)
        writer.writeheader()
        for r in staged_payloads:
            writer.writerow({
                "case_id": r["case_id"],
                "case_title": r["case_title"],
                "court": r["court"],
                "decision_date": r["decision_date"],
                "proceeding_type": r["proceeding_type"],
                "procedural_role": r["procedural_role"],
                "proposed_disposition": r["disposition"],
                "proposed_successful_party": r["successful_party"],
                "source_char_offset": r["source_char_offset"],
                "source_char_length": r["source_char_length"],
                "exact_evidence_excerpt": r["evidence"],
                "disposition_rationale": r["disposition_rationale"],
                "party_success_rationale": r["party_success_rationale"],
                "ocr_extraction_uncertainty": r["ocr_uncertainty"],
                "legal_review_ambiguity": r["ambiguity_notes"],
                "review_status": r["status"]
            })
    print(f"[STAGING] Wrote CSV review file to: {csv_file.resolve()}")

    # Step 6: Post-audit verification — ensure master database stores were NOT committed
    session_after = OutcomeAnnotationSessionManager()
    dash_after = session_after.get_progress_dashboard()

    print("\n[POST-AUDIT] Verifying Database Counts Remain Strictly Unchanged (No Commit):")
    print(f"  Verified Count:    {dash_after['total_verified']} (Expected: 16)")
    print(f"  Pending Count:     {dash_after['pending']} (Expected: 134)")
    assert dash_after["total_verified"] == 16, "UNAUTHORIZED WRITE: Total verified changed!"
    assert dash_after["pending"] == 134, "UNAUTHORIZED WRITE: Total pending changed!"

    # Step 7: Cryptographic hash verification of source datasets
    integrity = session_after.verify_source_integrity()
    print("\n[POST-AUDIT] Source Integrity Check (Cryptographic SHA-256):")
    for fname, ok in integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok, f"Integrity failed for {fname}"

    print("\n" + "=" * 80)
    print("BATCH 1.4 REFINED STAGING COMPLETE — ZERO COMMITS, 100% EVIDENCE VALIDATED")
    print("=" * 80)

if __name__ == "__main__":
    stage_batch_1_4()
