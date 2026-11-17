import json
import csv
from pathlib import Path

datasets_dir = Path("ml-service/app/datasets")

# 1. Check open_india_law_sample_150.json
with open(datasets_dir / "open_india_law_sample_150.json", "r", encoding="utf-8") as f:
    source_cases = json.load(f)

print(f"Total source cases: {len(source_cases)}")
for idx, c in enumerate(source_cases):
    cid = c.get("id")
    title = c.get("caseTitle", "")
    date = c.get("judgmentDate", "")
    if cid == "OIL-SC-1996_INSC_503" or "RAM NATH" in title.upper() or "RAM SWARUP" in title.upper():
        print(f"SOURCE [{idx}]: id={cid}, title={title}, date={date}")

# 2. Check outcome_label_candidates_v2.json
with open(datasets_dir / "outcome_label_candidates_v2.json", "r", encoding="utf-8") as f:
    cands_data = json.load(f)
cands = cands_data.get("records", [])
print(f"Total candidate records in v2 JSON: {len(cands)}")
for idx, c in enumerate(cands):
    cid = c.get("case_id")
    title = c.get("case_title", "")
    date = c.get("decision_date", "")
    if cid == "OIL-SC-1996_INSC_503" or "RAM NATH" in title.upper() or "RAM SWARUP" in title.upper():
        print(f"CAND_JSON [{idx}]: case_id={cid}, title={title}, date={date}")

# 3. Check outcome_label_review_v2.csv
with open(datasets_dir / "outcome_label_review_v2.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    csv_rows = list(reader)
print(f"Total CSV rows: {len(csv_rows)}")
for idx, c in enumerate(csv_rows):
    cid = c.get("case_id")
    title = c.get("case_title", "")
    date = c.get("decision_date", "")
    if cid == "OIL-SC-1996_INSC_503" or "RAM NATH" in title.upper() or "RAM SWARUP" in title.upper():
        print(f"CSV [{idx}]: case_id={cid}, title={title}, date={date}")

# 4. Check review_batches
batch_1_file = datasets_dir / "review_batches" / "batch_1_definitive_candidates.json"
if batch_1_file.exists():
    with open(batch_1_file, "r", encoding="utf-8") as f:
        b1_data = json.load(f)
    b1_recs = b1_data.get("records", b1_data.get("candidates", []))
    print(f"Total Batch 1 records: {len(b1_recs)}")
    for idx, c in enumerate(b1_recs):
        cid = c.get("case_id")
        title = c.get("case_title", "")
        date = c.get("decision_date", "")
        if cid == "OIL-SC-1996_INSC_503" or "RAM NATH" in title.upper() or "RAM SWARUP" in title.upper():
            print(f"BATCH_1 [{idx}]: case_id={cid}, title={title}, date={date}")
