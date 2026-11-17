import json
from pathlib import Path

datasets_dir = Path("ml-service/app/datasets")

with open(datasets_dir / "open_india_law_sample_150.json", "r", encoding="utf-8") as f:
    source_cases = {c["id"]: c for c in json.load(f)}

with open(datasets_dir / "outcome_label_candidates_v2.json", "r", encoding="utf-8") as f:
    cands = {c["case_id"]: c for c in json.load(f).get("records", [])}

cid = "OIL-SC-2022_INSC_130"
s = source_cases[cid]
c = cands[cid]

print(f"CASE: {cid}")
print(f"Start offset: {c.get('source_start_offset')}, End offset: {c.get('source_end_offset')}")
print(f"Matched text: {repr(c.get('matched_text'))}")

# Check slice from source text at offsets
start = c.get('source_start_offset')
end = c.get('source_end_offset')
if start is not None and end is not None:
    slice_text = s.get('judgmentText', "")[start:end]
    print(f"Slice from offsets: {repr(slice_text)}")

# Let's check why 'matched' wasn't directly in jtext:
print(f"In jtext? {c.get('matched_text') in s.get('judgmentText', '')}")
if not (c.get('matched_text') in s.get('judgmentText', '')):
    # Search for words from matched_text in jtext
    words = c.get('matched_text', '').split()[:5]
    print(f"First 5 words: {words}")
    import re
    first_word = words[0] if words else ""
    matches = [m.start() for m in re.finditer(re.escape(first_word), s.get('judgmentText', ''))]
    print(f"Occurrences of first word '{first_word}': {matches[:5]}")
    for idx in matches[:2]:
        print(f"Context at {idx}: {repr(s.get('judgmentText', '')[idx:idx+100])}")
