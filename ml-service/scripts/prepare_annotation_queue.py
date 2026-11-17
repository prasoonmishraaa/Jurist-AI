"""
Prepares the Human-Reviewed Annotation Queue and CSV for the 36 Unjudged Precedent Candidates
Jurist AI — Feature 1.5: Human-Reviewed Expanded Retrieval Benchmark

Creates:
- ml-service/app/datasets/expanded_benchmark_annotation_queue.json
- ml-service/app/datasets/expanded_benchmark_annotation.csv

Strict Integrity Rules:
- All 36 candidates are strictly marked as reviewStatus = "pending_review".
- Human relevance labels and reviewer IDs are set to None / blank.
- Zero synthetic labels or automated acceptances.
"""

import os
import sys
import json
import csv
from collections import defaultdict
from typing import Dict, Any, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_annotation_queue():
    unjudged_path = os.path.join(BASE_DIR, "app", "datasets", "expanded_benchmark_unjudged_review.json")
    benchmark_path = os.path.join(BASE_DIR, "app", "datasets", "retrieval_benchmark.json")
    judgments_path = os.path.join(BASE_DIR, "app", "datasets", "unified_judgments.json")
    passages_path = os.path.join(BASE_DIR, "app", "models", "unified_passages_metadata.json")
    results_path = os.path.join(BASE_DIR, "app", "models", "retrieval_expanded_benchmark_results.json")

    with open(unjudged_path, "r", encoding="utf-8") as f:
        unjudged_data = json.load(f)
    with open(benchmark_path, "r", encoding="utf-8") as f:
        benchmark_queries = {q["queryId"]: q for q in json.load(f)}
    with open(judgments_path, "r", encoding="utf-8") as f:
        judgments_map = {j["id"]: j for j in json.load(f)}
    with open(passages_path, "r", encoding="utf-8") as f:
        passages_list = json.load(f)

    # Group passages by case_id
    case_passages = defaultdict(list)
    for p in passages_list:
        case_passages[p["case_id"]].append(p)

    # Extract configuration ranks
    configs = {}
    if os.path.exists(results_path):
        with open(results_path, "r", encoding="utf-8") as f:
            res_json = json.load(f)
            configs = res_json.get("configurations", {})

    candidates = unjudged_data.get("candidates", [])
    queue_records: List[Dict[str, Any]] = []

    for idx, c in enumerate(candidates, start=1):
        qid = c["queryId"]
        cid = c["caseId"]
        bench_q = benchmark_queries.get(qid, {})
        case_info = judgments_map.get(cid, {})

        # Ranks across modalities
        ranks_across = {}
        for cfg_name, cfg_data in configs.items():
            for q_res in cfg_data.get("perQueryResults", []):
                if q_res["queryId"] == qid and cid in q_res.get("retrievedIds", []):
                    ranks_across[cfg_name] = q_res["retrievedIds"].index(cid) + 1

        # Extract passages
        relevant_passages = []
        for p in case_passages.get(cid, []):
            relevant_passages.append({
                "passageId": p.get("passage_id"),
                "isSummary": p.get("is_summary", False),
                "text": p.get("passage_text", "")
            })

        annotation_id = f"ANN-{qid}-{idx:02d}"

        record = {
            "annotationId": annotation_id,
            "queryId": qid,
            "queryText": bench_q.get("query", c.get("querySnippet", "")),
            "domain": bench_q.get("domain", "Criminal Law"),
            "targetAspect": bench_q.get("targetAspect", ""),
            "judgmentId": cid,
            "caseTitle": case_info.get("caseTitle", c.get("caseTitle", "Unknown")),
            "court": case_info.get("court", c.get("court", "Unknown")),
            "decisionDate": case_info.get("judgmentDate", c.get("judgmentDate", "")),
            "citation": case_info.get("citation", c.get("citation", "")),
            "sourceDataset": case_info.get("sourceDataset", "open_india_law_sample"),
            "legalProvisions": case_info.get("legalProvisions", []),
            "retrievedRank": c.get("retrievedRank", 1),
            "retrievalConfiguration": "3-way RRF (TF-IDF + BM25 + Semantic)",
            "ranksAcrossConfigurations": ranks_across,
            "judgmentPassages": relevant_passages,
            "existingBenchmarkRelevance": bench_q.get("relevanceGrading", {}).get(cid, None),
            # Primary Reviewer
            "humanRelevanceLabel": None,  # Options: 0, 1, 2, 3, "uncertain"
            "reviewerId": None,
            "reviewStatus": "pending_review",
            "reviewerNotes": "",
            "relevanceEvidence": "",
            # Second Reviewer (for inter-annotator agreement & disagreement tracking)
            "secondReviewer": {
                "reviewerId": None,
                "humanRelevanceLabel": None,
                "reviewStatus": "pending_review",
                "reviewerNotes": "",
                "relevanceEvidence": ""
            },
            # Adjudication (when reviewers disagree)
            "adjudication": {
                "adjudicatorId": None,
                "finalGrade": None,
                "adjudicationStatus": "unadjudicated",
                "adjudicationNotes": "",
                "disagreementDetected": False
            }
        }
        queue_records.append(record)

    # Save JSON queue
    json_output_path = os.path.join(BASE_DIR, "app", "datasets", "expanded_benchmark_annotation_queue.json")
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(queue_records, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(queue_records)} annotation queue records to: {json_output_path}")

    # Save CSV queue for spreadsheet / manual annotation
    csv_output_path = os.path.join(BASE_DIR, "app", "datasets", "expanded_benchmark_annotation.csv")
    csv_fields = [
        "annotation_id",
        "query_id",
        "query_text",
        "judgment_id",
        "case_title",
        "court",
        "decision_date",
        "source_dataset",
        "legal_provisions",
        "retrieved_rank_3way",
        "key_passages_excerpt",
        "existing_benchmark_relevance",
        "human_relevance_label",
        "reviewer_id",
        "review_status",
        "reviewer_notes",
        "relevance_evidence",
        "second_reviewer_id",
        "second_relevance_label",
        "adjudicated_grade"
    ]

    with open(csv_output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for r in queue_records:
            # Format excerpt: take first 2 passages (up to 400 chars each)
            passages = r["judgmentPassages"]
            excerpt_parts = []
            for p in passages[:2]:
                prefix = "[Summary] " if p.get("isSummary") else "[Holding] "
                clean_text = p.get("text", "").replace("\n", " ").strip()
                excerpt_parts.append(prefix + (clean_text[:300] + "..." if len(clean_text) > 300 else clean_text))
            excerpt = " | ".join(excerpt_parts)

            provisions_str = "; ".join(r.get("legalProvisions", []))

            writer.writerow({
                "annotation_id": r["annotationId"],
                "query_id": r["queryId"],
                "query_text": r["queryText"],
                "judgment_id": r["judgmentId"],
                "case_title": r["caseTitle"],
                "court": r["court"],
                "decision_date": r["decisionDate"],
                "source_dataset": r["sourceDataset"],
                "legal_provisions": provisions_str,
                "retrieved_rank_3way": r["retrievedRank"],
                "key_passages_excerpt": excerpt,
                "existing_benchmark_relevance": "" if r["existingBenchmarkRelevance"] is None else r["existingBenchmarkRelevance"],
                "human_relevance_label": "",  # pending
                "reviewer_id": "",
                "review_status": r["reviewStatus"],
                "reviewer_notes": "",
                "relevance_evidence": "",
                "second_reviewer_id": "",
                "second_relevance_label": "",
                "adjudicated_grade": ""
            })
    print(f"Saved {len(queue_records)} CSV annotation rows to: {csv_output_path}")


if __name__ == "__main__":
    build_annotation_queue()
