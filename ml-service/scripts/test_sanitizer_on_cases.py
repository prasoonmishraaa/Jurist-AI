import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path("ml-service").resolve()))
from app.prediction.verified_outcome_model import TargetLeakageSanitizer

sanitizer = TargetLeakageSanitizer()

with open("ml-service/app/datasets/open_india_law_sample_150.json", "r", encoding="utf-8") as f:
    source_cases = {c["id"]: c for c in json.load(f)}

test_ids = [
    "OIL-SC-2021_INSC_327",
    "OIL-SC-1996_INSC_503",
    "OIL-SC-2007_INSC_31",
    "OIL-SC-2007_INSC_1082",
    "OIL-SC-2003_INSC_88",
    "OIL-SC-1973_INSC_203"
]

print("=== LEAKAGE SANITIZER AUDIT ON REPRESENTATIVE CASES ===")
for cid in test_ids:
    c = source_cases[cid]
    raw_text = c["judgmentText"]
    sanitized, meta = sanitizer.sanitize_judgment_text(raw_text)

    print(f"\n--- {cid} ({c['caseTitle'][:40]}...) ---")
    print(f"Original length:     {meta['original_length']}")
    print(f"Sanitized length:    {meta['sanitized_length']}")
    print(f"Truncated operative: {meta['truncated_operative_section']}")
    print(f"Stripped phrases:    {meta['stripped_phrase_count']}")

    # Check if any outcome keywords remain in the sanitized tail (last 500 chars)
    san_tail = sanitized[-500:] if len(sanitized) > 500 else sanitized
    print(f"Sanitized Tail:\n{san_tail.strip()}")

    # Leakage check: test for keywords like allowed, dismissed, set aside, guilty, acquitted
    leakage_signals = []
    for pat in [
        r"\b(?:appeal|petition)\s+(?:is\s+)?allowed\b",
        r"\b(?:appeal|petition)\s+(?:is\s+)?dismissed\b",
        r"\bset\s+aside\b",
        r"\bquashed\b",
        r"\bconviction\s+(?:is\s+)?affirmed\b",
        r"\breleased\s+on\s+bail\b",
        r"\bimpugned\s+order\b.*?\bset\s+aside\b",
        r"\bcosts\s+quantified\s+at\b"
    ]:
        m = re.findall(pat, san_tail, re.IGNORECASE)
        if m:
            leakage_signals.extend(m)
    print("Residual tail signals:", leakage_signals)
