import sys
from pathlib import Path

sys.path.insert(0, str(Path("ml-service").resolve()))
from app.prediction.outcome_annotation_session import OutcomeAnnotationSessionManager

session = OutcomeAnnotationSessionManager()
dash = session.get_progress_dashboard()

print("=== BASELINE ANNOTATION STATE ===")
print("Total candidates: ", dash["total_candidates"])
print("Approved:         ", dash["approved"])
print("Pending:          ", dash["pending"])
print("Total verified:   ", dash["total_verified"])
print("Rejected:         ", dash["rejected"])
print("Uncertain:        ", dash["uncertain"])
print("Deferred:         ", dash["deferred"])

print("\n=== RISK TIER PROGRESS ===")
for t, d in dash["risk_tier_progress"].items():
    print(f"  {t:10s} ({d['label']}): total={d['total']}, verified={d['verified']}, pending={d['pending']}, other={d['other']}")

print("\n=== VERIFIED DISPOSITIONS ===")
print(dash["verified_disposition_distribution"])

print("\n=== SOURCE INTEGRITY ===")
print(dash["source_integrity"])
