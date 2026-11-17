"""
Text Preprocessing and Legal Normalization Pipeline
Jurist AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System
"""

import re
import string
from typing import List, Dict, Any

# Common Indian legal abbreviations and normalization mapping
LEGAL_ABBREVIATIONS: Dict[str, str] = {
    r"\bu/s\b": "under section",
    r"\bs\.\s*": "section ",
    r"\bsec\.\s*": "section ",
    r"\bart\.\s*": "article ",
    r"\bcr\.?p\.?c\b": "code of criminal procedure",
    r"\bi\.?p\.?c\b": "indian penal code",
    r"\bc\.?p\.?c\b": "code of civil procedure",
    r"\bn\.?i\.?\s*act\b": "negotiable instruments act",
    r"\bhc\b": "high court",
    r"\bsc\b": "supreme court",
    r"\bsci\b": "supreme court of india",
    r"\bcji\b": "chief justice of india",
    r"\bfir\b": "first information report",
    r"\bwp\b": "writ petition",
    r"\bslp\b": "special leave petition",
    r"\ba\.?i\.?r\b": "all india reporter",
    r"\bs\.?c\.?c\b": "supreme court cases",
}

# Standard English stopwords plus non-informative legal boilerplate
LEGAL_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", 
    "arent", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", 
    "but", "by", "cant", "cannot", "could", "couldnt", "did", "didnt", "do", "does", "doesnt", 
    "doing", "dont", "down", "during", "each", "few", "for", "from", "further", "had", "hadnt", 
    "has", "hasnt", "have", "havent", "having", "he", "hed", "hell", "hes", "her", "here", 
    "heres", "hers", "herself", "him", "himself", "his", "how", "hows", "i", "id", "ill", "im", 
    "ive", "if", "in", "into", "is", "isnt", "it", "its", "itself", "lets", "me", "more", "most", 
    "mustnt", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", 
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shant", "she", "shed", 
    "shell", "shes", "should", "shouldnt", "so", "some", "such", "than", "that", "thats", "the", 
    "their", "theirs", "them", "themselves", "then", "there", "theres", "these", "they", "theyd", 
    "theyll", "theyre", "theyve", "this", "those", "through", "to", "too", "under", "until", "up", 
    "very", "was", "wasnt", "we", "wed", "well", "were", "werent", "what", "whats", "when", 
    "whens", "where", "wheres", "which", "while", "who", "whos", "whom", "why", "whys", "with", 
    "wont", "would", "wouldnt", "you", "youd", "youll", "youre", "youve", "your", "yours", 
    "yourself", "yourselves", "thereof", "herein", "wherein", "aforesaid", "heretofore"
}


def clean_legal_text(text: str, expand_abbreviations: bool = True) -> str:
    """
    Cleans raw legal text by removing OCR noise, court docket artifacts,
    unnecessary whitespace, and normalizing statutory citations.
    """
    if not text or not isinstance(text, str):
        return ""

    # Normalize line breaks and tabs
    cleaned = re.sub(r"[\r\n\t]+", " ", text)

    # Remove repeated page numbers, docket headers (e.g. "Page 1 of 42", "ITEM NO. 1")
    cleaned = re.sub(r"\bPage\s+\d+\s+of\s+\d+\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bItem\s+No\.?\s*\d+\b", " ", cleaned, flags=re.IGNORECASE)

    if expand_abbreviations:
        for pattern, replacement in LEGAL_ABBREVIATIONS.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    # Normalize multiple whitespace characters
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


def legal_word_tokenizer(text: str) -> List[str]:
    """Top-level named tokenizer function for picklable TfidfVectorizer."""
    return tokenize_words(text, remove_stopwords=True)


def tokenize_sentences(text: str) -> List[str]:
    """
    Splits legal text into meaningful sentences, preserving legal citations
    such as 'Sec. 438 Cr.P.C.' without breaking prematurely on dots.
    """
    cleaned = clean_legal_text(text, expand_abbreviations=False)
    if not cleaned:
        return []

    # Mask known abbreviations with periods
    masked = re.sub(r"\b(u/s|sec|art|v|vs|ors|anr|no|nos|para|hon'ble|shri|smt|s)\.", r"\1__DOT__", cleaned, flags=re.IGNORECASE)
    # Match sentences ending with period, exclamation, or question mark followed by space or end of string
    sentences = re.split(r"(?<=[.!?])\s+", masked)

    unmasked = [s.replace("__DOT__", ".").strip() for s in sentences if s.strip()]
    return unmasked


def tokenize_words(text: str, remove_stopwords: bool = True, lowercase: bool = True) -> List[str]:
    """
    Tokenizes text into words/legal tokens, optionally removing stopwords and lowercasing.
    """
    cleaned = clean_legal_text(text, expand_abbreviations=True)
    if lowercase:
        cleaned = cleaned.lower()

    # Retain alphanumeric tokens and hyphenated terms (e.g., 'pre-trial', 'quashing')
    tokens = re.findall(r"\b[a-zA-Z0-9_\-]+\b", cleaned)

    if remove_stopwords:
        tokens = [t for t in tokens if t not in LEGAL_STOPWORDS and len(t) > 1]

    return tokens


def extract_statutory_provisions(text: str) -> List[str]:
    """
    Identifies statutory provisions like 'Section 138 of Negotiable Instruments Act'
    or 'Article 21 of the Constitution'.
    """
    provisions = []
    
    # Matches Article XX of Constitution
    art_matches = re.finditer(
        r"\bArticle\s+(\d+[A-Za-z]?(?:\(\d+\))?(?:\([a-z]\))?)(?:\s+(?:of|in)\s+(?:the\s+)?Constitution)?\b",
        text,
        re.IGNORECASE
    )
    for m in art_matches:
        provisions.append(f"Article {m.group(1)} of Constitution of India")

    # Matches Section XX of <Act>
    sec_matches = re.finditer(
        r"\bSection\s+(\d+[A-Za-z]?)(?:\s+(?:of\s+the|of|under)\s+([A-Za-z\s]+(?:Act|Code)))?\b",
        text,
        re.IGNORECASE
    )
    for m in sec_matches:
        sec_num = m.group(1)
        act_name = m.group(2).strip() if m.group(2) else ""
        if act_name:
            provisions.append(f"Section {sec_num}, {act_name}")
        else:
            provisions.append(f"Section {sec_num}")

    # Remove duplicates preserving order
    seen = set()
    unique_provisions = []
    for p in provisions:
        p_clean = " ".join(p.split())
        if p_clean.lower() not in seen:
            seen.add(p_clean.lower())
            unique_provisions.append(p_clean)

    return unique_provisions
