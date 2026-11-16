"""
Legal Entity Extraction and Terminology Identification Engine
Jurist AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System
"""

import re
from typing import Dict, List, Any, Optional

# Attempt to load spacy gracefully if available; fall back to regex/gazetteer pipeline
_SPACY_AVAILABLE = False
_NLP = None

try:
    import spacy
    try:
        _NLP = spacy.load("en_core_web_sm")
        _SPACY_AVAILABLE = True
    except Exception:
        # Model not downloaded yet; spacy library present
        _SPACY_AVAILABLE = False
except ImportError:
    _SPACY_AVAILABLE = False


INDIAN_COURTS_PATTERNS = [
    r"Supreme Court of India",
    r"High Court of (?:Judicature at )?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?",
    r"(?:Delhi|Bombay|Allahabad|Madras|Calcutta|Karnataka|Gujarat|Punjab and Haryana)\s+High Court",
    r"Judicial Magistrate First Class|Chief Judicial Magistrate|Additional Chief Judicial Magistrate|Sessions Court|Magistrate",
    r"National Green Tribunal",
    r"National Company Law (?:Appellate )?Tribunal",
    r"NCLAT",
    r"Debt Recovery Tribunal",
    r"Consumer Disputes Redressal Commission"
]

INDIAN_ACTS = [
    "Constitution of India",
    "Bharatiya Nyaya Sanhita, 2023",
    "Bharatiya Nagarik Suraksha Sanhita, 2023",
    "Bharatiya Sakshya Adhiniyam, 2023",
    "Indian Penal Code, 1860",
    "Code of Criminal Procedure, 1973",
    "Code of Civil Procedure, 1908",
    "Evidence Act, 1872",
    "Negotiable Instruments Act, 1881",
    "Information Technology Act, 2000",
    "Arbitration and Conciliation Act, 1996",
    "Trade Marks Act, 1999",
    "Limitation Act, 1963",
    "Contract Act, 1872",
    "Specific Relief Act, 1963",
    "Companies Act, 2013",
    "Insolvency and Bankruptcy Code, 2016",
    "Transfer of Property Act, 1882",
    "Prevention of Money Laundering Act, 2002",
    "Unlawful Activities (Prevention) Act, 1967",
    "Consumer Protection Act, 2019",
    "Motor Vehicles Act, 1988",
    "Hindu Marriage Act, 1955",
    "Special Marriage Act, 1954",
    "Protection of Children from Sexual Offences Act, 2012",
    "SC/ST (Prevention of Atrocities) Act, 1989"
]

ACT_SHORTHAND_MAP = {
    "bns": "Bharatiya Nyaya Sanhita, 2023",
    "bnss": "Bharatiya Nagarik Suraksha Sanhita, 2023",
    "bsa": "Bharatiya Sakshya Adhiniyam, 2023",
    "ipc": "Indian Penal Code, 1860",
    "crpc": "Code of Criminal Procedure, 1973",
    "cpc": "Code of Civil Procedure, 1908",
    "ni act": "Negotiable Instruments Act, 1881",
    "it act": "Information Technology Act, 2000",
    "pmla": "Prevention of Money Laundering Act, 2002",
    "uapa": "Unlawful Activities (Prevention) Act, 1967",
    "article": "Constitution of India"
}

LEGAL_TERMS_GAZETTEER = {
    "habeas corpus": "Prerogative writ requiring a person under detention to be brought before a court.",
    "mandamus": "Judicial writ issued as a command to an inferior court or public officer.",
    "certiorari": "Writ seeking judicial review of a decision by a lower court or administrative tribunal.",
    "quo warranto": "Writ requiring the person to whom it is directed to show what authority they have for exercising some right or office.",
    "res judicata": "A matter that has been adjudicated by a competent court and may not be pursued further by the same parties.",
    "ratio decidendi": "The legal rationale and principle that forms the basis of the court's binding judgment.",
    "obiter dicta": "Remarks or observations made by a judge that are not essential to the decision and not legally binding.",
    "mens rea": "The intention or knowledge of wrongdoing that constitutes part of a crime.",
    "actus reus": "The actual objective action or conduct that constitutes the criminal act.",
    "quashing": "Nullification or voiding of an FIR, chargesheet, or court proceeding under inherent powers (e.g. S. 482 CrPC).",
    "anticipatory bail": "Pre-arrest bail granted by a Sessions Court or High Court under Section 438 CrPC where an individual apprehends arrest.",
    "regular bail": "Release of an accused person from custody pending trial or appeal under Section 437/439 CrPC.",
    "interim injunction": "A temporary restraining order issued by a court to prevent irreparable harm before final determination.",
    "rebuttable presumption": "An assumption of fact that the law requires a court to make, but which can be disproved by evidence (e.g. S. 139 NI Act).",
    "suo motu": "Action taken by a court of its own accord without any formal application from a party.",
    "sub judice": "Under judicial consideration and therefore prohibited from public discussion or prejudgment.",
    "in limine": "At the outset; a threshold preliminary dismissal or motion.",
    "cheque bounce": "Dishonour of a negotiable instrument due to insufficiency of funds under Section 138 NI Act."
}

CITATION_PATTERN = re.compile(
    r"\b(?:\(\d{4}\)|\d{4})\s+(?:\d+\s+)?(?:INSC|SCC|AIR|SCR|SCALE|SCC OnLine(?:\s+[A-Z][a-z]+)?)\s+\d+\b",
    re.IGNORECASE
)


class LegalEntityExtractor:
    """
    Extracts legal entities, court names, statutes, sections, and legal terms
    from input text using a hybrid approach combining statistical NLP (when spacy is available)
    and deterministic legal pattern matching.
    """

    def __init__(self):
        self.spacy_available = _SPACY_AVAILABLE
        self.nlp = _NLP

    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Parses text and extracts structured legal entities.
        """
        if not text:
            return {
                "parties": {"petitioners": [], "respondents": []},
                "courts": [],
                "judges": [],
                "statutes": [],
                "sections": [],
                "citations": [],
                "legalTerms": [],
                "nlpEngine": "spaCy + Indian Legal Pattern Extractor" if self.spacy_available else "Rule-based Indian Legal Pattern Extractor",
                "disclaimer": "NER models detect named entities and statutory citations using pattern matching. General spaCy models are not specifically trained on Indian court jurisprudence."
            }

        courts = self._extract_courts(text)
        judges = self._extract_judges(text)
        parties = self._extract_parties(text)
        statutes = self._extract_statutes(text)
        sections = self._extract_sections(text)
        citations = self._extract_citations(text)
        legal_terms = self._extract_legal_terms(text)

        # Incorporate spaCy entities if available
        if self.spacy_available and self.nlp:
            try:
                doc = self.nlp(text[:5000])  # limit length for lightweight performance
                for ent in doc.ents:
                    if ent.label_ == "PERSON" and ent.text not in judges and len(ent.text.split()) > 1:
                        # Potential litigant or judge
                        if any(term in text.lower() for term in ["justice", "judge"]):
                            pass
                        elif ent.text not in parties["petitioners"] and ent.text not in parties["respondents"]:
                            parties["petitioners"].append(ent.text)
            except Exception:
                pass

        return {
            "parties": parties,
            "courts": courts,
            "judges": judges,
            "statutes": statutes,
            "sections": sections,
            "citations": citations,
            "legalTerms": legal_terms,
            "nlpEngine": "spaCy (en_core_web_sm) + Indian Legal Regex Gazetteer" if self.spacy_available else "Indian Legal Regex Gazetteer (Lightweight Deterministic NLP)",
            "disclaimer": "General language models are not specifically pretrained on Indian court jurisprudence. Rule-based legal extraction provides exact statutory matching."
        }

    def _extract_courts(self, text: str) -> List[str]:
        found = []
        for pattern in INDIAN_COURTS_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                m_clean = m.strip()
                if m_clean not in found:
                    found.append(m_clean)
        return found

    def _extract_judges(self, text: str) -> List[str]:
        found = []
        judge_patterns = [
            r"(?:Hon'ble\s+)?(?:Mr\.|Ms\.|Mrs\.)?\s*Justice\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+)",
            r"Chief Justice\s+([A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+)",
            r"Bench:\s*([^\n\r.]+)"
        ]
        for pat in judge_patterns:
            matches = re.finditer(pat, text, re.IGNORECASE)
            for m in matches:
                name = m.group(1).strip()
                if len(name) > 3 and name not in found:
                    found.append(name)
        return found

    def _extract_parties(self, text: str) -> Dict[str, List[str]]:
        petitioners = []
        respondents = []

        # Matches "X v. Y" or "X versus Y"
        v_match = re.search(r"([A-Z][A-Za-z0-9\s.,&'\(\)]+?)\s+(?:v\.|vs\.?|versus)\s+([A-Z][A-Za-z0-9\s.,&'\(\)]+?)(?:\s+on|\s+dated|\s+in\s+Writ|\n|$)", text)
        if v_match:
            pet = v_match.group(1).strip()
            resp = v_match.group(2).strip()
            # Clean trailing punctuation
            pet = re.sub(r"[\n\r]+", " ", pet)
            resp = re.sub(r"[\n\r]+", " ", resp)
            if len(pet) < 100 and pet not in petitioners:
                petitioners.append(pet)
            if len(resp) < 100 and resp not in respondents:
                respondents.append(resp)

        # Explicit roles
        pet_matches = re.finditer(r"(?:Petitioner|Appellant|Applicant):\s*([^\n\r,]+)", text, re.IGNORECASE)
        for m in pet_matches:
            val = m.group(1).strip()
            if val and val not in petitioners:
                petitioners.append(val)

        resp_matches = re.finditer(r"(?:Respondent|Defendant|Opposite Party):\s*([^\n\r,]+)", text, re.IGNORECASE)
        for m in resp_matches:
            val = m.group(1).strip()
            if val and val not in respondents:
                respondents.append(val)

        return {"petitioners": petitioners, "respondents": respondents}

    def _extract_statutes(self, text: str) -> List[str]:
        found = []
        for act in INDIAN_ACTS:
            act_name_only = act.split(",")[0]
            if re.search(r"\b" + re.escape(act_name_only) + r"\b", text, re.IGNORECASE):
                if act not in found:
                    found.append(act)
        for abbr, full_act in ACT_SHORTHAND_MAP.items():
            if re.search(r"\b" + re.escape(abbr) + r"\b", text, re.IGNORECASE):
                if full_act not in found:
                    found.append(full_act)
        return found

    def _extract_sections(self, text: str) -> List[str]:
        found = []
        matches = re.finditer(
            r"\b(?:Section|Sections|Sec\.|S\.|u/s|Article|Articles|Art\.)\s+(\d+[A-Za-z]?(?:\(\d+\))?(?:\([a-z]\))?)(?:\s+(?:of|in|under)\s+(?:the\s+)?([A-Za-z\s]+?(?:Act|Code|Constitution|BNS|BNSS|BSA|IPC|CrPC|CPC)))?",
            text,
            re.IGNORECASE
        )
        for m in matches:
            sec_token = m.group(1)
            act_ref = m.group(2)
            if act_ref:
                entry = f"Section/Article {sec_token} of {act_ref.strip()}"
            else:
                entry = f"Section/Article {sec_token}"
            if entry not in found:
                found.append(entry)
        return found

    def _extract_citations(self, text: str) -> List[str]:
        matches = CITATION_PATTERN.findall(text)
        unique = []
        for m in matches:
            clean = m.strip()
            if clean not in unique:
                unique.append(clean)
        return unique

    def _extract_legal_terms(self, text: str) -> List[Dict[str, str]]:
        found = []
        text_lower = text.lower()
        for term, definition in LEGAL_TERMS_GAZETTEER.items():
            if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
                found.append({
                    "term": term.title(),
                    "definition": definition
                })
        return found
