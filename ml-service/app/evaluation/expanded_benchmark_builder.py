"""
Expanded Retrieval Benchmark Ground Truth Builder & Adjudication Engine
Jurist AI — Feature 1.5: Human-Reviewed Expanded Retrieval Benchmark

Enforces:
1. Strict preservation of original benchmark ground-truth labels and query structures.
2. Complete exclusion of pending_review and uncertain records from finalized ground truth.
3. Multi-reviewer disagreement detection and documented adjudication resolution.
4. Deduplication of query–judgment pairs.
5. Complete audit provenance (reviewer IDs, adjudicator IDs, timestamps, evidence).
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)

# Valid graded relevance scores
VALID_GRADES = {0, 1, 2, 3}
RELEVANCE_THRESHOLD = 2  # Grade >= 2 qualifies for relevantJudgmentIds


class BenchmarkAnnotationError(Exception):
    """Raised when annotation schema or provenance validation fails."""
    pass


def validate_annotation_record(record: Dict[str, Any]) -> Tuple[bool, str]:
    """Validates structure, types, and required fields of an annotation record."""
    required_fields = [
        "annotationId", "queryId", "queryText", "judgmentId",
        "caseTitle", "court", "sourceDataset", "retrievedRank",
        "reviewStatus"
    ]
    for field in required_fields:
        if field not in record:
            return False, f"Missing required field: '{field}'"

    status = record.get("reviewStatus")
    if status not in {"pending_review", "approved", "rejected", "uncertain", "adjudicated"}:
        return False, f"Invalid reviewStatus: '{status}'"

    grade = record.get("humanRelevanceLabel")
    if grade is not None:
        if grade not in VALID_GRADES and grade != "uncertain":
            return False, f"Invalid humanRelevanceLabel: '{grade}' (must be 0, 1, 2, 3, or 'uncertain')"

    return True, "Valid"


def resolve_adjudication(
    r1_grade: Optional[Any],
    r2_grade: Optional[Any],
    adjudicator_grade: Optional[Any],
    adjudication_notes: str = ""
) -> Dict[str, Any]:
    """
    Evaluates two reviewer grades and returns consensus or adjudication resolution.
    """
    # Case 1: Both unreviewed
    if r1_grade is None and r2_grade is None:
        return {
            "isResolved": False,
            "finalGrade": None,
            "disagreementDetected": False,
            "resolutionMethod": "unreviewed"
        }

    # Case 2: Only Reviewer 1 reviewed
    if r1_grade is not None and r2_grade is None:
        if r1_grade == "uncertain":
            return {
                "isResolved": False,
                "finalGrade": None,
                "disagreementDetected": False,
                "resolutionMethod": "single_reviewer_uncertain"
            }
        return {
            "isResolved": True,
            "finalGrade": int(r1_grade),
            "disagreementDetected": False,
            "resolutionMethod": "single_reviewer"
        }

    # Case 3: Both reviewed - check agreement
    if r1_grade == r2_grade:
        if r1_grade == "uncertain":
            if adjudicator_grade in VALID_GRADES:
                return {
                    "isResolved": True,
                    "finalGrade": int(adjudicator_grade),
                    "disagreementDetected": True,
                    "resolutionMethod": "adjudicated_uncertainty"
                }
            return {
                "isResolved": False,
                "finalGrade": None,
                "disagreementDetected": False,
                "resolutionMethod": "consensus_uncertain"
            }
        return {
            "isResolved": True,
            "finalGrade": int(r1_grade),
            "disagreementDetected": False,
            "resolutionMethod": "reviewer_consensus"
        }

    # Case 4: Disagreement between reviewers
    disagreement = True
    if adjudicator_grade in VALID_GRADES:
        return {
            "isResolved": True,
            "finalGrade": int(adjudicator_grade),
            "disagreementDetected": True,
            "resolutionMethod": "lead_adjudication"
        }

    return {
        "isResolved": False,
        "finalGrade": None,
        "disagreementDetected": True,
        "resolutionMethod": "unresolved_disagreement"
    }


def build_expanded_benchmark(
    original_benchmark_path: str,
    annotation_queue_path: str,
    output_path: Optional[str] = None,
    allow_empty_annotations: bool = False
) -> Dict[str, Any]:
    """
    Merges approved human annotations with the original retrieval benchmark.
    
    STRICT INTEGRITY INVARIANTS:
    - Never modifies original_benchmark_path.
    - Preserves all original queries, landmark IDs, and relevance grades verbatim.
    - Excludes pending_review and uncertain records from finalized ground truth.
    - Deduplicates multiple annotations for identical (queryId, judgmentId) pairs.
    - Attaches comprehensive audit provenance.
    """
    if not os.path.exists(original_benchmark_path):
        raise FileNotFoundError(f"Original benchmark not found: {original_benchmark_path}")
    if not os.path.exists(annotation_queue_path):
        raise FileNotFoundError(f"Annotation queue not found: {annotation_queue_path}")

    with open(original_benchmark_path, "r", encoding="utf-8") as f:
        original_queries = json.load(f)
    with open(annotation_queue_path, "r", encoding="utf-8") as f:
        annotations = json.load(f)

    # Validate annotations
    for a in annotations:
        is_valid, msg = validate_annotation_record(a)
        if not is_valid:
            raise BenchmarkAnnotationError(f"Annotation {a.get('annotationId')} failed validation: {msg}")

    # Index original benchmark queries
    expanded_queries = []
    original_ids_by_query: Dict[str, Set[str]] = {}
    original_grades_by_query: Dict[str, Dict[str, int]] = {}

    for q in original_queries:
        qid = q["queryId"]
        original_ids_by_query[qid] = set(q.get("relevantJudgmentIds", []))
        original_grades_by_query[qid] = dict(q.get("relevanceGrading", {}))

        # Deep copy to guarantee original remains untouched
        q_copy = {
            "queryId": qid,
            "query": q["query"],
            "domain": q.get("domain", "General Law"),
            "targetAspect": q.get("targetAspect", ""),
            "relevantJudgmentIds": list(q.get("relevantJudgmentIds", [])),
            "relevanceGrading": dict(q.get("relevanceGrading", {})),
            "manualReviewStatus": q.get("manualReviewStatus", "manually_reviewed"),
            "reviewNotes": q.get("reviewNotes", ""),
            "provenance": {
                "originalLandmarkCount": len(q.get("relevantJudgmentIds", [])),
                "addedHumanReviewedCount": 0,
                "addedCases": []
            }
        }
        expanded_queries.append(q_copy)

    expanded_map = {q["queryId"]: q for q in expanded_queries}

    # Group annotations by (queryId, judgmentId) for deduplication
    grouped_annotations: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for a in annotations:
        pair_key = (a["queryId"], a["judgmentId"])
        if pair_key not in grouped_annotations:
            grouped_annotations[pair_key] = []
        grouped_annotations[pair_key].append(a)

    approved_count = 0
    pending_count = 0
    uncertain_count = 0
    excluded_count = 0
    disagreement_count = 0

    for (qid, cid), ann_list in grouped_annotations.items():
        if qid not in expanded_map:
            logger.warning("Query ID %s not in benchmark queries. Skipping.", qid)
            continue

        # If duplicates exist, use latest entry with valid resolution
        target_ann = ann_list[-1]

        # Extract reviewer grades and adjudication
        r1_grade = target_ann.get("humanRelevanceLabel")
        r2_obj = target_ann.get("secondReviewer") or {}
        r2_grade = r2_obj.get("humanRelevanceLabel")

        adj_obj = target_ann.get("adjudication") or {}
        adj_grade = adj_obj.get("finalGrade")
        adj_notes = adj_obj.get("adjudicationNotes", "")

        resolution = resolve_adjudication(r1_grade, r2_grade, adj_grade, adj_notes)

        if resolution["disagreementDetected"]:
            disagreement_count += 1

        if not resolution["isResolved"]:
            status = target_ann.get("reviewStatus", "pending_review")
            if status == "pending_review" or r1_grade is None:
                pending_count += 1
            elif r1_grade == "uncertain" or resolution["resolutionMethod"] == "consensus_uncertain":
                uncertain_count += 1
            else:
                excluded_count += 1
            continue

        final_grade = resolution["finalGrade"]
        if final_grade not in VALID_GRADES:
            excluded_count += 1
            continue

        approved_count += 1
        target_query = expanded_map[qid]

        # Provenance entry
        provenance_entry = {
            "judgmentId": cid,
            "caseTitle": target_ann.get("caseTitle"),
            "court": target_ann.get("court"),
            "sourceDataset": target_ann.get("sourceDataset", "open_india_law_sample"),
            "assignedGrade": final_grade,
            "resolutionMethod": resolution["resolutionMethod"],
            "primaryReviewerId": target_ann.get("reviewerId"),
            "secondReviewerId": r2_obj.get("reviewerId"),
            "adjudicatorId": adj_obj.get("adjudicatorId"),
            "evidence": target_ann.get("relevanceEvidence", ""),
            "reviewerNotes": target_ann.get("reviewerNotes", ""),
            "adjudicationNotes": adj_notes,
            "originalRetrievedRank": target_ann.get("retrievedRank"),
            "mergedTimestamp": datetime.now(timezone.utc).isoformat()
        }

        # Add to relevanceGrading map
        target_query["relevanceGrading"][cid] = final_grade

        # If grade meets relevance threshold (>= 2), add to relevantJudgmentIds (deduplicated)
        if final_grade >= RELEVANCE_THRESHOLD:
            if cid not in target_query["relevantJudgmentIds"]:
                target_query["relevantJudgmentIds"].append(cid)

        target_query["provenance"]["addedCases"].append(provenance_entry)
        target_query["provenance"]["addedHumanReviewedCount"] += 1

    # Invariant verification: original landmark IDs and grades must be 100% untouched
    for qid, orig_ids in original_ids_by_query.items():
        curr_ids = set(expanded_map[qid]["relevantJudgmentIds"])
        assert orig_ids.issubset(curr_ids), f"Original landmark IDs were lost for query {qid}!"

    for qid, orig_grades in original_grades_by_query.items():
        curr_grades = expanded_map[qid]["relevanceGrading"]
        for cid, grade in orig_grades.items():
            assert curr_grades.get(cid) == grade, f"Original grade modified for {qid}:{cid}!"

    summary = {
        "status": "success",
        "totalAnnotationPairs": len(grouped_annotations),
        "approvedAnnotations": approved_count,
        "pendingAnnotations": pending_count,
        "uncertainAnnotations": uncertain_count,
        "excludedAnnotations": excluded_count,
        "disagreementsDetected": disagreement_count,
        "finalizedGroundTruth": approved_count > 0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Write output file ONLY if approved annotations exist, or if allow_empty_annotations=True
    if output_path:
        if approved_count > 0 or allow_empty_annotations:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(expanded_queries, f, indent=2, ensure_ascii=False)
            logger.info("Saved expanded ground truth to: %s", output_path)
            summary["outputFile"] = output_path
        else:
            logger.warning(
                "Ground truth not written to %s because 0 approved annotations exist (%d pending). "
                "Adhering to strict rule: no unreviewed labels in finalized ground truth.",
                output_path, pending_count
            )
            summary["outputFile"] = None

    return summary
