"""
Python Internal NLP/ML HTTP Microservice
Jurist AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Provides REST endpoints for:
- GET  /api/ml/health
- POST /api/ml/analyze
- POST /api/ml/similarity
- POST /api/ml/predict
"""

import json
import os
import sys
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.preprocessing.text_cleaner import clean_legal_text
from app.nlp.entity_extractor import LegalEntityExtractor
from app.nlp.issue_identifier import identify_legal_issues
from app.similarity.tfidf_retriever import PrecedentRetriever
from app.similarity.bm25_retriever import BM25Retriever
from app.similarity.semantic_retriever import SemanticRetriever
from app.similarity.hybrid_retriever import HybridPrecedentRetriever
from app.prediction.outcome_model import OutcomePredictor
from app.prediction.verified_outcome_model import VerifiedOutcomePredictor
from app.ocr.document_extractor import DocumentExtractor, PYMUPDF_AVAILABLE
from app.ocr.ocr_engine import OCREngine
from app.nlp.fact_analyzer import LegalFactAnalyzer
from app.nlp.citation_grounder import CitationGroundingValidator
from app.nlp.legal_argument_generator import LegalArgumentGenerator

# Load ml-service/.env if present
_env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
if os.path.exists(_env_file):
    try:
        with open(_env_file, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    if _k.strip() not in os.environ:
                        os.environ[_k.strip()] = _v.strip()
    except Exception:
        pass

PORT = int(os.environ.get("ML_PORT", os.environ.get("PORT", 8000)))
INTERNAL_KEY = os.environ.get("INTERNAL_ML_SECRET", "jurist-internal-secret-key")

# Global singleton engine instances
retriever = PrecedentRetriever()
bm25_retriever = BM25Retriever()
semantic_retriever = SemanticRetriever()
hybrid_retriever = HybridPrecedentRetriever()
extractor = LegalEntityExtractor()
predictor = OutcomePredictor()
predictor.load_model()
verified_predictor = VerifiedOutcomePredictor()
verified_predictor.load_model()
doc_extractor = DocumentExtractor()
citation_validator = CitationGroundingValidator()
argument_generator = LegalArgumentGenerator(citation_validator)


class MLServiceHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, data: Dict[str, Any]):
        response = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):
        if self.path in ("/api/ml/health", "/health", "/api/ml/stats", "/api/ml/corpus-stats"):
            active_modalities = ["tfidf", "bm25"]
            if hybrid_retriever.semantic_retriever.is_available:
                active_modalities.append("semantic")

            ocr_engine = doc_extractor.ocr_engine

            manifest_version = "v1.4.0-unified"
            corpus_manifest_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "datasets", "unified_corpus_manifest.json"
            )
            if os.path.exists(corpus_manifest_path):
                try:
                    with open(corpus_manifest_path, "r", encoding="utf-8") as f:
                        m_data = json.load(f)
                        manifest_version = m_data.get("manifestVersion", manifest_version)
                except Exception:
                    pass

            self._send_json(200, {
                "status": "healthy",
                "service": "Jurist-AI ML & NLP Engine",
                "modelVersion": predictor.MODEL_VERSION,
                "corpusSize": len(hybrid_retriever.corpus),
                "corpusManifestVersion": manifest_version,
                "sourceBreakdown": {
                    "landmark": sum(1 for c in hybrid_retriever.corpus if not str(c.get("id", "")).startswith("OIL-")),
                    "open_india_law": sum(1 for c in hybrid_retriever.corpus if str(c.get("id", "")).startswith("OIL-")),
                    "official_verified_landmark": sum(1 for c in hybrid_retriever.corpus if not str(c.get("id", "")).startswith("OIL-") and c.get("officialSourceVerified") is True),
                    "secondary_reference_landmark": sum(1 for c in hybrid_retriever.corpus if not str(c.get("id", "")).startswith("OIL-") and not c.get("officialSourceVerified"))
                },
                "retrievalEngine": "Hybrid RRF (TF-IDF + BM25 + Semantic)",
                "activeModalities": active_modalities,
                "semanticAvailable": hybrid_retriever.semantic_retriever.is_available,
                "semanticStatus": hybrid_retriever.semantic_retriever.availability_status,
                "semanticModel": "BAAI/bge-small-en-v1.5",
                "semanticDimension": hybrid_retriever.semantic_retriever.dimension,
                "indexedPassages": len(hybrid_retriever.semantic_retriever.passages),
                "indexStatus": "operational",
                "ocrAvailable": ocr_engine.is_available,
                "tesseractFound": ocr_engine.is_available,
                "tesseractStatus": ocr_engine.availability_status,
                "pymupdfAvailable": PYMUPDF_AVAILABLE,
                "pillowAvailable": True,
                "supportedFormats": ["pdf", "docx", "txt", "png", "jpg", "jpeg"],
                "nlpEngine": "spaCy + Indian Legal Gazetteer" if extractor.spacy_available else "Regex Legal Gazetteer",
                "outcomePrediction": {
                    "pipelineVersion": verified_predictor.MODEL_VERSION,
                    "statisticalModelTrained": verified_predictor.is_trained,
                    "predictionMode": "statistical_verified" if verified_predictor.is_trained else "qualitative_research",
                    "verifiedDataStatus": {
                        "candidateRecords": 150,
                        "humanApprovedRecords": 46,
                        "pendingReviewRecords": 104,
                        "modelAEligible": 43,
                        "modelBEligible": 37
                    }
                }
            })
        else:
            self._send_json(404, {"error": "Not Found"})

    def do_POST(self):
        # Optional internal secret check
        req_secret = self.headers.get("x-internal-secret")
        if req_secret and req_secret != INTERNAL_KEY:
            self._send_json(401, {"error": "Unauthorized internal request"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            self._send_json(400, {"error": "Invalid JSON payload"})
            return

        # Document Intelligence / OCR extraction endpoint
        if self.path == "/api/ml/extract-document":
            file_b64 = payload.get("fileBase64") or payload.get("buffer") or ""
            filename = payload.get("filename") or payload.get("fileName") or "document.pdf"
            if not file_b64:
                self._send_json(400, {
                    "success": False,
                    "filename": filename,
                    "documentType": "unknown",
                    "extractedText": "",
                    "pageCount": 0,
                    "pages": [],
                    "extractionMethod": "none",
                    "overallStatus": "FAILED",
                    "warnings": ["Field 'fileBase64' is required"]
                })
                return
            try:
                raw_bytes = base64.b64decode(file_b64)
            except Exception as e:
                self._send_json(400, {
                    "success": False,
                    "filename": filename,
                    "documentType": "unknown",
                    "extractedText": "",
                    "pageCount": 0,
                    "pages": [],
                    "extractionMethod": "none",
                    "overallStatus": "FAILED",
                    "warnings": [f"Invalid base64 payload: {str(e)}"]
                })
                return

            extraction_result = doc_extractor.extract_document(raw_bytes, filename)
            status_code = 200 if extraction_result.get("success", False) else 400
            self._send_json(status_code, extraction_result)
            return

        text = payload.get("text", "")
        if not text:
            self._send_json(400, {"error": "Field 'text' is required"})
            return

        if self.path == "/api/ml/similarity" or self.path == "/api/ml/hybrid-similarity":
            top_k = int(payload.get("top_k", 5))
            engine_mode = payload.get("engine", "hybrid").lower()
            
            if engine_mode == "tfidf":
                similar = retriever.retrieve_similar(text, top_k=top_k)
                engine_used = "tfidf_standalone"
            elif engine_mode == "bm25":
                similar = bm25_retriever.retrieve_similar(text, top_k=top_k)
                engine_used = "bm25_standalone"
            elif engine_mode == "semantic":
                similar = semantic_retriever.retrieve_similar(text, top_k=top_k)
                engine_used = "semantic_standalone"
            else:
                similar = hybrid_retriever.retrieve_similar(text, top_k=top_k)
                engine_used = "hybrid_rrf"

            self._send_json(200, {
                "precedents": similar,
                "count": len(similar),
                "retrievalEngine": engine_used,
                "activeModalities": ["tfidf", "bm25"] + (["semantic"] if hybrid_retriever.semantic_retriever.is_available else [])
            })

        elif self.path == "/api/ml/predict":
            # Feature 4.26 Experimental Outcome Prediction (Model A & Model B)
            category = payload.get("category", "")
            prediction = verified_predictor.predict_outcome(text, category=category)
            if "similarPrecedents" not in prediction or not prediction["similarPrecedents"]:
                try:
                    prediction["similarPrecedents"] = hybrid_retriever.retrieve_similar(text, top_k=5)
                except Exception:
                    prediction["similarPrecedents"] = []
            self._send_json(200, {"prediction": prediction})

        elif self.path == "/api/ml/analyze":
            cleaned = clean_legal_text(text)
            entities = extractor.extract_entities(text)
            issues = identify_legal_issues(text)
            top_precedents = hybrid_retriever.retrieve_similar(text, top_k=6)
            category = payload.get("category", "")

            self._send_json(200, {
                "cleanedTextSnippet": cleaned[:300] + "..." if len(cleaned) > 300 else cleaned,
                "entities": entities,
                "legalIssues": issues,
                "precedents": top_precedents,
                "prediction": verified_predictor.predict_outcome(text, category=category)
            })

        elif self.path == "/api/ml/legal-intelligence":
            # Feature: Direct LLM Legal Intelligence & Grounded Pleading Generation (No RAG)
            category = payload.get("category", "")
            court = payload.get("court", "Supreme Court of India")
            doc_metadata = payload.get("documentMetadata")
            applicable_law = payload.get("applicableLaw", {})

            # 1. Fact & Procedural Posture Intelligence (Structured Case Context)
            case_understanding = LegalFactAnalyzer.analyze_facts(
                text, category=category, court=court, document_metadata=doc_metadata
            )

            # 2. Multi-modal Hybrid Precedent Retrieval (Independent for Authorities & Matches)
            top_precedents = hybrid_retriever.retrieve_similar(text, top_k=6)

            # 3. Direct LLM Argument & Counterargument Generation (Precedents NOT fed to LLM prompt)
            intelligence = argument_generator.generate_intelligence(
                text=text,
                category=category,
                court=court,
                case_understanding=case_understanding,
                applicable_law=applicable_law,
                precedents_for_validation=top_precedents
            )

            # 4. Entity Extraction
            entities = extractor.extract_entities(text)

            # 5. Outcome Prediction (Preserving Model A & Model B)
            prediction = verified_predictor.predict_outcome(text, category=category)

            self._send_json(200, {
                **intelligence,
                "entities": entities,
                "precedents": top_precedents,
                "prediction": prediction,
                "statutoryEntityCounts": {
                    "acts": len(entities.get("acts", [])),
                    "sections": len(entities.get("sections", [])),
                    "courts": len(entities.get("courts", []))
                }
            })
        else:
            self._send_json(404, {"error": "Endpoint not found"})

    def log_message(self, format, *args):
        # Concise logging
        sys.stderr.write(f"[ML Service] {self.address_string()} - {format%args}\n")


def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, MLServiceHandler)
    print(f"Jurist AI ML Service running on port {PORT}...", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down ML Service.", flush=True)
        httpd.server_close()


if __name__ == "__main__":
    run_server()
