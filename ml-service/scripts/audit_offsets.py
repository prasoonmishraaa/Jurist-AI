import json
from pathlib import Path

datasets_dir = Path("ml-service/app/datasets")
with open(datasets_dir / "outcome_label_candidates_v2.json", "r", encoding="utf-8") as f:
    cands = json.load(f)["records"]

offset_neg1 = [c for c in cands if c.get("source_start_offset") == -1]
print(f"Total with source_start_offset == -1: {len(offset_neg1)}")

dispositions_neg1 = {}
for c in offset_neg1:
    d = c.get("normalized_disposition")
    dispositions_neg1[d] = dispositions_neg1.get(d, 0) + 1
print("Dispositions with offset == -1:", dispositions_neg1)

# Check the other candidates where source_start_offset != -1
offset_valid = [c for c in cands if c.get("source_start_offset") != -1]
print(f"\nTotal with valid offsets: {len(offset_valid)}")

with open(datasets_dir / "open_india_law_sample_150.json", "r", encoding="utf-8") as f:
    source_cases = {c["id"]: c for c in json.load(f)}

valid_match_in_text = 0
valid_slice_matches = 0
for c in offset_valid:
    cid = c["case_id"]
    s = source_cases[cid]
    jtext = s.get("judgmentText", "")
    start = c.get("source_start_offset")
    end = c.get("source_end_offset")
    slice_text = jtext[start:end]
    matched = c.get("matched_text", "")
    if matched in jtext:
        valid_match_in_text += 1
    if slice_text == matched:
        valid_slice_matches += 1

print(f"Valid offset candidates where matched_text is in jtext: {valid_match_in_text} / {len(offset_valid)}")
print(f"Valid offset candidates where slice_text == matched_text: {valid_slice_matches} / {len(offset_valid)}")
