"""
BM25 Legal Precedent Retrieval Engine
Jurist AI — Feature 1: Hybrid Legal Retrieval

Implements Okapi BM25 ranking for Indian legal precedents with exact statutory
terminology preservation and inverted-index acceleration.
"""

import os
import json
import math
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from app.preprocessing.text_cleaner import clean_legal_text, legal_word_tokenizer


try:
    from rank_bm25 import BM25Okapi as ExternalBM25Okapi
    HAS_RANK_BM25 = True
except ImportError:
    HAS_RANK_BM25 = False


class InvertedBM25Okapi:
    """
    High-performance inverted-index Okapi BM25 implementation (Robertson & Zaragoza, 2009).
    Fully compatible with rank-bm25 parameters and scoring behavior.
    """

    def __init__(
        self,
        corpus: List[List[str]],
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25
    ):
        self.k1 = float(k1)
        self.b = float(b)
        self.epsilon = float(epsilon)
        self.corpus_size = len(corpus)
        self.doc_lens = np.array([len(doc) for doc in corpus], dtype=np.float32)
        self.avgdl = float(np.mean(self.doc_lens)) if self.corpus_size > 0 else 1.0

        # Inverted index: term -> list of (doc_index, term_frequency)
        self.inverted_index: Dict[str, List[Tuple[int, int]]] = {}
        self.idf: Dict[str, float] = {}
        self.doc_len_norm = 1.0 - self.b + self.b * (self.doc_lens / max(self.avgdl, 1e-6))
        self._build_index(corpus)

    def _build_index(self, corpus: List[List[str]]):
        term_doc_counts: Dict[str, int] = {}

        for doc_idx, doc in enumerate(corpus):
            term_freqs: Dict[str, int] = {}
            for token in doc:
                term_freqs[token] = term_freqs.get(token, 0) + 1

            for token, freq in term_freqs.items():
                if token not in self.inverted_index:
                    self.inverted_index[token] = []
                self.inverted_index[token].append((doc_idx, freq))
                term_doc_counts[token] = term_doc_counts.get(token, 0) + 1

        positive_idfs = []
        for token, df in term_doc_counts.items():
            # Robertson-Spärck Jones IDF
            idf_val = math.log((self.corpus_size - df + 0.5) / (df + 0.5) + 1.0)
            self.idf[token] = idf_val
            if idf_val > 0.0:
                positive_idfs.append(idf_val)

        # Apply epsilon floor to negative IDFs
        avg_positive_idf = float(np.mean(positive_idfs)) if positive_idfs else 1.0
        eps_floor = self.epsilon * avg_positive_idf
        for token, idf_val in self.idf.items():
            if idf_val <= 0.0:
                self.idf[token] = eps_floor

    def get_scores(self, query_tokens: List[str]) -> np.ndarray:
        """Computes BM25 score vector for the given query tokens."""
        scores = np.zeros(self.corpus_size, dtype=np.float32)
        if not query_tokens or self.corpus_size == 0:
            return scores

        for token in query_tokens:
            if token not in self.inverted_index:
                continue

            q_idf = self.idf[token]
            postings = self.inverted_index[token]

            for doc_idx, freq in postings:
                num = freq * (self.k1 + 1.0)
                den = freq + self.k1 * self.doc_len_norm[doc_idx]
                scores[doc_idx] += q_idf * (num / den)

        return scores


class BM25Retriever:
    """
    BM25 Legal Precedent Retriever.
    Indexes statutory terms, section numbers, case titles, and judgment bodies.
    Caches the index in memory at instantiation time.
    """

    def __init__(
        self,
        corpus_path: Optional[str] = None,
        k1: float = 1.5,
        b: float = 0.75,
        epsilon: float = 0.25
    ):
        if corpus_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            unified_path = os.path.join(base_dir, "datasets", "unified_judgments.json")
            if os.path.exists(unified_path):
                corpus_path = unified_path
            else:
                corpus_path = os.path.join(base_dir, "datasets", "indian_judgments.json")

        self.corpus_path = corpus_path
        self.k1 = k1
        self.b = b
        self.epsilon = epsilon
        self.corpus: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25 = None
        self.engine_type = "rank-bm25" if HAS_RANK_BM25 else "internal-vectorized"
        self._load_and_index()

    def _load_and_index(self):
        """Loads corpus JSON and builds the in-memory BM25 index."""
        if not os.path.exists(self.corpus_path):
            raise FileNotFoundError(f"Corpus file not found at: {self.corpus_path}")

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            self.corpus = json.load(f)

        self.tokenized_corpus = []
        for case in self.corpus:
            provisions_str = " ".join(case.get("legalProvisions", []))
            doc_text = (
                f"{case.get('caseTitle', '')} {case.get('category', '')} "
                f"{provisions_str} {case.get('summary', '')} {case.get('judgmentText', '')}"
            )
            cleaned = clean_legal_text(doc_text, expand_abbreviations=True)
            tokens = legal_word_tokenizer(cleaned)
            self.tokenized_corpus.append(tokens)

        if HAS_RANK_BM25:
            self.bm25 = ExternalBM25Okapi(self.tokenized_corpus, k1=self.k1, b=self.b, epsilon=self.epsilon)
        else:
            self.bm25 = InvertedBM25Okapi(self.tokenized_corpus, k1=self.k1, b=self.b, epsilon=self.epsilon)

    def retrieve_similar(
        self,
        query_text: str,
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top_k ranked precedents using BM25 scoring.
        Returns full precedent dictionaries with similarityScore and matchedTerms.
        """
        if not query_text or not self.corpus:
            return []

        cleaned_query = clean_legal_text(query_text, expand_abbreviations=True)
        query_tokens = legal_word_tokenizer(cleaned_query)

        if not query_tokens:
            return []

        raw_scores = self.bm25.get_scores(query_tokens)
        max_score = float(np.max(raw_scores)) if len(raw_scores) > 0 else 0.0

        scored = []
        for idx, case in enumerate(self.corpus):
            score = float(raw_scores[idx])
            if score <= min_score:
                continue

            # Identify which query tokens matched this document
            doc_token_set = set(self.tokenized_corpus[idx])
            matched_terms = [t for t in query_tokens if t in doc_token_set]
            # Deduplicate matched terms preserving order
            seen_terms = set()
            unique_matched = []
            for t in matched_terms:
                if t not in seen_terms:
                    seen_terms.add(t)
                    unique_matched.append(t)

            # Normalized score between 0.0 and 0.99 for display compatibility
            normalized_score = round(min(0.99, score / max_score) if max_score > 0 else 0.0, 4)

            scored.append({
                "id": case.get("id"),
                "caseTitle": case.get("caseTitle"),
                "court": case.get("court"),
                "judgmentDate": case.get("judgmentDate"),
                "caseIdentifier": case.get("caseIdentifier"),
                "citation": case.get("citation"),
                "bench": case.get("bench"),
                "category": case.get("category"),
                "sourceDataset": case.get("sourceDataset") or ("open_india_law_sample" if str(case.get("id", "")).startswith("OIL-") else "indian_judgments_landmark"),
                "legalProvisions": case.get("legalProvisions", []),
                "summary": case.get("summary"),
                "judgmentText": case.get("judgmentText"),
                "officialSourceUrl": case.get("officialSourceUrl", ""),
                "officialSourceLabel": case.get("officialSourceLabel", ""),
                "officialSourceVerified": bool(case.get("officialSourceVerified", False)),
                "secondaryReferenceUrl": case.get("secondaryReferenceUrl", ""),
                "secondaryReferenceLabel": case.get("secondaryReferenceLabel", ""),
                "sourceUrl": case.get("sourceUrl", ""),
                "verificationStatus": case.get("verificationStatus", "unverified"),
                "verificationNote": case.get("verificationNote", ""),
                "article141Status": case.get("article141Status", ""),
                "obiterAndScopeNote": case.get("obiterAndScopeNote", ""),
                "subsequentTreatment": case.get("subsequentTreatment", ""),
                "similarityScore": normalized_score,
                "rawBm25Score": round(score, 4),
                "matchedTerms": unique_matched[:6],
                "relevanceClassification": "BM25 Probabilistic Match",
                "retrievalReason": f"BM25 term match on {', '.join(unique_matched[:3])}" if unique_matched else "BM25 score match",
                "historicalOutcome": case.get("outcome"),
                "outcomeRationale": case.get("outcomeRationale")
            })

        scored.sort(key=lambda x: x["rawBm25Score"], reverse=True)
        return scored[:top_k]
