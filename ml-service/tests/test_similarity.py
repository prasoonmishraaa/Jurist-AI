"""
Unit Tests for TF-IDF Precedent Retrieval & Cosine Similarity
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.similarity.tfidf_retriever import PrecedentRetriever


class TestPrecedentSimilarity(unittest.TestCase):
    def setUp(self):
        self.retriever = PrecedentRetriever()

    def test_corpus_loaded(self):
        self.assertGreater(len(self.retriever.corpus), 10)
        self.assertIsNotNone(self.retriever.tfidf_matrix)

    def test_retrieve_puttaswamy_privacy(self):
        query = "Aadhaar scheme biometric data collection infringes right to privacy under Article 21"
        results = self.retriever.retrieve_similar(query, top_k=3)
        self.assertGreater(len(results), 0)
        top_match = results[0]
        self.assertIn("Puttaswamy", top_match["caseTitle"])
        self.assertGreater(top_match["similarityScore"], 0.10)
        self.assertIn("Article 21, Constitution of India", top_match["legalProvisions"])

    def test_retrieve_cheque_bounce(self):
        query = "Cheque dishonour under Section 138 Negotiable Instruments Act presumption under Section 139"
        results = self.retriever.retrieve_similar(query, top_k=3)
        self.assertGreater(len(results), 0)
        matched_titles = [r["caseTitle"] for r in results]
        self.assertTrue(any("Bir Singh" in t or "Rangappa" in t for t in matched_titles))

    def test_retrieve_arrest_grounds_vihaan_kumar(self):
        query = (
            "Accused arrested without written grounds of arrest under Article 22(1) and Section 50 CrPC / Section 47 BNSS "
            "and produced before Magistrate beyond 24 hours remand challenge."
        )
        results = self.retriever.retrieve_similar(query, top_k=5)
        titles = [r["caseTitle"] for r in results]
        self.assertTrue(any("Vihaan Kumar" in t or "Prabir Purkayastha" in t or "Mihir Rajesh Shah" in t for t in titles))
        for item in results:
            self.assertIn("officialSourceVerified", item)
            self.assertIn("relevanceClassification", item)
            self.assertIn("retrievalReason", item)

    def test_low_similarity_empty(self):
        query = "xyz random gibberish 12345 nonlegal string"
        results = self.retriever.retrieve_similar(query, top_k=3, min_score=0.1)
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
