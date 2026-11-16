import sys
import json
import re
from pathlib import Path

# Add ml-service to path
ML_SERVICE_DIR = Path("ml-service").resolve()
sys.path.insert(0, str(ML_SERVICE_DIR))

from scripts.build_verified_outcome_dataset import TargetLeakageSanitizer

source_path = ML_SERVICE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"
with open(source_path, "r", encoding="utf-8") as f:
    cases = json.load(f)

sanitizer = TargetLeakageSanitizer()

print("Auditing existing sanitizer against all 150 judgments...")

# Phrases that indicate residual leakage if found in sanitized pre-decision text
leakage_audit_patterns = [
    ("bare_appeal_dismissed", re.compile(r"(?:^|\n|\.\s+)(?:Appeals?|Petitions?)\s+(?:allowed|dismissed|disposed\s+of)\s*[\.:]?", re.IGNORECASE)),
    ("we_dismiss_allow", re.compile(r"\bwe\s+(?:hereby\s+|accordingly\s+|therefore\s+)?(?:allow|dismiss|partly\s+allow|set\s+aside|quash)\b", re.IGNORECASE)),
    ("therefore_fails_dismissed", re.compile(r"\bappeal\s+therefore\s+fails\s+and\s+is\s+hereby\s+dismissed\b", re.IGNORECASE)),
    ("set_aside_order_of_detention", re.compile(r"\bset\s+aside\s+(?:the\s+)?(?:ihe\s+)?order\s+of\s+detention\b", re.IGNORECASE)),
    ("scraper_header", re.compile(r"\[SECTION\]\s*##", re.IGNORECASE)),
    ("operative_order_heading", re.compile(r"(?:^|\n)\s*(?:O\s*R\s*D\s*E\s*R|CONCLUSION|IN\s+THE\s+RESULT)\s*:", re.IGNORECASE)),
]

leakage_found_baseline = {name: 0 for name, _ in leakage_audit_patterns}
affected_cases_baseline = set()

for c in cases:
    cid = c["id"]
    text = c.get("judgmentText", "")
    sanitized, meta = sanitizer.sanitize_judgment_text(text)
    
    for name, rx in leakage_audit_patterns:
        m = rx.search(sanitized)
        if m:
            leakage_found_baseline[name] += 1
            affected_cases_baseline.add(cid)

print("\n=== BASELINE SANITIZER RESIDUAL LEAKAGE AUDIT (150 Cases) ===")
for name, cnt in leakage_found_baseline.items():
    print(f"  {name:30s}: {cnt} occurrences")
print(f"Total affected cases with residual leakage: {len(affected_cases_baseline)} / 150")

# Specifically check our 6 verified cases
target_ids = [
    "OIL-SC-2021_INSC_327",
    "OIL-SC-1996_INSC_503",
    "OIL-SC-2007_INSC_31",
    "OIL-SC-2007_INSC_1082",
    "OIL-SC-2003_INSC_88",
    "OIL-SC-1973_INSC_203"
]

print("\n=== RESIDUAL LEAKAGE IN THE 6 HUMAN-VERIFIED CASES ===")
for cid in target_ids:
    c = next(x for x in cases if x["id"] == cid)
    text = c["judgmentText"]
    sanitized, meta = sanitizer.sanitize_judgment_text(text)
    tail = sanitized[-500:] if len(sanitized) > 500 else sanitized
    print(f"\nCase {cid} ({c['caseTitle'][:50]}):")
    print(f"  Orig len: {len(text)} -> Sanitized len: {len(sanitized)} (Operative truncated: {meta['truncated_operative_section']}, Redacted: {meta['stripped_phrase_count']})")
    
    leaks = []
    for name, rx in leakage_audit_patterns:
        if rx.search(sanitized):
            leaks.append(name)
    print(f"  Residual leaks detected: {leaks if leaks else 'NONE'}")
    print(f"  Sanitized concluding tail excerpt (last 150 chars):")
    print(f"    {repr(tail[-150:])}")
