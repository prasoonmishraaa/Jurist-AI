"""
TF-IDF & Multi-Signal Statutory Precedent Retrieval Engine
"""

import json
import os
import re
from typing import List, Dict, Any, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.preprocessing.text_cleaner import clean_legal_text, legal_word_tokenizer


class PrecedentRetriever:
    """
    Retrieves and ranks Indian legal precedents from the verified corpus
    using TF-IDF term weighting combined with deterministic statutory/posture alignment.
    """

    def __init__(self, corpus_path: Optional[str] = None):
        if corpus_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            unified_path = os.path.join(base_dir, "datasets", "unified_judgments.json")
            if os.path.exists(unified_path):
                corpus_path = unified_path
            else:
                corpus_path = os.path.join(base_dir, "datasets", "indian_judgments.json")

        self.corpus_path = corpus_path
        self.corpus: List[Dict[str, Any]] = []
        self.vectorizer = TfidfVectorizer(
            tokenizer=legal_word_tokenizer,
            ngram_range=(1, 2),
            sublinear_tf=True,
            min_df=1,
            max_df=0.95
        )
        self.tfidf_matrix = None
        self.feature_names = []
        self._load_and_fit()

    def _load_and_fit(self):
        """Loads corpus JSON and computes TF-IDF representation."""
        if not os.path.exists(self.corpus_path):
            raise FileNotFoundError(f"Corpus file not found at {self.corpus_path}")

        with open(self.corpus_path, "r", encoding="utf-8") as f:
            self.corpus = json.load(f)

        corpus_texts = []
        for case in self.corpus:
            provisions_str = " ".join(case.get("legalProvisions", []))
            doc = (
                f"{case.get('caseTitle', '')} {case.get('category', '')} "
                f"{provisions_str} {case.get('summary', '')} {case.get('judgmentText', '')}"
            )
            corpus_texts.append(doc)

        self.tfidf_matrix = self.vectorizer.fit_transform(corpus_texts)
        self.feature_names = np.array(self.vectorizer.get_feature_names_out())

    def _detect_signals(self, text_lower: str) -> Dict[str, bool]:
        return {
            "arrest": bool(re.search(r"\b(?:arrest|arrested|custody|detained|detention|remand|police station|41a|35 bnss|47 bnss|50 crpc|57 crpc|58 bnss)\b", text_lower)),
            "grounds_or_24h": bool(re.search(r"\b(?:grounds of arrest|written grounds|reason for arrest|not informed|without notice|notice|24 hours|24 hrs|article 22|magistrate|remand)\b", text_lower)),
            "bail": bool(re.search(r"\b(?:bail|anticipatory|regular bail|default bail|437|438|439|480|482 bnss|483 bnss|custody)\b", text_lower)),
            "cheating": bool(re.search(r"\b(?:cheat|cheating|420|318 bns|fraud|dishonest inducement|breach of trust|406)\b", text_lower)),
            "matrimonial": bool(re.search(r"\b(?:498a|85 bns|dowry|matrimonial|cruelty|stridhan|marriage|spouse)\b", text_lower)),
            "privacy": bool(re.search(r"\b(?:privacy|surveillance|aadhaar|biometric|phone tap|personal data|decisional autonomy|intrus)", text_lower)),
            "cheque": bool(re.search(r"\b(?:138|139|cheque|dishonour|dishonor|blank cheque|stop payment|insufficient funds|negotiable instrument)\b", text_lower)),
            "quashing": bool(re.search(r"\b(?:quash|quashing|482 crpc|528 bnss|abuse of process|frivolous fir|bhajan lal)\b", text_lower)),
            "fir": bool(re.search(r"\b(?:register fir|refusal to register|section 154|173 bnss|cognizable|preliminary inquiry)\b", text_lower)),
            "arbitration": bool(re.search(r"\b(?:arbitration|arbitral|arbitrator|section 8|section 11|section 34|patent illegality|arbitrable)\b", text_lower)),
            "trademark": bool(re.search(r"\b(?:trademark|passing off|infringement|deceptive similarity|mark|goodwill)\b", text_lower)),
            "special_act": bool(re.search(r"\b(?:pmla|money laundering|uapa|unlawful activities|mcoca|ndps|gujcoca)\b", text_lower))
        }

    def _evaluate_fit(self, signals: Dict[str, bool], case: Dict[str, Any]):
        cid = case.get("id", "")
        provs = ", ".join(case.get("legalProvisions", [])[:3])
        boost = 0.0
        relevance = "Supporting authority"
        reason = f"Retrieved for overlapping statutory concepts ({provs})."

        if signals["arrest"]:
            if cid == "SC-2025-026":
                boost += 0.52 if signals["grounds_or_24h"] else 0.36
                relevance = "Directly relevant"
                reason = "Directly relevant under ordinary criminal law (Article 22(1) & S. 50 CrPC / S. 47 BNSS): failure to communicate written grounds invalidates arrest and remand."
            elif cid == "SC-2025-027":
                boost += 0.50 if signals["grounds_or_24h"] else 0.34
                relevance = "Directly relevant"
                reason = "Directly affirms written grounds of arrest mandate across all offences under IPC / BNS 2023."
            elif cid == "SC-2024-025":
                boost += 0.44 if signals["grounds_or_24h"] else 0.28
                relevance = "Directly relevant" if signals["special_act"] else "Supporting authority"
                reason = "Establishes mandatory written 'grounds of arrest' under Article 22(1) (note factual origin in UAPA; extended generally to ordinary arrests)."
            elif cid == "SC-2023-024":
                boost += 0.40 if signals["grounds_or_24h"] else 0.24
                relevance = "Directly relevant" if signals["special_act"] else "Supporting authority"
                reason = "Requires written copy of grounds of arrest to be furnished (PMLA factual context; constitutional ratio applies more broadly)."
            elif cid == "SC-2014-003":
                boost += 0.44
                relevance = "Directly relevant" if signals["matrimonial"] else "Supporting authority"
                reason = (
                    "Directly binding precedent on pre-arrest notice under S. 41/41A CrPC and S. 498A IPC."
                    if signals["matrimonial"]
                    else "Supporting procedural authority: Supreme Court directions under S. 41/41A CrPC (now S. 35 BNSS) govern ALL offences punishable up to 7 years (note S. 498A IPC does not arise on current facts)."
                )
            elif cid == "SC-2022-023":
                boost += 0.45
                relevance = "Directly relevant"
                reason = "Directly enforces Arnesh Kumar pre-arrest compliance, Magistrate scrutiny on remand, and bail principles for Category A offences."
            elif cid == "SC-1996-012":
                boost += 0.34
                relevance = "Constitutional background"
                reason = "Foundational custodial safeguard mandate (arrest memo, medical exam, relative intimation, 24-hour production oversight)."

        if (signals["quashing"] or signals["cheating"]) and cid == "SC-1990-009":
            boost += 0.46 if signals["quashing"] else 0.28
            relevance = "Directly relevant" if signals["quashing"] else "Supporting authority"
            reason = "Landmark quashing framework (S. 482 CrPC / S. 528 BNSS / Art. 226) where civil commercial disputes are given criminal colour."

        if signals["cheque"] and cid in ("SC-2019-007", "SC-2010-008"):
            boost += 0.50
            relevance = "Potentially adverse authority"
            reason = "Binding NI Act authority enforcing S. 139 statutory presumption unless rebutted on preponderance of probabilities."

        if signals["privacy"] and cid == "SC-2017-001":
            boost += 0.52
            relevance = "Directly relevant"
            reason = "Nine-Judge Constitution Bench authority affirming Article 21 informational privacy and proportionality review."

        if signals["fir"] and cid == "SC-2013-004":
            boost += 0.48
            relevance = "Directly relevant"
            reason = "Constitution Bench mandate governing S. 154 CrPC / S. 173 BNSS FIR registration and narrow preliminary-inquiry exceptions."

        if signals["arbitration"] and cid in ("SC-2020-013", "SC-2014-020"):
            boost += 0.46
            relevance = "Directly relevant"

        if signals["trademark"] and cid == "DEL-2022-016":
            boost += 0.46
            relevance = "Directly relevant"

        if not signals["matrimonial"] and cid in ("SC-2017-006", "ALL-2020-022"):
            boost -= 0.30

        return boost, relevance, reason

    def retrieve_similar(self, query_text: str, top_k: int = 5, min_score: float = 0.05) -> List[Dict[str, Any]]:
        """
        Calculates TF-IDF similarity plus deterministic domain/statutory boost.
        Returns top_k ranked precedents with verified primary/secondary source URLs.
        """
        if not query_text or not self.corpus:
            return []

        cleaned_query = clean_legal_text(query_text)
        query_vec = self.vectorizer.transform([cleaned_query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        signals = self._detect_signals(query_text.lower())
        q_vec_arr = query_vec.toarray().flatten()

        scored = []
        for idx, case in enumerate(self.corpus):
            base_sim = float(similarities[idx])
            boost, relevance, reason = self._evaluate_fit(signals, case)
            combined = max(0.0, min(0.99, base_sim * 0.65 + boost if boost > 0 else base_sim + boost))

            if combined < min_score:
                continue

            doc_vec = self.tfidf_matrix[idx].toarray().flatten()
            product = doc_vec * q_vec_arr
            top_kw_indices = np.argsort(product)[::-1][:6]
            matched_terms = [
                str(self.feature_names[i])
                for i in top_kw_indices
                if product[i] > 0
            ]

            scored.append({
                "id": case.get("id"),
                "caseTitle": case.get("caseTitle"),
                "court": case.get("court"),
                "judgmentDate": case.get("judgmentDate"),
                "caseIdentifier": case.get("caseIdentifier"),
                "citation": case.get("citation"),
                "bench": case.get("bench"),
                "category": case.get("category"),
                "sourceDataset": case.get("sourceDataset") or ("open_india_law_sample" if str(case.get("id", "")).startswith("OIL-") else "indian_judgments_landmark"),
                "legalProvisions": case.get("legalProvisions", []),
                "summary": case.get("summary"),
                "judgmentText": case.get("judgmentText"),
                "officialSourceUrl": case.get("officialSourceUrl", ""),
                "officialSourceLabel": case.get("officialSourceLabel", ""),
                "officialSourceVerified": bool(case.get("officialSourceVerified", False)),
                "secondaryReferenceUrl": case.get("secondaryReferenceUrl", ""),
                "secondaryReferenceLabel": case.get("secondaryReferenceLabel", ""),
                "sourceUrl": case.get("sourceUrl", ""),
                "verificationStatus": case.get("verificationStatus", "unverified"),
                "verificationNote": case.get("verificationNote", ""),
                "article141Status": case.get("article141Status", ""),
                "obiterAndScopeNote": case.get("obiterAndScopeNote", ""),
                "subsequentTreatment": case.get("subsequentTreatment", ""),
                "similarityScore": round(combined, 4),
                "matchedTerms": matched_terms,
                "relevanceClassification": relevance,
                "retrievalReason": reason,
                "historicalOutcome": case.get("outcome"),
                "outcomeRationale": case.get("outcomeRationale")
            })

        scored.sort(key=lambda x: x["similarityScore"], reverse=True)
        return scored[:top_k]

    def export_artifacts_for_serverless(self, export_path: str):
        """
        Exports TF-IDF vocabulary, IDF weights, and document corpus JSON artifacts
        for serverless TypeScript inference.
        """
        data = {
            "vocabulary": {term: int(idx) for term, idx in self.vectorizer.vocabulary_.items()},
            "idf": self.vectorizer.idf_.tolist(),
            "corpus": self.corpus,
            "corpusVectors": self.tfidf_matrix.toarray().tolist()
        }
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
