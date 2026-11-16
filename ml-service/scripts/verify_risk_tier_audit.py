import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path("ml-service").resolve()))
from app.prediction.outcome_annotation_session import OutcomeAnnotationSessionManager
from app.prediction.risk_prioritized_queue import RiskPrioritizer, RiskTier

session = OutcomeAnnotationSessionManager()
prioritizer = session.risk_prioritizer

stratified = prioritizer.stratify_queue(session.records, session.source_cases, only_pending=False)

tier_1 = stratified[RiskTier.TIER_1_DEFINITIVE_MERITS]
tier_2 = stratified[RiskTier.TIER_2_MODERATE_RISK_BAIL_DIRECTIVES]
tier_3 = stratified[RiskTier.TIER_3_HIGH_RISK_PROCEDURAL]
tier_4 = stratified[RiskTier.TIER_4_CRITICAL_DEFERRED]

print("=== RISK TIER ASSIGNMENT AUDIT ===")
print(f"Tier 1 count: {len(tier_1)} (Expected: 35)")
print(f"Tier 2 count: {len(tier_2)} (Expected: 21)")
print(f"Tier 3 count: {len(tier_3)} (Expected: 43)")
print(f"Tier 4 count: {len(tier_4)} (Expected: 51)")
total = len(tier_1) + len(tier_2) + len(tier_3) + len(tier_4)
print(f"Total count:  {total} (Expected: 150)")

assert len(tier_1) == 35, f"Tier 1 count mismatch: {len(tier_1)}"
assert len(tier_2) == 21, f"Tier 2 count mismatch: {len(tier_2)}"
assert len(tier_3) == 43, f"Tier 3 count mismatch: {len(tier_3)}"
assert len(tier_4) == 51, f"Tier 4 count mismatch: {len(tier_4)}"
assert total == 150, f"Total count mismatch: {total}"

# Check uniqueness and partition properties
set_1 = set(r["case_id"] for r in tier_1)
set_2 = set(r["case_id"] for r in tier_2)
set_3 = set(r["case_id"] for r in tier_3)
set_4 = set(r["case_id"] for r in tier_4)

print("\n--- Disjoint Tier Intersections ---")
print(f"Intersection 1 & 2: {set_1.intersection(set_2)}")
print(f"Intersection 1 & 3: {set_1.intersection(set_3)}")
print(f"Intersection 1 & 4: {set_1.intersection(set_4)}")
print(f"Intersection 2 & 3: {set_2.intersection(set_3)}")
print(f"Intersection 2 & 4: {set_2.intersection(set_4)}")
print(f"Intersection 3 & 4: {set_3.intersection(set_4)}")

all_tier_ids = set_1 | set_2 | set_3 | set_4
print(f"\nUnion of all tiers: {len(all_tier_ids)} unique IDs")
source_ids = set(session.source_cases.keys())
print(f"Matches source IDs exactly: {all_tier_ids == source_ids}")

# Verify get_batch_view for each tier
print("\n--- get_batch_view() Tier Integrity Check ---")
for t_idx, t_name in [("1", "tier_1"), ("2", "tier_2"), ("3", "tier_3"), ("4", "tier_4")]:
    batch = session.get_batch_view(batch_size=5, tier=t_idx)
    print(f"Tier {t_idx} batch: {len(batch)} cases returned")
    for c in batch:
        cid = c["case_id"]
        source_title = session.source_cases[cid]["caseTitle"]
        view_title = c["case_title"]
        source_date = session.source_cases[cid]["judgmentDate"]
        view_date = c["decision_date"]
        source_court = session.source_cases[cid]["court"]
        view_court = c["court"]

        assert source_title == view_title, f"Title mismatch in get_batch_view for {cid}: {source_title} vs {view_title}"
        assert source_date == view_date, f"Date mismatch in get_batch_view for {cid}: {source_date} vs {view_date}"
        assert source_court == view_court, f"Court mismatch in get_batch_view for {cid}: {source_court} vs {view_court}"
        assert c["risk_tier"] == t_name, f"Risk tier mismatch in get_batch_view for {cid}: {c['risk_tier']} vs {t_name}"

print("All get_batch_view cases match source title, date, court, and tier perfectly!")
