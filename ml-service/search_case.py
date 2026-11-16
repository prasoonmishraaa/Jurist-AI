import json
import numpy as np
import joblib
from pathlib import Path
from app.prediction.verified_outcome_model import VerifiedOutcomePredictor

predictor = VerifiedOutcomePredictor()

pipe_a = predictor.pipeline_a
pipe_b = predictor.pipeline_b
classes_a = predictor.classes_a
classes_b = predictor.classes_b

with open('app/datasets/open_india_law_sample_150.json', 'r', encoding='utf-8') as f:
    cases = json.load(f)

print(f"Loaded {len(cases)} cases.")

matches = []

for idx, c in enumerate(cases):
    cid = c.get('id', '')
    title = c.get('caseTitle', '')
    text = c.get('judgmentText', '')
    
    # Try different slices: first 1500 chars, first 3000 chars, full text sanitized
    for label_slice, slice_text in [("first_1500", text[:1500]), ("first_3000", text[:3000]), ("first_5000", text[:5000])]:
        res = predictor.predict_outcome(slice_text)
        if res.get('status') == 'validated_estimate':
            pred_a = res.get('modelA', {}).get('prediction')
            pred_b = res.get('modelB', {}).get('prediction')
            score_a = res.get('modelA', {}).get('confidenceScore')
            score_b = res.get('modelB', {}).get('confidenceScore')
            scores_a = res.get('modelA', {}).get('uncalibratedScores', {})
            scores_b = res.get('modelB', {}).get('uncalibratedScores', {})
            
            # Check if Model A predicted appeal_dismissed with ~0.28 and Model B respondent with ~0.28
            pct_a = round(scores_a.get('appeal_dismissed', 0) * 100)
            pct_b = round(scores_b.get('respondent', 0) * 100)
            
            if pred_a == 'appeal_dismissed' and pred_b == 'respondent':
                matches.append({
                    "idx": idx,
                    "id": cid,
                    "title": title,
                    "slice": label_slice,
                    "pred_a": pred_a,
                    "pred_b": pred_b,
                    "score_a": score_a,
                    "score_b": score_b,
                    "pct_a": pct_a,
                    "pct_b": pct_b,
                    "scores_a": scores_a,
                    "scores_b": scores_b,
                    "raw_a": res.get('modelA', {}).get('rawScores', {}),
                    "raw_b": res.get('modelB', {}).get('rawScores', {}),
                    "domain": res.get('domainDetected')
                })

print(f"Found {len(matches)} matches where Model A = appeal_dismissed and Model B = respondent:")
for m in matches:
    print(f"\nCase [{m['idx']}] {m['id']}: {m['title']} ({m['slice']})")
    print(f"  Domain: {m['domain']}")
    print(f"  Model A: {m['pred_a']} (score: {m['score_a']}, pct: {m['pct_a']}%) - scores: {m['scores_a']}")
    print(f"  Model A raw: {m['raw_a']}")
    print(f"  Model B: {m['pred_b']} (score: {m['score_b']}, pct: {m['pct_b']}%) - scores: {m['scores_b']}")
    print(f"  Model B raw: {m['raw_b']}")
