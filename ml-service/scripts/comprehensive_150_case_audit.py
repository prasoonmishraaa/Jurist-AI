import sys
import json
import csv
from pathlib import Path

datasets_dir = Path("ml-service/app/datasets")

# Load source dataset
with open(datasets_dir / "open_india_law_sample_150.json", "r", encoding="utf-8") as f:
    source_cases = json.load(f)

# Load candidate JSON
with open(datasets_dir / "outcome_label_candidates_v2.json", "r", encoding="utf-8") as f:
    cands_json = json.load(f).get("records", [])

# Load review CSV
with open(datasets_dir / "outcome_label_review_v2.csv", "r", encoding="utf-8") as f:
    csv_rows = list(csv.DictReader(f))

# Load review_batches
batch_dir = datasets_dir / "review_batches"
batch_records = {}
for bf in batch_dir.glob("*.json"):
    with open(bf, "r", encoding="utf-8") as f:
        bdata = json.load(f)
        recs = bdata.get("records", bdata.get("candidates", []))
        batch_records[bf.name] = recs

print(f"Source count:      {len(source_cases)}")
print(f"Candidates JSON:   {len(cands_json)}")
print(f"Review CSV:        {len(csv_rows)}")
print(f"Batch files found: {list(batch_records.keys())}")
for bname, brecs in batch_records.items():
    print(f"  {bname}: {len(brecs)} records")

# Dictionaries indexed by ID
source_by_id = {c["id"]: c for c in source_cases if "id" in c}
cands_by_id = {c["case_id"]: c for c in cands_json if "case_id" in c}
csv_by_id = {c["case_id"]: c for c in csv_rows if "case_id" in c}

source_ids = set(source_by_id.keys())
cands_ids = set(cands_by_id.keys())
csv_ids = set(csv_by_id.keys())

print("\n--- 1. ID SET COMPARISON ---")
print(f"Unique source IDs:    {len(source_ids)}")
print(f"Unique candidate IDs: {len(cands_ids)}")
print(f"Unique CSV IDs:       {len(csv_ids)}")

diff_source_cand = source_ids.symmetric_difference(cands_ids)
diff_source_csv = source_ids.symmetric_difference(csv_ids)
print(f"Symmetric diff (source vs candidate JSON): {diff_source_cand}")
print(f"Symmetric diff (source vs review CSV):     {diff_source_csv}")

# Check duplicates
print("\n--- 2. DUPLICATE ID CHECK ---")
source_id_list = [c["id"] for c in source_cases if "id" in c]
cand_id_list = [c["case_id"] for c in cands_json if "case_id" in c]
csv_id_list = [c["case_id"] for c in csv_rows if "case_id" in c]

dup_source = [cid for cid, count in Counter(source_id_list).items() if count > 1] if 'Counter' in globals() else []
from collections import Counter
dup_source = [cid for cid, count in Counter(source_id_list).items() if count > 1]
dup_cands = [cid for cid, count in Counter(cand_id_list).items() if count > 1]
dup_csv = [cid for cid, count in Counter(csv_id_list).items() if count > 1]
print(f"Duplicate IDs in source:     {dup_source}")
print(f"Duplicate IDs in candidate:  {dup_cands}")
print(f"Duplicate IDs in review CSV: {dup_csv}")

# Cross-field integrity checks for all 150 IDs
title_mismatches = []
date_mismatches = []
court_mismatches = []
text_missing = []
matched_text_missing = []

for cid in source_ids:
    s = source_by_id[cid]
    c = cands_by_id[cid]
    r = csv_by_id[cid]

    s_title = (s.get("caseTitle") or "").strip()
    c_title = (c.get("case_title") or "").strip()
    r_title = (r.get("case_title") or "").strip()

    # Compare titles (normalize casing and spaces)
    if s_title.lower() != c_title.lower() or c_title.lower() != r_title.lower():
        title_mismatches.append((cid, s_title, c_title, r_title))

    s_date = (s.get("judgmentDate") or "").strip()
    c_date = (c.get("decision_date") or "").strip()
    r_date = (r.get("decision_date") or "").strip()
    if s_date != c_date or c_date != r_date:
        date_mismatches.append((cid, s_date, c_date, r_date))

    s_court = (s.get("court") or "").strip()
    c_court = (c.get("court") or "").strip()
    r_court = (r.get("court") or "").strip()
    if s_court.lower() != c_court.lower() or c_court.lower() != r_court.lower():
        court_mismatches.append((cid, s_court, c_court, r_court))

    jtext = s.get("judgmentText", "")
    if not jtext or len(jtext.strip()) == 0:
        text_missing.append(cid)

    # Check matched text
    matched = c.get("matched_text", "")
    if matched and matched not in jtext:
        # Check if matched text might be slightly stripped
        if matched.strip() not in jtext:
            matched_text_missing.append((cid, matched[:50]))

print("\n--- 3. FIELD-LEVEL MISMATCHES (SOURCE vs CANDIDATE vs CSV) ---")
print(f"Title mismatches:        {len(title_mismatches)}")
for m in title_mismatches[:5]:
    print(f"  {m[0]}: Source='{m[1]}' vs Cand='{m[2]}' vs CSV='{m[3]}'")

print(f"Date mismatches:         {len(date_mismatches)}")
for m in date_mismatches[:5]:
    print(f"  {m[0]}: Source='{m[1]}' vs Cand='{m[2]}' vs CSV='{m[3]}'")

print(f"Court mismatches:        {len(court_mismatches)}")
for m in court_mismatches[:5]:
    print(f"  {m[0]}: Source='{m[1]}' vs Cand='{m[2]}' vs CSV='{m[3]}'")

print(f"Missing judgment text:   {len(text_missing)}")
print(f"Matched text not in raw: {len(matched_text_missing)}")
for m in matched_text_missing[:5]:
    print(f"  {m[0]}: '{m[1]}...'")

# Check review_batches consistency
print("\n--- 4. REVIEW BATCHES CONSISTENCY ---")
for bname, brecs in batch_records.items():
    batch_title_mismatch = 0
    batch_missing_in_source = 0
    for r in brecs:
        bcid = r.get("case_id")
        if bcid not in source_by_id:
            batch_missing_in_source += 1
        else:
            st = source_by_id[bcid].get("caseTitle", "").strip().lower()
            bt = (r.get("case_title") or "").strip().lower()
            if st != bt:
                batch_title_mismatch += 1
    print(f"  Batch '{bname}': {len(brecs)} recs, missing in source={batch_missing_in_source}, title mismatches={batch_title_mismatch}")
