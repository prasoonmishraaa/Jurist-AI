"""
Legal Issue Identification Engine (Date & Statute-Aware)
"""

import re
from typing import List, Dict, Any

ISSUE_RULES = [
    {
        "issue": "Legality of Arrest, Written Grounds of Arrest & Pre-Arrest Safeguards",
        "keywords": [
            "arrest", "arrested", "custody", "grounds of arrest", "notice of appearance",
            "section 41a", "section 41", "section 35", "section 47", "section 50",
            "article 22", "remand", "24 hours", "magistrate", "without notice"
        ],
        "minMatches": 2,
        "requiredRegex": r"\b(?:arrest|arrested|custody|remand|grounds of arrest|41a|35 bnss|47 bnss|50 crpc|article 22|24 hours)\b",
        "provision": "Article 22(1) & 22(2), Constitution of India; S. 35, 47, 48 & 58 BNSS / S. 41, 41A, 50 & 57 CrPC",
        "description": "Examines written grounds of arrest communication, pre-arrest notice compliance for offences punishable up to 7 years, and 24-hour Magistrate production compliance."
    },
    {
        "issue": "Matrimonial Cruelty / Section 498A IPC (Section 85 BNS) Arrest Safeguards",
        "keywords": ["498a", "section 85", "dowry", "matrimonial", "cruelty", "stridhan"],
        "minMatches": 1,
        "requiredRegex": r"\b(?:498a|85 bns|dowry|matrimonial|stridhan)\b",
        "provision": "Section 498A IPC / Sections 85 & 86 BNS; Section 41A CrPC / Section 35 BNSS",
        "description": "Evaluates mandatory pre-arrest scrutiny in matrimonial cruelty complaints under the Arnesh Kumar framework."
    },
    {
        "issue": "Constitutionality of State Surveillance / Privacy Infringement",
        "keywords": ["privacy", "surveillance", "data protection", "article 21", "aadhaar", "biometric", "fundamental right", "proportionality"],
        "minMatches": 2,
        "provision": "Article 21 & Article 14, Constitution of India",
        "description": "Examines whether state action satisfies legality, legitimate aim, necessity, and proportionality under Justice K.S. Puttaswamy."
    },
    {
        "issue": "Overbreadth and Chilling Effect on Freedom of Speech Online",
        "keywords": ["section 66a", "speech", "expression", "online post", "social media", "article 19(1)(a)", "defamation online"],
        "minMatches": 2,
        "provision": "Section 66A IT Act (struck down) / Article 19(1)(a) Constitution of India",
        "description": "Examines whether statutory speech restrictions are vague or cast an impermissible chilling effect on expression."
    },
    {
        "issue": "Mandatory Obligation of Police to Register FIR for Cognizable Offences",
        "keywords": ["fir", "section 154", "section 173 bnss", "cognizable", "complaint", "police refusal", "preliminary inquiry"],
        "minMatches": 2,
        "provision": "Section 154 CrPC / Section 173 BNSS",
        "description": "Assesses mandatory FIR registration upon disclosure of a cognizable offence versus permissible preliminary inquiry categories."
    },
    {
        "issue": "Rebuttal of Statutory Presumption in Cheque Dishonour / NI Act",
        "keywords": ["138", "139", "cheque", "dishonour", "dishonor", "negotiable instrument", "enforceable debt", "blank cheque"],
        "minMatches": 2,
        "provision": "Sections 138, 139 & 141, Negotiable Instruments Act, 1881",
        "description": "Evaluates statutory demand notice service, signature admission, and rebuttal of the Section 139 presumption on preponderance of probabilities."
    },
    {
        "issue": "Civil Dispute Distinction & Maintainability of Quashing Petition",
        "keywords": ["section 482", "section 528", "quash", "quashing", "abuse of process", "420", "318 bns", "cheating", "bhajan lal"],
        "minMatches": 2,
        "provision": "Section 482 CrPC / Section 528 BNSS; Article 226 Constitution of India",
        "description": "Determines whether complaint allegations disclose criminal ingredients or constitute a civil dispute maintainable for quashing."
    },
    {
        "issue": "Arbitrability of Subject Matter and Judicial Non-Interference",
        "keywords": ["arbitration", "section 8", "section 11", "section 34", "arbitral tribunal", "arbitrable", "patent illegality"],
        "minMatches": 2,
        "provision": "Sections 8, 11 & 34, Arbitration and Conciliation Act, 1996",
        "description": "Evaluates non-arbitrability thresholds and narrow grounds of patent illegality under Section 34."
    },
    {
        "issue": "Grant of Regular or Pre-Arrest Bail & Personal Liberty",
        "keywords": ["bail", "anticipatory bail", "regular bail", "438", "439", "480", "482 bnss", "483 bnss", "incarceration"],
        "minMatches": 2,
        "provision": "Sections 480, 482 & 483 BNSS / Sections 437, 438 & 439 CrPC",
        "description": "Considers custody posture and the triple test for bail (flight risk, evidence tampering, witness intimidation)."
    },
    {
        "issue": "Protection of Well-Known Trademarks and Passing Off",
        "keywords": ["trademark", "infringement", "passing off", "deceptive similarity", "interim injunction", "dilution"],
        "minMatches": 2,
        "provision": "Sections 27, 29 & 135, Trade Marks Act, 1999 / Order XXXIX CPC",
        "description": "Assesses likelihood of confusion, goodwill dilution, and interlocutory injunction parameters."
    }
]


def identify_legal_issues(text: str) -> List[Dict[str, Any]]:
    """
    Identifies legal issues deterministically without cross-triggering unrelated offences
    (such as triggering Section 498A on generic non-matrimonial arrests).
    """
    if not text:
        return []

    text_lower = text.lower()
    identified = []

    for rule in ISSUE_RULES:
        req = rule.get("requiredRegex")
        if req and not re.search(req, text, re.IGNORECASE):
            continue

        matched_keywords = [kw for kw in rule["keywords"] if kw in text_lower]
        if len(matched_keywords) >= rule.get("minMatches", 2):
            identified.append({
                "issue": rule["issue"],
                "statutoryProvision": rule["provision"],
                "description": rule["description"],
                "matchedKeywords": matched_keywords
            })

    identified.sort(key=lambda x: len(x["matchedKeywords"]), reverse=True)
    return identified
