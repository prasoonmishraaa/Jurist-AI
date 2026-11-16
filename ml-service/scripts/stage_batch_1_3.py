"""
Stage Batch 1.3 Annotations for Human Review (Two-Phase Protocol)
Feature 4.11 — Prepare Outcome Annotation Batch 1.3

Guarantees:
1. Stages five Tier 1 candidate judgments prioritizing criminal appeals and petitions:
   - OIL-SC-2006_INSC_699: appeal_allowed, successful_party: accused (Supreme Court Criminal Appeal)
   - OIL-SC-2010_INSC_109: appeal_dismissed, successful_party: state_prosecution (Supreme Court Criminal Appeal)
   - OIL-AHC-UPHC020034182022: appeal_allowed, successful_party: accused (Allahabad High Court Criminal Appeal)
   - OIL-DHC-DLHC015857912015: petition_allowed, successful_party: petitioner (Delhi High Court Criminal Petition u/s 482 CrPC)
   - OIL-SC-1992_INSC_350: appeal_dismissed, successful_party: respondent (Supreme Court Appeal / dataset criminal_appeal metadata)
2. Verifies exact byte-for-byte substring matches in primary source judgments (open_india_law_sample_150.json).
3. Validates decision schemas against OutcomeAnnotationSessionManager._validate_decision_payload.
4. Generates batch_1_3_staged.json and batch_1_3_review.csv.
5. DOES NOT commit or modify outcome_label_candidates_v2.json or outcome_label_review_v2.csv.
6. Verifies database dashboard counts remain exactly 11 verified and 139 pending.
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

def stage_batch_1_3():
    print("=" * 80)
    print("STAGE BATCH 1.3: FEATURE 4.11 CANDIDATE PREPARATION (CRIMINAL APPEALS)")
    print("=" * 80)

    session = OutcomeAnnotationSessionManager()

    # Step 1: Pre-audit baseline state
    dash_before = session.get_progress_dashboard()
    print("\n[PRE-AUDIT] Dashboard State Before Staging:")
    print(f"  Total Candidates:    {dash_before['total_candidates']}")
    print(f"  Total Verified:      {dash_before['total_verified']} (Approved: {dash_before['approved']}, Corrected: {dash_before['corrected']})")
    print(f"  Total Pending:       {dash_before['pending']}")
    print(f"  Tier 1 Progress:     {dash_before['risk_tier_progress']['tier_1']['verified']} verified, {dash_before['risk_tier_progress']['tier_1']['pending']} pending")

    assert dash_before["total_verified"] == 11, f"Expected 11 verified, got {dash_before['total_verified']}"
    assert dash_before["pending"] == 139, f"Expected 139 pending, got {dash_before['pending']}"
    assert dash_before["risk_tier_progress"]["tier_1"]["verified"] == 11, "Expected 11 verified in Tier 1"
    assert dash_before["risk_tier_progress"]["tier_1"]["pending"] == 24, "Expected 24 pending in Tier 1"

    # Step 2: Define candidate records for Batch 1.3
    proposed_candidates = [
        {
            "case_id": "OIL-SC-2006_INSC_699",
            "case_title": "ISHWARCHAND AMICHAND GOVADIA AND ORS. versus STATE OF MAHARASHTRA AND ANR.",
            "court": "Supreme Court of India",
            "decision_date": "2006-10-13",
            "proceeding_type": "criminal_appeal",
            "procedural_role": "appellant (accused)",
            "action": "accept",
            "disposition": "appeal_allowed",
            "successful_party": "accused",
            "evidence": (
                "That being so, it would be proper for the Trial Court to defer the question of framing charge under Section 3048 after F examination of Dr. R.M. Dhotre and relevance of the subsequent certificate and its acceptability.\n\n"
                "The High Court has failed to consider the relevant aspects and, should not have dismissed the application. The impugned order is set aside.\n\n"
                "The appeal is allowed."
            ),
            "disposition_rationale": "Supreme Court set aside the High Court order dismissing application against premature alteration/framing of charge under Section 304B IPC; operative concluding text unequivocally states 'The impugned order is set aside. The appeal is allowed.'",
            "party_success_rationale": "Accused appellants succeeded in reversing the trial court and High Court orders, securing postponement of framing of Section 304B dowry death charge until medical witness Dr. Dhotre is examined.",
            "ocr_uncertainty": "Contains OCR misread of letter 'B' as numeral '8' in 'Section 3048' (referring to Section 304B IPC), along with margin reporter artifact 'after F examination' and trailing 'D.G. G'.",
            "ambiguity": "None regarding operative relief or party success. Operative order explicitly sets aside impugned order and allows appeal."
        },
        {
            "case_id": "OIL-SC-2010_INSC_109",
            "case_title": "ABDUL MANNAN versus STATE OF ASSAM",
            "court": "Supreme Court of India",
            "decision_date": "2010-02-18",
            "proceeding_type": "criminal_appeal",
            "procedural_role": "appellant (convicted accused)",
            "action": "accept",
            "disposition": "appeal_dismissed",
            "successful_party": "state_prosecution",
            "evidence": (
                "22. The appeal, being devoid of any merit, is accordingly dismissed. The bail bonds of the appellant, who is on bail, are C cancelled and he shall surrender to the court. In case the appellant does not surrender within four weeks, the respondent-State would take all necessary steps to arrest the appellant and lodge him in jail to serve out the remaining period of sentence.\n\n"
                "D.G.\n\n"
                "Appeal dismissed. D"
            ),
            "disposition_rationale": "Supreme Court affirmed conviction under Section 304 Part II IPC and 4-year sentence, dismissing the appeal in paragraph 22 and terminal order stamp.",
            "party_success_rationale": "State of Assam as prosecuting authority succeeded in defending the High Court's reversal of trial court acquittal; appellant's bail cancelled and State directed to lodge appellant in jail.",
            "ocr_uncertainty": "Includes reporter column markers 'are C cancelled' and trailing reporter stamp 'Appeal dismissed. D'. Text length is 17,947 characters with zero truncation.",
            "ambiguity": "None. Appellant was acquitted by trial court, convicted by High Court on State appeal, and Supreme Court affirmed conviction on accused's appeal. State/prosecution successfully defended conviction."
        },
        {
            "case_id": "OIL-AHC-UPHC020034182022",
            "case_title": "/188/2022 of RAMAKANT AND 2 OTHERS Vs STATE OF U.P. THROUGH PRIN. SECY. HOME LKO AND ANOTHER",
            "court": "High Court of Judicature at Allahabad",
            "decision_date": "2022-06-07",
            "proceeding_type": "criminal_appeal",
            "procedural_role": "appellants (accused)",
            "action": "accept",
            "disposition": "appeal_allowed",
            "successful_party": "accused",
            "evidence": (
                "(v) The applicants shall remain present, in person,before  the  trial  court  on  the  dates  fixed  for  (i)opening of the case, (ii) framing of charge and (iii)recording of statement under Section 313 Cr.P.C. Ifin the opinion  of the trial  court absence of theapplicant is deliberate or without sufÏcient cause,then it shall be open for the trial court to treatsuch default as abuse of liberty of bail and proceedagainst him in accordance with law.\n\n"
                "9.  Subject  to  above  noted  terms,  the  appeal  isallowed and the impugned order dated 24.11.2021is hereby set aside."
            ),
            "disposition_rationale": "Statutory criminal appeal under Section 14-A(1) of SC/ST (Prevention of Atrocities) Act allowed by High Court; operative paragraph 9 unequivocally sets aside impugned order dated 24.11.2021.",
            "party_success_rationale": "Accused appellants succeeded in setting aside trial court order dated 24.11.2021 subject to appearance conditions.",
            "ocr_uncertainty": "Contains character-fusion artifacts from electronic PDF text extraction: 'in person,before', 'Ifin', 'theapplicant', 'sufÏcient' (special ligature character Ï for ffi), 'proceedagainst', 'isallowed', and '24.11.2021is'.",
            "ambiguity": "Relief granted subject to conditions of personal appearance on specific dates; setting aside of impugned order constitutes merits victory for accused."
        },
        {
            "case_id": "OIL-DHC-DLHC015857912015",
            "case_title": "CRL.M.C./4714/2015 of MOHD NADEEM & ORS Vs THE STATE GOVT OF DELHI & ANR",
            "court": "High Court of Delhi",
            "decision_date": "2016-03-15",
            "proceeding_type": "criminal_misc_petition_482",
            "procedural_role": "petitioners (accused family members)",
            "action": "accept",
            "disposition": "petition_allowed",
            "successful_party": "petitioner",
            "evidence": (
                "13.In the facts and circumstances of this case, in view of statementmade by the respondent No.2 and the compromise arrived at betweenthe parties, the FIR in question warrants to be put to an end andproceedings emanating thereupon need to be quashed.\n\n"
                "14.Accordingly, this petition is allowed and FIR No.174/2013dated 13.05.2013, under Sections 498A/406/34 IPC and Section 4\n\n"
                "Dowry Prohibition Act registered at Police Station Jyoti Nagar and theproceedings emanating therefrom are quashed against the petitioners.15.This petition is accordingly disposed of."
            ),
            "disposition_rationale": "High Court exercised inherent jurisdiction under Section 482 Cr.P.C., expressly holding in paragraph 14: 'Accordingly, this petition is allowed and FIR... and the proceedings emanating therefrom are quashed against the petitioners.'",
            "party_success_rationale": "Petitioners (accused family members) obtained complete quashing of criminal prosecution and FIR registered under Sections 498A/406/34 IPC and Section 4 Dowry Prohibition Act.",
            "ocr_uncertainty": "Contains PDF text concatenation artifacts: 'statementmade', 'betweenthe', 'andproceedings', '14.Accordingly', 'No.174/2013dated', 'theproceedings', 'petitioners.15.This'.",
            "ambiguity": "Paragraph 15 adds 'This petition is accordingly disposed of' after Paragraph 14 specifically allowed the petition and quashed the FIR. Operative substantive disposition is petition_allowed."
        },
        {
            "case_id": "OIL-SC-1992_INSC_350",
            "case_title": "BRITISH MACHINARY SUPPLIES COMPANY versus UNLON OF INDIA AND ORS.",
            "court": "Supreme Court of India",
            "decision_date": "1992-12-17",
            "proceeding_type": "civil_appellate_proceeding",
            "procedural_role": "appellant (commercial purchaser)",
            "action": "accept",
            "disposition": "appeal_dismissed",
            "successful_party": "respondent",
            "evidence": (
                "In the circumstances, we are of the view that the justification or the relevance of the increase in the price cannot be attacked by the appellant.\n\n"
                "F\n\n"
                "17. In the result, the appeal fails and is dismissed with costs.\n\n"
                "G.N.\n\n"
                "Appeal dismissed."
            ),
            "disposition_rationale": "Supreme Court rejected challenge to price fixation for imported steel sheets; paragraph 17 explicitly holds: 'In the result, the appeal fails and is dismissed with costs.'",
            "party_success_rationale": "Respondents (Union of India and Steel Authority of India Ltd.) succeeded in defending validity of price fixation, and appeal was dismissed with costs.",
            "ocr_uncertainty": "Contains OCR misread in case title ('UNLON OF INDIA' instead of 'UNION OF INDIA') and internal typos ('polic_:y', '~such hnported'), with margin markers 'F' and reporter stamp 'G.N. Appeal dismissed.'",
            "ambiguity": "Dataset proceeding anomaly: Open India Law cataloged this record under category 'Criminal Law' and proceeding_type 'criminal_appeal'. Substantive analysis confirms an administrative/commercial price challenge. Successful party is classified as 'respondent' (not state_prosecution)."
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

    # Step 4: Write batch_1_3_staged.json
    review_batches_dir = ML_SERVICE_DIR / "app" / "datasets" / "review_batches"
    review_batches_dir.mkdir(parents=True, exist_ok=True)
    staging_file = review_batches_dir / "batch_1_3_staged.json"

    staging_metadata = {
        "batch_id": "batch_1_3",
        "batch_name": "Tier 1 Pending Criminal Appeals & Petitions - Sub-Batch 1.3",
        "staged_at": datetime.now(timezone.utc).isoformat(),
        "total_staged": len(staged_payloads),
        "status": "staged_for_review",
        "reviewer_designate": "SNR-LEGAL-NLP-01",
        "records": staged_payloads
    }
    with open(staging_file, "w", encoding="utf-8") as f:
        json.dump(staging_metadata, f, indent=2, ensure_ascii=False)
    print(f"\n[STAGING] Wrote JSON staging file to: {staging_file.resolve()}")

    # Step 5: Write batch_1_3_review.csv
    csv_file = review_batches_dir / "batch_1_3_review.csv"
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

    # Step 6: Post-audit verification — ensure database stores were NOT committed
    session_after = OutcomeAnnotationSessionManager()
    dash_after = session_after.get_progress_dashboard()

    print("\n[POST-AUDIT] Verifying Database Counts Remain Strictly Unchanged (No Commit):")
    print(f"  Verified Count:    {dash_after['total_verified']} (Expected: 11)")
    print(f"  Pending Count:     {dash_after['pending']} (Expected: 139)")
    assert dash_after["total_verified"] == 11, "UNAUTHORIZED WRITE: Total verified changed!"
    assert dash_after["pending"] == 139, "UNAUTHORIZED WRITE: Total pending changed!"

    # Step 7: Cryptographic hash verification of source datasets
    integrity = session_after.verify_source_integrity()
    print("\n[POST-AUDIT] Source Integrity Check (Cryptographic SHA-256):")
    for fname, ok in integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok, f"Integrity failed for {fname}"

    print("\n" + "=" * 80)
    print("BATCH 1.3 STAGING COMPLETE — ZERO COMMITS, 100% EVIDENCE VALIDATED")
    print("=" * 80)

if __name__ == "__main__":
    stage_batch_1_3()
