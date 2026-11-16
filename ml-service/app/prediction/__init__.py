"""
Outcome Prediction and Disposition Extraction Package
JURIST AI
"""

from app.prediction.outcome_model import OutcomePredictor
from app.prediction.label_extractor import (
    JudicialDispositionExtractor,
    DispositionCandidate,
    VALID_DISPOSITIONS,
)

__all__ = [
    "OutcomePredictor",
    "JudicialDispositionExtractor",
    "DispositionCandidate",
    "VALID_DISPOSITIONS",
]
