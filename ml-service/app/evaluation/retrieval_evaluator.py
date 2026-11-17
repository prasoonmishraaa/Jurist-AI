"""
Information Retrieval (IR) Evaluation Metrics Module
Jurist AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Implements standard, mathematically rigorous ranking metrics:
- Precision@K
- Recall@K
- Mean Reciprocal Rank (MRR@K)
- Normalized Discounted Cumulative Gain (NDCG@K)
"""

import os
import json
import math
from typing import List, Dict, Any, Set, Optional


def compute_precision_at_k(
    retrieved_ids: List[str],
    relevant_ids: Set[str],
    k: int = 5
) -> float:
    """
    Precision@K = (Number of relevant documents in top K) / K
    """
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    relevant_retrieved = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return relevant_retrieved / float(k)


def compute_recall_at_k(
    retrieved_ids: List[str],
    relevant_ids: Set[str],
    k: int = 5
) -> float:
    """
    Recall@K = (Number of relevant documents in top K) / (Total relevant documents)
    Returns 0.0 if there are no known relevant documents for the query.
    """
    if not relevant_ids or k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    relevant_retrieved = sum(1 for doc_id in top_k if doc_id in relevant_ids)
    return relevant_retrieved / float(len(relevant_ids))


def compute_reciprocal_rank(
    retrieved_ids: List[str],
    relevant_ids: Set[str],
    k: int = 5
) -> float:
    """
    Reciprocal Rank (RR@K) = 1 / rank of first relevant document (1-indexed).
    Returns 0.0 if no relevant document appears in top K.
    """
    if not relevant_ids or k <= 0:
        return 0.0
    for idx, doc_id in enumerate(retrieved_ids[:k]):
        if doc_id in relevant_ids:
            return 1.0 / float(idx + 1)
    return 0.0


def compute_dcg_at_k(
    retrieved_ids: List[str],
    relevance_grades: Dict[str, float],
    k: int = 5
) -> float:
    """
    Discounted Cumulative Gain (DCG@K) using standard logarithmic discount:
    DCG@K = sum_{i=1}^K (2^{rel_i} - 1) / log2(i + 1)
    """
    if k <= 0:
        return 0.0
    dcg = 0.0
    for idx, doc_id in enumerate(retrieved_ids[:k]):
        rel = float(relevance_grades.get(doc_id, 0.0))
        if rel > 0:
            dcg += (math.pow(2.0, rel) - 1.0) / math.log2(idx + 2)
    return dcg


def compute_ndcg_at_k(
    retrieved_ids: List[str],
    relevance_grades: Dict[str, float],
    k: int = 5
) -> float:
    """
    Normalized Discounted Cumulative Gain (NDCG@K) = DCG@K / IDCG@K.
    Returns 0.0 if IDCG@K == 0.0 (no relevant documents exist).
    """
    if not relevance_grades or k <= 0:
        return 0.0

    dcg = compute_dcg_at_k(retrieved_ids, relevance_grades, k=k)

    # Ideal ranking: sort all positive relevance grades descending, take top K
    sorted_grades = sorted([float(g) for g in relevance_grades.values() if g > 0], reverse=True)
    if not sorted_grades:
        return 0.0

    idcg = 0.0
    for idx, rel in enumerate(sorted_grades[:k]):
        idcg += (math.pow(2.0, rel) - 1.0) / math.log2(idx + 2)

    if idcg <= 0.0:
        return 0.0

    return dcg / idcg


def evaluate_retrieval_benchmark(
    retriever: Any,
    benchmark_path: Optional[str] = None,
    k: int = 5
) -> Dict[str, Any]:
    """
    Evaluates the given retriever against the standard retrieval benchmark.
    Returns overall metrics and per-query evaluation breakdown.
    """
    if benchmark_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        benchmark_path = os.path.join(base_dir, "datasets", "retrieval_benchmark.json")

    if not os.path.exists(benchmark_path):
        raise FileNotFoundError(f"Benchmark file not found at: {benchmark_path}")

    with open(benchmark_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    per_query_results = []
    p1_scores = []
    p3_scores = []
    p5_scores = []
    precision_scores = []
    recall_scores = []
    rr_scores = []
    ndcg_scores = []
    hits = 0

    for item in queries:
        qid = item["queryId"]
        query_text = item["query"]
        domain = item.get("domain", "General")
        expected_ids = item.get("relevantJudgmentIds", [])
        expected_set = set(expected_ids)
        relevance_grades = item.get("relevanceGrading", {doc_id: 1.0 for doc_id in expected_ids})

        results = retriever.retrieve_similar(query_text, top_k=max(k, 5))
        retrieved_ids = [r.get("id") for r in results if r.get("id")]
        retrieved_scores = [r.get("similarityScore", 0.0) for r in results]

        p_at_1 = compute_precision_at_k(retrieved_ids, expected_set, k=1)
        p_at_3 = compute_precision_at_k(retrieved_ids, expected_set, k=3)
        p_at_5 = compute_precision_at_k(retrieved_ids, expected_set, k=5)
        p_at_k = compute_precision_at_k(retrieved_ids, expected_set, k=k)
        r_at_k = compute_recall_at_k(retrieved_ids, expected_set, k=k)
        rr = compute_reciprocal_rank(retrieved_ids, expected_set, k=k)
        ndcg = compute_ndcg_at_k(retrieved_ids, relevance_grades, k=k)

        p1_scores.append(p_at_1)
        p3_scores.append(p_at_3)
        p5_scores.append(p_at_5)
        precision_scores.append(p_at_k)
        recall_scores.append(r_at_k)
        rr_scores.append(rr)
        ndcg_scores.append(ndcg)

        is_hit = rr > 0.0
        if is_hit:
            hits += 1

        matched_expected = [did for did in retrieved_ids[:k] if did in expected_set]
        missed_expected = [did for did in expected_ids if did not in retrieved_ids[:k]]

        per_query_results.append({
            "queryId": qid,
            "query": query_text,
            "domain": domain,
            "expectedIds": expected_ids,
            "retrievedIds": retrieved_ids[:k],
            "retrievedScores": retrieved_scores[:k],
            "matchedExpected": matched_expected,
            "missedExpected": missed_expected,
            "precisionAt1": round(p_at_1, 4),
            "precisionAt3": round(p_at_3, 4),
            "precisionAt5": round(p_at_5, 4),
            "precisionAtK": round(p_at_k, 4),
            "recallAtK": round(r_at_k, 4),
            "reciprocalRank": round(rr, 4),
            "ndcgAtK": round(ndcg, 4),
            "isHit": is_hit
        })

    total_queries = len(queries)
    mean_p1 = sum(p1_scores) / max(total_queries, 1)
    mean_p3 = sum(p3_scores) / max(total_queries, 1)
    mean_p5 = sum(p5_scores) / max(total_queries, 1)
    mean_precision = sum(precision_scores) / max(total_queries, 1)
    mean_recall = sum(recall_scores) / max(total_queries, 1)
    mean_rr = sum(rr_scores) / max(total_queries, 1)
    mean_ndcg = sum(ndcg_scores) / max(total_queries, 1)
    hit_rate = hits / max(total_queries, 1)

    return {
        "k": k,
        "totalQueries": total_queries,
        "corpusSize": len(getattr(retriever, "corpus", [])),
        "hitRate": round(hit_rate, 4),
        "precisionAt1": round(mean_p1, 4),
        "precisionAt3": round(mean_p3, 4),
        "precisionAt5": round(mean_p5, 4),
        "precisionAtK": round(mean_precision, 4),
        "recallAtK": round(mean_recall, 4),
        "mrr": round(mean_rr, 4),
        "ndcgAtK": round(mean_ndcg, 4),
        "perQueryResults": per_query_results
    }
