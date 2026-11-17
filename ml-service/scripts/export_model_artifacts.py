"""
Export Model & Precedent Artifacts for Serverless Inference
Jurist AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.similarity.tfidf_retriever import PrecedentRetriever
from app.prediction.outcome_model import OutcomePredictor


def export_all():
    print("Exporting TF-IDF and Classifier artifacts...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_artifacts_dir = os.path.join(
        os.path.dirname(base_dir),
        "backend",
        "src",
        "integrations",
        "artifacts"
    )
    os.makedirs(backend_artifacts_dir, exist_ok=True)
    models_dir = os.path.join(base_dir, "app", "models")
    os.makedirs(models_dir, exist_ok=True)

    # 1. Precedent Retriever
    retriever = PrecedentRetriever()
    path_ml = os.path.join(models_dir, "precedents_artifacts.json")
    path_backend = os.path.join(backend_artifacts_dir, "precedents_artifacts.json")
    retriever.export_artifacts_for_serverless(path_ml)
    retriever.export_artifacts_for_serverless(path_backend)
    print(f"Exported precedent artifacts to {path_backend}")

    # 2. Outcome Classifier
    predictor = OutcomePredictor(model_dir=models_dir)
    predictor.train_and_evaluate()
    path_ml_cls = os.path.join(models_dir, "outcome_model_artifacts.json")
    path_backend_cls = os.path.join(backend_artifacts_dir, "outcome_model_artifacts.json")
    predictor.export_classifier_for_serverless(path_ml_cls)
    predictor.export_classifier_for_serverless(path_backend_cls)
    print(f"Exported outcome classifier artifacts to {path_backend_cls}")

    print("All inference artifacts successfully exported!")


if __name__ == "__main__":
    export_all()
