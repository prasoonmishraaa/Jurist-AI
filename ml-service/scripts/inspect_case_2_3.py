import sys
from pathlib import Path

sys.path.insert(0, str(Path("ml-service").resolve()))
from app.prediction.outcome_annotation_session import OutcomeAnnotationSessionManager

session = OutcomeAnnotationSessionManager()
batch = session.get_batch_view(batch_size=5, tier="1")

for idx in [1, 2]: # Case 2 and Case 3
    case = batch[idx]
    print("=" * 80)
    print(f"CASE {idx+1}: {case['case_id']} - {case['case_title']}")
    print("Decision Date:", case["decision_date"])
    print("Machine candidate:", case["machine_candidate"])
    print("Concluding 1000 characters:")
    print(case["full_judgment_text"][-1000:])
