import json
import csv
from pathlib import Path

datasets_dir = Path("ml-service/app/datasets")

# 1. Source record
with open(datasets_dir / "open_india_law_sample_150.json", "r", encoding="utf-8") as f:
    source_cases = {c["id"]: c for c in json.load(f)}
s = source_cases.get("OIL-SC-2021_INSC_327")
print("=== 1. SOURCE RECORD (open_india_law_sample_150.json) ===")
print("ID:           ", s.get("id"))
print("Title:        ", s.get("caseTitle"))
print("Date:         ", s.get("judgmentDate"))
print("Court:        ", s.get("court"))
print("Length:       ", len(s.get("judgmentText", "")))
print("Text Start:   ", repr(s.get("judgmentText", "")[:200]))
print("Text End:     ", repr(s.get("judgmentText", "")[-300:]))

# 2. Candidate JSON
with open(datasets_dir / "outcome_label_candidates_v2.json", "r", encoding="utf-8") as f:
    cands_json = {c["case_id"]: c for c in json.load(f).get("records", [])}
c = cands_json.get("OIL-SC-2021_INSC_327")
print("\n=== 2. CANDIDATE JSON (outcome_label_candidates_v2.json) ===")
print("case_id:      ", c.get("case_id"))
print("case_title:   ", c.get("case_title"))
print("decision_date:", c.get("decision_date"))
print("court:        ", c.get("court"))
print("review_status:", c.get("review_status"))
print("approved_lbl: ", c.get("human_approved_label"))
print("succ_party:   ", c.get("human_successful_party"))
print("reviewer_ref: ", c.get("reviewer_reference"))
print("evidence_ref: ", c.get("evidence_reference"))
print("human_notes:  ", c.get("human_notes"))
print("audit_history:", json.dumps(c.get("audit_history", []), indent=2))

# 3. Review CSV
with open(datasets_dir / "outcome_label_review_v2.csv", "r", encoding="utf-8") as f:
    csv_rows = {row["case_id"]: row for row in csv.DictReader(f)}
r = csv_rows.get("OIL-SC-2021_INSC_327")
print("\n=== 3. REVIEW CSV (outcome_label_review_v2.csv) ===")
print("case_id:      ", r.get("case_id"))
print("case_title:   ", r.get("case_title"))
print("decision_date:", r.get("decision_date"))
print("court:        ", r.get("court"))
print("review_status:", r.get("review_status"))
print("approved_lbl: ", r.get("human_approved_label"))
print("succ_party:   ", r.get("human_successful_party"))
print("reviewer_ref: ", r.get("reviewer_reference"))
print("evidence_ref: ", r.get("evidence_reference"))

# 4. Review Batch 1
with open(datasets_dir / "review_batches" / "batch_1_definitive_candidates.json", "r", encoding="utf-8") as f:
    b1_recs = {rec["case_id"]: rec for rec in json.load(f).get("records", [])}
b1 = b1_recs.get("OIL-SC-2021_INSC_327")
print("\n=== 4. BATCH 1 FILE ===")
print("case_id:      ", b1.get("case_id"))
print("case_title:   ", b1.get("case_title"))
print("decision_date:", b1.get("decision_date"))
print("court:        ", b1.get("court"))

# 5. Check whether the approved evidence quote exists in the source judgment text
print("\n=== 5. EVIDENCE VERIFICATION IN SOURCE TEXT ===")
evidence_text = c.get("evidence_reference", "")
print("Evidence quote to verify:")
print(repr(evidence_text))
jtext = s.get("judgmentText", "")
print(f"Is evidence in source judgment text? {evidence_text in jtext}")
if not (evidence_text in jtext):
    # Try searching for substring
    clean_ev = "wholly unjustified, unwarranted, arbitrary and illegal"
    print(f"Is '{clean_ev}' in source text? {clean_ev in jtext}")
    clean_ev2 = "The same are set aside and the appeal is allowed with no order as to costs"
    print(f"Is '{clean_ev2}' in source text? {clean_ev2 in jtext}")
