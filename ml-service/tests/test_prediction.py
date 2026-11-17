"""
Unit Tests for Machine Learning Outcome Likelihood Estimation
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.prediction.outcome_model import OutcomePredictor


class TestOutcomePrediction(unittest.TestCase):
    def setUp(self):
        self.predictor = OutcomePredictor()
        self.predictor.train_and_evaluate()

    def test_training_metrics(self):
        metrics = self.predictor.evaluation_metrics
        self.assertIn("trainAccuracy", metrics)
        self.assertIn("crossValAccuracy", metrics)
        self.assertGreaterEqual(metrics["trainAccuracy"], 0.70)
        self.assertIn("confusionMatrix", metrics)

    def test_prediction_output_structure(self):
        query = "Petition filed challenging arbitrary arrest without compliance of Section 41 notice."
        pred = self.predictor.predict_outcome(query, max_similarity=0.45)
        self.assertIn("estimatedOutcome", pred)
        self.assertIn("probabilities", pred)
        self.assertIn("confidenceLevel", pred)
        self.assertIn("disclaimer", pred)

    def test_low_similarity_unvalidated_status(self):
        query = "Generic inquiry with no legal connection."
        pred = self.predictor.predict_outcome(query, max_similarity=0.03)
        self.assertEqual(pred["status"], "unvalidated_low_similarity")
        self.assertEqual(pred["estimatedOutcome"], "Inconclusive")


if __name__ == "__main__":
    unittest.main()
