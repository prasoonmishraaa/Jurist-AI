"""
Paragraph-Aware Legal Passage Chunker
Jurist AI — Feature 1.4: Expand Hybrid Legal Retrieval Corpus to Open India Law

Chunks landmark and Open India Law judgments into dense retrieval passages while preserving:
- case_id, case_title, court, judgment_date, citation, source_url
- legal_provisions, category, source_dataset
- passage_id (deterministic: e.g. SC-2017-001#p00), passage_index, is_summary
- constitutional & statutory context headers for dense embedding

STRICT INTEGRITY RESTRICTION:
- Outcome labels (e.g. Allowed, Dismissed, bail_granted, appeal_allowed) are kept in METADATA ONLY.
- Embedding passage text must NOT contain target disposition labels, preventing artificial label leakage.
"""

import os
import re
import json
import logging
from collections import Counter
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

MAX_PASSAGE_CHARS = 1200
TARGET_CHUNK_CHARS = 800
MIN_PASSAGE_CHARS = 80


def clean_passage_text(text: str) -> str:
    """Normalizes whitespace and removes redundant characters."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_raw_legal_text(text: str) -> str:
    """
    Cleans raw judgment text from OCR noise, margin pagination markers (A-H),
    markup section headers ([SECTION], [TITLE]), and formatting artifacts.
    """
    if not text:
        return ""
    # Remove standalone OCR line-margin letters (A through H) common in Indian law reports
    text = re.sub(r"^[A-H]\s*$", "", text, flags=re.MULTILINE)
    # Remove [SECTION] ## ..., [TITLE] # ..., %
    text = re.sub(r"\[SECTION\]\s*##?[^\n]*", "", text)
    text = re.sub(r"\[TITLE\]\s*#?[^\n]*", "", text)
    text = re.sub(r"%\s*\n", "", text)
    # Normalize multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def sanitize_outcome_leakage(text: str) -> str:
    """
    Strips explicit target disposition labels to prevent outcome leakage into embeddings.
    Focuses on substantive facts, legal issues, and judicial analysis.
    """
    if not text:
        return ""

    patterns = [
        r"\b(the\s+)?(appeal|petition|application|writ\s+petition|special\s+leave\s+petition)\s+(is|are|was|stand[s]?\s+hereby)?\s+(allowed|dismissed|disposed\s+of|partly\s+allowed)\b",
        r"\b(appeal|petition|application)\s+(allowed|dismissed)\b",
        r"\bbail\s+(is\s+)?(granted|rejected|refused|denied)\b",
        r"\boutcome\s*:\s*(allowed|dismissed|disposed|partly allowed|bail granted|bail denied)\b",
        r"\bdisposition\s*:\s*(allowed|dismissed|disposed|partly allowed)\b",
        r"\b(appeal\s+stands\s+allowed|appeal\s+stands\s+dismissed)\b",
        r"\baccordingly,\s*(the\s+)?(appeal|petition)\s+is\s+(allowed|dismissed)\b"
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(p, "[holding on merits]", cleaned, flags=re.IGNORECASE)
    return cleaned


def split_into_sentences(text: str) -> List[str]:
    """Splits text into sentences using standard punctuation heuristics while respecting legal abbreviations."""
    if not text:
        return []
    # Use standard punctuation boundary split followed by abbreviation repair
    raw_splits = re.split(r"(?<=[.!?])\s+", text.strip())
    abbrevs = {"v.", "vs.", "no.", "ors.", "anr.", "hon.", "art.", "sec.", "para.", "paras.", "ed.", "al.", "vol.", "scc.", "scr."}
    
    sentences = []
    accum = []
    for s in raw_splits:
        s = s.strip()
        if not s:
            continue
        accum.append(s)
        # If the segment ends with a known abbreviation, don't split yet
        last_word = s.split()[-1].lower() if s.split() else ""
        if last_word not in abbrevs:
            sentences.append(" ".join(accum))
            accum = []
    if accum:
        sentences.append(" ".join(accum))
    return sentences


def chunk_judgment_text(text: str, max_chars: int = MAX_PASSAGE_CHARS) -> List[str]:
    """
    Chunks raw judgment text into clean paragraphs/passages, respecting sentence boundaries.
    Provided for backward-compatible passage chunking.
    """
    return select_salient_paragraphs(text, max_passages=10, max_chars=max_chars)


def select_salient_paragraphs(
    raw_text: str,
    max_passages: int = 4,
    max_chars: int = MAX_PASSAGE_CHARS,
    min_chars: int = MIN_PASSAGE_CHARS
) -> List[str]:
    """
    Selects the most informative substantive paragraphs from long judgment texts,
    prioritizing headnotes, legal provisions, ratio/holding, and legal analysis.
    Prevents sprawling procedural or appearance lists from diluting the index.
    """
    cleaned = clean_raw_legal_text(raw_text)
    if not cleaned:
        return []

    raw_paras = [p.strip() for p in re.split(r"\n\s*\n|\r\n\s*\r\n", cleaned) if len(p.strip()) >= min_chars]

    if not raw_paras:
        # Fall back to single block if no paragraph breaks
        clean_block = clean_passage_text(cleaned)
        return [clean_block[:max_chars]] if clean_block else []

    # Score paragraphs for legal salience (holding, constitutional principles, statutory analysis)
    salience_keywords = [
        "held", "held:", "ratio", "constitution", "article", "section", "act",
        "contempt", "quashed", "mandatory", "liberty", "fundamental", "arbitration",
        "jurisdiction", "interpretation", "principle", "doctrine", "established",
        "precedent", "bench", "observed", "rule", "statutory", "guidelines"
    ]

    scored_paras = []
    for idx, p in enumerate(raw_paras):
        p_clean = clean_passage_text(p)
        if len(p_clean) < min_chars:
            continue
        p_lower = p_clean.lower()

        # Filter out obvious procedural/appearance lists
        if any(skip in p_lower for skip in ["advocate for petitioner", "advocates for respondent", "for the appearing parties", "counsel appearing"]):
            continue

        score = sum(1 for kw in salience_keywords if kw in p_lower)
        # Position prior: early paragraphs often contain headnote / core issue
        if idx < 3:
            score += 2

        # Split long paragraphs if they exceed max_chars
        if len(p_clean) > max_chars:
            sentences = split_into_sentences(p_clean)
            chunk_accum = []
            chunk_len = 0
            for sent in sentences:
                if chunk_len + len(sent) + 1 > max_chars and chunk_accum:
                    scored_paras.append((score, idx, " ".join(chunk_accum)))
                    chunk_accum = [sent]
                    chunk_len = len(sent)
                else:
                    chunk_accum.append(sent)
                    chunk_len += len(sent) + 1
            if chunk_accum:
                scored_paras.append((score, idx, " ".join(chunk_accum)))
        else:
            scored_paras.append((score, idx, p_clean))

    if not scored_paras:
        return [clean_passage_text(raw_paras[0])[:max_chars]]

    # Sort primarily by salience score descending, breaking ties by chronological paragraph order
    scored_paras.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    # Take top max_passages, then restore narrative order
    selected = scored_paras[:max_passages]
    selected.sort(key=lambda x: x[1])

    return [p[2] for p in selected]


def build_legal_passages(
    cases: List[Dict[str, Any]],
    include_summary_passage: bool = True,
    max_passages_per_case: int = 4,
    max_chars_per_chunk: int = MAX_PASSAGE_CHARS
) -> List[Dict[str, Any]]:
    """
    Converts a list of judgment dictionaries into dense retrieval passages.
    Handles both concise landmark cases and full-length Open India Law cases.
    Guarantees that target outcome labels are NOT included in embedding text.
    """
    passages: List[Dict[str, Any]] = []

    for case in cases:
        case_id = str(case.get("id") or case.get("case_id") or "").strip()
        case_title = str(case.get("caseTitle") or case.get("case_title") or "Unknown Title").strip()
        court = str(case.get("court") or "Unknown Court").strip()
        judgment_date = str(case.get("judgmentDate") or case.get("decision_date") or "").strip()
        citation = str(case.get("citation") or "").strip()
        source_url = str(
            case.get("officialSourceUrl")
            or case.get("sourceUrl")
            or case.get("secondaryReferenceUrl")
            or ""
        ).strip()
        legal_provisions = case.get("legalProvisions") or []
        category = str(case.get("category") or "General Law").strip()
        source_dataset = str(case.get("sourceDataset") or "unknown").strip()

        # Metadata fields ONLY — kept out of embedding text
        outcome = str(case.get("outcome") or "").strip()
        outcome_rationale = str(case.get("outcomeRationale") or "").strip()

        summary = str(case.get("summary") or "").strip()
        judgment_text = str(case.get("judgmentText") or case.get("judgment_text") or "").strip()

        # Build context header with legal provisions for semantic grounding
        provisions_summary = ", ".join(legal_provisions[:3]) if legal_provisions else ""
        if provisions_summary:
            context_header = f"[{case_title} | {provisions_summary}]"
        else:
            context_header = f"[{case_title} | {court}]"

        passage_idx = 0

        # Passage 0: Summary Passage (sanitized of explicit target outcome labels)
        if include_summary_passage and summary:
            sanitized_summary = sanitize_outcome_leakage(summary)
            clean_sum = clean_passage_text(sanitized_summary)
            full_passage_text = f"{context_header} Summary: {clean_sum}"

            passages.append({
                "passage_id": f"{case_id}#p{passage_idx:02d}",
                "case_id": case_id,
                "case_title": case_title,
                "court": court,
                "judgment_date": judgment_date,
                "citation": citation,
                "source_url": source_url,
                "legal_provisions": legal_provisions,
                "category": category,
                "source_dataset": source_dataset,
                "passage_text": full_passage_text,
                "raw_text": clean_sum,
                "passage_index": passage_idx,
                "is_summary": True,
                "outcome": outcome,
                "outcome_rationale": outcome_rationale
            })
            passage_idx += 1

        # Passages 1..N: Substantive Holding & Analysis Paragraphs
        if judgment_text:
            is_landmark = (len(judgment_text) < 1500 and source_dataset == "indian_judgments_landmark")
            if is_landmark:
                # Landmark concise cases: use single clean chunk
                sanitized_text = sanitize_outcome_leakage(judgment_text)
                clean_chunk = clean_passage_text(sanitized_text)
                if clean_chunk:
                    full_passage_text = f"{context_header} {clean_chunk}"
                    passages.append({
                        "passage_id": f"{case_id}#p{passage_idx:02d}",
                        "case_id": case_id,
                        "case_title": case_title,
                        "court": court,
                        "judgment_date": judgment_date,
                        "citation": citation,
                        "source_url": source_url,
                        "legal_provisions": legal_provisions,
                        "category": category,
                        "source_dataset": source_dataset,
                        "passage_text": full_passage_text,
                        "raw_text": clean_chunk,
                        "passage_index": passage_idx,
                        "is_summary": False,
                        "outcome": outcome,
                        "outcome_rationale": outcome_rationale
                    })
                    passage_idx += 1
            else:
                # Long or full-text cases (Open India Law): extract salient paragraphs
                selected_paras = select_salient_paragraphs(
                    judgment_text,
                    max_passages=max_passages_per_case,
                    max_chars=max_chars_per_chunk,
                    min_chars=MIN_PASSAGE_CHARS
                )

                for chunk in selected_paras:
                    sanitized_chunk = sanitize_outcome_leakage(chunk)
                    clean_chunk = clean_passage_text(sanitized_chunk)
                    if not clean_chunk or len(clean_chunk) < MIN_PASSAGE_CHARS:
                        continue

                    full_passage_text = f"{context_header} {clean_chunk}"

                    passages.append({
                        "passage_id": f"{case_id}#p{passage_idx:02d}",
                        "case_id": case_id,
                        "case_title": case_title,
                        "court": court,
                        "judgment_date": judgment_date,
                        "citation": citation,
                        "source_url": source_url,
                        "legal_provisions": legal_provisions,
                        "category": category,
                        "source_dataset": source_dataset,
                        "passage_text": full_passage_text,
                        "raw_text": clean_chunk,
                        "passage_index": passage_idx,
                        "is_summary": False,
                        "outcome": outcome,
                        "outcome_rationale": outcome_rationale
                    })
                    passage_idx += 1

        # Fallback if both summary and judgment_text were empty
        if passage_idx == 0:
            passages.append({
                "passage_id": f"{case_id}#p00",
                "case_id": case_id,
                "case_title": case_title,
                "court": court,
                "judgment_date": judgment_date,
                "citation": citation,
                "source_url": source_url,
                "legal_provisions": legal_provisions,
                "category": category,
                "source_dataset": source_dataset,
                "passage_text": f"{context_header} {category}",
                "raw_text": category,
                "passage_index": 0,
                "is_summary": False,
                "outcome": outcome,
                "outcome_rationale": outcome_rationale
            })

    return passages


def get_chunking_statistics(passages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes comprehensive chunking metrics across datasets and courts."""
    total_passages = len(passages)
    unique_cases = len(set(p["case_id"] for p in passages))
    dataset_counts = Counter(p.get("source_dataset", "unknown") for p in passages)
    court_counts = Counter(p.get("court", "unknown") for p in passages)

    lengths = [len(p["passage_text"]) for p in passages]
    summary_count = sum(1 for p in passages if p.get("is_summary", False))
    holding_count = total_passages - summary_count

    return {
        "totalPassages": total_passages,
        "uniqueCases": unique_cases,
        "meanPassagesPerCase": round(total_passages / max(unique_cases, 1), 2),
        "passagesByDataset": dict(dataset_counts),
        "passagesByCourt": dict(court_counts),
        "summaryPassages": summary_count,
        "substantivePassages": holding_count,
        "lengthStats": {
            "minChars": min(lengths) if lengths else 0,
            "maxChars": max(lengths) if lengths else 0,
            "meanChars": round(sum(lengths) / max(total_passages, 1), 1)
        }
    }


def save_passages_manifest(passages: List[Dict[str, Any]], output_path: str):
    """Saves passages metadata list to JSON."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(passages, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d passages to %s", len(passages), output_path)


def load_passages_manifest(input_path: str) -> List[Dict[str, Any]]:
    """Loads passages metadata list from JSON."""
    with open(input_path, "r", encoding="utf-8") as f:
        return json.load(f)
