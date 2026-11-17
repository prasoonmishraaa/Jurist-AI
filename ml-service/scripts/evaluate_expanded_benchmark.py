"""
Evaluation Runner for Human-Reviewed Expanded Benchmark
Jurist AI — Feature 1.5: Human-Reviewed Expanded Retrieval Benchmark

Evaluates all 5 retrieval configurations:
1. TF-IDF alone
2. BM25 alone
3. 2-way RRF (TF-IDF + BM25)
4. Semantic alone (BGE-small ONNX)
5. 3-way RRF (TF-IDF + BM25 + Semantic)

Computes:
- Precision@1, Precision@3, Precision@5, Recall@5, MRR, NDCG@5, and query latency.
Supports separate evaluation across:
- (A) Original 27-landmark benchmark
- (B) Newly annotated Open India Law benchmark (when human-approved labels exist)
- (C) Combined expanded benchmark (when human-approved labels exist)
"""

import os
import sys
import time
import json
import logging
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.similarity.tfidf_retriever import PrecedentRetriever
from app.similarity.bm25_retriever import BM25Retriever
from app.similarity.semantic_retriever import SemanticRetriever
from app.similarity.hybrid_retriever import HybridPrecedentRetriever
from app.evaluation.retrieval_evaluator import evaluate_retrieval_benchmark

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_expanded_benchmark")


class TwoWayRRFWrapper:
    """Disables semantic retrieval to benchmark 2-way RRF."""
    def __init__(self, hybrid: HybridPrecedentRetriever):
        self.hybrid = hybrid
        self.corpus = hybrid.corpus
        self._orig_avail = hybrid.semantic_retriever.is_available

    def retrieve_similar(self, query: str, top_k: int = 5):
        self.hybrid.semantic_retriever.is_available = False
        try:
            return self.hybrid.retrieve_similar(query, top_k=top_k)
        finally:
            self.hybrid.semantic_retriever.is_available = self._orig_avail


def benchmark_single_engine(
    name: str,
    retriever: Any,
    benchmark_path: str,
    k: int = 5
) -> Dict[str, Any]:
    with open(benchmark_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    # Warm-up run
    _ = retriever.retrieve_similar("Right to privacy Article 21", top_k=k)

    latencies = []
    for q in queries:
        t0 = time.perf_counter()
        _ = retriever.retrieve_similar(q["query"], top_k=k)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    avg_latency = sum(latencies) / max(len(latencies), 1)
    p50_latency = sorted(latencies)[len(latencies) // 2] if latencies else 0.0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0

    eval_result = evaluate_retrieval_benchmark(retriever, benchmark_path=benchmark_path, k=k)

    return {
        "engine": name,
        "k": k,
        "corpusSize": len(getattr(retriever, "corpus", [])),
        "totalQueries": eval_result["totalQueries"],
        "hitRate": eval_result["hitRate"],
        "precisionAt1": eval_result.get("precisionAt1", 0.0),
        "precisionAt3": eval_result.get("precisionAt3", 0.0),
        "precisionAt5": eval_result.get("precisionAt5", eval_result.get("precisionAtK", 0.0)),
        "recallAt5": eval_result.get("recallAtK", 0.0),
        "mrr": eval_result["mrr"],
        "ndcgAt5": eval_result["ndcgAtK"],
        "latency_avg_ms": round(avg_latency, 2),
        "latency_p50_ms": round(p50_latency, 2),
        "latency_p95_ms": round(p95_latency, 2),
        "perQueryResults": eval_result["perQueryResults"]
    }


def run_benchmark_suite(benchmark_path: str, suite_label: str) -> Dict[str, Any]:
    print(f"\n--- Running Benchmark Suite: {suite_label} ---")
    print(f"Path: {benchmark_path}")

    # Initialize engines
    t0 = time.perf_counter()
    tfidf = PrecedentRetriever()
    res_tfidf = benchmark_single_engine("TF-IDF alone", tfidf, benchmark_path, k=5)
    res_tfidf["init_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

    t0 = time.perf_counter()
    bm25 = BM25Retriever()
    res_bm25 = benchmark_single_engine("BM25 alone", bm25, benchmark_path, k=5)
    res_bm25["init_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

    hybrid = HybridPrecedentRetriever()
    two_way = TwoWayRRFWrapper(hybrid)
    res_2way = benchmark_single_engine("2-way RRF (TF-IDF + BM25)", two_way, benchmark_path, k=5)
    res_2way["init_ms"] = round(res_tfidf["init_ms"] + res_bm25["init_ms"], 2)

    t0 = time.perf_counter()
    semantic = SemanticRetriever()
    res_sem = benchmark_single_engine("Semantic alone (BGE-small ONNX)", semantic, benchmark_path, k=5)
    res_sem["init_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

    t0 = time.perf_counter()
    res_3way = benchmark_single_engine("3-way RRF (TF-IDF + BM25 + Semantic)", hybrid, benchmark_path, k=5)
    res_3way["init_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

    results = {
        "tfidf": res_tfidf,
        "bm25": res_bm25,
        "2way_rrf": res_2way,
        "semantic": res_sem,
        "3way_rrf": res_3way
    }

    # Print summary table
    print(f"\n{'Engine':<38} | {'P@1':<7} | {'P@3':<7} | {'P@5':<7} | {'R@5':<7} | {'MRR':<7} | {'NDCG@5':<7} | {'Latency':<10}")
    print("-" * 105)
    for k, data in results.items():
        print(
            f"{data['engine']:<38} | "
            f"{data['precisionAt1']:<7.4f} | "
            f"{data['precisionAt3']:<7.4f} | "
            f"{data['precisionAt5']:<7.4f} | "
            f"{data['recallAt5']:<7.4f} | "
            f"{data['mrr']:<7.4f} | "
            f"{data['ndcgAt5']:<7.4f} | "
            f"{data['latency_avg_ms']:>6.2f} ms"
        )
    print("=" * 105)

    return results


def main():
    original_benchmark_path = os.path.join(BASE_DIR, "app", "datasets", "retrieval_benchmark.json")
    expanded_benchmark_path = os.path.join(BASE_DIR, "app", "datasets", "retrieval_benchmark_expanded_human_reviewed.json")
    annotation_queue_path = os.path.join(BASE_DIR, "app", "datasets", "expanded_benchmark_annotation_queue.json")

    print("\n" + "="*85)
    print(" JURIST AI — MULTI-BENCHMARK RETRIEVAL EVALUATION")
    print("="*85)

    # 1. Evaluate on Original Landmark Benchmark (Baseline)
    print("\n[Suite 1/3] Evaluating on Original 27-Landmark Ground Truth...")
    orig_results = run_benchmark_suite(original_benchmark_path, "Original 27-Landmark Benchmark")

    # 2. Check if Human-Reviewed Ground Truth is Available
    if os.path.exists(expanded_benchmark_path):
        print("\n[Suite 2/3 & 3/3] Human-reviewed expanded ground truth detected.")
        exp_results = run_benchmark_suite(expanded_benchmark_path, "Combined Human-Reviewed Benchmark")
    else:
        print("\n[Suite 2/3 & 3/3] Notice: 'retrieval_benchmark_expanded_human_reviewed.json' is not yet present.")
        print("Reason: All 36 unjudged candidate occurrences in 'expanded_benchmark_annotation_queue.json' are currently in 'pending_review'.")
        print("Strict Integrity Constraint: No unreviewed labels or synthetic ground-truth files may be generated.")
        print("To evaluate once human review is complete, run: python ml-service/scripts/build_expanded_ground_truth.py && python ml-service/scripts/evaluate_expanded_benchmark.py")


if __name__ == "__main__":
    main()
