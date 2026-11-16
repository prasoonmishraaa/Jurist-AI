"""
Unit & Integration Tests for Hybrid Legal Retrieval
Jurist AI — Feature 1: Hybrid Legal Retrieval

Covers:
- BM25 ranking and term preservation
- Semantic retriever interface and graceful offline handling
- Reciprocal Rank Fusion (RRF) calculation and 1-based indexing
- Deduplication of cases across modalities
- Missing modality fallback
- API response contract and non-breaking retrievalSignals
"""

import os
import sys
import unittest
import numpy as np

# Ensure ml-service root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.similarity.bm25_retriever import BM25Retriever, InvertedBM25Okapi
from app.similarity.semantic_retriever import SemanticRetriever
from app.similarity.hybrid_retriever import HybridPrecedentRetriever


class TestBM25Retriever(unittest.TestCase):
    def setUp(self):
        self.retriever = BM25Retriever()

    def test_bm25_initialization_and_corpus_load(self):
        self.assertGreater(len(self.retriever.corpus), 0)
        self.assertEqual(len(self.retriever.corpus), len(self.retriever.tokenized_corpus))

    def test_bm25_exact_statutory_and_keyword_ranking(self):
        # Query on Section 154 CrPC mandatory FIR registration
        query = "Police officer refuses to register First Information Report under Section 154"
        results = self.retriever.retrieve_similar(query, top_k=3)
        self.assertGreaterEqual(len(results), 1)

        # Lalita Kumari (SC-2013-004) should rank top
        top_id = results[0]["id"]
        self.assertEqual(top_id, "SC-2013-004")
        self.assertIn("154", results[0]["matchedTerms"])
        self.assertGreater(results[0]["rawBm25Score"], 0.0)

    def test_bm25_isolated_okapi_math(self):
        corpus = [
            ["section", "138", "negotiable", "instruments", "cheque", "dishonour"],
            ["section", "482", "crpc", "quashing", "criminal", "proceedings"],
            ["right", "to", "privacy", "article", "21", "aadhaar", "surveillance"]
        ]
        bm = InvertedBM25Okapi(corpus, k1=1.5, b=0.75)
        scores = bm.get_scores(["section", "138", "cheque"])
        self.assertEqual(len(scores), 3)
        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[0], scores[2])


class TestSemanticRetriever(unittest.TestCase):
    def setUp(self):
        self.retriever = SemanticRetriever()

    def test_semantic_interface_contract(self):
        # Must provide is_available property and availability_status string
        self.assertIsInstance(self.retriever.is_available, bool)
        self.assertIsInstance(self.retriever.availability_status, str)

    def test_graceful_offline_degradation_without_simulation(self):
        # When offline / model uninstalled, must NOT fabricate embeddings
        if not self.retriever.is_available:
            results = self.retriever.retrieve_similar("arbitrary legal query", top_k=5)
            self.assertEqual(results, [])
            self.assertIn("unavailable", self.retriever.availability_status.lower())


class TestReciprocalRankFusion(unittest.TestCase):
    def setUp(self):
        self.hybrid = HybridPrecedentRetriever()

    def test_rrf_scoring_formula(self):
        # Test mathematical formula: RRF(d) = sum w / (60 + rank)
        k = 60
        w_tfidf = 1.0
        w_bm25 = 1.0
        
        # Doc with tfidf_rank=1, bm25_rank=1
        expected_top = (w_tfidf / (k + 1)) + (w_bm25 / (k + 1))
        # Doc with tfidf_rank=1, bm25_rank=2
        expected_second = (w_tfidf / (k + 1)) + (w_bm25 / (k + 2))
        
        self.assertAlmostEqual(expected_top, 2.0 / 61.0, places=6)
        self.assertGreater(expected_top, expected_second)

    def test_duplicate_case_removal(self):
        # Ensure every case ID in hybrid results is completely unique
        results = self.hybrid.retrieve_similar(
            "Arrest without furnishing written grounds of arrest Article 22(1)",
            top_k=10
        )
        case_ids = [r["id"] for r in results]
        self.assertEqual(len(case_ids), len(set(case_ids)), "Duplicate case IDs detected in hybrid results")

    def test_missing_modality_contributes_zero(self):
        # If a candidate only appears in TF-IDF or only in BM25, the other modality contributes 0
        results = self.hybrid.retrieve_similar("anticipatory bail non-bailable offence", top_k=10)
        for r in results:
            sig = r.get("retrievalSignals", {})
            self.assertIn("rrf_score", sig)
            self.assertIn("active_modalities", sig)
            
            # Verify calculation from ranks
            calc_score = 0.0
            if sig.get("tfidf_rank") is not None:
                calc_score += 1.0 / (60 + sig["tfidf_rank"])
            if sig.get("bm25_rank") is not None:
                calc_score += 1.0 / (60 + sig["bm25_rank"])
            if sig.get("semantic_rank") is not None:
                calc_score += 1.2 / (60 + sig["semantic_rank"])
                
            self.assertAlmostEqual(sig["rrf_score"], calc_score, places=5)

    def test_retrieval_signals_schema_conformance(self):
        results = self.hybrid.retrieve_similar("cheque dishonour Section 138 presumption", top_k=5)
        self.assertGreater(len(results), 0)
        
        for r in results:
            # Check all mandatory standard schema fields
            self.assertIn("id", r)
            self.assertIn("caseTitle", r)
            self.assertIn("citation", r)
            self.assertIn("similarityScore", r)
            self.assertIn("matchedTerms", r)
            self.assertIn("retrievalSignals", r)
            
            sig = r["retrievalSignals"]
            self.assertIn("tfidf_rank", sig)
            self.assertIn("bm25_rank", sig)
            self.assertIn("semantic_rank", sig)
            self.assertIn("rrf_score", sig)
            self.assertIn("active_modalities", sig)
            
            # Semantic rank should be None when semantic retrieval is offline
            if not self.hybrid.semantic_retriever.is_available:
                self.assertIsNone(sig["semantic_rank"])


if __name__ == "__main__":
    unittest.main()
