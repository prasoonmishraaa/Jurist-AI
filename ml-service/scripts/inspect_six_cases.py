import json
import re
from prototype_hardened_sanitizer import HardenedTargetLeakageSanitizer

source_path = "ml-service/app/datasets/open_india_law_sample_150.json"
with open(source_path, "r", encoding="utf-8") as f:
    cases = json.load(f)

sanitizer = HardenedTargetLeakageSanitizer()
we_rx = re.compile(r"\bwe\s+(?:hereby\s+|accordingly\s+|therefore\s+)?(?:allow|dismiss|partly\s+allow|set\s+aside|quash)\b", re.IGNORECASE)

print("=== INSPECTING THE 6 CASES WITH 'WE DISMISS/ALLOW' ===")
for c in cases:
    text = c.get("judgmentText", "")
    sanitized, meta = sanitizer.sanitize_judgment_text(text)
    for m in we_rx.finditer(sanitized):
        idx = m.start()
        print(f"Case {c['id']}:")
        print("  Context:", repr(sanitized[max(0, idx-40): min(len(sanitized), idx+80)]))
