import sys
import json
import csv
from pathlib import Path

# Add ml-service to path
ML_SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    KNOWN_SOURCE_HASHES,
)

def verify():
    print("=" * 80)
    print("POST-COMMIT BATCH 1.2 VERIFICATION")
    print("=" * 80)

    session = OutcomeAnnotationSessionManager()
    dash = session.get_progress_dashboard()

    print("\n1. DASHBOARD STATUS:")
    print(f"  Total Candidates:    {dash['total_candidates']}")
    print(f"  Total Verified:      {dash['total_verified']} / 150 (Approved: {dash['approved']}, Corrected: {dash['corrected']})")
    print(f"  Pending:             {dash['pending']}")
    print(f"  Tier 1 Progress:     {dash['risk_tier_progress']['tier_1']['verified']} verified, {dash['risk_tier_progress']['tier_1']['pending']} pending")

    assert dash["total_verified"] == 11, f"Expected 11 verified, got {dash['total_verified']}"
    assert dash["approved"] == 10, f"Expected 10 approved, got {dash['approved']}"
    assert dash["corrected"] == 1, f"Expected 1 corrected, got {dash['corrected']}"
    assert dash["pending"] == 139, f"Expected 139 pending, got {dash['pending']}"
    assert dash["risk_tier_progress"]["tier_1"]["verified"] == 11
    assert dash["risk_tier_progress"]["tier_1"]["pending"] == 24

    print("\n2. VERIFIED CLASS DISTRIBUTION:")
    for d, c in sorted(dash["verified_disposition_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {d:30s}: {c}")

    print("\n3. SUCCESSFUL PARTY DISTRIBUTION:")
    for p, c in sorted(dash["successful_party_distribution"].items(), key=lambda x: -x[1]):
        print(f"  {p:30s}: {c}")

    print("\n4. REVIEWER-WISE PROGRESS:")
    for r, s in dash["reviewer_wise_progress"].items():
        print(f"  {r:25s}: total={s['total']}, approved={s['approved']}, corrected={s['corrected']}")
    assert "SNR-LEGAL-NLP-01" in dash["reviewer_wise_progress"]
    assert dash["reviewer_wise_progress"]["SNR-LEGAL-NLP-01"]["total"] == 11

    # Check synchronization between JSON and CSV
    print("\n5. SYNCHRONIZATION AUDIT (JSON vs CSV):")
    json_path = ML_SERVICE_DIR / "app" / "datasets" / "outcome_label_candidates_v2.json"
    csv_path = ML_SERVICE_DIR / "app" / "datasets" / "outcome_label_review_v2.csv"

    with open(json_path, "r", encoding="utf-8") as f:
        json_recs = {r["case_id"]: r for r in json.load(f)["records"]}
    with open(csv_path, "r", encoding="utf-8") as f:
        csv_recs = {r["case_id"]: r for r in csv.DictReader(f)}

    assert len(json_recs) == 150
    assert len(csv_recs) == 150

    for cid in json_recs:
        jr = json_recs[cid]
        cr = csv_recs[cid]
        assert jr["review_status"] == cr["review_status"], f"Status mismatch for {cid}"
        assert jr.get("human_approved_label", "") == cr.get("human_approved_label", ""), f"Label mismatch for {cid}"
        assert jr.get("human_successful_party", "") == cr.get("human_successful_party", ""), f"Party mismatch for {cid}"
        assert jr.get("reviewer_reference", "") == cr.get("reviewer_reference", ""), f"Reviewer mismatch for {cid}"
    print("  All 150 records match identically across JSON candidates and CSV tracker.")

    # Check all 11 verified cases
    print("\n6. AUDIT TRAILS FOR ALL 11 VERIFIED CASES:")
    all_11_ids = [
        "OIL-SC-2021_INSC_327",
        "OIL-SC-1996_INSC_503",
        "OIL-SC-2007_INSC_31",
        "OIL-SC-2007_INSC_1082",
        "OIL-SC-2003_INSC_88",
        "OIL-SC-1973_INSC_203",
        "OIL-SC-2000_INSC_110",
        "OIL-SC-2016_INSC_467",
        "OIL-SC-1973_INSC_247",
        "OIL-SC-1979_INSC_85",
        "OIL-SC-1998_INSC_267"
    ]
    for cid in all_11_ids:
        rec = json_recs[cid]
        audits = rec.get("audit_history", [])
        assert len(audits) >= 1, f"Audit history missing for {cid}"
        last_ev = audits[-1]
        print(f"  [{rec['review_status'].upper()}] {cid}:")
        print(f"    Disposition:      {rec['human_approved_label']}")
        print(f"    Successful Party: {rec['human_successful_party']}")
        print(f"    Reviewer:         {rec['reviewer_reference']}")
        print(f"    Audit Timestamp:  {last_ev['timestamp']}")
        print(f"    Audit Action:     {last_ev['action']}")

    # Cryptographic integrity
    print("\n7. CRYPTOGRAPHIC SOURCE INTEGRITY:")
    integrity = session.verify_source_integrity()
    for fname, ok in integrity.items():
        print(f"  {fname}: {'INTACT' if ok else 'FAILED'}")
        assert ok

    # Training readiness check
    print("\n8. TRAINING READINESS GATEKEEPER:")
    readiness = session.check_training_readiness(min_total_verified=30)
    print(f"  Eligible: {readiness['is_training_eligible']}")
    print(f"  Mode:     {readiness['recommended_mode']}")
    print(f"  Blockers: {readiness['blockers']}")
    assert not readiness["is_training_eligible"]
    assert readiness["recommended_mode"] == "qualitative_research_mode"

    print("\n" + "=" * 80)
    print("ALL 8 VERIFICATION GATES PASSED CLEANLY")
    print("=" * 80)

if __name__ == "__main__":
    verify()
