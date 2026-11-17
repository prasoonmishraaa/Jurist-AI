"""
Batch Dense Embedding Precomputation Script for Unified Legal Corpus
Jurist AI — Feature 1.4: Expand Hybrid Legal Retrieval Corpus to Open India Law

Uses BAAI/bge-small-en-v1.5 via ONNX Runtime CPU to encode legal passages into
L2-normalized 384-dimensional float32 vectors.
Saves:
- app/models/unified_embeddings.npy (and corpus_embeddings.npy)
- app/models/unified_passages_metadata.json (and corpus_passages_metadata.json)
- app/models/retrieval_index_manifest.json (full index audit manifest)
"""

import os
import sys
import time
import json
import argparse
import hashlib
import logging
from datetime import datetime
import numpy as np

# Ensure ml-service root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.similarity.passage_chunker import (
    build_legal_passages,
    get_chunking_statistics,
    save_passages_manifest
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("precompute_embeddings")


def compute_file_sha256(path: str) -> str:
    """Computes SHA-256 checksum of a file if it exists."""
    if not os.path.exists(path):
        return ""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def parse_args():
    parser = argparse.ArgumentParser(description="Precompute dense vectors for legal passages using BGE-small ONNX.")
    default_corpus = os.path.join(BASE_DIR, "app", "datasets", "unified_judgments.json")
    if not os.path.exists(default_corpus):
        default_corpus = os.path.join(BASE_DIR, "app", "datasets", "indian_judgments.json")

    parser.add_argument(
        "--corpus",
        type=str,
        default=default_corpus,
        help="Path to judgments corpus JSON (default: unified_judgments.json if available)."
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=os.path.join(BASE_DIR, "app", "models", "bge-small-en-v1.5"),
        help="Path to bge-small-en-v1.5 directory with model.onnx and tokenizer.json."
    )
    parser.add_argument(
        "--output-embeddings",
        type=str,
        default=os.path.join(BASE_DIR, "app", "models", "unified_embeddings.npy"),
        help="Path for output numpy embeddings array."
    )
    parser.add_argument(
        "--output-metadata",
        type=str,
        default=os.path.join(BASE_DIR, "app", "models", "unified_passages_metadata.json"),
        help="Path for output passages metadata JSON manifest."
    )
    parser.add_argument(
        "--index-manifest",
        type=str,
        default=os.path.join(BASE_DIR, "app", "models", "retrieval_index_manifest.json"),
        help="Path for output index audit manifest."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for ONNX inference."
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=512,
        help="Maximum token sequence length (<= 512 for BGE-small)."
    )
    return parser.parse_args()


def batch_encode_passages(
    passages: list,
    model_dir: str,
    batch_size: int = 32,
    max_length: int = 512
) -> np.ndarray:
    """
    Encodes passages into L2-normalized 384-dimensional dense vectors.
    Uses CLS pooling (first token) as prescribed by BGE architecture.
    """
    import onnxruntime as ort
    from tokenizers import Tokenizer

    onnx_path = os.path.join(model_dir, "model.onnx")
    tokenizer_path = os.path.join(model_dir, "tokenizer.json")

    if not os.path.exists(onnx_path):
        raise FileNotFoundError(f"ONNX model file not found at: {onnx_path}")
    if not os.path.exists(tokenizer_path):
        raise FileNotFoundError(f"Tokenizer file not found at: {tokenizer_path}")

    logger.info(f"Loading ONNX session from {onnx_path} (providers: CPUExecutionProvider)")
    sess_options = ort.SessionOptions()
    sess_options.intra_op_num_threads = min(os.cpu_count() or 4, 8)
    session = ort.InferenceSession(onnx_path, sess_options=sess_options, providers=["CPUExecutionProvider"])

    logger.info(f"Loading Tokenizer from {tokenizer_path}")
    tokenizer = Tokenizer.from_file(tokenizer_path)
    tokenizer.enable_truncation(max_length=max_length)
    tokenizer.enable_padding(length=max_length)

    input_names = [inp.name for inp in session.get_inputs()]
    output_names = [out.name for out in session.get_outputs()]
    logger.info(f"ONNX Inputs: {input_names} | Outputs: {output_names}")

    total_passages = len(passages)
    all_embeddings = []

    start_time = time.time()
    for batch_start in range(0, total_passages, batch_size):
        batch_end = min(batch_start + batch_size, total_passages)
        batch_slice = passages[batch_start:batch_end]
        texts = [p["passage_text"] for p in batch_slice]

        # Tokenize batch
        encoded_batch = tokenizer.encode_batch(texts)
        input_ids = np.array([enc.ids for enc in encoded_batch], dtype=np.int64)
        attention_mask = np.array([enc.attention_mask for enc in encoded_batch], dtype=np.int64)
        token_type_ids = np.array([enc.type_ids for enc in encoded_batch], dtype=np.int64)

        inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask
        }
        if "token_type_ids" in input_names:
            inputs["token_type_ids"] = token_type_ids

        # ONNX inference
        outputs = session.run(output_names, inputs)
        # BGE-small uses CLS pooling (token 0 of last_hidden_state)
        # outputs[0] shape: (batch_size, seq_len, 384)
        cls_embeddings = outputs[0][:, 0, :]  # shape: (batch_size, 384)

        # L2-normalization
        norms = np.linalg.norm(cls_embeddings, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-9)
        normalized = cls_embeddings / norms

        all_embeddings.append(normalized.astype(np.float32))

        logger.info(f"  Encoded {batch_end}/{total_passages} passages ({((batch_end/total_passages)*100):.1f}%)")

    embeddings_matrix = np.vstack(all_embeddings)
    elapsed = time.time() - start_time
    logger.info(f"Encoding complete in {elapsed:.2f}s ({total_passages / max(elapsed, 0.001):.1f} passages/sec)")
    return embeddings_matrix


def main():
    args = parse_args()
    logger.info(f"Corpus path: {args.corpus}")
    logger.info(f"Model directory: {args.model_dir}")

    if not os.path.exists(args.corpus):
        raise FileNotFoundError(f"Corpus file not found: {args.corpus}")

    with open(args.corpus, "r", encoding="utf-8") as f:
        cases = json.load(f)
    logger.info(f"Loaded {len(cases)} cases from corpus.")

    # 1. Chunk into legal passages
    passages = build_legal_passages(cases)
    stats = get_chunking_statistics(passages)
    logger.info(
        f"Generated {len(passages)} passages from {len(cases)} cases "
        f"(mean {stats['meanPassagesPerCase']} passages/case)."
    )

    # 2. Save passages metadata manifest
    save_passages_manifest(passages, args.output_metadata)
    logger.info(f"Saved passage metadata to: {args.output_metadata}")

    # Backward compatibility copy to corpus_passages_metadata.json
    legacy_metadata_path = os.path.join(BASE_DIR, "app", "models", "corpus_passages_metadata.json")
    save_passages_manifest(passages, legacy_metadata_path)

    # 3. Batch encode into dense embeddings
    embeddings = batch_encode_passages(
        passages,
        model_dir=args.model_dir,
        batch_size=args.batch_size,
        max_length=args.max_length
    )

    # 4. Save numpy array
    os.makedirs(os.path.dirname(os.path.abspath(args.output_embeddings)), exist_ok=True)
    np.save(args.output_embeddings, embeddings)
    logger.info(f"Saved dense embeddings to: {args.output_embeddings}")

    # Backward compatibility copy to corpus_embeddings.npy
    legacy_embeddings_path = os.path.join(BASE_DIR, "app", "models", "corpus_embeddings.npy")
    np.save(legacy_embeddings_path, embeddings)

    # 5. Verify saved array
    loaded_embeddings = np.load(args.output_embeddings)
    row_norms = np.linalg.norm(loaded_embeddings, axis=1)
    is_finite = np.all(np.isfinite(loaded_embeddings))

    logger.info(f"Embeddings verification:")
    logger.info(f"  Shape: {loaded_embeddings.shape}")
    logger.info(f"  Dtype: {loaded_embeddings.dtype}")
    logger.info(f"  Finite: {is_finite}")
    logger.info(f"  Min norm: {row_norms.min():.6f}, Max norm: {row_norms.max():.6f}, Mean norm: {row_norms.mean():.6f}")

    assert is_finite, "Embeddings contain NaN or Inf values!"
    assert np.allclose(row_norms, 1.0, atol=1e-5), "Embeddings are not unit normalized!"
    logger.info("All embeddings verified finite and L2-normalized to 1.0.")

    # 6. Build index audit manifest
    corpus_manifest_path = os.path.join(BASE_DIR, "app", "datasets", "unified_corpus_manifest.json")
    corpus_manifest_data = {}
    if os.path.exists(corpus_manifest_path):
        with open(corpus_manifest_path, "r", encoding="utf-8") as f:
            corpus_manifest_data = json.load(f)

    index_manifest = {
        "indexName": "Jurist-AI Dense Semantic Precedent Index",
        "indexVersion": "v1.4.0-unified",
        "buildTimestamp": datetime.utcnow().isoformat() + "Z",
        "modelName": "BAAI/bge-small-en-v1.5",
        "modelRevision": "main (ONNX CPU)",
        "modelFileSha256": compute_file_sha256(os.path.join(args.model_dir, "model.onnx")),
        "tokenizerSha256": compute_file_sha256(os.path.join(args.model_dir, "tokenizer.json")),
        "corpusSourcePath": os.path.relpath(args.corpus, BASE_DIR),
        "corpusSha256": compute_file_sha256(args.corpus),
        "totalUniqueJudgments": len(cases),
        "totalPassages": len(passages),
        "embeddingMatrixShape": list(loaded_embeddings.shape),
        "embeddingDtype": str(loaded_embeddings.dtype),
        "embeddingSizeBytes": int(loaded_embeddings.nbytes),
        "chunkingStatistics": stats,
        "skippedRecords": corpus_manifest_data.get("deduplicationDecisions", []),
        "targetOutcomeSanitization": "ENABLED (no target labels Allowed/Dismissed in passage text)"
    }

    with open(args.index_manifest, "w", encoding="utf-8") as f:
        json.dump(index_manifest, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved retrieval index audit manifest to: {args.index_manifest}")

    print("\n" + "="*80)
    print(" DENSE RETRIEVAL INDEX BUILD COMPLETE")
    print("="*80)
    print(f"Total Unique Judgments:    {index_manifest['totalUniqueJudgments']}")
    print(f"Total Passages:            {index_manifest['totalPassages']}")
    print(f"Embedding Matrix:          {index_manifest['embeddingMatrixShape']} ({index_manifest['embeddingDtype']})")
    print(f"Index Memory Footprint:    {index_manifest['embeddingSizeBytes'] / 1024:.1f} KiB")
    print(f"Audit Manifest:            {args.index_manifest}")
    print("="*80)


if __name__ == "__main__":
    main()
