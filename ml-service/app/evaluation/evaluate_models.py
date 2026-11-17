"""
Model & Precedent Retrieval Evaluation Script
Jurist AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System

Evaluates:
1. Retrieval Benchmark (Precision@5, Recall@5, MRR, NDCG@5 on Indian Legal Benchmark Queries)
2. Historical Sanity Queries (validating similarityScore schema)
3. Outcome Likelihood Classifier (Stratified K-Fold CV, precision, recall, F1, confusion matrix)
"""

import sys
import os
import json

# Add ml-service root directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.prediction.outcome_model import OutcomePredictor
from app.similarity.tfidf_retriever import PrecedentRetriever
from app.evaluation.retrieval_evaluator import evaluate_retrieval_benchmark


def run_full_evaluation():
    print("=" * 70)
    print("JURIST AI — MODEL & PRECEDENT RETRIEVAL EVALUATION REPORT")
    print("=" * 70)

    # 1. Initialize Precedent Retrieval Engine
    print("\n[1] Initializing Precedent Retrieval Engine...")
    retriever = PrecedentRetriever()
    print(f"Loaded {len(retriever.corpus)} verified Indian court judgments into TF-IDF index.")

    # 2. Sanity Checks on Sample Queries (verifying response schema)
    test_queries = [
        "Writ petition challenging state surveillance and violation of right to privacy under Article 21",
        "Police officer arrested husband under Section 498A IPC without giving notice under Section 41A CrPC",
        "Drawer signed a blank cheque which was dishonoured due to insufficient funds under Section 138 NI Act",
        "Quashing of FIR under Section 482 CrPC for commercial dispute where allegations are frivolous"
    ]

    print("\n--- SANITY QUERY CHECKS ---")
    for query in test_queries:
        results = retriever.retrieve_similar(query, top_k=2)
        top = results[0] if results else None
        if top:
            print(f"Query: '{query[:50]}...'")
            print(f"  -> Matched: {top['caseTitle']} ({top['citation']}) | Similarity Score: {top['similarityScore']}")
            print(f"  -> Matched Terms: {', '.join(top['matchedTerms'][:4])}")
        else:
            print(f"Query: '{query[:50]}...' -> No match found")

    # 3. Benchmark Retrieval Evaluation (Precision@5, Recall@5, MRR, NDCG@5)
    print("\n" + "=" * 70)
    print("[2] EVALUATING RETRIEVAL BENCHMARK (Precision@5, Recall@5, MRR, NDCG@5)")
    print("=" * 70)

    benchmark_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "datasets",
        "retrieval_benchmark.json"
    )

    retrieval_results = evaluate_retrieval_benchmark(retriever, benchmark_path=benchmark_path, k=5)

    print(f"\nCorpus Size:               {retrieval_results['corpusSize']} judgments")
    print(f"Benchmark Queries:         {retrieval_results['totalQueries']} queries")
    print(f"Hit Rate @ 5:              {retrieval_results['hitRate'] * 100:.2f}%")
    print(f"Precision @ 5:             {retrieval_results['precisionAtK']:.4f}")
    print(f"Recall @ 5:                {retrieval_results['recallAtK']:.4f}")
    print(f"Mean Reciprocal Rank (MRR):{retrieval_results['mrr']:.4f}")
    print(f"NDCG @ 5:                  {retrieval_results['ndcgAtK']:.4f}")

    print("\n--- PER-QUERY RETRIEVAL BREAKDOWN ---")
    for q_res in retrieval_results["perQueryResults"]:
        status_flag = "HIT " if q_res["isHit"] else "MISS"
        print(f"[{status_flag}] {q_res['queryId']} ({q_res['domain']})")
        print(f"       Query: \"{q_res['query'][:65]}...\"")
        print(f"       Expected:  {', '.join(q_res['expectedIds'])}")
        print(f"       Retrieved: {', '.join(q_res['retrievedIds'][:5]) if q_res['retrievedIds'] else 'None'}")
        print(f"       P@5: {q_res['precisionAtK']:.2f} | R@5: {q_res['recallAtK']:.2f} | RR: {q_res['reciprocalRank']:.2f} | NDCG@5: {q_res['ndcgAtK']:.2f}")
        if q_res["missedExpected"]:
            print(f"       Missed:    {', '.join(q_res['missedExpected'])}")

    # Failure Analysis
    misses = [q for q in retrieval_results["perQueryResults"] if not q["isHit"]]
    suboptimal = [q for q in retrieval_results["perQueryResults"] if q["isHit"] and q["recallAtK"] < 1.0]

    print("\n--- RETRIEVAL FAILURE & OBSERVATION ANALYSIS ---")
    if misses:
        print(f"Total Complete Misses (RR=0.0): {len(misses)}")
        for m in misses:
            print(f"  - {m['queryId']}: No expected judgments appeared in top 5 retrieved results.")
    else:
        print("Total Complete Misses (RR=0.0): 0 (Every query retrieved at least one relevant authority in top 5)")

    if suboptimal:
        print(f"\nPartially Recalled Queries ({len(suboptimal)} queries with Recall < 1.0):")
        for s in suboptimal:
            print(f"  - {s['queryId']}: Found {len(s['matchedExpected'])} of {len(s['expectedIds'])} expected. Missed: {', '.join(s['missedExpected'])}")
    else:
        print("\nAll queries achieved 100% recall.")

    # Save retrieval baseline metrics to models directory
    models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    os.makedirs(models_dir, exist_ok=True)
    retrieval_metrics_path = os.path.join(models_dir, "retrieval_baseline_metrics.json")
    with open(retrieval_metrics_path, "w", encoding="utf-8") as f:
        json.dump(retrieval_results, f, indent=2)
    print(f"\nSaved retrieval baseline metrics to: {retrieval_metrics_path}")

    # 4. Evaluate Outcome Prediction Classifier
    print("\n" + "=" * 70)
    print("[3] TRAINING & EVALUATING OUTCOME LIKELIHOOD ESTIMATION MODEL")
    print("=" * 70)
    predictor = OutcomePredictor()
    outcome_metrics = predictor.train_and_evaluate()

    print("\n--- OUTCOME ESTIMATION METRICS ---")
    print(f"Model Version:          {outcome_metrics['modelVersion']}")
    print(f"Training Sample Size:   {outcome_metrics['trainingSampleSize']} cases")
    print(f"Class Distribution:     {outcome_metrics['classDistribution']}")
    print(f"Training Accuracy:      {outcome_metrics['trainAccuracy'] * 100:.2f}%")
    print(f"Training Precision:     {outcome_metrics['trainPrecision'] * 100:.2f}%")
    print(f"Training Recall:        {outcome_metrics['trainRecall'] * 100:.2f}%")
    print(f"Training F1-Score:      {outcome_metrics['trainF1'] * 100:.2f}%")
    print(f"Cross-Val Accuracy:     {outcome_metrics['crossValAccuracy'] * 100:.2f}%")
    print(f"Cross-Val F1-Score:     {outcome_metrics['crossValF1'] * 100:.2f}%")
    if outcome_metrics.get("rocAuc"):
        print(f"ROC-AUC:                {outcome_metrics['rocAuc']:.4f}")
    print(f"Confusion Matrix:       {outcome_metrics['confusionMatrix']}")
    print("=" * 70)
    print("Evaluation completed successfully.")

    return {
        "retrieval": retrieval_results,
        "prediction": outcome_metrics
    }


if __name__ == "__main__":
    run_full_evaluation()
