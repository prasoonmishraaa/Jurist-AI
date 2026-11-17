"""
Comprehensive Unit & Integration Tests for BGE-small ONNX Semantic Retrieval
Jurist AI — Feature 1.3: Complete Semantic Retrieval

Tests:
- ONNX Runtime and Tokenizer loading
- Availability status and dimension verification (384-d)
- Query encoding, BGE instruction prefixing, and L2 normalization (norm == 1.0)
- Paragraph-aware passage chunking and Max-P aggregation
- Precedent ranking and schema conformance
- Deterministic retrieval outputs
- Graceful degradation with missing artifacts (offline fallback)
- 3-Way Reciprocal Rank Fusion integration in HybridPrecedentRetriever
"""

import os
import sys
import unittest
import numpy as np

# Ensure ml-service root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.similarity.semantic_retriever import SemanticRetriever, BGE_QUERY_PREFIX
from app.similarity.passage_chunker import build_legal_passages, chunk_judgment_text
from app.similarity.hybrid_retriever import HybridPrecedentRetriever


class TestSemanticRetrieverRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever = SemanticRetriever()

    def test_01_engine_initialization_and_availability(self):
        """Verifies ONNX model and tokenizer load into active state."""
        self.assertTrue(self.retriever.is_available, f"Semantic engine should be available. Status: {self.retriever.availability_status}")
        self.assertEqual(self.retriever.availability_status, "active_onnx")
        self.assertEqual(self.retriever.model_backend, "onnxruntime")
        self.assertEqual(self.retriever.dimension, 384)
        self.assertIsNotNone(self.retriever.session)
        self.assertIsNotNone(self.retriever.tokenizer)

    def test_02_corpus_and_passages_manifest_loaded(self):
        """Verifies corpus judgments, passage metadata, and embeddings array match."""
        self.assertGreaterEqual(len(self.retriever.corpus), 27)
        self.assertGreaterEqual(len(self.retriever.passages), 27)
        self.assertIsNotNone(self.retriever.corpus_embeddings)
        self.assertEqual(self.retriever.corpus_embeddings.shape[1], 384)
        self.assertEqual(self.retriever.corpus_embeddings.shape[0], len(self.retriever.passages))

    def test_03_query_encoding_and_normalization(self):
        """Verifies query encoding produces 384-d vector with unit L2 norm."""
        query = "Right to privacy and informational autonomy Article 21"
        vec = self.retriever.encode_query(query)
        self.assertIsNotNone(vec)
        self.assertIsInstance(vec, np.ndarray)
        self.assertEqual(vec.shape, (384,))
        self.assertEqual(vec.dtype, np.float32)

        # L2 norm must be 1.0 within floating point precision
        norm = np.linalg.norm(vec)
        self.assertAlmostEqual(float(norm), 1.0, places=5)

    def test_04_query_encoding_empty_or_whitespace(self):
        """Empty or whitespace queries return None without exception."""
        self.assertIsNone(self.retriever.encode_query(""))
        self.assertIsNone(self.retriever.encode_query("   "))

    def test_05_dense_retrieval_ranking(self):
        """Verifies dense retrieval returns expected landmark precedent for topical query."""
        query = "Fundamental right to privacy and informational autonomy Article 21"
        results = self.retriever.retrieve_similar(query, top_k=3)
        self.assertGreaterEqual(len(results), 1)

        # Puttaswamy (SC-2017-001) must rank #1
        top_case = results[0]
        self.assertEqual(top_case["id"], "SC-2017-001")
        self.assertIn("Puttaswamy", top_case["caseTitle"])
        self.assertGreater(top_case["similarityScore"], 0.6)
        self.assertEqual(top_case["relevanceClassification"], "Semantic Embedding Match")
        self.assertIn("SC-2017-001", top_case["matchedPassageId"])
        self.assertIn("privacy", top_case["matchedPassage"].lower())

    def test_06_passage_schema_conformance(self):
        """Verifies every returned precedent conforms to schema expectations."""
        query = "Cheque bounce Section 138 presumption of legally enforceable debt"
        results = self.retriever.retrieve_similar(query, top_k=5)
        self.assertGreater(len(results), 0)

        for r in results:
            self.assertIn("id", r)
            self.assertIn("caseTitle", r)
            self.assertIn("court", r)
            self.assertIn("citation", r)
            self.assertIn("similarityScore", r)
            self.assertIn("matchedPassage", r)
            self.assertIn("matchedPassageId", r)
            self.assertIn("matchedPassageIndex", r)
            self.assertIn("retrievalReason", r)
            self.assertIn("historicalOutcome", r)
            self.assertIsInstance(r["similarityScore"], float)
            self.assertGreaterEqual(r["similarityScore"], 0.0)
            self.assertLessEqual(r["similarityScore"], 1.0)

    def test_07_deterministic_output(self):
        """Identical queries must return identical scores and order."""
        query = "Mandatory registration of FIR under Section 154 CrPC"
        res1 = self.retriever.retrieve_similar(query, top_k=5)
        res2 = self.retriever.retrieve_similar(query, top_k=5)

        self.assertEqual([r["id"] for r in res1], [r["id"] for r in res2])
        self.assertEqual([r["similarityScore"] for r in res1], [r["similarityScore"] for r in res2])

    def test_08_offline_fallback_degradation(self):
        """When initialized with non-existent model dir, engine degrades gracefully."""
        offline_retriever = SemanticRetriever(model_dir="/non/existent/model/dir")
        self.assertFalse(offline_retriever.is_available)
        self.assertIn("unavailable", offline_retriever.availability_status.lower())
        results = offline_retriever.retrieve_similar("Any query", top_k=5)
        self.assertEqual(results, [])


class TestPassageChunker(unittest.TestCase):
    def test_passage_chunking_preserves_metadata(self):
        mock_cases = [
            {
                "id": "MOCK-001",
                "caseTitle": "Test Case v. Union of India",
                "court": "Supreme Court of India",
                "judgmentDate": "2024-01-01",
                "citation": "(2024) 1 SCC 1",
                "legalProvisions": ["Article 21"],
                "summary": "This is a summary of the fundamental right to liberty.",
                "judgmentText": "The court held that personal liberty cannot be curtailed arbitrarily. Fair procedure is mandatory under Article 21.",
                "outcome": "Allowed",
                "outcomeRationale": "Arbitrary detention violated constitutional guarantees."
            }
        ]
        passages = build_legal_passages(mock_cases)
        self.assertEqual(len(passages), 2)  # 1 summary + 1 judgment chunk

        # Summary passage
        p0 = passages[0]
        self.assertEqual(p0["passage_id"], "MOCK-001#p00")
        self.assertEqual(p0["case_id"], "MOCK-001")
        self.assertTrue(p0["is_summary"])
        self.assertIn("Test Case", p0["passage_text"])
        self.assertIn("Article 21", p0["passage_text"])

        # Judgment passage
        p1 = passages[1]
        self.assertEqual(p1["passage_id"], "MOCK-001#p01")
        self.assertFalse(p1["is_summary"])
        self.assertIn("personal liberty cannot be curtailed", p1["raw_text"])


class TestThreeWayHybridIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hybrid = HybridPrecedentRetriever()

    def test_three_way_active_modalities(self):
        """Verifies active modalities includes semantic when semantic retriever is available."""
        self.assertTrue(self.hybrid.semantic_retriever.is_available)
        results = self.hybrid.retrieve_similar("Right to privacy Article 21", top_k=5)
        self.assertGreater(len(results), 0)

        for r in results:
            sig = r.get("retrievalSignals", {})
            self.assertEqual(sig.get("active_modalities"), ["tfidf", "bm25", "semantic"])
            # Top candidate should have a valid semantic rank
            if r["id"] == "SC-2017-001":
                self.assertIsNotNone(sig.get("semantic_rank"))
                self.assertIsInstance(sig["semantic_rank"], int)

    def test_three_way_rrf_formula_calculation(self):
        """Verifies that 3-way RRF combines tfidf, bm25, and semantic weights accurately."""
        results = self.hybrid.retrieve_similar("cheque dishonour section 138", top_k=5)
        self.assertGreater(len(results), 0)

        for r in results:
            sig = r["retrievalSignals"]
            r_tf = sig.get("tfidf_rank")
            r_bm = sig.get("bm25_rank")
            r_sem = sig.get("semantic_rank")

            expected_rrf = 0.0
            if r_tf is not None:
                expected_rrf += 1.0 / (60 + r_tf)
            if r_bm is not None:
                expected_rrf += 1.0 / (60 + r_bm)
            if r_sem is not None:
                expected_rrf += 1.2 / (60 + r_sem)

            self.assertAlmostEqual(sig["rrf_score"], expected_rrf, places=5)


if __name__ == "__main__":
    unittest.main()
