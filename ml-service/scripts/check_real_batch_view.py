import sys
from pathlib import Path

sys.path.insert(0, str(Path("ml-service").resolve()))
from app.prediction.outcome_annotation_session import OutcomeAnnotationSessionManager

session = OutcomeAnnotationSessionManager()
batch = session.get_batch_view(batch_size=5, tier="1")

print(f"Total cases returned in batch view: {len(batch)}")
for idx, c in enumerate(batch, 1):
    print(f"\n--- [{idx}/5] CASE {c['case_id']} ---")
    print(f"Title:  {c['case_title']}")
    print(f"Court:  {c['court']}")
    print(f"Date:   {c['decision_date']}")
    print(f"Role:   {c['procedural_role']}")
    print(f"Risk:   {c['risk_tier_label']}")
    print(f"Mach:   {c['machine_candidate']['normalized_disposition']} -> {c['machine_candidate']['successful_party']}")
    print(f"Tail:   {c['operative_order_excerpt'][-200:].strip()}")
