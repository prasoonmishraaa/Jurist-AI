import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path("ml-service").resolve()))
from app.prediction.outcome_annotation_session import OutcomeAnnotationSessionManager

session = OutcomeAnnotationSessionManager()
batch = session.get_batch_view(batch_size=5, tier="1")

print(f"Retrieved {len(batch)} cases from Tier 1 pending queue:")

for idx, case in enumerate(batch, 1):
    print("=" * 80)
    print(f"CASE {idx}: {case['case_id']}")
    print("=" * 80)
    print("Title:           ", case["case_title"])
    print("Court:           ", case["court"])
    print("Decision Date:   ", case["decision_date"])
    print("Category:        ", case["category"])
    print("Procedural Role: ", case["procedural_role"])
    print("Legal Provisions:", case["legal_provisions"])
    print("Text Length:     ", case["judgment_text_length"])
    print("\nMACHINE SUGGESTION:")
    cand = case["machine_candidate"]
    for k, v in cand.items():
        print(f"  {k}: {v}")

    print("\nRISK ASSESSMENT:")
    risk = case["risk_assessment"]
    for k, v in risk.items():
        print(f"  {k}: {v}")

    print("\nCONCLUDING OPERATIVE SECTION (Last 2,000 chars):")
    tail = case["concluding_tail"]
    excerpt = tail[-2000:] if len(tail) > 2000 else tail
    for line in excerpt.strip().split("\n"):
        print(f"  | {line}")
    print("\n")
