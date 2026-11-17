#!/usr/bin/env python3
"""
Interactive Judicial Outcome Annotation CLI
JURIST AI — Feature 4.5: Interactive Human-Reviewed Judicial Outcome Annotation

Interactive console tool for legal data annotators to inspect judgment text,
evaluate machine-extracted candidate dispositions, and record verified ground-truth labels.
"""

import os
import sys
import argparse
from pathlib import Path

# Add ml-service to path
ML_SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_SERVICE_DIR))

from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    VALID_DISPOSITIONS,
    VALID_SUCCESSFUL_PARTIES,
    AnnotationValidationError,
    ConfirmationRequiredError,
)
from app.prediction.risk_prioritized_queue import RiskPrioritizer, RiskTier


def print_banner():
    print("=" * 80)
    print("  JURIST AI — Judicial Outcome Annotation & Verification Console")
    print("  Human-in-the-Loop Ground-Truth Verification Workflow (Feature 4.5)")
    print("=" * 80)


def print_dashboard(session: OutcomeAnnotationSessionManager):
    dash = session.get_progress_dashboard()
    readiness = session.check_training_readiness()

    print("\n" + "=" * 80)
    print("  OUTCOME ANNOTATION PROGRESS DASHBOARD")
    print("=" * 80)
    print(f"  Total Candidate Cases:         {dash['total_candidates']}")
    print(f"  Batch 1 (Definitive High-Q):   {dash['batch_1_definitive_candidates']}")
    print(f"  Approved (Verified Ground Truth): {dash['approved']}")
    print(f"  Corrected (Human Adjusted):    {dash['corrected']}")
    print(f"  Adjudicated (Senior Ruling):   {dash['adjudicated_approved']}")
    print(f"  ---------------------------------------------")
    print(f"  Total Human-Verified:          {dash['total_verified']} / {dash['total_candidates']}")
    print(f"  Pending Review:                {dash['pending']}")
    print(f"  Rejected (False Positives):    {dash['rejected']}")
    print(f"  Uncertain:                     {dash['uncertain']}")
    print(f"  Deferred (Needs Full Text):    {dash['deferred']}")
    print(f"  Disputed (Needs Adjudication): {dash['disputed']}")
    print(f"  Remaining to Annotate:         {dash['remaining_candidates']}")
    print("-" * 80)

    b1 = dash["batch_1_progress"]
    print(f"  BATCH 1 PROGRESS: {b1['verified']} / {b1['total']} verified ({b1['percent_complete']}%) | {b1['pending']} pending")
    print("-" * 80)

    risk_prog = dash.get("risk_tier_progress", {})
    if risk_prog:
        print("  RISK-BASED QUEUE STRATIFICATION:")
        for rk, rdata in risk_prog.items():
            print(f"    - {rdata['label']:50s}: {rdata['verified']}/{rdata['total']} verified ({rdata['percent_complete']}%) | {rdata['pending']} pending")
        print("-" * 80)

    dist = dash["verified_disposition_distribution"]
    print("  VERIFIED DISPOSITION DISTRIBUTION:")
    if dist:
        for k, v in dist.items():
            print(f"    - {k:35s}: {v}")
    else:
        print("    [None] Zero records currently verified. Model operates in qualitative research mode.")
    print("-" * 80)

    party_dist = dash.get("successful_party_distribution", {})
    print("  SUCCESSFUL PARTY DISTRIBUTION:")
    if party_dist:
        for pk, pv in party_dist.items():
            print(f"    - {pk:35s}: {pv}")
    else:
        print("    [None] No party success verified yet.")
    print("-" * 80)

    rev_progress = dash.get("reviewer_wise_progress", {})
    print("  REVIEWER-WISE PROGRESS:")
    if rev_progress:
        for rk, rv in rev_progress.items():
            print(f"    - Reviewer '{rk}': {rv['total']} total ({rv['approved']} approved, {rv['corrected']} corrected, {rv['adjudicated']} adjudicated)")
    else:
        print("    [None] Zero cases finalized by human annotators.")
    print("-" * 80)

    print("  TRAINING READINESS CHECK:")
    print(f"    - Status: {'READY FOR ML TRAINING' if readiness['is_training_eligible'] else 'NOT ELIGIBLE (QUALITATIVE FALLBACK ACTIVE)'}")
    print(f"    - Verified Samples: {readiness['total_verified_count']} (Required: {readiness['minimum_required']})")
    print(f"    - Recommended Mode: {readiness['recommended_mode']}")
    if readiness["blockers"]:
        print("    - Active Blockers:")
        for b in readiness["blockers"]:
            print(f"      * {b}")
    print("-" * 80)

    integrity = dash["source_integrity"]
    print("  SOURCE DATASET INTEGRITY:")
    for fn, ok in integrity.items():
        status_str = "OK (SHA-256 Verified)" if ok else "MISMATCH / ALTERED!"
        print(f"    - {fn:32s}: {status_str}")
    print("=" * 80 + "\n")


def display_case_details(case: dict):
    print("\n" + "#" * 80)
    print(f"  CASE ID: {case['case_id']}  {'[BATCH 1 DEFINITIVE]' if case['is_batch_1'] else '[BATCH 2/3]'}")
    print(f"  Title:   {case['case_title']}")
    print(f"  Court:   {case['court']} | Date: {case['decision_date']}")
    print(f"  Type:    {case['proceeding_type']} | Category: {case['category']}")
    print(f"  Role:    {case['procedural_role']}")
    if case["legal_provisions"]:
        provisions_str = ", ".join(case["legal_provisions"][:6])
        print(f"  Provisions: {provisions_str}")
    print("-" * 80)

    cand = case["machine_candidate"]
    print("  MACHINE-EXTRACTED SUGGESTION (UNVERIFIED CANDIDATE):")
    print(f"    Suggested Disposition: {cand['normalized_disposition']} (Raw: {cand['original_disposition']})")
    print(f"    Suggested Party:       {cand['successful_party']}")
    print(f"    Parser Confidence:     {cand['parser_confidence']:.2f}")
    if cand["extracted_phrase"]:
        print(f"    Extracted Phrase:      \"{cand['extracted_phrase']}\"")
    if cand["recommended_action"]:
        print(f"    Guidance Action:       {cand['recommended_action']}")
    if cand["ambiguity_reason"]:
        print(f"    Ambiguity Note:        {cand['ambiguity_reason']}")
    print("-" * 80)

    print("  CONCLUDING OPERATIVE SECTION EXCERPT (Final ~1,500 chars):")
    tail = case["concluding_tail"]
    excerpt = tail[-1500:] if len(tail) > 1500 else tail
    for line in excerpt.strip().split("\n"):
        print(f"    | {line}")
    print("#" * 80)


def prompt_choice(prompt_text: str, options: list) -> str:
    while True:
        choice = input(prompt_text).strip().lower()
        if choice in options:
            return choice
        print(f"Invalid option. Please choose from {options}.")


def select_from_list(prompt_text: str, items: list) -> str:
    print(f"\n{prompt_text}")
    for idx, item in enumerate(items, 1):
        print(f"  [{idx:2d}] {item}")
    while True:
        val = input("Enter number or full text: ").strip()
        if val.isdigit() and 1 <= int(val) <= len(items):
            return items[int(val) - 1]
        elif val in items:
            return val
        print(f"Invalid choice. Select 1 to {len(items)}.")


def print_batch_plan(session: OutcomeAnnotationSessionManager, batch_size: int = 5):
    """
    Displays the human review plan partitioning the 99 definitive Batch 1 cases
    into manageable review sub-batches of five cases each.
    """
    b1_records = [r for r in session.records if r.get("case_id") in session.batch_1_ids]
    total_b1 = len(b1_records)

    print("\n" + "=" * 80)
    print("  JURIST AI — BATCH 1 HUMAN REVIEW EXECUTION PLAN (99 CASES)")
    print(f"  Partitioned into {((total_b1 - 1) // batch_size) + 1} Review Sets of {batch_size} Cases Each")
    print("=" * 80)

    for i in range(0, total_b1, batch_size):
        chunk = b1_records[i : i + batch_size]
        sub_batch_num = (i // batch_size) + 1
        print(f"\n--- SUB-BATCH 1.{sub_batch_num} (Cases {i + 1} to {min(i + batch_size, total_b1)} of {total_b1}) ---")
        for j, rec in enumerate(chunk, i + 1):
            cid = rec.get("case_id")
            title = rec.get("case_title")
            court = rec.get("court")
            date = rec.get("decision_date")
            disp = rec.get("normalized_disposition")
            party = rec.get("successful_party")
            status = rec.get("review_status", "pending_review")
            phrase = rec.get("original_disposition_phrase") or "No exact phrase"

            print(f"  [{j:2d}] {cid:24s} | Status: {status:15s}")
            print(f"       Title: {title}")
            print(f"       Court: {court} | Date: {date}")
            print(f"       Machine Candidate: '{disp}' (Party: '{party}') | Phrase: \"{phrase}\"")
            print(f"       Review Action Needed: Verify operative holding; do NOT accept solely from title.")

    print("\n" + "=" * 80)
    print("  END OF BATCH 1 REVIEW PLAN (Ready for human review in sets of 5)")
    print("=" * 80 + "\n")


def run_interactive_session(session: OutcomeAnnotationSessionManager, batch_filter: str, preset_reviewer: str = "", batch_size: int = 5):
    reviewer_id = preset_reviewer.strip()
    if not reviewer_id:
        while not reviewer_id or len(reviewer_id) < 2:
            reviewer_id = input("\nEnter your Reviewer ID / Initials (e.g. JD, ADV-01): ").strip()

    print(f"\nWelcome, Reviewer '{reviewer_id}'. Active queue: {batch_filter.upper()} (Checkpoint every {batch_size} cases)")

    reviewed_count = 0

    while True:
        case = session.get_next_pending(batch_filter=batch_filter)
        if not case:
            print("\n" + "=" * 80)
            print(f"  NO PENDING CASES REMAINING IN QUEUE '{batch_filter.upper()}'.")
            print("=" * 80)
            print_dashboard(session)
            break

        display_case_details(case)

        print("\nREVIEW ACTIONS:")
        print("  [1] Accept candidate disposition and party success (if verified correct)")
        print("  [2] Correct disposition and/or party success")
        print("  [3] Reject candidate label (extractor false-positive / erroneous)")
        print("  [4] Mark as Uncertain / Deferred (needs full un-truncated text)")
        print("  [5] View full judgment text")
        print("  [6] View Dashboard")
        print("  [q] Save & Quit")

        action_choice = input("\nSelect action [1/2/3/4/5/6/q]: ").strip().lower()

        if action_choice in ["q", "quit", "exit"]:
            print("Exiting review session. All changes are saved.")
            break

        elif action_choice == "5":
            print("\n" + "=" * 80)
            print(f"  FULL JUDGMENT TEXT ({case['judgment_text_length']} characters)")
            print("=" * 80)
            print(case["full_judgment_text"])
            input("\nPress Enter to return to review options...")
            continue

        elif action_choice == "6":
            print_dashboard(session)
            input("Press Enter to resume review...")
            continue

        elif action_choice in ["1", "a", "accept"]:
            cand = case["machine_candidate"]
            disp = cand["normalized_disposition"]
            party = cand["successful_party"]

            print(f"\nAccepting candidate: disposition='{disp}', party='{party}'")
            evidence = input("Paste exact operative phrase from text as evidence: ").strip()
            if not evidence:
                evidence = cand.get("extracted_phrase") or cand.get("matched_text") or "Concluding order confirmed."
            notes = input("Review notes (optional): ").strip()

            confirm = input(f"\nConfirm ACCEPT for '{case['case_id']}'? (y/N): ").strip().lower() == "y"
            if confirm:
                try:
                    session.submit_review(
                        case_id=case["case_id"],
                        action="accept",
                        reviewer_id=reviewer_id,
                        disposition=disp,
                        successful_party=party,
                        evidence=evidence,
                        notes=notes,
                        confirm=True
                    )
                    print(f"SUCCESS: Case '{case['case_id']}' marked APPROVED.")
                    reviewed_count += 1
                except Exception as e:
                    print(f"ERROR: {e}")
            else:
                print("Action cancelled.")

        elif action_choice in ["2", "c", "correct"]:
            selected_disp = select_from_list("Select correct disposition category:", VALID_DISPOSITIONS)
            selected_party = select_from_list("Select verified successful party:", VALID_SUCCESSFUL_PARTIES)
            evidence = input("Paste exact operative phrase from text as evidence: ").strip()
            while len(evidence) < 5:
                evidence = input("Evidence is mandatory (at least 5 characters): ").strip()
            notes = input("Enter justification notes for correction: ").strip()
            while len(notes) < 5:
                notes = input("Justification notes are mandatory (at least 5 characters): ").strip()

            print(f"\nSummary: Disposition='{selected_disp}', Successful Party='{selected_party}'")
            confirm = input(f"Confirm CORRECTION for '{case['case_id']}'? (y/N): ").strip().lower() == "y"
            if confirm:
                try:
                    session.submit_review(
                        case_id=case["case_id"],
                        action="correct",
                        reviewer_id=reviewer_id,
                        disposition=selected_disp,
                        successful_party=selected_party,
                        evidence=evidence,
                        notes=notes,
                        confirm=True
                    )
                    print(f"SUCCESS: Case '{case['case_id']}' updated with human correction.")
                    reviewed_count += 1
                except Exception as e:
                    print(f"ERROR: {e}")
            else:
                print("Action cancelled.")

        elif action_choice in ["3", "r", "reject"]:
            reason = input("Enter rejection reason (why extractor was wrong): ").strip()
            while len(reason) < 5:
                reason = input("Reason is required (at least 5 chars): ").strip()

            confirm = input(f"Confirm REJECT for '{case['case_id']}'? (y/N): ").strip().lower() == "y"
            if confirm:
                try:
                    session.submit_review(
                        case_id=case["case_id"],
                        action="reject",
                        reviewer_id=reviewer_id,
                        notes=reason,
                        confirm=True
                    )
                    print(f"SUCCESS: Case '{case['case_id']}' marked REJECTED.")
                    reviewed_count += 1
                except Exception as e:
                    print(f"ERROR: {e}")
            else:
                print("Action cancelled.")

        elif action_choice in ["4", "u", "uncertain"]:
            reason = input("Enter reason for uncertainty / deferral: ").strip()
            action_type = "defer" if "truncat" in reason.lower() else "uncertain"

            confirm = input(f"Confirm UNCERTAIN for '{case['case_id']}'? (y/N): ").strip().lower() == "y"
            if confirm:
                try:
                    session.submit_review(
                        case_id=case["case_id"],
                        action=action_type,
                        reviewer_id=reviewer_id,
                        notes=reason,
                        confirm=True
                    )
                    print(f"SUCCESS: Case '{case['case_id']}' marked UNCERTAIN/DEFERRED.")
                    reviewed_count += 1
                except Exception as e:
                    print(f"ERROR: {e}")
            else:
                print("Action cancelled.")

        # Batch checkpoint
        if reviewed_count > 0 and reviewed_count % batch_size == 0:
            print("\n" + "=" * 80)
            print(f"  CHECKPOINT: COMPLETED REVIEW BATCH OF {batch_size} CASES (Total reviewed this session: {reviewed_count})")
            print("=" * 80)
            print_dashboard(session)
            cont = input(f"Proceed to next sub-batch of {batch_size} cases? [Y/n]: ").strip().lower()
            if cont == "n":
                print("Review session paused. Progress is safely saved.")
                break


def display_batch_overview(batch_cases: list):
    """
    Presents five candidate cases concurrently for visual inspection,
    displaying case metadata, procedural role, machine candidates,
    risk warnings, and concluding operative order excerpts.
    """
    print("\n" + "=" * 90)
    print(f"  ACCELERATED BATCH REVIEW: {len(batch_cases)} CASES PRESENTED FOR CONCURRENT INSPECTION")
    print("=" * 90)

    for idx, case in enumerate(batch_cases, 1):
        cand = case["machine_candidate"]
        risk = case.get("risk_assessment", {})
        flags = risk.get("flags", [])
        flags_str = " | ".join(flags) if flags else "CLEAN_MERITS_HOLDING"

        print(f"\n[{idx}/{len(batch_cases)}] CASE ID: {case['case_id']}  |  {case['court']}  |  {case['decision_date']}")
        print(f"      Title:    {case['case_title']}")
        print(f"      Role:     {case['procedural_role']}  |  Category: {case['category']}")
        print(f"      Risk:     {case.get('risk_tier_label', 'Unknown Tier')} [Mode: {case.get('recommended_review_mode', 'standard')}]")
        print(f"      Flags:    {flags_str}")
        print(f"      Machine:  Suggested='{cand['normalized_disposition']}' (Conf: {cand['parser_confidence']:.2f})  -->  Party='{cand['successful_party']}'")
        if cand.get("extracted_phrase"):
            print(f"      Phrase:   \"{cand['extracted_phrase']}\"")
        if cand.get("ambiguity_reason"):
            print(f"      Ambiguity: {cand['ambiguity_reason']}")
        print(f"      Operative Excerpt (Concluding Tail):")
        tail = case.get("operative_order_excerpt") or case.get("concluding_tail", "")
        tail_lines = [ln.strip() for ln in tail.strip().split("\n") if ln.strip()]
        for line in tail_lines[-6:]:
            print(f"        | {line}")
        print("-" * 90)


def print_risk_summary(session: OutcomeAnnotationSessionManager):
    """Displays comprehensive risk-tier distribution across all candidate records."""
    dash = session.get_progress_dashboard()
    risk_prog = dash.get("risk_tier_progress", {})

    print("\n" + "=" * 90)
    print("  JURIST AI — RISK-BASED OUTCOME ANNOTATION QUEUE STRATIFICATION")
    print("=" * 90)
    for t_key, t_info in risk_prog.items():
        print(f"  [{t_key.upper()}] {t_info['label']}")
        print(f"    - Total Cases:       {t_info['total']}")
        print(f"    - Human Verified:    {t_info['verified']} ({t_info['percent_complete']}%)")
        print(f"    - Pending Review:    {t_info['pending']}")
        print(f"    - Other / Deferred:  {t_info['other']}")
    print("=" * 90 + "\n")


def run_batch_review_session(
    session: OutcomeAnnotationSessionManager,
    tier: str = "1",
    preset_reviewer: str = "",
    batch_size: int = 5
):
    """
    Executes accelerated 5-case batch verification workflow:
    1. Displays five cases together with concluding operative text and risk flags.
    2. Allows reviewer to stage individual decisions for each case.
    3. Prevents bulk auto-approval: validates each case payload individually.
    4. Displays staged summary table.
    5. Commits atomically upon single explicit human confirmation.
    """
    reviewer_id = preset_reviewer.strip()
    if not reviewer_id:
        while not reviewer_id or len(reviewer_id) < 2:
            reviewer_id = input("\nEnter your Reviewer ID / Initials (e.g. SNR-LEGAL-01): ").strip()

    batch_cases = session.get_batch_view(batch_size=batch_size, tier=tier)
    if not batch_cases:
        print(f"\nNo pending cases found for Tier '{tier}'. Inspect dashboard for other tiers.")
        return

    display_batch_overview(batch_cases)

    print("\n" + "=" * 90)
    print("  STAGE INDIVIDUAL DECISIONS FOR EACH CASE IN THE BATCH")
    print("  (Decisions are staged locally and committed atomically after review)")
    print("=" * 90)

    staged_decisions = []
    for idx, case in enumerate(batch_cases, 1):
        cid = case["case_id"]
        cand = case["machine_candidate"]
        print(f"\n>>> [Case {idx}/{len(batch_cases)}] {cid}")
        print(f"    Machine Candidate: '{cand['normalized_disposition']}' -> Successful Party: '{cand['successful_party']}'")
        print("    Actions: [a]ccept candidate | [c]orrect | [r]eject false-positive | [u]ncertain | [d]efer | [s]kip")

        choice = prompt_choice("    Your decision for this case [a/c/r/u/d/s]: ", ["a", "c", "r", "u", "d", "s", "accept", "correct", "reject", "uncertain", "defer", "skip"])

        if choice in ["s", "skip"]:
            print(f"    Skipping {cid} from this batch submission.")
            continue

        if choice in ["a", "accept"]:
            disp = cand["normalized_disposition"]
            party = cand["successful_party"]
            default_ev = cand.get("extracted_phrase") or cand.get("matched_text") or "Concluding operative order confirmed in judgment text."
            print(f"    Accepting candidate: disposition='{disp}', party='{party}'")
            ev = input(f"    Evidence quote (press Enter for: '{default_ev[:60]}...'): ").strip()
            if not ev:
                ev = default_ev
            while len(ev) < 5:
                ev = input("    Evidence quote is mandatory (at least 5 characters): ").strip()
            notes = input("    Review notes (optional): ").strip()
            staged_decisions.append({
                "case_id": cid,
                "action": "accept",
                "disposition": disp,
                "successful_party": party,
                "evidence": ev,
                "notes": notes or f"Accepted machine candidate '{disp}'."
            })

        elif choice in ["c", "correct"]:
            selected_disp = select_from_list("    Select correct disposition category:", VALID_DISPOSITIONS)
            selected_party = select_from_list("    Select verified successful party:", VALID_SUCCESSFUL_PARTIES)
            ev = input("    Paste exact operative phrase from judgment as evidence: ").strip()
            while len(ev) < 5:
                ev = input("    Evidence is mandatory (at least 5 characters): ").strip()
            notes = input("    Enter justification notes for correction: ").strip()
            while len(notes) < 5:
                notes = input("    Justification notes are mandatory (at least 5 characters): ").strip()
            staged_decisions.append({
                "case_id": cid,
                "action": "correct",
                "disposition": selected_disp,
                "successful_party": selected_party,
                "evidence": ev,
                "notes": notes
            })

        elif choice in ["r", "reject"]:
            reason = input("    Enter rejection reason (at least 5 chars): ").strip()
            while len(reason) < 5:
                reason = input("    Rejection reason is mandatory (at least 5 chars): ").strip()
            staged_decisions.append({
                "case_id": cid,
                "action": "reject",
                "notes": reason,
                "evidence": "Extractor false-positive"
            })

        elif choice in ["u", "d", "uncertain", "defer"]:
            action = "defer" if choice in ["d", "defer"] else "uncertain"
            reason = input(f"    Enter reason for {action} (optional): ").strip()
            staged_decisions.append({
                "case_id": cid,
                "action": action,
                "notes": reason or f"Marked {action} pending review.",
                "evidence": "Ambiguous or truncated operative order"
            })

    if not staged_decisions:
        print("\nNo decisions staged. Batch submission aborted.")
        return

    # Present Staged Decisions Summary Table
    print("\n" + "=" * 90)
    print(f"  STAGED BATCH DECISIONS SUMMARY ({len(staged_decisions)} cases staged for reviewer '{reviewer_id}')")
    print("=" * 90)
    for idx, d in enumerate(staged_decisions, 1):
        disp = d.get("disposition", "-")
        party = d.get("successful_party", "-")
        print(f"  [{idx}] {d['case_id']:25s} | Action: {d['action']:8s} | Disp: {disp:25s} | Party: {party:15s}")
        print(f"      Evidence: {d.get('evidence', '')[:70]}...")
        if d.get("notes"):
            print(f"      Notes:    {d.get('notes', '')[:70]}...")
    print("-" * 90)

    confirm = input(f"\nConfirm commit for all {len(staged_decisions)} staged decisions to verified database? [y/N]: ").strip().lower()
    if confirm == "y":
        try:
            res = session.submit_batch_reviews(staged_decisions, reviewer_id=reviewer_id, confirm=True)
            print("\n" + "=" * 90)
            print(f"  SUCCESS: {res['committed_count']} DECISIONS COMMITTED ATOMICALLY BY REVIEWER '{reviewer_id}'")
            print("=" * 90)
            print_dashboard(session)
        except Exception as e:
            print(f"\nERROR committing batch: {e}")
    else:
        print("\nBatch commit cancelled by reviewer. No changes were committed to disk.")


def main():
    parser = argparse.ArgumentParser(description="JURIST AI — Interactive Judicial Outcome Annotation Tool")
    parser.add_argument("--dashboard", action="store_true", help="Print progress dashboard and exit")
    parser.add_argument("--readiness", action="store_true", help="Print ML training readiness check and exit")
    parser.add_argument("--risk-summary", action="store_true", help="Print risk-tier queue stratification and exit")
    parser.add_argument("--batch-plan", action="store_true", help="Print the 99-case Batch 1 sub-batch plan and exit")
    parser.add_argument("--batch-review", action="store_true", help="Review 5 cases concurrently in an accelerated risk-prioritized batch")
    parser.add_argument("--tier", type=str, default="1", help="Target risk tier for batch review (1, 2, 3, 4, or all; default: 1)")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of cases per review sub-batch (default: 5)")
    parser.add_argument("--batch", choices=["1", "2", "3", "all"], default="1", help="Target review batch (default: 1)")
    parser.add_argument("--reviewer", type=str, default="", help="Reviewer ID or initials")
    parser.add_argument("--case", type=str, default="", help="Inspect a specific case ID")

    args = parser.parse_args()

    session = OutcomeAnnotationSessionManager()

    if args.dashboard:
        print_banner()
        print_dashboard(session)
        return

    if args.readiness:
        print_banner()
        readiness = session.check_training_readiness()
        print("\nTRAINING READINESS CHECK:")
        print(f"Eligible: {readiness['is_training_eligible']}")
        print(f"Verified count: {readiness['total_verified_count']} (Min required: {readiness['minimum_required']})")
        print(f"Blockers: {readiness['blockers']}")
        return

    if args.risk_summary:
        print_banner()
        print_risk_summary(session)
        return

    if args.batch_plan:
        print_banner()
        print_batch_plan(session, batch_size=args.batch_size)
        return

    if args.batch_review:
        print_banner()
        run_batch_review_session(
            session,
            tier=args.tier,
            preset_reviewer=args.reviewer,
            batch_size=args.batch_size
        )
        return

    print_banner()
    if args.case:
        try:
            view = session.get_case_view(args.case)
            display_case_details(view)
        except KeyError as e:
            print(f"Error: {e}")
        return

    batch_map = {"1": "batch_1", "2": "batch_2", "3": "batch_3", "all": "all"}
    run_interactive_session(
        session,
        batch_filter=batch_map[args.batch],
        preset_reviewer=args.reviewer,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()
