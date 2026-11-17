import sys
import json
import csv
from pathlib import Path

datasets_dir = Path("ml-service/app/datasets")

with open(datasets_dir / "open_india_law_sample_150.json", "r", encoding="utf-8") as f:
    source_cases = {c["id"]: c for c in json.load(f)}

with open(datasets_dir / "outcome_label_candidates_v2.json", "r", encoding="utf-8") as f:
    cands = {c["case_id"]: c for c in json.load(f).get("records", [])}

with open(datasets_dir / "outcome_label_review_v2.csv", "r", encoding="utf-8") as f:
    csv_rows = {r["case_id"]: r for r in csv.DictReader(f)}

sys.path.insert(0, str(Path("ml-service").resolve()))
from app.prediction.outcome_annotation_session import OutcomeAnnotationSessionManager
session = OutcomeAnnotationSessionManager()

print(f"Total source cases: {len(source_cases)}")
print(f"Total candidate cases: {len(cands)}")
print(f"Total CSV cases: {len(csv_rows)}")

mismatches = []
text_issues = []
approved_records = []

for cid, sc in source_cases.items():
    cc = cands.get(cid)
    cr = csv_rows.get(cid)
    cv = session.get_case_view(cid)

    if not cc:
        mismatches.append(f"Missing in candidate JSON: {cid}")
        continue
    if not cr:
        mismatches.append(f"Missing in review CSV: {cid}")
        continue

    # Title check
    s_title = sc.get("caseTitle", "").strip()
    c_title = cc.get("case_title", "").strip()
    r_title = cr.get("case_title", "").strip()
    v_title = cv.get("case_title", "").strip()
    if not (s_title == c_title == r_title == v_title):
        mismatches.append(f"Title mismatch for {cid}: source='{s_title}', cand='{c_title}', csv='{r_title}', view='{v_title}'")

    # Date check
    s_date = sc.get("judgmentDate", "").strip()
    c_date = cc.get("decision_date", "").strip()
    r_date = cr.get("decision_date", "").strip()
    v_date = cv.get("decision_date", "").strip()
    if not (s_date == c_date == r_date == v_date):
        mismatches.append(f"Date mismatch for {cid}: source='{s_date}', cand='{c_date}', csv='{r_date}', view='{v_date}'")

    # Court check
    s_court = sc.get("court", "").strip()
    c_court = cc.get("court", "").strip()
    r_court = cr.get("court", "").strip()
    v_court = cv.get("court", "").strip()
    if not (s_court == c_court == r_court == v_court):
        mismatches.append(f"Court mismatch for {cid}: source='{s_court}', cand='{c_court}', csv='{r_court}', view='{v_court}'")

    # Text check
    s_text = sc.get("judgmentText", "")
    v_text = cv.get("full_judgment_text", "")
    if len(s_text) == 0:
        text_issues.append(f"Empty text in source: {cid}")
    if s_text != v_text:
        text_issues.append(f"Source text vs view text mismatch: {cid}")

    # Tail check
    v_tail = cv.get("concluding_tail", "")
    if not s_text.endswith(v_tail):
        text_issues.append(f"Concluding tail not at end of judgment text for {cid}")

    # Check status
    status = cc.get("review_status", "pending_review")
    if status == "approved":
        approved_records.append(cid)

print(f"\n--- Metadata & Association Mismatches: {len(mismatches)} ---")
for m in mismatches:
    print("  ", m)

print(f"\n--- Text & Tail Association Issues: {len(text_issues)} ---")
for t in text_issues:
    print("  ", t)

print(f"\n--- Approved Records Found: {len(approved_records)} ---")
print("  Approved Case IDs:", approved_records)

# Check all non-approved records
unapproved_with_labels = []
for cid, cc in cands.items():
    if cid not in approved_records:
        status = cc.get("review_status")
        lbl = cc.get("human_approved_label")
        if status != "pending_review" or lbl:
            unapproved_with_labels.append((cid, status, lbl))

print(f"\n--- Non-Approved Cases with Non-Pending Status or Labels: {len(unapproved_with_labels)} ---")
for item in unapproved_with_labels:
    print("  ", item)
