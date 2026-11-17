"""
Unit Tests for Retrieval Evaluation Metrics (Precision@K, Recall@K, MRR, NDCG@K)
Jurist AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System
"""

import sys
import os
import unittest
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.evaluation.retrieval_evaluator import (
    compute_precision_at_k,
    compute_recall_at_k,
    compute_reciprocal_rank,
    compute_dcg_at_k,
    compute_ndcg_at_k,
    evaluate_retrieval_benchmark
)
from app.similarity.tfidf_retriever import PrecedentRetriever


class TestRetrievalEvaluator(unittest.TestCase):
    def test_precision_at_k(self):
        retrieved = ["A", "B", "C", "D", "E"]
        relevant = {"A", "C"}
        # 2 out of 5 are relevant
        self.assertAlmostEqual(compute_precision_at_k(retrieved, relevant, k=5), 0.4)
        # 1 out of 2 are relevant for k=2
        self.assertAlmostEqual(compute_precision_at_k(retrieved, relevant, k=2), 0.5)
        # Empty inputs
        self.assertEqual(compute_precision_at_k([], relevant, k=5), 0.0)
        self.assertEqual(compute_precision_at_k(retrieved, set(), k=5), 0.0)

    def test_recall_at_k(self):
        retrieved = ["A", "B", "C", "D", "E"]
        relevant = {"A", "C", "Z"}
        # Found 2 out of 3 total relevant
        self.assertAlmostEqual(compute_recall_at_k(retrieved, relevant, k=5), 2.0 / 3.0)
        # Top 1 finds 1 out of 3
        self.assertAlmostEqual(compute_recall_at_k(retrieved, relevant, k=1), 1.0 / 3.0)
        # Empty relevant set
        self.assertEqual(compute_recall_at_k(retrieved, set(), k=5), 0.0)

    def test_reciprocal_rank(self):
        relevant = {"C"}
        # First relevant is at rank 3 -> RR = 1/3
        retrieved = ["A", "B", "C", "D", "E"]
        self.assertAlmostEqual(compute_reciprocal_rank(retrieved, relevant, k=5), 1.0 / 3.0)

        # First relevant is at rank 1 -> RR = 1.0
        retrieved_first = ["C", "A", "B"]
        self.assertAlmostEqual(compute_reciprocal_rank(retrieved_first, relevant, k=5), 1.0)

        # Relevant is beyond K -> RR = 0.0
        retrieved_beyond = ["A", "B", "D", "E", "F", "C"]
        self.assertEqual(compute_reciprocal_rank(retrieved_beyond, relevant, k=5), 0.0)

    def test_ndcg_at_k_perfect_ranking(self):
        retrieved = ["DOC-1", "DOC-2", "DOC-3"]
        grades = {"DOC-1": 2.0, "DOC-2": 1.0, "DOC-3": 0.0}
        # In ideal order: DOC-1 (2), DOC-2 (1) -> NDCG must be 1.0
        ndcg = compute_ndcg_at_k(retrieved, grades, k=3)
        self.assertAlmostEqual(ndcg, 1.0)

    def test_ndcg_at_k_suboptimal_ranking(self):
        retrieved = ["DOC-2", "DOC-1"]
        grades = {"DOC-1": 2.0, "DOC-2": 1.0}
        # DCG = (2^1 - 1)/log2(2) + (2^2 - 1)/log2(3) = 1 + 3/1.58496 = 2.89278
        # IDCG = (2^2 - 1)/log2(2) + (2^1 - 1)/log2(3) = 3 + 1/1.58496 = 3.63092
        # NDCG = 2.89278 / 3.63092 ~= 0.7967
        ndcg = compute_ndcg_at_k(retrieved, grades, k=2)
        self.assertGreater(ndcg, 0.70)
        self.assertLess(ndcg, 0.90)

    def test_ndcg_at_k_edge_cases(self):
        self.assertEqual(compute_ndcg_at_k([], {"A": 1.0}, k=5), 0.0)
        self.assertEqual(compute_ndcg_at_k(["A"], {}, k=5), 0.0)
        self.assertEqual(compute_ndcg_at_k(["A"], {"A": 0.0}, k=5), 0.0)

    def test_benchmark_evaluation_execution(self):
        retriever = PrecedentRetriever()
        results = evaluate_retrieval_benchmark(retriever, k=5)
        self.assertIn("totalQueries", results)
        self.assertIn("precisionAtK", results)
        self.assertIn("recallAtK", results)
        self.assertIn("mrr", results)
        self.assertIn("ndcgAtK", results)
        self.assertEqual(results["totalQueries"], 15)
        self.assertGreaterEqual(results["mrr"], 0.0)
        self.assertLessEqual(results["mrr"], 1.0)


if __name__ == "__main__":
    unittest.main()
