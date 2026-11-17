import sys
from pathlib import Path

sys.path.insert(0, str(Path("ml-service").resolve()))
sys.path.insert(0, str(Path("ml-service/scripts").resolve()))
from build_verified_outcome_dataset import OutcomeDataAuditor

auditor = OutcomeDataAuditor()
audit = auditor.audit_all()

print("=== GROUPED AUDIT AND CONNECTED PROCEEDINGS ===")
print("Candidate records count:", audit["candidate_records_count"])
print("Human approved count:   ", audit["human_approved_count"])
print("Pending review count:   ", audit["pending_review_count"])
print("Verified classes:       ", audit["verified_class_distribution"])
print("Sufficient pre-decision:", audit["cases_with_sufficient_pre_decision_text"])
print("Duplicate / related grps:", len(audit["duplicate_or_related_cases"]))
for grp in audit["duplicate_or_related_cases"]:
    print("  Related group:", grp)
