"""
CLI Script to Build Expanded Ground Truth from Human Annotations
Jurist AI — Feature 1.5: Human-Reviewed Expanded Retrieval Benchmark

Executes:
- Validation of annotation queue
- Disagreement resolution & adjudication check
- Exclusion of pending_review records
- Merging with original benchmark
"""

import os
import sys
import json
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.evaluation.expanded_benchmark_builder import build_expanded_benchmark

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def main():
    original_benchmark_path = os.path.join(BASE_DIR, "app", "datasets", "retrieval_benchmark.json")
    annotation_queue_path = os.path.join(BASE_DIR, "app", "datasets", "expanded_benchmark_annotation_queue.json")
    output_path = os.path.join(BASE_DIR, "app", "datasets", "retrieval_benchmark_expanded_human_reviewed.json")

    print("\n" + "="*85)
    print(" JURIST AI — EXPANDED RETRIEVAL BENCHMARK GROUND TRUTH MERGE")
    print("="*85)

    summary = build_expanded_benchmark(
        original_benchmark_path=original_benchmark_path,
        annotation_queue_path=annotation_queue_path,
        output_path=output_path,
        allow_empty_annotations=False
    )

    print(f"Total Annotation Pairs Inspected: {summary['totalAnnotationPairs']}")
    print(f"Approved Human Annotations:       {summary['approvedAnnotations']}")
    print(f"Pending Annotations (Excluded):   {summary['pendingAnnotations']}")
    print(f"Uncertain Annotations (Excluded): {summary['uncertainAnnotations']}")
    print(f"Disagreements Detected:           {summary['disagreementsDetected']}")
    print(f"Ground Truth Finalized:           {summary['finalizedGroundTruth']}")

    if summary["outputFile"]:
        print(f"\nFinalized ground truth saved to: {summary['outputFile']}")
    else:
        print("\nNotice: Finalized ground truth was NOT written because all candidate annotations are pending review.")
        print("Adhering strictly to rule: Do not create a finalized ground truth file containing unreviewed labels.")


if __name__ == "__main__":
    main()
