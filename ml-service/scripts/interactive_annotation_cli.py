"""
Interactive Human Annotation Terminal CLI & Session Interface
Jurist AI — Feature 1.5A: Interactive Human Annotation & Review

Enables:
1. Candidate inspection with complete query context, metadata, and substantive passages.
2. Review progress tracking (reviewed, pending, uncertain, remaining).
3. Explicit human confirmation before saving each annotation.
4. Overwrite protection and correction audit history.
5. Interactive REPL mode and scriptable CLI options (--status, --show, --submit, --list).
"""

import os
import sys
import argparse
import logging
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.evaluation.annotation_session import (
    AnnotationSessionManager,
    AnnotationValidationError,
    OverwriteProtectionError
)

logging.basicConfig(level=logging.WARNING, format="%(message)s")


def print_progress_summary(manager: AnnotationSessionManager):
    p = manager.get_progress()
    print("\n" + "=" * 65)
    print(" JURIST AI — EXPANDED BENCHMARK ANNOTATION PROGRESS")
    print("=" * 65)
    print(f"Total Candidates in Queue:   {p['totalCandidates']}")
    print(f"Reviewed (Approved Grades):  {p['reviewedCandidates']}")
    print(f"Pending Review:              {p['pendingCandidates']}")
    print(f"Uncertain / Inconclusive:    {p['uncertainCandidates']}")
    print(f"Remaining to Review:         {p['remainingCandidates']}")
    print(f"Completion Percentage:       {p['percentComplete']}%")
    if p["nextPendingIndex"] is not None:
        cand = manager.get_candidate(p["nextPendingIndex"])
        print(f"Next Pending Candidate:      #{p['nextPendingIndex'] + 1} ({cand['annotationId']})")
    else:
        print("Status:                      All candidates have been reviewed!")
    print("=" * 65 + "\n")


def list_candidates_table(manager: AnnotationSessionManager):
    print("\n" + "=" * 105)
    print(f"{'#':<3} | {'Annotation ID':<18} | {'Query ID':<10} | {'Case ID':<26} | {'Rank':<5} | {'Status':<14} | {'Grade':<6} | {'Reviewer':<10}")
    print("-" * 105)
    for idx, c in enumerate(manager.queue, start=1):
        status = c.get("reviewStatus", "pending_review")
        grade = str(c.get("humanRelevanceLabel") if c.get("humanRelevanceLabel") is not None else "-")
        reviewer = str(c.get("reviewerId") or "-")
        print(
            f"{idx:<3} | "
            f"{c['annotationId']:<18} | "
            f"{c['queryId']:<10} | "
            f"{c['judgmentId'][:25]:<26} | "
            f"#{c['retrievedRank']:<4} | "
            f"{status:<14} | "
            f"{grade:<6} | "
            f"{reviewer:<10}"
        )
    print("=" * 105 + "\n")


def run_interactive_repl(manager: AnnotationSessionManager, reviewer_id: Optional[str] = None):
    print("\n" + "=" * 80)
    print(" JURIST AI — HUMAN RELEVANCE ANNOTATION WORKFLOW INTERACTION")
    print("=" * 80)
    print("Guidelines: Assess substantive judgment passages for query legal relevance.")
    print("Scale: [3] Highly Relevant | [2] Relevant | [1] Partially Relevant | [0] Not Relevant | [u] Uncertain")

    if not reviewer_id:
        while not reviewer_id:
            try:
                inp = input("\nEnter your Reviewer ID (e.g., REV-LEGAL-01): ").strip()
                if inp:
                    reviewer_id = inp
            except (KeyboardInterrupt, EOFError):
                print("\nSession aborted.")
                return

    current_idx = manager.get_progress()["nextPendingIndex"] or 0

    while True:
        try:
            print_progress_summary(manager)
            print(f"Current Selected Candidate: #{current_idx + 1} ({manager.get_candidate(current_idx)['annotationId']})")
            print("\nOptions:")
            print("  [V] View current candidate details & passages")
            print("  [R] Review & assign grade to current candidate")
            print("  [N] Jump to next pending candidate")
            print("  [P] Jump to previous candidate")
            print("  [J] Jump to specific candidate number (1-36)")
            print("  [L] List all candidates in table")
            print("  [Q] Quit session")

            choice = input("\nSelect command: ").strip().lower()

            if choice == "q":
                print("\nAnnotation session paused. Progress has been saved. Exiting.")
                break

            elif choice == "v":
                print(manager.format_candidate_display(current_idx))
                input("\nPress Enter to return to menu...")

            elif choice == "n":
                p = manager.get_progress()
                if p["nextPendingIndex"] is not None:
                    current_idx = p["nextPendingIndex"]
                else:
                    current_idx = (current_idx + 1) % len(manager.queue)

            elif choice == "p":
                current_idx = (current_idx - 1) % len(manager.queue)

            elif choice == "j":
                target = input(f"Enter candidate number (1-{len(manager.queue)}): ").strip()
                if target.isdigit():
                    t_idx = int(target) - 1
                    if 0 <= t_idx < len(manager.queue):
                        current_idx = t_idx
                    else:
                        print("Invalid candidate number.")

            elif choice == "l":
                list_candidates_table(manager)
                input("\nPress Enter to return to menu...")

            elif choice == "r":
                cand = manager.get_candidate(current_idx)
                print(manager.format_candidate_display(current_idx))

                is_overwrite = cand.get("reviewStatus") == "approved"
                if is_overwrite:
                    print(f"\n[NOTICE] Candidate is currently APPROVED with grade '{cand.get('humanRelevanceLabel')}'.")
                    confirm_ow = input("Do you wish to modify this existing annotation? (y/n): ").strip().lower()
                    if confirm_ow != "y":
                        continue

                grade_raw = input("\nEnter Relevance Grade [3, 2, 1, 0, or u]: ").strip().lower()
                evidence = input("Enter specific textual evidence (which paragraph/ratio supports this): ").strip()
                notes = input("Enter reviewer notes (optional): ").strip()

                print("\n" + "-" * 50)
                print("CONFIRM SUBMISSION:")
                print(f"  Candidate ID: {cand['annotationId']}")
                print(f"  Reviewer:     {reviewer_id}")
                print(f"  Grade:        {grade_raw}")
                print(f"  Evidence:     {evidence}")
                print("-" * 50)
                confirm = input("Save this annotation to ground truth queue? (y/n): ").strip().lower()

                if confirm == "y":
                    try:
                        res = manager.submit_annotation(
                            annotation_id=cand["annotationId"],
                            reviewer_id=reviewer_id,
                            grade=grade_raw,
                            evidence=evidence,
                            notes=notes,
                            allow_overwrite=is_overwrite
                        )
                        print(f"\n[SUCCESS] Saved annotation for {res['annotationId']} (Grade: {res['assignedGrade']}). Queue and CSV updated.")
                        # Advance to next pending candidate
                        next_p = manager.get_progress()["nextPendingIndex"]
                        if next_p is not None:
                            current_idx = next_p
                    except (AnnotationValidationError, OverwriteProtectionError) as err:
                        print(f"\n[ERROR] Submission rejected: {err}")
                        input("Press Enter to continue...")
                else:
                    print("\nAnnotation cancelled.")

        except (KeyboardInterrupt, EOFError):
            print("\nSession paused. Progress saved.")
            break


def main():
    parser = argparse.ArgumentParser(description="JURIST AI Interactive Legal Relevance Annotation CLI")
    parser.add_argument("--status", action="store_true", help="Print review queue progress summary")
    parser.add_argument("--list", action="store_true", help="List all 36 candidates in table")
    parser.add_argument("--show", type=str, help="Show formatted details & passages for candidate by index (1-36) or annotationId")
    parser.add_argument("--submit", action="store_true", help="Submit annotation via command line flags")
    parser.add_argument("--id", type=str, help="Candidate annotationId for submission")
    parser.add_argument("--reviewer", type=str, help="Reviewer ID for submission")
    parser.add_argument("--grade", type=str, help="Relevance grade (3, 2, 1, 0, or uncertain)")
    parser.add_argument("--evidence", type=str, default="", help="Supporting textual evidence")
    parser.add_argument("--notes", type=str, default="", help="Reviewer notes")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting existing approved annotation")
    parser.add_argument("--second-reviewer", action="store_true", help="Submit as second reviewer")

    args = parser.parse_args()
    manager = AnnotationSessionManager()

    if args.status:
        print_progress_summary(manager)
        return

    if args.list:
        list_candidates_table(manager)
        return

    if args.show:
        target = args.show.strip()
        if target.isdigit():
            idx = int(target) - 1
            if 0 <= idx < len(manager.queue):
                print(manager.format_candidate_display(idx))
            else:
                print(f"Index {target} out of range [1, {len(manager.queue)}]")
        else:
            cand = manager.get_candidate_by_id(target)
            if cand:
                idx = manager.queue.index(cand)
                print(manager.format_candidate_display(idx))
            else:
                print(f"Annotation ID '{target}' not found in queue.")
        return

    if args.submit:
        if not args.id or not args.reviewer or args.grade is None:
            print("Error: --submit requires --id, --reviewer, and --grade")
            sys.exit(1)
        try:
            res = manager.submit_annotation(
                annotation_id=args.id,
                reviewer_id=args.reviewer,
                grade=args.grade,
                evidence=args.evidence,
                notes=args.notes,
                allow_overwrite=args.overwrite,
                is_second_reviewer=args.second_reviewer
            )
            print(f"Successfully saved annotation: {res}")
        except Exception as e:
            print(f"Submission failed: {e}")
            sys.exit(1)
        return

    # Default: Interactive REPL
    run_interactive_repl(manager, reviewer_id=args.reviewer)


if __name__ == "__main__":
    main()
