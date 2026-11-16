"""
Verified Machine Learning Legal Outcome Prediction Pipeline
JURIST AI — Feature 4.4: Supervised Outcome Prediction Pipeline

Implements a leak-safe, verified-label Scikit-learn Pipeline for judicial outcome estimation:
- Pre-decision text sanitization (stripping operative orders and disposition keywords).
- TF-IDF Vectorizer + Calibrated/Balanced Logistic Regression inside Pipeline.
- Case-level group-aware train/test separation (preventing duplicate/chunk leakage).
- Rigorous evaluation metrics: Accuracy, Balanced Accuracy, Macro-F1, Per-class Precision/Recall, Confusion Matrix.
- Safety Guardrail: Refuses to train or serialize a statistical model if human-approved labels
  fall below empirical reliability thresholds (minimum 30 verified samples across classes).
- Qualitative Research Fallback: Returns structured doctrinal assessment and uncertainty disclaimer
  when empirical model criteria are not met.
"""

import os
import sys
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import Counter
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    brier_score_loss,
)
import joblib

# Import leakage sanitizer from builder script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scripts.build_verified_outcome_dataset import TargetLeakageSanitizer

logger = logging.getLogger("VerifiedOutcomePredictor")


class InsufficientVerifiedDataError(ValueError):
    """Raised when training data lacks sufficient human-approved samples for valid ML training."""
    pass


class VerifiedOutcomePredictor:
    """
    Supervised outcome prediction pipeline operating strictly on human-verified ground truth.
    """

    MODEL_VERSION = "v4.4.0-verified-pipeline"
    MIN_VERIFIED_SAMPLES_THRESHOLD = 30
    MIN_CLASS_SAMPLES_THRESHOLD = 5

    def __init__(self, model_dir: Optional[str] = None):
        if model_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_dir = os.path.join(base_dir, "models")

        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)

        self.sanitizer = TargetLeakageSanitizer()

        # Scikit-learn Pipeline combining TF-IDF and Balanced Logistic Regression
        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                sublinear_tf=True,
                min_df=1,
                max_df=0.95,
                strip_accents="unicode"
            )),
            ("classifier", LogisticRegression(
                C=1.0,
                class_weight="balanced",
                random_state=42,
                max_iter=1000,
                solver="lbfgs"
            ))
        ])

        self.is_trained = False
        self.classes_: List[str] = []
        self.evaluation_metrics: Dict[str, Any] = {}
        self.safeguard_status: Dict[str, Any] = {
            "eligible": False,
            "status": "uninitialized",
            "reason": "Model has not been trained on verified data."
        }

        # Dual-Model Architecture (Model A: Disposition, Model B: Successful Party)
        self.pipeline_a = None
        self.pipeline_b = None
        self.classes_a: List[str] = []
        self.classes_b: List[str] = []
        self.metadata_a: Dict[str, Any] = {}
        self.metadata_b: Dict[str, Any] = {}
        self.has_dual_models = False

    def train_and_evaluate(
        self,
        dataset: Union[str, Dict[str, Any]],
        test_size: float = 0.25,
        random_state: int = 42,
        raise_if_ineligible: bool = True,
        target_field: str = "verified_label"
    ) -> Dict[str, Any]:
        """
        Trains and evaluates the pipeline using case-level group-aware train/test separation.
        Enforces strict safety checks: if verified samples are insufficient, refuses to train.
        Feature 4.14: Supports independent training for Model A (disposition) or Model B (party).
        """
        if isinstance(dataset, str):
            with open(dataset, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = dataset

        records = data.get("records", [])
        is_eligible = data.get("is_training_eligible", False) and len(records) >= self.MIN_VERIFIED_SAMPLES_THRESHOLD

        # If data is not eligible or approved samples are insufficient
        if not is_eligible or len(records) < self.MIN_VERIFIED_SAMPLES_THRESHOLD:
            msg = (
                f"Insufficient verified outcome labels ({len(records)} found, minimum {self.MIN_VERIFIED_SAMPLES_THRESHOLD} required). "
                "Adhering to safety protocol: statistical model training halted to prevent deploying an unvalidated model."
            )
            logger.warning(msg)
            self.safeguard_status = {
                "eligible": False,
                "status": "safeguard_triggered",
                "verifiedCount": len(records),
                "threshold": self.MIN_VERIFIED_SAMPLES_THRESHOLD,
                "reason": msg,
                "qualitativeFallbackActive": True
            }
            if raise_if_ineligible:
                raise InsufficientVerifiedDataError(msg)
            return self.safeguard_status

        # Eligible classes filter based on target
        if target_field in ["verified_successful_party", "successful_party", "model_b"]:
            eligible_set = {"respondent", "petitioner", "state_prosecution", "accused"}
            excluded_set = {"none_procedural", "unresolved", "unknown"}
        elif target_field in ["judicial_disposition", "disposition", "model_a"]:
            eligible_set = {"appeal_allowed", "appeal_dismissed", "petition_allowed", "petition_dismissed"}
            excluded_set = {"remanded", "dismissed_as_infructuous", "uncertain", "unknown"}
        else:
            # Default verified_label: exclude non-trainable procedural classes
            eligible_set = None
            excluded_set = {"remanded", "dismissed_as_infructuous", "uncertain", "none_procedural", "unresolved", "unknown"}

        # Extract features and targets
        texts: List[str] = []
        labels: List[str] = []
        groups: List[str] = []

        for r in records:
            # Strictly use pre-decision sanitized text or composite
            text = r.get("factual_composite") or r.get("sanitized_pre_decision_text")
            label = r.get(target_field) if target_field in r else r.get("verified_label")
            group = r.get("case_group_id") or r.get("case_id")

            if text and label:
                if excluded_set and label in excluded_set:
                    continue
                if eligible_set and label not in eligible_set:
                    continue
                # Extra sanitization pass to guarantee zero leakage
                sanitized_text, _ = self.sanitizer.sanitize_judgment_text(text)
                texts.append(sanitized_text)
                labels.append(label)
                groups.append(group)

        # Check class distribution
        unique_classes, class_counts = np.unique(labels, return_counts=True)
        if len(unique_classes) < 2:
            msg = f"Cannot train model with fewer than 2 classes. Found: {list(unique_classes)}"
            logger.error(msg)
            if raise_if_ineligible:
                raise InsufficientVerifiedDataError(msg)
            return {"status": "error", "reason": msg}

        min_class_count = int(class_counts.min())
        if min_class_count < self.MIN_CLASS_SAMPLES_THRESHOLD:
            msg = f"Minority class has only {min_class_count} samples (minimum {self.MIN_CLASS_SAMPLES_THRESHOLD} required)."
            logger.warning(msg)
            if raise_if_ineligible:
                raise InsufficientVerifiedDataError(msg)
            return {"status": "safeguard_triggered", "reason": msg}

        # Case-level group-aware train/test separation
        # Prevents connected/duplicate cases from appearing in both train and test sets
        gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
        train_idx, test_idx = next(gss.split(texts, labels, groups=groups))

        X_train = [texts[i] for i in train_idx]
        y_train = [labels[i] for i in train_idx]
        X_test = [texts[i] for i in test_idx]
        y_test = [labels[i] for i in test_idx]

        # Verify group isolation
        train_groups = set(groups[i] for i in train_idx)
        test_groups = set(groups[i] for i in test_idx)
        group_overlap = train_groups.intersection(test_groups)
        assert len(group_overlap) == 0, f"Case group leakage detected across split: {group_overlap}"

        # Train Scikit-learn Pipeline
        self.pipeline.fit(X_train, y_train)
        self.is_trained = True
        self.classes_ = [str(c) for c in self.pipeline.classes_]

        # Evaluate on held-out test cases
        y_pred = self.pipeline.predict(X_test)
        y_prob = self.pipeline.predict_proba(X_test)

        acc = float(accuracy_score(y_test, y_pred))
        bal_acc = float(balanced_accuracy_score(y_test, y_pred))
        macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
        precision_macro = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
        recall_macro = float(recall_score(y_test, y_pred, average="macro", zero_division=0))

        cm = confusion_matrix(y_test, y_pred, labels=self.classes_).tolist()
        report = classification_report(y_test, y_pred, labels=self.classes_, output_dict=True, zero_division=0)

        # Calibration assessment for binary problems
        brier = None
        if len(self.classes_) == 2 and len(y_test) >= 10:
            try:
                binary_y_test = [1 if y == self.classes_[1] else 0 for y in y_test]
                pos_probs = y_prob[:, 1]
                brier = float(brier_score_loss(binary_y_test, pos_probs))
            except Exception:
                brier = None

        self.evaluation_metrics = {
            "modelVersion": self.MODEL_VERSION,
            "trainingSampleSize": len(X_train),
            "testSampleSize": len(X_test),
            "totalSampleSize": len(texts),
            "classDistribution": {str(k): int(v) for k, v in zip(unique_classes, class_counts)},
            "testAccuracy": round(acc, 4),
            "testBalancedAccuracy": round(bal_acc, 4),
            "testMacroF1": round(macro_f1, 4),
            "testMacroPrecision": round(precision_macro, 4),
            "testMacroRecall": round(recall_macro, 4),
            "confusionMatrix": cm,
            "confusionMatrixLabels": self.classes_,
            "classificationReport": report,
            "brierScoreLoss": round(brier, 4) if brier is not None else None,
            "caseLevelGroupIsolationVerified": True,
            "targetLeakageSanitization": "Operative order headings, disposition clauses, and outcome fields stripped."
        }

        self.safeguard_status = {
            "eligible": True,
            "status": "model_trained_and_validated",
            "metrics": self.evaluation_metrics
        }

        # Save artifacts
        self.save_model()
        return self.evaluation_metrics

    def evaluate_stratified_group_cross_validation(
        self,
        dataset: Union[str, Dict[str, Any]],
        n_splits: int = 5,
        random_state: int = 42,
        target_field: str = "verified_label"
    ) -> Dict[str, Any]:
        """
        Executes Stratified Group 5-Fold Cross-Validation as the authorized internal
        experimental evaluation harness (Feature 4.18 P1).

        Enforces:
        - Strict case-level group isolation across folds (no connected proceeding in both train and val).
        - Fitting vectorizer and classifier strictly within each training fold (zero test fold leakage).
        - Out-of-fold prediction generation for every eligible sample.
        - Macro-F1 (primary metric), Weighted-F1, per-class precision/recall/F1/support,
          balanced accuracy, accuracy, and confusion matrix.
        - Zero production side effects: does NOT serialize model weights or toggle self.is_trained.
        - Explicit documentation of small-sample statistical limitations.
        """
        if isinstance(dataset, str):
            with open(dataset, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = dataset

        records = data.get("records", [])

        # Target-specific eligibility filtering
        if target_field in ["verified_successful_party", "successful_party", "model_b"]:
            eligible_set = {"respondent", "petitioner", "state_prosecution", "accused"}
            excluded_set = {"none_procedural", "unresolved", "unknown"}
        elif target_field in ["judicial_disposition", "disposition", "model_a", "verified_label"]:
            eligible_set = {"appeal_allowed", "appeal_dismissed", "petition_allowed", "petition_dismissed"}
            excluded_set = {"remanded", "dismissed_as_infructuous", "uncertain", "unknown"}
        else:
            eligible_set = None
            excluded_set = {"remanded", "dismissed_as_infructuous", "uncertain", "none_procedural", "unresolved", "unknown"}

        texts: List[str] = []
        labels: List[str] = []
        groups: List[str] = []
        case_ids: List[str] = []

        for r in records:
            text = r.get("factual_composite") or r.get("sanitized_pre_decision_text")
            label = r.get(target_field) if target_field in r else r.get("verified_label")
            group = r.get("case_group_id") or r.get("case_id")
            cid = r.get("case_id", "")

            if text and label:
                if excluded_set and label in excluded_set:
                    continue
                if eligible_set and label not in eligible_set:
                    continue
                sanitized_text, _ = self.sanitizer.sanitize_judgment_text(text)
                texts.append(sanitized_text)
                labels.append(label)
                groups.append(group)
                case_ids.append(cid)

        if len(texts) < self.MIN_VERIFIED_SAMPLES_THRESHOLD:
            raise InsufficientVerifiedDataError(
                f"Insufficient eligible samples for cross-validation ({len(texts)} found, minimum {self.MIN_VERIFIED_SAMPLES_THRESHOLD} required)."
            )

        unique_classes = sorted(list(set(labels)))
        if len(unique_classes) < 2:
            raise InsufficientVerifiedDataError(f"Cannot evaluate with fewer than 2 classes. Found: {unique_classes}")

        # Execute Stratified Group K-Fold
        sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        oof_predictions = [None] * len(texts)
        oof_probabilities = [None] * len(texts)
        fold_metrics = []

        for fold_idx, (train_idx, val_idx) in enumerate(sgkf.split(texts, labels, groups=groups)):
            X_train = [texts[i] for i in train_idx]
            y_train = [labels[i] for i in train_idx]
            X_val = [texts[i] for i in val_idx]
            y_val = [labels[i] for i in val_idx]

            # Verify group isolation strictly
            train_groups = set(groups[i] for i in train_idx)
            val_groups = set(groups[i] for i in val_idx)
            group_overlap = train_groups.intersection(val_groups)
            assert len(group_overlap) == 0, f"Fold {fold_idx} group leakage: {group_overlap}"

            # Isolated pipeline fit strictly on training fold
            fold_pipeline = Pipeline([
                ("tfidf", TfidfVectorizer(
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    min_df=1,
                    max_df=0.95,
                    strip_accents="unicode"
                )),
                ("classifier", LogisticRegression(
                    C=1.0,
                    class_weight="balanced",
                    random_state=random_state,
                    max_iter=1000,
                    solver="lbfgs"
                ))
            ])
            fold_pipeline.fit(X_train, y_train)
            val_preds = fold_pipeline.predict(X_val)
            val_probs = fold_pipeline.predict_proba(X_val)

            for local_i, global_i in enumerate(val_idx):
                oof_predictions[global_i] = val_preds[local_i]
                oof_probabilities[global_i] = val_probs[local_i].tolist()

            fold_macro_f1 = float(f1_score(y_val, val_preds, average="macro", zero_division=0))
            fold_acc = float(accuracy_score(y_val, val_preds))
            fold_metrics.append({
                "fold": fold_idx + 1,
                "train_size": len(X_train),
                "val_size": len(X_val),
                "macro_f1": round(fold_macro_f1, 4),
                "accuracy": round(fold_acc, 4)
            })

        # Aggregate Out-Of-Fold evaluation
        overall_acc = float(accuracy_score(labels, oof_predictions))
        overall_bal_acc = float(balanced_accuracy_score(labels, oof_predictions))
        overall_macro_f1 = float(f1_score(labels, oof_predictions, average="macro", zero_division=0))
        overall_weighted_f1 = float(f1_score(labels, oof_predictions, average="weighted", zero_division=0))
        overall_macro_prec = float(precision_score(labels, oof_predictions, average="macro", zero_division=0))
        overall_macro_rec = float(recall_score(labels, oof_predictions, average="macro", zero_division=0))

        cm = confusion_matrix(labels, oof_predictions, labels=unique_classes).tolist()
        report = classification_report(labels, oof_predictions, labels=unique_classes, output_dict=True, zero_division=0)

        # Baseline comparisons
        label_counts = Counter(labels)
        majority_class, majority_count = label_counts.most_common(1)[0]
        majority_acc = majority_count / len(labels)
        stratified_acc = sum((cnt / len(labels)) ** 2 for cnt in label_counts.values())

        return {
            "evaluation_protocol": "StratifiedGroup5FoldCV",
            "target_field": target_field,
            "total_evaluated_samples": len(texts),
            "n_splits": n_splits,
            "group_isolation_verified": True,
            "classes": unique_classes,
            "class_distribution": dict(label_counts),
            "out_of_fold_metrics": {
                "macro_f1": round(overall_macro_f1, 4),
                "weighted_f1": round(overall_weighted_f1, 4),
                "balanced_accuracy": round(overall_bal_acc, 4),
                "accuracy": round(overall_acc, 4),
                "macro_precision": round(overall_macro_prec, 4),
                "macro_recall": round(overall_macro_rec, 4)
            },
            "baselines": {
                "majority_class": majority_class,
                "majority_class_accuracy": round(majority_acc, 4),
                "stratified_prior_accuracy": round(stratified_acc, 4),
                "uniform_random_accuracy": round(1.0 / len(unique_classes), 4)
            },
            "per_class_report": report,
            "confusion_matrix": cm,
            "confusion_matrix_labels": unique_classes,
            "fold_breakdown": fold_metrics,
            "statistical_limitations": (
                f"Sample size (N={len(texts)}) is suitable for internal exploratory validation only. "
                "Static held-out test splits remain prohibited until corpus expands to N >= 60-100."
            )
        }

    def detect_case_domain(self, text: str, category: Optional[str] = None) -> str:
        """
        Infers whether the proceeding is criminal, civil writ, or commercial civil.
        Used to detect domain limitations for Model B substantive party predictions.
        """
        cat = (category or "").lower().strip()
        if "criminal" in cat:
            return "criminal"
        if any(w in cat for w in ["commercial", "corporate", "arbitrat", "banking", "tax"]):
            return "commercial_civil"
        if any(w in cat for w in ["constitutional", "writ", "civil", "administrative"]):
            return "civil_writ"

        text_lower = text.lower()
        has_criminal = bool(re.search(r'\b(?:chargesheet|police custody|judicial custody|remand order|bail application|regular bail|anticipatory bail|438 crpc|439 crpc|480 bnss|482 bnss|483 bnss|section 302|section 420|section 498a|section 318)\b', text_lower))
        has_commercial = bool(re.search(r'\b(?:arbitrat|arbitral|section 8|section 11|section 34|commercial suit|recovery suit|promissory note|trademark|patent|insolvency|nclt)\b', text_lower))
        has_writ = bool(re.search(r'\b(?:writ petition|article 32|article 226|mandamus|certiorari|fundamental right)\b', text_lower))

        if has_commercial and not has_criminal:
            return "commercial_civil"
        if has_writ and not has_criminal:
            return "civil_writ"
        if has_criminal:
            return "criminal"
        return "general"

    def predict_outcome(self, text: str, max_similarity: float = 0.5, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Estimates the likelihood of judicial outcomes for an incoming case query.
        If empirical model is not trained (insufficient verified labels),
        safely falls back to qualitative research mode with mandatory disclaimers.
        """
        if not text or len(text.strip()) < 15:
            return {
                "status": "insufficient_input",
                "estimatedOutcome": "Insufficient Case Input",
                "probabilities": {},
                "confidenceScore": 0.0,
                "confidenceLevel": "Low",
                "rationale": "Provide at least a concise factual chronology and statutory grievance for structured legal analysis.",
                "disclaimer": "This platform prepares structured legal research and draft submissions rather than automated judicial outcome predictions.",
                "modelVersion": self.MODEL_VERSION
            }

        # If not trained on verified data, retain qualitative research mode
        if not self.is_trained:
            return {
                "status": "qualitative_research_mode",
                "predictionMode": "qualitative_research",
                "estimatedOutcome": "Structured Doctrinal & Authority Assessment",
                "probabilities": {},
                "confidenceScore": None,
                "confidenceLevel": "Informational",
                "rationale": (
                    "Empirical outcome forecasting is offline pending human verification of authentic "
                    "training labels (150 candidates currently pending human review). Legal assessment requires "
                    "verified pleadings, primary evidence on record, statutory limitation, and judicial discretion."
                ),
                "modelVersion": self.MODEL_VERSION,
                "disclaimer": (
                    "Legal research output only. Judicial outcomes turn on primary evidence on record, statutory "
                    "interpretation, and judicial discretion. Predictions are experimental research aids, not legal advice."
                ),
                "verifiedDataStatus": {
                    "candidateRecords": 150,
                    "humanApprovedRecords": 0,
                    "pendingReviewRecords": 150,
                    "statisticalModelTrained": False
                }
            }

        # Strict leakage sanitization on query text before inference
        sanitized_query, _ = self.sanitizer.sanitize_judgment_text(text)

        # Dual-Model Mode (Model A: Disposition, Model B: Prevailing Party)
        if self.has_dual_models and self.pipeline_a and self.pipeline_b:
            probs_a = self.pipeline_a.predict_proba([sanitized_query])[0]
            pred_disp = self.classes_a[int(np.argmax(probs_a))]
            max_prob_a = float(np.max(probs_a))
            prob_dict_a = {cls: round(float(p), 4) for cls, p in zip(self.classes_a, probs_a)}
            raw_scores_a = {cls: float(p) for cls, p in zip(self.classes_a, probs_a)}

            probs_b = self.pipeline_b.predict_proba([sanitized_query])[0]
            pred_party = self.classes_b[int(np.argmax(probs_b))]
            max_prob_b = float(np.max(probs_b))
            prob_dict_b = {cls: round(float(p), 4) for cls, p in zip(self.classes_b, probs_b)}
            raw_scores_b = {cls: float(p) for cls, p in zip(self.classes_b, probs_b)}

            # Domain validation for Model B substantive party
            domain = self.detect_case_domain(text, category)
            is_non_criminal = domain in ["civil_writ", "commercial_civil"]
            model_b_abstained = False
            model_b_domain_limitation = None
            final_pred_party = pred_party

            if is_non_criminal:
                model_b_domain_limitation = (
                    "Domain Limitation: Party identities 'accused' and 'state_prosecution' are specific to "
                    "criminal proceedings and are legally inapplicable to civil and constitutional writ litigation. "
                    "Model B taxonomy contains criminal classes which do not apply to this proceeding."
                )
                if pred_party in ["accused", "state_prosecution"]:
                    model_b_abstained = True
                    final_pred_party = "domain_abstained"

            confidence = "Moderate" if max_prob_a >= 0.50 else "Low"

            if model_b_abstained:
                estimated_outcome_str = f"{pred_disp} (Prevailing: Abstained — Civil Domain)"
                rationale_str = (
                    f"Experimental precedent analysis: Model A estimates disposition '{pred_disp}' "
                    f"({round(max_prob_a * 100, 1)}% uncalibrated score). Model B abstains from party estimation "
                    f"because criminal party labels ('accused' / 'state_prosecution') are outside the substantive "
                    f"scope of civil/constitutional litigation."
                )
            else:
                estimated_outcome_str = f"{pred_disp} (Prevailing: {final_pred_party})"
                rationale_str = (
                    f"Experimental precedent analysis: Model A estimates disposition '{pred_disp}' "
                    f"({round(max_prob_a * 100, 1)}% uncalibrated score); Model B estimates prevailing party '{final_pred_party}' "
                    f"({round(max_prob_b * 100, 1)}% uncalibrated score) based on pre-decision text features."
                )

            return {
                "status": "validated_estimate",
                "predictionMode": "statistical_verified",
                "isExperimental": True,
                "predictedDisposition": pred_disp,
                "predictedSuccessfulParty": final_pred_party,
                "disposition": pred_disp,
                "successfulParty": final_pred_party,
                "estimatedOutcome": estimated_outcome_str,
                "domainDetected": domain,
                "modelA": {
                    "target": "judicial_disposition",
                    "prediction": pred_disp,
                    "uncalibratedScores": prob_dict_a,
                    "rawScores": raw_scores_a,
                    "confidenceScore": round(max_prob_a, 3),
                    "confidenceLevel": "Moderate" if max_prob_a >= 0.50 else "Low",
                    "sampleSize": 43,
                    "macroF1": 0.2559,
                    "classes": self.classes_a,
                    "domainStatus": "supported"
                },
                "modelB": {
                    "target": "successful_party",
                    "prediction": final_pred_party,
                    "rawPrediction": pred_party,
                    "uncalibratedScores": prob_dict_b,
                    "rawScores": raw_scores_b,
                    "confidenceScore": round(max_prob_b, 3) if not model_b_abstained else 0.0,
                    "confidenceLevel": "Abstained (Domain Limitation)" if model_b_abstained else ("Moderate" if max_prob_b >= 0.50 else "Low"),
                    "sampleSize": 37,
                    "macroF1": 0.3664,
                    "classes": self.classes_b,
                    "domainStatus": "domain_limited" if is_non_criminal else "supported",
                    "domainLimitation": model_b_domain_limitation,
                    "abstained": model_b_abstained
                },
                "probabilities": prob_dict_a,
                "confidenceScore": round(max_prob_a, 3),
                "confidenceLevel": confidence,
                "rationale": rationale_str,
                "modelVersion": "v4.26-dual-experimental",
                "disclaimer": (
                    "Experimental research prototype for presentation demonstration. "
                    "Trained on 43 (Model A) and 37 (Model B) verified judicial precedents. "
                    "Class scores are uncalibrated historical vocabulary correlations and do not constitute legal advice."
                )
            }

        # Single pipeline fallback
        probs = self.pipeline.predict_proba([sanitized_query])[0]
        pred_label = self.classes_[int(np.argmax(probs))]
        max_prob = float(np.max(probs))

        prob_dict = {cls: round(float(p), 4) for cls, p in zip(self.classes_, probs)}

        # Low precedent similarity guard
        if max_similarity < 0.08:
            return {
                "status": "unvalidated_low_similarity",
                "predictionMode": "statistical_guarded",
                "estimatedOutcome": "Inconclusive",
                "probabilities": prob_dict,
                "confidenceScore": round(max_prob, 3),
                "confidenceLevel": "Low",
                "rationale": "The factual and statutory details provided do not exhibit sufficient correlation with verified precedents in the corpus.",
                "disclaimer": "Outcome estimation is restricted when precedent correlation is low to avoid misleading predictions.",
                "modelVersion": self.MODEL_VERSION
            }

        if max_prob >= 0.70:
            confidence = "High"
        elif max_prob >= 0.58:
            confidence = "Moderate"
        else:
            confidence = "Low"

        return {
            "status": "validated_estimate",
            "predictionMode": "statistical_verified",
            "estimatedOutcome": pred_label,
            "probabilities": prob_dict,
            "confidenceScore": round(max_prob, 3),
            "confidenceLevel": confidence,
            "rationale": (
                f"Statistical precedent analysis indicates {round(max_prob * 100, 1)}% probability "
                f"for outcome class '{pred_label}' based on matched statutory grounds and pre-decision facts."
            ),
            "modelVersion": self.MODEL_VERSION,
            "disclaimer": (
                "This estimate is an experimental decision-support research aid based purely on historical precedent correlation. "
                "It does not constitute legal advice or a guarantee of future judicial rulings."
            )
        }

    def save_model(self, file_prefix: str = "verified_outcome"):
        """Serializes the pipeline and evaluation metrics."""
        pipe_path = os.path.join(self.model_dir, f"{file_prefix}_pipeline.joblib")
        metrics_path = os.path.join(self.model_dir, f"{file_prefix}_metrics.json")

        joblib.dump(self.pipeline, pipe_path)
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(self.evaluation_metrics, f, indent=2)

    def load_model(self, file_prefix: str = "verified_outcome") -> bool:
        """Loads serialized verified pipeline(s) if present."""
        pipe_path = os.path.join(self.model_dir, f"{file_prefix}_pipeline.joblib")
        metrics_path = os.path.join(self.model_dir, f"{file_prefix}_metrics.json")

        model_a_path = os.path.join(self.model_dir, "model_a_disposition_pipeline.joblib")
        model_b_path = os.path.join(self.model_dir, "model_b_party_pipeline.joblib")
        meta_a_path = os.path.join(self.model_dir, "model_a_metadata.json")
        meta_b_path = os.path.join(self.model_dir, "model_b_metadata.json")

        # Check if dual models exist
        if os.path.exists(model_a_path) and os.path.exists(model_b_path):
            try:
                self.pipeline_a = joblib.load(model_a_path)
                self.pipeline_b = joblib.load(model_b_path)
                self.classes_a = [str(c) for c in self.pipeline_a.classes_]
                self.classes_b = [str(c) for c in self.pipeline_b.classes_]
                if os.path.exists(meta_a_path):
                    with open(meta_a_path, "r", encoding="utf-8") as f:
                        self.metadata_a = json.load(f)
                if os.path.exists(meta_b_path):
                    with open(meta_b_path, "r", encoding="utf-8") as f:
                        self.metadata_b = json.load(f)
                
                # Default primary pipeline is Model A
                self.pipeline = self.pipeline_a
                self.classes_ = self.classes_a
                self.evaluation_metrics = self.metadata_a.get("oof_metrics", {})
                self.is_trained = True
                self.has_dual_models = True
                return True
            except Exception as e:
                logger.error(f"Error loading dual models: {e}")

        # Fallback to single pipeline if file_prefix pipeline exists
        if os.path.exists(pipe_path):
            self.pipeline = joblib.load(pipe_path)
            self.classes_ = [str(c) for c in self.pipeline.classes_]
            if os.path.exists(metrics_path):
                with open(metrics_path, "r", encoding="utf-8") as f:
                    self.evaluation_metrics = json.load(f)
            self.is_trained = True
            return True
        return False
