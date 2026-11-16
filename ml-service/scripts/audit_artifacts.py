import json
from pathlib import Path

source_path = Path("ml-service/app/datasets/open_india_law_sample_150.json")
with open(source_path, "r", encoding="utf-8") as f:
    source_cases = {c["id"]: c for c in json.load(f)}

cands_path = Path("ml-service/app/datasets/outcome_label_candidates_v2.json")
with open(cands_path, "r", encoding="utf-8") as f:
    cand_data = json.load(f)
cand_records = {r["case_id"]: r for r in cand_data["records"]}

artifacts_to_check = [
    ("OIL-SC-2007_INSC_1082", "cannot be c sustained"),
    ("OIL-SC-2007_INSC_1082", "similarly D situated"),
    ("OIL-SC-2003_INSC_88", "without ariy order"),
    ("OIL-SC-1973_INSC_203", "ihe order"),
    ("OIL-SC-1973_INSC_203", "ear· lier directed"),
]

print("=== ARTIFACT INVESTIGATION ===")
for cid, phrase in artifacts_to_check:
    src_text = source_cases[cid]["judgmentText"]
    cand_ev = cand_records[cid].get("evidence_reference", "")
    in_src = phrase in src_text
    in_ev = phrase in cand_ev
    print(f"Case: {cid}")
    print(f"  Target phrase: '{phrase}'")
    print(f"  Exists in original source dataset (open_india_law_sample_150.json): {in_src}")
    print(f"  Exists in committed evidence: {in_ev}")
    if in_src:
        idx = src_text.find(phrase)
        snippet = src_text[max(0, idx - 40): min(len(src_text), idx + len(phrase) + 40)]
        print(f"  Source context: ...{repr(snippet)}...")
    print("-" * 60)
