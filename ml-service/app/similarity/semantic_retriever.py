"""
Semantic Precedent Retrieval Engine (Dense Vector Embeddings)
Jurist AI — Feature 1.3: Complete Semantic Retrieval

Primary model: BAAI/bge-small-en-v1.5 using ONNX Runtime on CPU.
Supports local, offline execution with precomputed corpus embeddings.
Uses paragraph-aware passage index with Max-P aggregation to case-level rankings.
Gracefully disables itself when model artifacts or dependencies are unavailable,
without fabricating scores or making external paid API calls.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from app.preprocessing.text_cleaner import clean_legal_text

logger = logging.getLogger(__name__)

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class SemanticRetriever:
    """
    Dense semantic vector retrieval engine for Indian legal precedents.
    Computes and caches normalized 384-dimensional dense vectors using BGE-small ONNX.
    Performs paragraph-aware passage retrieval with Max-P case score aggregation.
    """

    def __init__(
        self,
        corpus_path: Optional[str] = None,
        model_dir: Optional[str] = None,
        embeddings_path: Optional[str] = None,
        passages_metadata_path: Optional[str] = None
    ):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if corpus_path is None:
            unified_corpus = os.path.join(base_dir, "datasets", "unified_judgments.json")
            if os.path.exists(unified_corpus):
                corpus_path = unified_corpus
            else:
                corpus_path = os.path.join(base_dir, "datasets", "indian_judgments.json")
        if model_dir is None:
            model_dir = os.path.join(base_dir, "models", "bge-small-en-v1.5")
        if embeddings_path is None:
            unified_emb = os.path.join(base_dir, "models", "unified_embeddings.npy")
            if os.path.exists(unified_emb):
                embeddings_path = unified_emb
            else:
                embeddings_path = os.path.join(base_dir, "models", "corpus_embeddings.npy")
        if passages_metadata_path is None:
            unified_meta = os.path.join(base_dir, "models", "unified_passages_metadata.json")
            if os.path.exists(unified_meta):
                passages_metadata_path = unified_meta
            else:
                passages_metadata_path = os.path.join(base_dir, "models", "corpus_passages_metadata.json")

        self.corpus_path = corpus_path
        self.model_dir = model_dir
        self.embeddings_path = embeddings_path
        self.passages_metadata_path = passages_metadata_path

        self.corpus: List[Dict[str, Any]] = []
        self.case_map: Dict[str, Dict[str, Any]] = {}
        self.passages: List[Dict[str, Any]] = []
        self.corpus_embeddings: Optional[np.ndarray] = None
        self.dimension: int = 384
        self.model_backend: Optional[str] = None
        self.session: Any = None
        self.tokenizer: Any = None

        self.is_available: bool = False
        self.availability_status: str = "uninitialized"

        self._load_corpus()
        self._initialize_engine()

    def _load_corpus(self):
        """Loads judgment corpus and builds case lookup map."""
        if os.path.exists(self.corpus_path):
            try:
                with open(self.corpus_path, "r", encoding="utf-8") as f:
                    self.corpus = json.load(f)
                self.case_map = {
                    str(c.get("id") or c.get("case_id")): c for c in self.corpus
                }
            except Exception as e:
                logger.error(f"Error loading corpus from {self.corpus_path}: {e}")
                self.corpus = []
                self.case_map = {}

    def _initialize_engine(self):
        """
        Initializes ONNX Runtime CPU session, Tokenizer, precomputed embeddings,
        and passages metadata. Gracefully reports status if any component is missing.
        """
        onnx_model_file = os.path.join(self.model_dir, "model.onnx")
        tokenizer_file = os.path.join(self.model_dir, "tokenizer.json")

        has_onnx_file = os.path.exists(onnx_model_file)
        has_tokenizer_file = os.path.exists(tokenizer_file)
        has_cached_embeddings = os.path.exists(self.embeddings_path)
        has_passages_metadata = os.path.exists(self.passages_metadata_path)

        # 1. Check for onnxruntime library
        try:
            import onnxruntime as ort
            has_onnxruntime = True
        except ImportError:
            has_onnxruntime = False

        # 2. Check for tokenizers library
        try:
            from tokenizers import Tokenizer
            has_tokenizers = True
        except ImportError:
            has_tokenizers = False

        if has_onnx_file and has_tokenizer_file and has_onnxruntime and has_tokenizers:
            try:
                # Initialize ONNX inference session
                sess_options = ort.SessionOptions()
                sess_options.intra_op_num_threads = min(os.cpu_count() or 4, 8)
                self.session = ort.InferenceSession(
                    onnx_model_file,
                    sess_options=sess_options,
                    providers=["CPUExecutionProvider"]
                )
                self.model_backend = "onnxruntime"

                # Initialize Tokenizer
                self.tokenizer = Tokenizer.from_file(tokenizer_file)
                self.tokenizer.enable_truncation(max_length=512)
                self.tokenizer.enable_padding(length=512)

                self.is_available = True
                self.availability_status = "active_onnx"
                logger.info(
                    "SemanticRetriever successfully initialized with BGE-small ONNX on CPU."
                )
            except Exception as e:
                self.is_available = False
                self.availability_status = f"onnx_initialization_failed: {str(e)}"
                logger.warning(f"Failed to initialize ONNX Runtime session: {e}")
        else:
            self.is_available = False
            reasons = []
            if not has_onnx_file:
                reasons.append(f"Model missing ({onnx_model_file})")
            if not has_tokenizer_file:
                reasons.append(f"Tokenizer missing ({tokenizer_file})")
            if not has_onnxruntime:
                reasons.append("onnxruntime package not installed")
            if not has_tokenizers:
                reasons.append("tokenizers package not installed")
            self.availability_status = "unavailable: " + "; ".join(reasons)
            logger.info(f"SemanticRetriever offline: {self.availability_status}")

        # 3. Load precomputed passages metadata
        if has_passages_metadata:
            try:
                with open(self.passages_metadata_path, "r", encoding="utf-8") as f:
                    self.passages = json.load(f)
                logger.info(f"Loaded {len(self.passages)} passage metadata entries.")
            except Exception as e:
                logger.warning(f"Could not load passages metadata: {e}")
                self.passages = []

        # 4. Load precomputed dense embeddings
        if has_cached_embeddings:
            try:
                self.corpus_embeddings = np.load(self.embeddings_path)
                logger.info(
                    f"Loaded precomputed corpus embeddings from {self.embeddings_path} "
                    f"(shape: {self.corpus_embeddings.shape}, dtype: {self.corpus_embeddings.dtype})"
                )
            except Exception as e:
                logger.warning(f"Could not load precomputed embeddings: {e}")
                self.corpus_embeddings = None

        # Verify alignment between passages and embeddings
        if self.corpus_embeddings is not None and self.passages:
            if len(self.passages) != self.corpus_embeddings.shape[0]:
                logger.warning(
                    f"Mismatch between passage count ({len(self.passages)}) "
                    f"and embedding rows ({self.corpus_embeddings.shape[0]})."
                )

    def encode_query(self, text: str) -> Optional[np.ndarray]:
        """
        Encodes query string into a normalized 384-dimensional float32 vector.
        Prepends the BGE query instruction for asymmetric dense retrieval.
        """
        if not self.is_available or self.session is None or self.tokenizer is None:
            return None

        cleaned = clean_legal_text(text)
        if not cleaned:
            return None

        # BGE-small asymmetric retrieval query instruction
        query_text = f"{BGE_QUERY_PREFIX}{cleaned}"

        try:
            encoded = self.tokenizer.encode(query_text)
            input_ids = np.array([encoded.ids], dtype=np.int64)
            attention_mask = np.array([encoded.attention_mask], dtype=np.int64)
            token_type_ids = np.array([encoded.type_ids], dtype=np.int64)

            inputs = {
                "input_ids": input_ids,
                "attention_mask": attention_mask
            }
            # Add token_type_ids if required by the model session
            input_names = [inp.name for inp in self.session.get_inputs()]
            if "token_type_ids" in input_names:
                inputs["token_type_ids"] = token_type_ids

            outputs = self.session.run(None, inputs)

            # BGE-small uses CLS token pooling (outputs[0][:, 0])
            # outputs[0] shape: (1, seq_len, 384)
            cls_vec = outputs[0][:, 0, :].squeeze(0).astype(np.float32)

            # L2 normalization
            norm = float(np.linalg.norm(cls_vec))
            norm = max(norm, 1e-9)
            normalized_vec = cls_vec / norm

            return normalized_vec
        except Exception as e:
            logger.error(f"Error encoding query: {e}")
            return None

    def retrieve_similar(
        self,
        query_text: str,
        top_k: int = 5,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top_k precedents via dense vector cosine similarity.
        Applies Max-P aggregation across passages to produce judgment-level ranking.
        Returns an empty list when semantic retrieval is disabled or model is offline.
        """
        if (
            not self.is_available
            or self.corpus_embeddings is None
            or not query_text
        ):
            return []

        query_vec = self.encode_query(query_text)
        if query_vec is None:
            return []

        # Vectorized cosine similarity: dot product of L2-normalized vectors
        passage_scores = np.dot(self.corpus_embeddings, query_vec)

        # Max-P aggregation: group passages by case_id, retaining the highest passage score
        case_best_score: Dict[str, float] = {}
        case_best_passage: Dict[str, Dict[str, Any]] = {}

        if self.passages and len(self.passages) == len(passage_scores):
            for idx, passage in enumerate(self.passages):
                cid = passage.get("case_id")
                if not cid:
                    continue
                score = float(passage_scores[idx])
                if cid not in case_best_score or score > case_best_score[cid]:
                    case_best_score[cid] = score
                    case_best_passage[cid] = passage
        else:
            # Fallback 1:1 if passages manifest not available (corpus-level embeddings)
            for idx, case in enumerate(self.corpus):
                cid = str(case.get("id"))
                if idx < len(passage_scores):
                    case_best_score[cid] = float(passage_scores[idx])
                    case_best_passage[cid] = {
                        "passage_id": f"{cid}#p00",
                        "raw_text": case.get("summary", ""),
                        "passage_index": 0
                    }

        scored = []
        for cid, best_score in case_best_score.items():
            if best_score < min_score:
                continue

            case = self.case_map.get(cid)
            if not case:
                continue

            best_p = case_best_passage.get(cid, {})
            passage_id = best_p.get("passage_id", "")
            raw_text = best_p.get("raw_text", "")
            passage_idx = best_p.get("passage_index", 0)

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
                "similarityScore": round(float(best_score), 4),
                "matchedTerms": [],
                "matchedPassage": raw_text[:300] if raw_text else "",
                "matchedPassageId": passage_id,
                "matchedPassageIndex": passage_idx,
                "relevanceClassification": "Semantic Embedding Match",
                "retrievalReason": (
                    f"Dense vector conceptual similarity ({best_score:.4f})"
                    + (f" via passage {passage_id}" if passage_id else "")
                ),
                "historicalOutcome": case.get("outcome"),
                "outcomeRationale": case.get("outcomeRationale")
            })

        # Sort descending by similarityScore
        scored.sort(key=lambda x: x["similarityScore"], reverse=True)
        return scored[:top_k]
