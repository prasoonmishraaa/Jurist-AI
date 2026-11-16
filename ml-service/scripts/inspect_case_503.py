import sys
from pathlib import Path

sys.path.insert(0, str(Path("ml-service").resolve()))
from app.prediction.outcome_annotation_session import OutcomeAnnotationSessionManager

session = OutcomeAnnotationSessionManager()
case = session.get_case_view("OIL-SC-1996_INSC_503")

print("=== CASE VIEW FOR OIL-SC-1996_INSC_503 ===")
print("case_id:        ", case["case_id"])
print("case_title:     ", case["case_title"])
print("court:          ", case["court"])
print("decision_date:  ", case["decision_date"])
print("procedural_role:", case["procedural_role"])
print("category:       ", case["category"])
print("legal_provisions:", case["legal_provisions"])
print("machine_candidate:")
for k, v in case["machine_candidate"].items():
    print(f"  {k}: {v}")
print("\nrisk_assessment:")
for k, v in case["risk_assessment"].items():
    print(f"  {k}: {v}")
print("\nconcluding_tail (last 600 chars):")
print(case["concluding_tail"][-600:])
