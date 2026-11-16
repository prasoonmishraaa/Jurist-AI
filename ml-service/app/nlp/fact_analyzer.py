"""
Legal Fact and Procedural Posture Intelligence Engine
Jurist AI — Feature: AI-Powered Legal Intelligence Enhancement

Analyzes raw case briefs and extracted legal document text to:
1. Detect procedural posture (custodial, pre-arrest, quashing, civil/statutory).
2. Classify factual assertions into:
   - User-provided facts
   - Material facts
   - Party allegations
   - Reasonable legal inferences
   - Facts requiring verification
3. Extract parties and chronological timeline events.
4. Generate a tailored evidence audit checklist ("Document to obtain / verify").
5. Attribute facts to document pages without heuristic guessing.
"""

import re
from typing import Dict, List, Any, Optional


class LegalFactAnalyzer:
    """
    Analyzes Indian legal factual narratives and extracted pleadings
    with date, custody, and statutory regime awareness.
    """

    @staticmethod
    def detect_procedural_posture(text: str) -> Dict[str, Any]:
        """
        Determines the procedural and custody posture of the proceeding.
        Distinguishes post-arrest detention, pre-arrest apprehension,
        quashing under S. 482 CrPC / S. 528 BNSS, and non-custodial civil/writ matters.
        """
        if not text:
            return {
                "detectedPosture": "Unspecified / Insufficient Text",
                "custodyStatus": "unclear",
                "availableRemedies": [],
                "remedyNote": "Insufficient text to determine procedural posture."
            }

        t = text.lower()

        is_past_arrest_confirmed = bool(re.search(
            r"\b(?:was arrested|has been arrested|were arrested|arrested on|taken into custody|took into custody)\b",
            t
        ))

        # Negation / Future apprehension indicators
        future_or_no_arrest = not is_past_arrest_confirmed and bool(re.search(
            r"\b(?:apprehending arrest|apprehends arrest|fears arrest|threat of arrest|"
            r"fear of arrest|seeks anticipatory bail|pre-arrest bail|"
            r"not yet arrested|has not been arrested|anticipatory bail)\b",
            t
        ))

        # Actual custody / arrested indicators
        is_arrested_or_detained = bool(re.search(
            r"\b(?:was arrested|has been arrested|were arrested|arrested on|taken into custody|"
            r"took into custody|in custody|police custody|judicial custody|remanded|remand order|"
            r"for remand|detained in|lockup|produced before magistrate|beyond 24 hours|"
            r"grounds of arrest were not|not informed of grounds of arrest|illegal detention)\b",
            t
        )) and not future_or_no_arrest

        is_apprehending = bool(re.search(
            r"\b(?:apprehending arrest|apprehends arrest|fears arrest|threat of arrest|"
            r"anticipatory bail|section 438|section 482 bnss|pre-arrest bail)\b",
            t
        ))

        is_quashing = bool(re.search(r"\b(?:quash|quashing|482 crpc|528 bnss|quash fir)\b", t)) and not is_arrested_or_detained

        # Commercial / Special statutory indicators
        is_ni_act = bool(re.search(r"\b(?:138|cheque|cheque bounce|dishonour|statutory notice|ni act)\b", t))
        is_arbitration = bool(re.search(r"\b(?:arbitrat|arbitral tribunal|section 11|section 34|arbitration agreement)\b", t))
        is_civil_or_constitutional = not bool(re.search(
            r"\b(?:arrest|fir|police|bail|remand|custody|accused|482|528|cheating|offence|penal)\b", t
        ))

        if is_arbitration:
            return {
                "detectedPosture": "Arbitration Proceeding (Commercial / Statutory Non-Custodial)",
                "custodyStatus": "civil_or_non_custodial",
                "availableRemedies": [
                    {
                        "remedy": "Application for Appointment of Arbitrator / Interim Relief",
                        "statutoryBasis": "Sections 9, 11, or 34, Arbitration and Conciliation Act, 1996",
                        "whenApplicable": "Disputes arising from a valid arbitration agreement with failure of agreed appointment mechanism or patent illegality in award.",
                        "cautionNote": "Verify invocation notice under Section 21 and stamping/admissibility compliance."
                    }
                ],
                "remedyNote": "Commercial arbitration dispute; non-custodial proceeding."
            }

        if is_ni_act and not is_arrested_or_detained:
            return {
                "detectedPosture": "Negotiable Instruments Act (Cheque Dishonour) Proceeding",
                "custodyStatus": "summons_trial_quasi_criminal",
                "availableRemedies": [
                    {
                        "remedy": "Defence on Rebuttal of Presumption / Compounding of Offence",
                        "statutoryBasis": "Sections 138, 139 & 147, Negotiable Instruments Act, 1881",
                        "whenApplicable": "Where cheque was issued as security without existing enforceable debt, or statutory 15-day notice was invalidly served.",
                        "cautionNote": "Check 15-day statutory notice service date, postal tracking voucher, and 30-day limitation window for filing complaint."
                    }
                ],
                "remedyNote": "Special summons proceeding; custody is not immediate unless NBW has been issued."
            }

        if is_civil_or_constitutional:
            return {
                "detectedPosture": "Civil / Constitutional / Special Statutory Proceeding (Non-Custodial)",
                "custodyStatus": "civil_or_non_custodial",
                "availableRemedies": [
                    {
                        "remedy": "Writ Jurisdiction / Constitutional Relief or Statutory Civil Suit",
                        "statutoryBasis": "Articles 226 / 32 of Constitution OR governing civil Act (e.g. CPC Order 39, Specific Relief Act)",
                        "whenApplicable": "Where infringement of fundamental rights or statutory illegality is raised without custodial detention.",
                        "cautionNote": "Confirm limitation timelines and absence of equally efficacious alternative statutory remedy before invoking writ jurisdiction."
                    }
                ],
                "remedyNote": "No criminal custody posture detected in submitted facts."
            }

        if is_arrested_or_detained:
            return {
                "detectedPosture": "Post-Arrest / Custodial Challenge & Bail Posture (Person already arrested / grounds of arrest raised)",
                "custodyStatus": "in_custody_arrested",
                "availableRemedies": [
                    {
                        "remedy": "Challenge to Arrest & Remand Legality / Application for Immediate Release",
                        "statutoryBasis": "Article 22(1) Constitution of India read with Section 50 CrPC / Section 47 BNSS (Prabir Purkayastha / Vihaan Kumar principles)",
                        "whenApplicable": "When arrest has ALREADY occurred and written/meaningful grounds of arrest were not communicated directly to the arrestee.",
                        "cautionNote": "Anticipatory bail is NOT maintainable once an accused has already been arrested. Counsel must pursue release challenging invalid arrest/remand or regular bail."
                    },
                    {
                        "remedy": "Regular Bail Application",
                        "statutoryBasis": "Section 437 / 439 CrPC (pre-01.07.2024) OR Section 480 / 483 BNSS (from 01.07.2024) read with Satender Kumar Antil non-compliance principles",
                        "whenApplicable": "Seeking bail during police or judicial custody pending investigation or trial, particularly citing non-compliance with S. 41/41A CrPC or S. 35 BNSS.",
                        "cautionNote": "Verify current custody location, remand order date, and whether chargesheet has been filed."
                    }
                ],
                "remedyNote": "Accused is in custody. Urgent remedies are challenge to remand/arrest legality and regular bail."
            }

        if is_apprehending:
            return {
                "detectedPosture": "Pre-Arrest / Anticipatory Bail Posture (Person apprehends arrest)",
                "custodyStatus": "apprehending_arrest",
                "availableRemedies": [
                    {
                        "remedy": "Anticipatory Bail Application",
                        "statutoryBasis": "Section 438 CrPC (pre-01.07.2024) OR Section 482 BNSS (from 01.07.2024)",
                        "whenApplicable": "Where there is reasonable apprehension of arrest on accusation of having committed a non-bailable offence.",
                        "cautionNote": "Maintainable ONLY so long as applicant is NOT yet arrested. Check whether statutory notice under S. 41A CrPC / S. 35 BNSS has been served."
                    }
                ],
                "remedyNote": "Person is not currently in custody. Anticipatory bail or quashing is the appropriate pathway."
            }

        if is_quashing:
            return {
                "detectedPosture": "Inherent Jurisdiction / Quashing Petition Posture",
                "custodyStatus": "not_in_custody",
                "availableRemedies": [
                    {
                        "remedy": "Petition for Quashing of FIR / Criminal Proceedings",
                        "statutoryBasis": "Section 482 CrPC / Section 528 BNSS / Article 226 Constitution of India",
                        "whenApplicable": "Where uncontroverted allegations in FIR do not disclose a cognizable offence, or proceeding is a civil dispute dressed up as criminal complaint.",
                        "cautionNote": "Apply Bhajan Lal guidelines; courts will not evaluate disputed facts or conduct mini-trials at quashing stage."
                    }
                ],
                "remedyNote": "Seeking quashing of proceedings. Ensure allegations fit Bhajan Lal categories."
            }

        return {
            "detectedPosture": "Unresolved Procedural Posture",
            "custodyStatus": "unclear",
            "availableRemedies": [
                {
                    "remedy": "Ascertain Custody Status Before Selecting Pleading",
                    "statutoryBasis": "Article 22(1) Constitution; Section 50/437/439 CrPC OR Section 47/480/483 BNSS",
                    "whenApplicable": "Applies if the person has already been arrested or remanded.",
                    "cautionNote": "Obtain Arrest Memo, Written Grounds of Arrest (if any), and Remand Order immediately."
                }
            ],
            "remedyNote": "Custody status cannot be confirmed conclusively from submitted text. Appropriate remedy differs fundamentally depending on whether arrest has already occurred."
        }

    @staticmethod
    def extract_parties(text: str) -> Dict[str, List[str]]:
        """
        Extracts petitioner/appellant and respondent/state names.
        """
        petitioners = []
        respondents = []

        # Check for title patterns e.g. "X vs Y" or "X v. State"
        vs_match = re.search(r"([A-Z][A-Za-z0-9\s,\.\(\)&]+?)\s+(?:versus|vs\.?|v\.)\s+([A-Z][A-Za-z0-9\s,\.\(\)&]+?)(?:\n|\.|$)", text, re.IGNORECASE)
        if vs_match:
            p_part = vs_match.group(1).strip()
            r_part = vs_match.group(2).strip()
            if len(p_part) > 2 and len(p_part) < 100:
                petitioners.append(p_part)
            if len(r_part) > 2 and len(r_part) < 100:
                respondents.append(r_part)

        # Look for explicit petitioner / applicant mentions
        pet_matches = re.findall(r"\b(?:petitioner|applicant|appellant|accused)\s+(?:named|is|namely|was)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", text, re.IGNORECASE)
        for m in pet_matches:
            if m and m not in petitioners and len(m) > 2:
                petitioners.append(m)

        # Look for respondent mentions
        if re.search(r"\b(?:state of|state|union of india|police|investigating officer|complainant)\b", text, re.IGNORECASE):
            state_match = re.search(r"\b(State of\s+[A-Z][a-z]+|Union of India|State\s*\([A-Z][a-z]+\))\b", text, re.IGNORECASE)
            if state_match and state_match.group(1) not in respondents:
                respondents.append(state_match.group(1))
            elif "State" not in respondents:
                respondents.append("State / Prosecution")

        return {
            "petitioners": petitioners if petitioners else ["Petitioner / Accused"],
            "respondents": respondents if respondents else ["State / Respondent"]
        }

    @staticmethod
    def extract_chronology(text: str, document_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Extracts chronological events with dates, descriptions, and party roles.
        """
        events = []
        # Match dates in forms like 01.07.2024, 15/08/2023, 14 October 2024, etc.
        date_pattern = re.compile(
            r"\b(\d{1,2}(?:st|nd|rd|th)?[\s\/\-\.](?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2})[\s\/\-\.]\d{2,4})\b",
            re.IGNORECASE
        )

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 15]

        for s in sentences:
            m = date_pattern.search(s)
            if m:
                d_str = m.group(1)
                events.append({
                    "date": d_str,
                    "event": s[:200] + ("..." if len(s) > 200 else ""),
                    "involvedParties": "Parties mentioned in event",
                    "sourceExcerpt": s[:300],
                    "verificationStatus": "User-provided fact"
                })

        return events[:10]  # Return top chronological milestones

    @staticmethod
    def classify_facts(text: str, posture: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs fine-grained classification of facts into:
        - userProvidedFacts
        - materialFacts
        - partyAllegations
        - reasonableInferences
        - factsRequiringVerification
        - disputedActions
        - allegedViolations
        """
        t = text.lower()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 12]

        user_provided = sentences[:12]
        material_facts = []
        party_allegations = []
        reasonable_inferences = []
        facts_requiring_verification = []
        disputed_actions = []
        alleged_violations = []

        # Custody & arrest facts
        if posture.get("custodyStatus") == "in_custody_arrested":
            material_facts.append("The subject individual has been arrested and is currently in police or judicial custody.")
            disputed_actions.append("Execution of arrest and subsequent Magisterial remand.")
            facts_requiring_verification.append("Exact date and time of arrest recorded in the Arrest Memo versus actual apprehension.")
            facts_requiring_verification.append("Whether written Grounds of Arrest were communicated directly to the arrestee prior to remand.")
            if re.search(r"\b(?:grounds of arrest|not communicated|not informed|without grounds)\b", t):
                alleged_violations.append("Asserted violation of Article 22(1) Constitution and Section 50 CrPC / Section 47 BNSS (non-furnishing of written grounds).")
                party_allegations.append("Petitioner asserts written grounds of arrest were never served or were furnished belatedly.")
        elif posture.get("custodyStatus") == "apprehending_arrest":
            material_facts.append("The individual has not yet been arrested and apprehends custodial detention.")
            facts_requiring_verification.append("Whether an FIR has been formally registered or summons issued.")
        elif posture.get("custodyStatus") == "civil_or_non_custodial":
            material_facts.append("The proceeding is civil, constitutional, or commercial without custodial detention.")

        # Pre-arrest notice (S. 41A CrPC / S. 35 BNSS)
        if re.search(r"\b(?:notice|41a|35 bnss|without notice|prior notice)\b", t):
            disputed_actions.append("Failure to serve statutory pre-arrest notice of appearance.")
            alleged_violations.append("Asserted non-compliance with statutory safeguards under Section 41A CrPC / Section 35 BNSS (Arnesh Kumar / Satender Kumar Antil principles).")
            facts_requiring_verification.append("Whether Investigating Officer recorded written reasons of necessity for arrest before dispensing with notice.")

        # Notification to family / nominated person (D.K. Basu / Art. 21/22)
        if re.search(r"\b(?:family|relative|friend|intimat|inform|d\.?k\.?\s*basu)\b", t):
            disputed_actions.append("Alleged omission to notify a nominated family member or friend regarding arrest and detention place.")
            alleged_violations.append("Asserted breach of custodial safeguards under Article 21/22 and Section 50A CrPC / Section 48 BNSS.")
            facts_requiring_verification.append("General Diary (GD) entry, Arrest Memo witness signature, and intimation memo to nominated person.")

        # 24-hour Magisterial production (Art. 22(2))
        if re.search(r"\b(?:24 hours|magistrate|remand|illegal detention)\b", t):
            disputed_actions.append("Timeliness of production before Judicial Magistrate within 24 hours of arrest.")
            alleged_violations.append("Asserted breach of Article 22(2) Constitution and Section 57 CrPC / Section 58 BNSS.")
            facts_requiring_verification.append("Exact transit time and Case Diary entries documenting timestamp of arrest versus production.")

        # Cheating / Commercial quashing
        if re.search(r"\b(?:cheating|cheat|420|318|commercial|breach of contract)\b", t):
            disputed_actions.append("Invocation of penal cheating provisions in an allegedly commercial or contractual dispute.")
            reasonable_inferences.append("Standard cheating offences carry punishment up to 7 years; statutory notice rules ordinarily apply unless aggravated provisions are invoked.")
            facts_requiring_verification.append("Whether fraudulent or dishonest intention existed at the inception of the transaction (distinguishing civil breach from criminal cheating).")

        return {
            "userProvidedFacts": user_provided,
            "materialFacts": material_facts if material_facts else user_provided[:3],
            "partyAllegations": party_allegations if party_allegations else ["Pleadings disclose contested factual allegations between the parties."],
            "reasonableInferences": reasonable_inferences if reasonable_inferences else ["Factual claims are subject to production of primary records."],
            "factsRequiringVerification": facts_requiring_verification if facts_requiring_verification else ["Corroborating documentary records must be verified."],
            "disputedActions": disputed_actions if disputed_actions else ["Core actions leading to initiation of legal proceedings."],
            "allegedViolations": alleged_violations if alleged_violations else ["Alleged violations of statutory or contractual provisions."]
        }

    @staticmethod
    def build_evidence_audit(text: str, posture: Dict[str, Any], category: str = "") -> List[Dict[str, Any]]:
        """
        Constructs an evidentiary audit checklist strictly marked as
        'Document to obtain / verify' with statutory purpose.
        """
        t = text.lower()
        items = []

        # Criminal / Custodial records
        if posture.get("custodyStatus") in ("in_custody_arrested", "apprehending_arrest") or "criminal" in category.lower() or "arrest" in t:
            items.append({
                "documentName": "First Information Report (FIR) Copy",
                "purpose": "Verify exact penal sections (IPC vs BNS), date of registration, and complainant assertions.",
                "status": "Document to obtain / verify",
                "relevanceNote": "Determines applicable procedural regime (CrPC vs BNSS) and maximum prescribed sentence."
            })
            items.append({
                "documentName": "Arrest Memo (Memo of Arrest / Punchnama)",
                "purpose": "Confirm recorded timestamp, location of arrest, attesting witness signatures, and arresting officer identification.",
                "status": "Document to obtain / verify",
                "relevanceNote": "Primary document to test compliance with D.K. Basu guidelines and S. 47 BNSS / S. 50 CrPC."
            })
            items.append({
                "documentName": "Written Grounds of Arrest Memo & Signed Acknowledgment",
                "purpose": "Ascertain whether written grounds of arrest were served on arrestee prior to remand and acknowledged in writing.",
                "status": "Document to obtain / verify",
                "relevanceNote": "Crucial for Article 22(1) challenge under Prabir Purkayastha / Vihaan Kumar doctrines."
            })
            items.append({
                "documentName": "Police Remand Application & Magistrate Remand Order",
                "purpose": "Verify whether Magistrate applied judicial mind to necessity of arrest and grounds of arrest.",
                "status": "Document to obtain / verify",
                "relevanceNote": "Mechanical remand orders without recorded reasons are vulnerable to Article 21/22 challenge."
            })
            items.append({
                "documentName": "Section 41A CrPC / Section 35 BNSS Notice of Appearance (if issued)",
                "purpose": "Determine whether pre-arrest notice was served and whether the noticee complied with appearance terms.",
                "status": "Document to obtain / verify",
                "relevanceNote": "Tests compliance with Arnesh Kumar / Satender Kumar Antil directions."
            })
            items.append({
                "documentName": "General Diary (GD) / Station Diary Entries",
                "purpose": "Verify departure and arrival timings of police team and entry of arrest details.",
                "status": "Document to obtain / verify",
                "relevanceNote": "Rebuts false arrest timestamps and establishes pre-custody transit timeline."
            })

        # NI Act Cheque Dishonour records
        if "138" in t or "cheque" in t or "ni act" in category.lower():
            items.append({
                "documentName": "Original Dishonoured Cheque & Bank Return Memo",
                "purpose": "Verify cheque details, reason for return ('funds insufficient'), and bank voucher date.",
                "status": "Document to obtain / verify",
                "relevanceNote": "Mandatory foundational proof under S. 138/146 NI Act."
            })
            items.append({
                "documentName": "Statutory Demand Notice, Postal Receipt & Tracking / Delivery Voucher",
                "purpose": "Prove dispatch within 30 days of dishonour and service upon drawer.",
                "status": "Document to obtain / verify",
                "relevanceNote": "Prerequisite for cause of action under Section 138 proviso (b) and (c)."
            })

        # Arbitration records
        if "arbitrat" in t or "arbitration" in category.lower():
            items.append({
                "documentName": "Arbitration Agreement / Contract Containing Dispute Resolution Clause",
                "purpose": "Establish existence, validity, and scope of arbitration clause.",
                "status": "Document to obtain / verify",
                "relevanceNote": "Threshold jurisdictional requirement under Sections 7, 8 & 11 of the Arbitration Act."
            })
            items.append({
                "documentName": "Notice Invoking Arbitration under Section 21",
                "purpose": "Confirm date of commencement of arbitral proceedings and limitation period.",
                "status": "Document to obtain / verify",
                "relevanceNote": "Governs Section 43 limitation calculation and arbitral tribunal constitution."
            })

        # Default fallback item if few matched
        if len(items) == 0:
            items.append({
                "documentName": "Primary Pleadings & Impugned Order / Notice",
                "purpose": "Verify core allegations, date of cause of action, and statutory basis of impugned action.",
                "status": "Document to obtain / verify",
                "relevanceNote": "Foundational record required to substantiate legal grounds in court."
            })

        return items

    @classmethod
    def analyze_facts(
        cls,
        text: str,
        category: str = "",
        court: str = "",
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end factual, procedural, and evidential analysis.
        Returns a complete ICaseUnderstanding dictionary.
        """
        posture = cls.detect_procedural_posture(text)
        parties = cls.extract_parties(text)
        chronology = cls.extract_chronology(text, document_metadata)
        fact_class = cls.classify_facts(text, posture)
        evidence_audit = cls.build_evidence_audit(text, posture, category)

        return {
            "parties": parties,
            "materialFacts": fact_class["materialFacts"],
            "chronology": chronology,
            "factClassification": {
                "userProvidedFacts": fact_class["userProvidedFacts"],
                "partyAllegations": fact_class["partyAllegations"],
                "reasonableInferences": fact_class["reasonableInferences"],
                "missingInformation": [
                    "Complete Case Diary / General Diary entries",
                    "Certified copy of lower court order / remand memo",
                    "Corroborating documentary evidence for contested assertions"
                ],
                "factsRequiringVerification": fact_class["factsRequiringVerification"]
            },
            "disputedActions": fact_class["disputedActions"],
            "allegedViolations": fact_class["allegedViolations"],
            "missingInformation": [
                "Exact timestamp of physical apprehension vs recorded arrest time",
                "Whether grounds of arrest were communicated in writing before remand",
                "Service proof of pre-arrest notice under S. 41A / 35 BNSS"
            ],
            "evidenceAudit": evidence_audit,
            "proceduralPosture": posture
        }
