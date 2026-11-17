"""
Hybrid Legal Precedent Retrieval Engine
Jurist AI — Feature 1: Hybrid Legal Retrieval

Aggregates TF-IDF (lexical + statutory boost), BM25 (term saturation + length normalization),
and Semantic (dense vectors) via Reciprocal Rank Fusion (RRF).
Gracefully degrades when semantic retrieval is unavailable without simulating scores.
"""

import os
import logging
from typing import List, Dict, Any, Optional

from app.similarity.tfidf_retriever import PrecedentRetriever
from app.similarity.bm25_retriever import BM25Retriever
from app.similarity.semantic_retriever import SemanticRetriever

logger = logging.getLogger(__name__)


class HybridPrecedentRetriever:
    """
    Three-way ensemble legal retrieval engine integrating:
    1. TF-IDF + statutory signal detector
    2. BM25Okapi probabilistic retriever
    3. Semantic dense vector retriever (when operational)
    Combined using Reciprocal Rank Fusion (RRF):
        RRF(d) = sum_{m in Active} w_m / (60 + rank_m(d))
    """

    def __init__(
        self,
        corpus_path: Optional[str] = None,
        weight_tfidf: float = 1.0,
        weight_bm25: float = 1.0,
        weight_semantic: float = 1.2,
        rrf_k: int = 60
    ):
        if corpus_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            unified_path = os.path.join(base_dir, "datasets", "unified_judgments.json")
            if os.path.exists(unified_path):
                corpus_path = unified_path
            else:
                corpus_path = os.path.join(base_dir, "datasets", "indian_judgments.json")

        self.corpus_path = corpus_path
        self.weight_tfidf = weight_tfidf
        self.weight_bm25 = weight_bm25
        self.weight_semantic = weight_semantic
        self.rrf_k = rrf_k

        # Initialize sub-engines
        self.tfidf_retriever = PrecedentRetriever(corpus_path=corpus_path)
        self.bm25_retriever = BM25Retriever(corpus_path=corpus_path)
        self.semantic_retriever = SemanticRetriever(corpus_path=corpus_path)

        self.corpus = self.tfidf_retriever.corpus

        logger.info(
            f"HybridPrecedentRetriever initialized. Corpus: {len(self.corpus)} cases. "
            f"Semantic operational: {self.semantic_retriever.is_available} "
            f"({self.semantic_retriever.availability_status})."
        )

    def retrieve_similar(
        self,
        query_text: str,
        top_k: int = 5,
        candidate_pool_size: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid multi-signal retrieval:
        1. Gathers candidate pools from active retrieval modalities.
        2. Applies Reciprocal Rank Fusion (RRF) with 1-based indexing.
        3. Normalizes scores and adds non-breaking retrievalSignals metadata.
        """
        if not query_text or not self.corpus:
            return []

        active_modalities = ["tfidf", "bm25"]
        if self.semantic_retriever.is_available:
            active_modalities.append("semantic")

        # 1. Retrieve candidates from each modality
        tfidf_candidates = self.tfidf_retriever.retrieve_similar(
            query_text, top_k=candidate_pool_size, min_score=0.0
        )
        bm25_candidates = self.bm25_retriever.retrieve_similar(
            query_text, top_k=candidate_pool_size, min_score=0.0
        )
        
        semantic_candidates = []
        if self.semantic_retriever.is_available:
            semantic_candidates = self.semantic_retriever.retrieve_similar(
                query_text, top_k=candidate_pool_size, min_score=0.0
            )

        logger.info(
            f"[HybridRetriever] Query: '{query_text[:50]}...' | "
            f"Candidates: TF-IDF={len(tfidf_candidates)}, BM25={len(bm25_candidates)}, "
            f"Semantic={len(semantic_candidates)} | Active: {active_modalities}"
        )

        # 2. Build 1-based rank maps
        tfidf_ranks: Dict[str, int] = {doc["id"]: idx + 1 for idx, doc in enumerate(tfidf_candidates)}
        bm25_ranks: Dict[str, int] = {doc["id"]: idx + 1 for idx, doc in enumerate(bm25_candidates)}
        semantic_ranks: Dict[str, int] = (
            {doc["id"]: idx + 1 for idx, doc in enumerate(semantic_candidates)}
            if self.semantic_retriever.is_available
            else {}
        )

        # Case record lookup pool (to preserve all case metadata)
        case_map: Dict[str, Dict[str, Any]] = {}
        for doc in tfidf_candidates:
            case_map[doc["id"]] = doc
        for doc in bm25_candidates:
            if doc["id"] not in case_map:
                case_map[doc["id"]] = doc
        for doc in semantic_candidates:
            if doc["id"] not in case_map:
                case_map[doc["id"]] = doc

        # 3. Calculate Reciprocal Rank Fusion (RRF) scores
        all_candidate_ids = set(tfidf_ranks.keys()) | set(bm25_ranks.keys()) | set(semantic_ranks.keys())
        
        scored_candidates = []
        max_possible_rrf = (
            (self.weight_tfidf / (self.rrf_k + 1))
            + (self.weight_bm25 / (self.rrf_k + 1))
            + (self.weight_semantic / (self.rrf_k + 1) if self.semantic_retriever.is_available else 0.0)
        )

        for cid in all_candidate_ids:
            doc = case_map.get(cid)
            if not doc:
                continue

            r_tfidf = tfidf_ranks.get(cid)
            r_bm25 = bm25_ranks.get(cid)
            r_sem = semantic_ranks.get(cid) if self.semantic_retriever.is_available else None

            # Formula: RRF(d) = sum_{m in Active} w_m / (60 + rank_m(d))
            rrf_score = 0.0
            if r_tfidf is not None:
                rrf_score += self.weight_tfidf / (self.rrf_k + r_tfidf)
            if r_bm25 is not None:
                rrf_score += self.weight_bm25 / (self.rrf_k + r_bm25)
            if r_sem is not None:
                rrf_score += self.weight_semantic / (self.rrf_k + r_sem)

            # Normalized similarity score for backward compatibility [0.0, 0.99]
            norm_sim = min(0.99, max(0.0, (rrf_score / max_possible_rrf) * 0.95)) if max_possible_rrf > 0 else 0.0

            # Merge matched terms from TF-IDF and BM25
            tfidf_terms = doc.get("matchedTerms", [])
            bm25_match = next((b.get("matchedTerms", []) for b in bm25_candidates if b["id"] == cid), [])
            merged_terms = []
            seen_terms = set()
            for t in (tfidf_terms + bm25_match):
                if t not in seen_terms:
                    seen_terms.add(t)
                    merged_terms.append(t)

            # Preserve or enrich retrieval reason
            signals_summary = []
            if r_tfidf:
                signals_summary.append(f"TF-IDF #{r_tfidf}")
            if r_bm25:
                signals_summary.append(f"BM25 #{r_bm25}")
            if r_sem:
                signals_summary.append(f"Semantic #{r_sem}")

            retrieval_reason = doc.get("retrievalReason", "")
            if signals_summary:
                fusion_note = f"Hybrid RRF ({', '.join(signals_summary)})"
                retrieval_reason = f"{fusion_note} - {retrieval_reason}" if retrieval_reason else fusion_note

            # Deep copy / clone dict to preserve metadata fields
            result_item = dict(doc)
            result_item["similarityScore"] = round(norm_sim, 4)
            result_item["rawRrfScore"] = round(rrf_score, 6)
            result_item["matchedTerms"] = merged_terms[:8]
            result_item["retrievalReason"] = retrieval_reason
            result_item["retrievalSignals"] = {
                "tfidf_rank": r_tfidf,
                "bm25_rank": r_bm25,
                "semantic_rank": r_sem,
                "rrf_score": round(rrf_score, 6),
                "active_modalities": active_modalities
            }

            scored_candidates.append(result_item)

        # 4. Sort descending by RRF score and slice to top_k
        scored_candidates.sort(key=lambda x: x["rawRrfScore"], reverse=True)
        return scored_candidates[:top_k]
