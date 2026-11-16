"""
Comprehensive Benchmark Evaluation Script for Expanded Legal Retrieval Corpus
Jurist AI — Feature 1.4: Expand Hybrid Legal Retrieval Corpus to Open India Law

Evaluates against app/datasets/retrieval_benchmark.json across 5 configurations on the 176-case corpus:
1. TF-IDF alone (PrecedentRetriever)
2. BM25 alone (BM25Retriever)
3. 2-way RRF (HybridPrecedentRetriever with TF-IDF + BM25, semantic disabled)
4. Semantic alone (SemanticRetriever with BGE-small ONNX)
5. 3-way RRF (HybridPrecedentRetriever with TF-IDF + BM25 + Semantic)

Measures:
- Precision@5, Recall@5, MRR, NDCG@5, Hit Rate
- Query Latency (Average, P50, P95)
- Initialization Time
- Corpus Size & Passage Count
- Unjudged retrieval diagnostics (identifies authentic OIL rulings retrieved for benchmark queries)
"""

import os
import sys
import time
import json
import logging
from typing import Dict, Any, List

# Ensure ml-service root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.similarity.tfidf_retriever import PrecedentRetriever
from app.similarity.bm25_retriever import BM25Retriever
from app.similarity.semantic_retriever import SemanticRetriever
from app.similarity.hybrid_retriever import HybridPrecedentRetriever
from app.evaluation.retrieval_evaluator import evaluate_retrieval_benchmark

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_semantic_benchmark")


class TwoWayRRFWrapper:
    """Wrapper that disables semantic retrieval to benchmark 2-way RRF."""
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


def benchmark_engine(name: str, retriever: Any, benchmark_path: str, k: int = 5) -> Dict[str, Any]:
    with open(benchmark_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    # Warm-up run
    _ = retriever.retrieve_similar("Right to privacy Article 21", top_k=k)

    # Timing queries
    latencies = []
    for q in queries:
        t0 = time.perf_counter()
        _ = retriever.retrieve_similar(q["query"], top_k=k)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    avg_latency = sum(latencies) / len(latencies)
    p50_latency = sorted(latencies)[len(latencies) // 2]
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

    eval_result = evaluate_retrieval_benchmark(retriever, benchmark_path=benchmark_path, k=k)

    return {
        "engine": name,
        "k": k,
        "corpusSize": len(getattr(retriever, "corpus", [])),
        "totalQueries": eval_result["totalQueries"],
        "hitRate": eval_result["hitRate"],
        "precisionAtK": eval_result["precisionAtK"],
        "recallAtK": eval_result["recallAtK"],
        "mrr": eval_result["mrr"],
        "ndcgAtK": eval_result["ndcgAtK"],
        "latency_avg_ms": round(avg_latency, 2),
        "latency_p50_ms": round(p50_latency, 2),
        "latency_p95_ms": round(p95_latency, 2),
        "perQueryResults": eval_result["perQueryResults"]
    }


def analyze_unjudged_retrievals(three_way_results: Dict[str, Any], benchmark_path: str) -> List[Dict[str, Any]]:
    """Identifies newly retrieved Open India Law records in top-5 positions that were unjudged."""
    unjudged_cases = []
    for q_res in three_way_results["perQueryResults"]:
        qid = q_res["queryId"]
        query = q_res["query"]
        expected = set(q_res["expectedIds"])
        retrieved = q_res["retrievedIds"]

        for rank, cid in enumerate(retrieved, start=1):
            if cid not in expected and cid.startswith("OIL-"):
                unjudged_cases.append({
                    "queryId": qid,
                    "querySnippet": query[:60],
                    "rank": rank,
                    "caseId": cid,
                    "status": "unjudged_open_india_law_candidate"
                })
    return unjudged_cases


def main():
    benchmark_path = os.path.join(BASE_DIR, "app", "datasets", "retrieval_benchmark.json")
    results = {}

    print("\n" + "="*95)
    print(" JURIST AI — EXPANDED UNIFIED CORPUS RETRIEVAL BENCHMARK EVALUATION (K=5)")
    print("="*95)

    # 1. TF-IDF
    t0 = time.perf_counter()
    tfidf_retriever = PrecedentRetriever()
    tfidf_init_ms = (time.perf_counter() - t0) * 1000.0
    res_tfidf = benchmark_engine("TF-IDF alone", tfidf_retriever, benchmark_path, k=5)
    res_tfidf["init_ms"] = round(tfidf_init_ms, 2)
    results["tfidf"] = res_tfidf

    # 2. BM25
    t0 = time.perf_counter()
    bm25_retriever = BM25Retriever()
    bm25_init_ms = (time.perf_counter() - t0) * 1000.0
    res_bm25 = benchmark_engine("BM25 alone", bm25_retriever, benchmark_path, k=5)
    res_bm25["init_ms"] = round(bm25_init_ms, 2)
    results["bm25"] = res_bm25

    # 3. 2-way RRF
    hybrid_instance = HybridPrecedentRetriever()
    two_way_wrapper = TwoWayRRFWrapper(hybrid_instance)
    res_2way = benchmark_engine("TF-IDF + BM25 (2-way RRF)", two_way_wrapper, benchmark_path, k=5)
    res_2way["init_ms"] = round(tfidf_init_ms + bm25_init_ms, 2)
    results["2way_rrf"] = res_2way

    # 4. Semantic alone
    t0 = time.perf_counter()
    semantic_retriever = SemanticRetriever()
    sem_init_ms = (time.perf_counter() - t0) * 1000.0
    res_sem = benchmark_engine("Semantic alone (BGE-small ONNX)", semantic_retriever, benchmark_path, k=5)
    res_sem["init_ms"] = round(sem_init_ms, 2)
    results["semantic"] = res_sem

    # 5. 3-way RRF
    t0 = time.perf_counter()
    hybrid_3way = HybridPrecedentRetriever()
    hybrid_init_ms = (time.perf_counter() - t0) * 1000.0
    res_3way = benchmark_engine("3-way RRF (TF-IDF + BM25 + Semantic)", hybrid_3way, benchmark_path, k=5)
    res_3way["init_ms"] = round(hybrid_init_ms, 2)
    results["3way_rrf"] = res_3way

    # Summary table
    print(f"\n{'Engine':<40} | {'Corpus':<7} | {'P@5':<7} | {'R@5':<7} | {'MRR':<7} | {'NDCG@5':<7} | {'HitRate':<7} | {'Avg Latency':<12}")
    print("-" * 110)
    for key, data in results.items():
        print(
            f"{data['engine']:<40} | "
            f"{data['corpusSize']:<7} | "
            f"{data['precisionAtK']:<7.4f} | "
            f"{data['recallAtK']:<7.4f} | "
            f"{data['mrr']:<7.4f} | "
            f"{data['ndcgAtK']:<7.4f} | "
            f"{data['hitRate']:<7.4f} | "
            f"{data['latency_avg_ms']:>6.2f} ms"
        )
    print("=" * 110)

    # Unjudged retrieval diagnostics
    unjudged_diagnostics = analyze_unjudged_retrievals(res_3way, benchmark_path)
    print(f"\nUnjudged OIL Candidates Retrieved in Top-5 Positions: {len(unjudged_diagnostics)}")
    for item in unjudged_diagnostics[:8]:
        print(f"  Q: {item['queryId']} ('{item['querySnippet']}...') -> Rank #{item['rank']}: {item['caseId']}")

    # Save benchmark metrics artifact to JSON
    output_path = os.path.join(BASE_DIR, "app", "models", "retrieval_expanded_benchmark_results.json")
    save_data = {
        "evaluationTimestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "corpusSize": 176,
        "passageCount": len(semantic_retriever.passages),
        "configurations": results,
        "unjudgedDiagnostics": unjudged_diagnostics,
        "evaluationCaveat": (
            "Benchmark relevance lists in retrieval_benchmark.json were constructed when the corpus contained 27 cases. "
            "Additional retrieved OIL cases are unjudged candidates rather than confirmed negatives."
        )
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, indent=2)
    print(f"\nDetailed expanded benchmark results saved to: {output_path}")

    return results


if __name__ == "__main__":
    main()
