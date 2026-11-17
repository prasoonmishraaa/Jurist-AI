import json
from pathlib import Path

datasets_dir = Path("ml-service/app/datasets")

with open(datasets_dir / "open_india_law_sample_150.json", "r", encoding="utf-8") as f:
    source_cases = {c["id"]: c for c in json.load(f)}

c = source_cases["OIL-SC-2021_INSC_327"]
text = c["judgmentText"]

print(f"Case ID: {c['id']}")
print(f"Case Title: {c['caseTitle']}")
print(f"Court: {c['court']}")
print(f"Date: {c['judgmentDate']}")
print(f"Total length: {len(text)}")

# Find Paragraph 20 and Paragraph 21 or search for concluding text
idx_21 = text.find("21.")
if idx_21 == -1:
    idx_21 = text.find("21")
print(f"Index of '21': {idx_21}")

# Print the last 2000 characters
print("\n=== LAST 2,000 CHARACTERS OF JUDGMENT TEXT ===")
print(text[-2000:])
