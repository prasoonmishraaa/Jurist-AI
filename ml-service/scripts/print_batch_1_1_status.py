import sys
import hashlib
from pathlib import Path

ML_SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from app.prediction.outcome_annotation_session import OutcomeAnnotationSessionManager, KNOWN_SOURCE_HASHES

session = OutcomeAnnotationSessionManager()
dash = session.get_progress_dashboard()

print("=== DASHBOARD METRICS ===")
print(f"Total Candidates:     {dash['total_candidates']}")
print(f"Approved:             {dash['approved']}")
print(f"Corrected:            {dash['corrected']}")
print(f"Total Verified:       {dash['total_verified']}")
print(f"Pending:              {dash['pending']}")
print(f"Rejected:             {dash['rejected']}")
print(f"Uncertain:            {dash['uncertain']}")
print(f"Deferred:             {dash['deferred']}")
print(f"Disputed:             {dash['disputed']}")
print(f"Remaining Candidates: {dash['remaining_candidates']}")

print("\n=== CLASS DISTRIBUTION ===")
for k, v in sorted(dash["verified_disposition_distribution"].items()):
    print(f"  {k:25s}: {v}")

print("\n=== SUCCESSFUL PARTY DISTRIBUTION ===")
for k, v in sorted(dash["successful_party_distribution"].items()):
    print(f"  {k:25s}: {v}")

print("\n=== REVIEWER PROGRESS ===")
for rev, stats in dash["reviewer_wise_progress"].items():
    print(f"  {rev:25s}: total={stats['total']}, approved={stats['approved']}, corrected={stats['corrected']}")

print("\n=== BATCH 1 PROGRESS ===")
print(f"  Verified: {dash['batch_1_progress']['verified']} / {dash['batch_1_progress']['total']} ({dash['batch_1_progress']['percent_complete']}%)")

print("\n=== RISK TIER PROGRESS ===")
for k, v in dash["risk_tier_progress"].items():
    print(f"  {v['label']:35s}: verified={v['verified']}, pending={v['pending']}, total={v['total']}")

print("\n=== SOURCE DATASET HASHES ===")
for fname, canonical in KNOWN_SOURCE_HASHES.items():
    p = ML_SERVICE_DIR / "app" / "datasets" / fname
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    match = (h == canonical)
    print(f"  {fname}:")
    print(f"    Computed:  {h}")
    print(f"    Canonical: {canonical}")
    print(f"    Matches:   {match}")

print("\n=== AUDIT HISTORY (CASE 1 + BATCH 1.1) ===")
target_ids = [
    "OIL-SC-2021_INSC_327",
    "OIL-SC-1996_INSC_503",
    "OIL-SC-2007_INSC_31",
    "OIL-SC-2007_INSC_1082",
    "OIL-SC-2003_INSC_88",
    "OIL-SC-1973_INSC_203"
]
for cid in target_ids:
    cv = session.get_case_view(cid)
    r = cv["current_review"]
    print(f"\nCase {cid}:")
    print(f"  Title:        {cv['case_title']}")
    print(f"  Court / Date: {cv['court']} ({cv['decision_date']})")
    print(f"  Status:       {r['review_status']}")
    print(f"  Disposition:  {r['human_approved_label']}")
    print(f"  Party:        {r['human_successful_party']}")
    print(f"  Reviewer:     {r['reviewer_reference']}")
    print(f"  Audit Events ({len(r.get('audit_history', []))}):")
    for evt in r.get("audit_history", []):
        print(f"    - [{evt['timestamp']}] Action: {evt['action']} | Reviewer: {evt['reviewer_id']} | Status: {evt['previous_status']} -> {evt['new_status']}")
        print(f"      Notes:    {evt['notes']}")
        print(f"      Evidence: {evt['evidence'][:90]}...")
