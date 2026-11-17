"""
Comprehensive Test Suite for Unified Legal Retrieval Corpus (Feature 1.4)
Jurist AI — Feature 1.4: Expand Hybrid Legal Retrieval Corpus to Open India Law

Verifies:
1. Unified Corpus construction, record counts, and schema conformance (176 unique records).
2. Deduplication integrity: exact duplicate pair detected, 1 excluded, retained in manifest.
3. Puttaswamy distinction: 2017 landmark 9-judge bench vs 2015 3-judge reference order preserved.
4. Strict Outcome Leakage Prevention: Zero target disposition terms in dense passage texts.
5. Dense Embedding Matrix: (771, 384) float32, L2-normalized, finite, 1:1 aligned with passages.
6. Three-Way RRF Hybrid Retrieval execution across unified corpus.
7. /api/ml/health endpoint contract and corpus metadata reporting.
"""

import os
import sys
import re
import json
import io
import unittest
import numpy as np

# Ensure ml-service root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.similarity.passage_chunker import (
    build_legal_passages,
    sanitize_outcome_leakage,
    load_passages_manifest
)
from app.similarity.hybrid_retriever import HybridPrecedentRetriever
from app.services.api import MLServiceHandler


class TestUnifiedCorpusIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.unified_path = os.path.join(BASE_DIR, "app", "datasets", "unified_judgments.json")
        cls.manifest_path = os.path.join(BASE_DIR, "app", "datasets", "unified_corpus_manifest.json")
        cls.landmark_path = os.path.join(BASE_DIR, "app", "datasets", "indian_judgments.json")
        cls.oil_path = os.path.join(BASE_DIR, "app", "datasets", "open_india_law_sample_150.json")

        with open(cls.unified_path, "r", encoding="utf-8") as f:
            cls.unified_data = json.load(f)
        with open(cls.manifest_path, "r", encoding="utf-8") as f:
            cls.manifest = json.load(f)

    def test_01_corpus_manifest_and_schema(self):
        """Unified corpus contains exactly 176 unique judgments with proper schema."""
        self.assertEqual(len(self.unified_data), 176)
        self.assertEqual(self.manifest["totalUniqueRecords"], 176)
        self.assertEqual(self.manifest["sourceBreakdown"]["indian_judgments_landmark"], 27)
        self.assertEqual(self.manifest["sourceBreakdown"]["open_india_law_sample"], 149)

        required_keys = {
            "id", "caseTitle", "court", "judgmentDate",
            "legalProvisions", "summary", "judgmentText", "sourceDataset"
        }

        landmark_count = 0
        oil_count = 0
        seen_ids = set()

        for case in self.unified_data:
            case_id = case.get("id")
            self.assertIsNotNone(case_id)
            self.assertNotIn(case_id, seen_ids, f"Duplicate case ID detected: {case_id}")
            seen_ids.add(case_id)

            for key in required_keys:
                self.assertIn(key, case, f"Case {case_id} missing required key '{key}'")

            source = case["sourceDataset"]
            self.assertIn(source, ["indian_judgments_landmark", "open_india_law_sample"])
            if source == "indian_judgments_landmark":
                landmark_count += 1
            else:
                oil_count += 1

        self.assertEqual(landmark_count, 27)
        self.assertEqual(oil_count, 149)

    def test_02_deduplication_integrity(self):
        """Duplicate pair in Open India Law is properly resolved and recorded in manifest."""
        self.assertEqual(self.manifest["totalDeduplicatedRecords"], 1)
        decisions = self.manifest["deduplicationDecisions"]
        self.assertEqual(len(decisions), 1)

        excluded_entry = decisions[0]
        self.assertEqual(excluded_entry["excludedId"], "OIL-DHC-DLHC012615072014")
        self.assertEqual(excluded_entry["retainedId"], "OIL-DHC-DLHC010440622015")
        self.assertIn("Identical judgment text hash", excluded_entry["reason"])

        # Excluded record must NOT be in unified corpus
        unified_ids = {c["id"] for c in self.unified_data}
        self.assertNotIn("OIL-DHC-DLHC012615072014", unified_ids)

        # Retained record MUST be in unified corpus
        self.assertIn("OIL-DHC-DLHC010440622015", unified_ids)

    def test_03_puttaswamy_distinction_preserved(self):
        """Puttaswamy 2017 (9-judge privacy) and 2015 (3-judge reference order) are both preserved."""
        case_map = {c["id"]: c for c in self.unified_data}

        self.assertIn("SC-2017-001", case_map)
        self.assertIn("OIL-SC-2015_INSC_559", case_map)

        p2017 = case_map["SC-2017-001"]
        p2015 = case_map["OIL-SC-2015_INSC_559"]

        # Titles and dates must be distinct
        self.assertIn("2017", p2017["judgmentDate"])
        self.assertIn("2015", p2015["judgmentDate"])

        # Sources must be distinct
        self.assertEqual(p2017["sourceDataset"], "indian_judgments_landmark")
        self.assertEqual(p2015["sourceDataset"], "open_india_law_sample")

        # Texts must be distinct
        self.assertNotEqual(p2017["judgmentText"], p2015["judgmentText"])


class TestPassageIntegrityAndLeakagePrevention(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.passages_path = os.path.join(BASE_DIR, "app", "models", "unified_passages_metadata.json")
        cls.passages = load_passages_manifest(cls.passages_path)

    def test_04_passages_manifest_integrity(self):
        """Passages manifest contains 771 passages across all 176 unique cases."""
        self.assertEqual(len(self.passages), 771)

        unique_case_ids = set(p["case_id"] for p in self.passages)
        self.assertEqual(len(unique_case_ids), 176)

        landmark_passages = [p for p in self.passages if p["source_dataset"] == "indian_judgments_landmark"]
        oil_passages = [p for p in self.passages if p["source_dataset"] in ["open_india_law_sample", "open_india_law"]]

        self.assertEqual(len(landmark_passages), 54)
        self.assertEqual(len(oil_passages), 717)

    def test_05_strict_outcome_leakage_absence(self):
        """Zero passage texts contain explicit target outcome labels, preventing leakage."""
        leakage_patterns = [
            re.compile(r"\bthe\s+appeal\s+is\s+allowed\b", re.I),
            re.compile(r"\bthe\s+appeal\s+is\s+dismissed\b", re.I),
            re.compile(r"\bappeal\s+stands\s+allowed\b", re.I),
            re.compile(r"\bappeal\s+stands\s+dismissed\b", re.I),
            re.compile(r"\bbail\s+is\s+granted\b", re.I),
            re.compile(r"\bbail\s+is\s+rejected\b", re.I),
            re.compile(r"\boutcome\s*:\s*(allowed|dismissed|bail granted)\b", re.I),
            re.compile(r"\bdisposition\s*:\s*(allowed|dismissed)\b", re.I),
        ]

        leaked_count = 0
        for p in self.passages:
            text = p["passage_text"]
            for pat in leakage_patterns:
                if pat.search(text):
                    leaked_count += 1
                    break

        self.assertEqual(leaked_count, 0, f"Found {leaked_count} passages with target outcome leakage!")

        # Outcome metadata keys MUST exist in metadata
        has_outcome_meta = any("outcome" in p for p in self.passages)
        self.assertTrue(has_outcome_meta, "Metadata should contain outcome key for downstream tasks")


class TestEmbeddingMatrixAlignment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.embeddings_path = os.path.join(BASE_DIR, "app", "models", "unified_embeddings.npy")
        cls.passages_path = os.path.join(BASE_DIR, "app", "models", "unified_passages_metadata.json")
        cls.embeddings = np.load(cls.embeddings_path)
        cls.passages = load_passages_manifest(cls.passages_path)

    def test_06_embedding_matrix_properties(self):
        """Embeddings matrix is shape (771, 384), float32, all finite, and unit L2 normalized."""
        self.assertEqual(self.embeddings.shape, (771, 384))
        self.assertEqual(self.embeddings.dtype, np.float32)

        # 1:1 alignment between matrix rows and passage list
        self.assertEqual(self.embeddings.shape[0], len(self.passages))

        # Check for NaN / Inf
        self.assertTrue(np.all(np.isfinite(self.embeddings)), "Embeddings contain NaN or Inf values")

        # Check L2 normalization
        norms = np.linalg.norm(self.embeddings, axis=1)
        self.assertTrue(np.allclose(norms, 1.0, atol=1e-4), "Not all vectors are L2 normalized to 1.0")


class TestRetrievalRuntimeOnUnifiedCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hybrid = HybridPrecedentRetriever()

    def test_07_three_way_rrf_retrieval(self):
        """Hybrid retriever searches across unified corpus and returns deduplicated case results."""
        self.assertTrue(self.hybrid.semantic_retriever.is_available)
        results = self.hybrid.retrieve_similar("Right to privacy Article 21", top_k=5)
        self.assertGreaterEqual(len(results), 1)

        # Deduplication check: each result must have unique ID
        retrieved_ids = [r["id"] for r in results]
        self.assertEqual(len(retrieved_ids), len(set(retrieved_ids)), "Retrieved results contain duplicate IDs")

        # Check signals and sourceDataset metadata
        for r in results:
            self.assertIn("sourceDataset", r)
            self.assertIn(r["sourceDataset"], ["indian_judgments_landmark", "open_india_law_sample", "open_india_law"])
            self.assertIn("retrievalSignals", r)
            signals = r["retrievalSignals"]
            self.assertIn("rrf_score", signals)
            self.assertIn("active_modalities", signals)
            self.assertIn("semantic", signals["active_modalities"])

    def test_08_ml_health_endpoint_expanded_corpus(self):
        """ML health endpoint reports expanded unified corpus statistics."""
        class DummyHandler(MLServiceHandler):
            def __init__(self):
                self.path = "/api/ml/health"
                self.wfile = io.BytesIO()
                self.status_code = None

            def send_response(self, code, message=None):
                self.status_code = code

            def send_header(self, keyword, value):
                pass

            def end_headers(self):
                pass

        handler = DummyHandler()
        handler.do_GET()
        self.assertEqual(handler.status_code, 200)
        data = json.loads(handler.wfile.getvalue().decode("utf-8"))

        self.assertEqual(data.get("corpusSize"), 176)
        self.assertEqual(data.get("indexedPassages"), 771)
        self.assertEqual(data.get("corpusManifestVersion"), "v1.4.0-unified")

        breakdown = data.get("sourceBreakdown", {})
        self.assertEqual(breakdown.get("landmark"), 27)
        self.assertEqual(breakdown.get("open_india_law"), 149)


if __name__ == "__main__":
    unittest.main()
