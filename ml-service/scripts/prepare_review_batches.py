import os
import json
import csv
from datetime import datetime

DATASETS_DIR = "ml-service/app/datasets"
BATCHES_DIR = os.path.join(DATASETS_DIR, "review_batches")
os.makedirs(BATCHES_DIR, exist_ok=True)

source_path = os.path.join(DATASETS_DIR, "open_india_law_sample_150.json")
candidates_path = os.path.join(DATASETS_DIR, "outcome_label_candidates.json")

with open(source_path, "r", encoding="utf-8") as f:
    source_cases = json.load(f)
source_dict = {c["id"]: c for c in source_cases}

with open(candidates_path, "r", encoding="utf-8") as f:
    cand_data = json.load(f)
candidates = cand_data["candidates"]

def infer_proceeding_type(case_id, title, identifier, category, text):
    cid = (identifier or "").upper()
    t = (title or "").upper()
    c = (category or "").upper()
    
    if "BAIL APPLN" in cid or "BAIL" in cid or "BAIL" in t:
        return "bail_application"
    if "CRL.M.C." in cid or "SECTION 482" in t or "482" in cid:
        return "quashing_petition_s482"
    if "CRL.REV.P." in cid or "REVISION" in cid:
        return "criminal_revision"
    if "MAC.APP." in cid:
        return "motor_accident_appeal"
    if "RFA" in cid or "CIVIL APPEAL" in cid or "CIVIL APPEAL" in t:
        return "civil_appeal"
    if "W.P.(CRL)" in cid or "CRLP" in cid:
        return "criminal_writ_petition"
    if "W.P.(C)" in cid or "W.P." in cid or "WRIT PETITION" in t:
        return "civil_writ_petition"
    if "CONTEMPT" in cid or "CONTEMPT" in t:
        return "contempt_petition"
    if "WPIL" in cid or "PIL" in t:
        return "public_interest_litigation"
    if "APPEAL" in cid or "CRIMINAL APPEAL" in t or "INSC" in case_id:
        if "CRIMINAL" in c or "CRIMINAL" in t or "ACCUSED" in t:
            return "criminal_appeal"
        return "appellate_proceeding"
    return "unspecified_proceeding"

def normalize_disposition_and_recommendation(candidate, raw_text):
    cat = candidate["candidate_disposition"]
    phrase = candidate.get("original_disposition_phrase", "")
    ctx = candidate.get("matched_text", "")
    t_len = len(raw_text)
    
    if cat == "disposed_with_directions":
        full_str = (phrase + " " + ctx).lower()
        if "infructuous" in full_str:
            norm_disp = "dismissed_as_infructuous"
            rec = "Confirm whether proceeding was rendered moot by efflux of time. Exclude from merits ML training."
            party = "none_procedural"
        elif any(w in full_str for w in ["direction", "directed", "shall", "protection", "liberty", "representation", "expeditiously"]):
            norm_disp = "disposed_with_substantive_directions"
            rec = "Confirm whether substantive directions (e.g. police protection, expedited hearing) were granted to petitioner."
            party = "petitioner"
        else:
            norm_disp = "disposed_procedural"
            rec = "Verify if disposal is purely procedural or carries substantive findings."
            party = "none_procedural"
        return norm_disp, party, rec
        
    elif cat == "appeal_allowed":
        norm_disp = "appeal_allowed"
        rec = "Verify whether appellate challenge was brought by State or Accused/Appellant to assign human_successful_party correctly."
        party = candidate.get("party_success", "unresolved")
        if party == "favorable_to_accused":
            party = "accused"
        elif party == "unfavorable_to_accused":
            party = "state_prosecution"
        return norm_disp, party, rec
        
    elif cat == "appeal_dismissed":
        norm_disp = "appeal_dismissed"
        rec = "CRITICAL: Check who appealed. If State appealed against acquittal, dismiss is favorable to accused. If accused appealed, unfavorable."
        party = candidate.get("party_success", "unresolved")
        if party == "favorable_to_accused":
            party = "accused"
        elif party == "unfavorable_to_accused":
            party = "state_prosecution"
        return norm_disp, party, rec
        
    elif cat == "bail_granted":
        norm_disp = "bail_granted"
        rec = "Verify regular or anticipatory bail conditions. Recommended approval with successful_party='accused'. Note: Bail is not acquittal."
        return norm_disp, "accused", rec
        
    elif cat == "bail_rejected":
        norm_disp = "bail_rejected"
        rec = "Verify grounds of bail refusal (gravity of offence / criminal history). Recommended approval with successful_party='state_prosecution'."
        return norm_disp, "state_prosecution", rec
        
    elif cat == "partly_allowed":
        norm_disp = "partly_allowed"
        rec = "Verify nature of partial relief (e.g. sentence reduction, Section 302 altered to 304). Note: Do NOT use for binary win/loss classification."
        return norm_disp, "unresolved", rec
        
    elif cat == "petition_allowed":
        norm_disp = "petition_allowed"
        rec = "Verify relief granted in writ / revision petition. Recommended approval with successful_party='petitioner'."
        return norm_disp, "petitioner", rec
        
    elif cat == "petition_dismissed":
        norm_disp = "petition_dismissed"
        rec = "Verify petition dismissal on merits. Recommended approval with successful_party='respondent'."
        return norm_disp, "respondent", rec
        
    elif cat == "withdrawn":
        norm_disp = "withdrawn"
        rec = "Confirm whether withdrawal was voluntary without adjudication on merits. Exclude from outcome prediction models."
        return norm_disp, "none_procedural", rec
        
    elif cat == "remanded":
        norm_disp = "remanded"
        rec = "Confirm impugned order set aside and remanded to lower forum for rehearing. Exclude from final outcome classification."
        return norm_disp, "none_procedural", rec
        
    elif cat == "ambiguous":
        norm_disp = "ambiguous"
        rec = "INSPECT CONTRADICTION: Check whether judgment had multiple appeals with split holdings or hypothetical conditional phrases."
        return norm_disp, "unresolved", rec
        
    elif cat == "unknown":
        if t_len >= 39900:
            norm_disp = "unknown_truncated_text"
            rec = "DEFER: Text truncated at 40,000 character ingestion limit. Operative order cut off. Review full text on official court portal."
        elif any(w in raw_text[-1500:].lower() for w in ["larger bench", "refer", "notice", "interim"]):
            norm_disp = "interlocutory_reference"
            rec = "Verify non-dispositive status: reference to Larger Bench, notice stage, or interim stay order."
        else:
            norm_disp = "unknown"
            rec = "Examine concluding section. If questions of law framed without final disposition, mark non-dispositive."
        return norm_disp, "unresolved", rec
        
    return cat, "unresolved", "Review operative text."

enhanced_records = []
for c in candidates:
    cid = c["case_id"]
    src = source_dict[cid]
    raw_text = src.get("judgmentText", "")
    
    proc_type = infer_proceeding_type(
        case_id=cid,
        title=c.get("case_title", ""),
        identifier=src.get("caseIdentifier", ""),
        category=c.get("case_type", ""),
        text=raw_text[:2000]
    )
    
    norm_disp, successful_party, rec_action = normalize_disposition_and_recommendation(c, raw_text)
    
    # Context window: surrounding sentence or last 400 chars of text if unknown
    if c["candidate_disposition"] == "unknown":
        context_snippet = raw_text[-400:].strip().replace("\n", " ")
        evidence_ref = f"Tail text (chars {len(raw_text)-400}:{len(raw_text)})"
    else:
        context_snippet = c.get("matched_text", "").strip().replace("\n", " ")
        evidence_ref = f"Chars {c.get('source_start_offset', -1)}:{c.get('source_end_offset', -1)}"
        
    record = {
        "case_id": cid,
        "case_title": c.get("case_title", ""),
        "court": c.get("court", ""),
        "decision_date": c.get("decision_date", ""),
        "proceeding_type": proc_type,
        "original_disposition": c.get("candidate_disposition", ""),
        "normalized_disposition": norm_disp,
        "successful_party": successful_party,
        "original_disposition_phrase": c.get("original_disposition_phrase", ""),
        "matched_text": context_snippet,
        "source_start_offset": c.get("source_start_offset", -1),
        "source_end_offset": c.get("source_end_offset", -1),
        "procedural_role": c.get("party_role", "unresolved"),
        "parser_confidence": c.get("extraction_confidence", 0.0),
        "recommended_action": rec_action,
        "evidence_reference": evidence_ref,
        "human_approved_label": "",
        "human_successful_party": "",
        "human_notes": "",
        "reviewer_reference": "",
        "review_status": "pending_review",
        "ambiguity_reason": c.get("ambiguity_reason", "")
    }
    enhanced_records.append(record)

print(f"Generated {len(enhanced_records)} enhanced review records.")

# Split into 3 batches
batch_1 = [r for r in enhanced_records if r["original_disposition"] not in ("unknown", "ambiguous")]
batch_2 = [r for r in enhanced_records if r["original_disposition"] == "ambiguous"]
batch_3 = [r for r in enhanced_records if r["original_disposition"] == "unknown"]

print(f"Batch 1 (Definitive Candidates): {len(batch_1)}")
print(f"Batch 2 (Ambiguous Candidates):  {len(batch_2)}")
print(f"Batch 3 (Unknown Candidates):    {len(batch_3)}")

def export_batch_json(records, batch_name, path):
    payload = {
        "metadata": {
            "batch_name": batch_name,
            "generated_at": datetime.now().isoformat(),
            "record_count": len(records),
            "review_status": "pending_human_review",
            "protocol_reference": "ml-service/app/prediction/outcome_annotation_guidelines.md"
        },
        "records": records
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Exported JSON: {path}")

def export_batch_csv(records, path):
    if not records:
        return
    fieldnames = list(records[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    print(f"Exported CSV:  {path}")

# Export batches
export_batch_json(batch_1, "Batch 1: Definitive Candidates", os.path.join(BATCHES_DIR, "batch_1_definitive_candidates.json"))
export_batch_csv(batch_1, os.path.join(BATCHES_DIR, "batch_1_definitive_candidates.csv"))

export_batch_json(batch_2, "Batch 2: Ambiguous Candidates", os.path.join(BATCHES_DIR, "batch_2_ambiguous_candidates.json"))
export_batch_csv(batch_2, os.path.join(BATCHES_DIR, "batch_2_ambiguous_candidates.csv"))

export_batch_json(batch_3, "Batch 3: Unknown Candidates", os.path.join(BATCHES_DIR, "batch_3_unknown_candidates.json"))
export_batch_csv(batch_3, os.path.join(BATCHES_DIR, "batch_3_unknown_candidates.csv"))

# Export master files
master_json_path = os.path.join(DATASETS_DIR, "outcome_label_candidates_v2.json")
master_csv_path = os.path.join(DATASETS_DIR, "outcome_label_review_v2.csv")
export_batch_json(enhanced_records, "Master Human Review Queue (150 Cases)", master_json_path)
export_batch_csv(enhanced_records, master_csv_path)

print("Batch preparation complete.")
