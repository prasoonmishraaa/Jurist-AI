"""
Expanded Precedent Retrieval Evaluator
Jurist AI — Phase 3.2 Evaluation Implementation

Implements standard, mathematically rigorous ranking metrics for both Track A (27 Landmark)
and Track B (177 Expanded) precedent retrieval:
- Precision@K
- Recall@K
- Mean Reciprocal Rank (MRR@K)
- Normalized Discounted Cumulative Gain (NDCG@K)
- Hit Rate@K
- Per-query and aggregate retrieval latency

Supports graded relevance conventions:
  2 = Directly relevant
  1 = Supporting authority
  0 = Irrelevant

Safeguard: In adherence to Phase 3.2 restrictions, definitive metrics for Track B
are guarded and will not be finalized while unjudged query-case pairs remain in the pool.
"""

import os
import json
import math
import time
from typing import List, Dict, Any, Set, Optional, Tuple


def compute_precision_at_k(retrieved_ids: List[str], relevant_set: Set[str], k: int = 5) -> float:
    """Precision@K = (Number of relevant documents in top K) / K"""
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    rel_count = sum(1 for doc_id in top_k if doc_id in relevant_set)
    return rel_count / float(k)


def compute_recall_at_k(retrieved_ids: List[str], relevant_set: Set[str], k: int = 5) -> float:
    """Recall@K = (Number of relevant documents in top K) / (Total known relevant documents)"""
    if not relevant_set or k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    rel_count = sum(1 for doc_id in top_k if doc_id in relevant_set)
    return rel_count / float(len(relevant_set))


def compute_reciprocal_rank(retrieved_ids: List[str], relevant_set: Set[str], k: int = 5) -> float:
    """Reciprocal Rank (RR@K) = 1 / rank of first relevant document (1-indexed), or 0.0."""
    if not relevant_set or k <= 0:
        return 0.0
    for idx, doc_id in enumerate(retrieved_ids[:k]):
        if doc_id in relevant_set:
            return 1.0 / float(idx + 1)
    return 0.0


def compute_dcg_at_k(retrieved_ids: List[str], relevance_grades: Dict[str, float], k: int = 5) -> float:
    """DCG@K = sum_{i=1}^K (2^{rel_i} - 1) / log2(i + 1)"""
    if k <= 0:
        return 0.0
    dcg = 0.0
    for idx, doc_id in enumerate(retrieved_ids[:k]):
        rel = float(relevance_grades.get(doc_id, 0.0))
        if rel > 0:
            dcg += (math.pow(2.0, rel) - 1.0) / math.log2(idx + 2)
    return dcg


def compute_ndcg_at_k(retrieved_ids: List[str], relevance_grades: Dict[str, float], k: int = 5) -> float:
    """NDCG@K = DCG@K / IDCG@K"""
    if not relevance_grades or k <= 0:
        return 0.0
    dcg = compute_dcg_at_k(retrieved_ids, relevance_grades, k=k)
    sorted_grades = sorted([float(g) for g in relevance_grades.values() if g > 0], reverse=True)
    if not sorted_grades:
        return 0.0
    idcg = 0.0
    for idx, rel in enumerate(sorted_grades[:k]):
        idcg += (math.pow(2.0, rel) - 1.0) / math.log2(idx + 2)
    return (dcg / idcg) if idcg > 0.0 else 0.0


class ExpandedBenchmarkEvaluator:
    """
    Unified evaluator for Track A and Track B retrieval engines against benchmark queries.
    """

    def __init__(
        self,
        benchmark_path: str,
        human_reviewed_oil_path: Optional[str] = None,
        pending_review_path: Optional[str] = None
    ):
        with open(benchmark_path, "r", encoding="utf-8") as f:
            self.benchmark_queries = json.load(f)

        self.oil_reviewed_map: Dict[Tuple[str, str], int] = {}
        if human_reviewed_oil_path and os.path.exists(human_reviewed_oil_path):
            with open(human_reviewed_oil_path, "r", encoding="utf-8") as f:
                oil_data = json.load(f)
                for item in oil_data:
                    self.oil_reviewed_map[(item["queryId"], item["caseId"])] = item["humanReview"]["approvedGrade"]

        self.pending_review_map: Dict[Tuple[str, str], int] = {}
        if pending_review_path and os.path.exists(pending_review_path):
            with open(pending_review_path, "r", encoding="utf-8") as f:
                pending_data = json.load(f)
                for item in pending_data:
                    if "approvedGrade" in item:
                        self.pending_review_map[(item["queryId"], item["caseId"])] = item["approvedGrade"]

    def evaluate_track(
        self,
        retriever: Any,
        track_name: str = "Track_A",
        k: int = 5,
        allow_unjudged: bool = False
    ) -> Dict[str, Any]:
        """
        Runs identical evaluation across all benchmark queries.
        """
        per_query_results = []
        precision_list = []
        recall_list = []
        rr_list = []
        ndcg_list = []
        latencies = []
        hits = 0
        unjudged_count = 0

        for item in self.benchmark_queries:
            qid = item["queryId"]
            query_text = item["query"]
            domain = item.get("domain", "General")
            expected_grades = {doc_id: float(g) for doc_id, g in item.get("relevanceGrading", {}).items()}

            # Measure latency
            t0 = time.perf_counter()
            retrieved = retriever.retrieve_similar(query_text, top_k=k)
            lat_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(lat_ms)

            retrieved_ids = [r["id"] for r in retrieved]
            
            # Combine benchmark grades + approved human grades
            active_grades = dict(expected_grades)
            for cid in retrieved_ids:
                if (qid, cid) in self.oil_reviewed_map:
                    active_grades[cid] = float(self.oil_reviewed_map[(qid, cid)])
                elif (qid, cid) in self.pending_review_map:
                    active_grades[cid] = float(self.pending_review_map[(qid, cid)])
                elif cid not in active_grades:
                    unjudged_count += 1

            relevant_set = {cid for cid, g in active_grades.items() if g > 0}

            p_k = compute_precision_at_k(retrieved_ids, relevant_set, k=k)
            r_k = compute_recall_at_k(retrieved_ids, relevant_set, k=k)
            rr = compute_reciprocal_rank(retrieved_ids, relevant_set, k=k)
            ndcg = compute_ndcg_at_k(retrieved_ids, active_grades, k=k)
            is_hit = any(cid in relevant_set for cid in retrieved_ids[:k])

            if is_hit:
                hits += 1

            precision_list.append(p_k)
            recall_list.append(r_k)
            rr_list.append(rr)
            ndcg_list.append(ndcg)

            per_query_results.append({
                "queryId": qid,
                "query": query_text,
                "domain": domain,
                "retrieved": [
                    {
                        "rank": idx + 1,
                        "caseId": r["id"],
                        "caseTitle": r["caseTitle"],
                        "court": r["court"],
                        "score": round(float(r["similarityScore"]), 4),
                        "assignedGrade": active_grades.get(r["id"], "UNJUDGED" if (qid, r["id"]) not in self.oil_reviewed_map and r["id"] not in expected_grades else 0)
                    }
                    for idx, r in enumerate(retrieved)
                ],
                "precisionAtK": round(p_k, 4),
                "recallAtK": round(r_k, 4),
                "reciprocalRank": round(rr, 4),
                "ndcgAtK": round(ndcg, 4),
                "isHit": is_hit,
                "latencyMs": round(lat_ms, 2)
            })

        total_q = len(self.benchmark_queries)
        return {
            "trackName": track_name,
            "k": k,
            "totalQueries": total_q,
            "hitRate": round(hits / float(total_q), 4),
            "meanPrecisionAtK": round(sum(precision_list) / float(total_q), 4),
            "meanRecallAtK": round(sum(recall_list) / float(total_q), 4),
            "mrr": round(sum(rr_list) / float(total_q), 4),
            "meanNdcgAtK": round(sum(ndcg_list) / float(total_q), 4),
            "avgLatencyMs": round(sum(latencies) / float(total_q), 2),
            "totalLatencyMs": round(sum(latencies), 2),
            "unjudgedQueryCasePairsCount": unjudged_count,
            "isDefinitive": (unjudged_count == 0),
            "perQueryResults": per_query_results
        }
