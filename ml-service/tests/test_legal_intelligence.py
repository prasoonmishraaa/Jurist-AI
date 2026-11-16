"""
Comprehensive Test Suite for AI-Powered Legal Intelligence & Grounding
Jurist AI — Feature: AI-Powered Legal Intelligence Enhancement
"""

import pytest
import json
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.nlp.fact_analyzer import LegalFactAnalyzer
from app.nlp.citation_grounder import CitationGroundingValidator
from app.nlp.legal_argument_generator import LegalArgumentGenerator


class TestLegalFactAnalyzer:
    """Tests fact classification, procedural posture, and evidence audit."""

    def test_custody_posture_detection_arrested(self):
        text = (
            "The petitioner was arrested on 14.10.2024 at 11:30 PM and was remanded to police custody "
            "by the Judicial Magistrate without grounds of arrest being communicated in writing."
        )
        posture = LegalFactAnalyzer.detect_procedural_posture(text)
        assert posture["custodyStatus"] == "in_custody_arrested"
        assert "Post-Arrest" in posture["detectedPosture"]
        assert len(posture["availableRemedies"]) >= 2
        # Verify challenge to remand legality is present
        remedy_names = [r["remedy"] for r in posture["availableRemedies"]]
        assert any("Challenge to Arrest" in r for r in remedy_names)

    def test_custody_posture_detection_apprehending(self):
        text = (
            "The applicant is apprehending arrest in connection with FIR No. 120/2024 "
            "registered at Police Station Cyber Crime for alleged offences under Section 318 BNS."
        )
        posture = LegalFactAnalyzer.detect_procedural_posture(text)
        assert posture["custodyStatus"] == "apprehending_arrest"
        assert any("Anticipatory Bail" in r["remedy"] for r in posture["availableRemedies"])

    def test_custody_posture_detection_arbitration(self):
        text = (
            "The dispute arises out of an EPC contract dated 12.01.2022 containing an arbitration clause. "
            "Petitioner issued notice under Section 21 and now seeks appointment of arbitrator under Section 11."
        )
        posture = LegalFactAnalyzer.detect_procedural_posture(text)
        assert posture["custodyStatus"] == "civil_or_non_custodial"
        assert "Arbitration" in posture["detectedPosture"]

    def test_fact_classification_and_verification_flags(self):
        text = (
            "Accused was arrested without prior notice under Section 35 BNSS. "
            "Written grounds of arrest were not provided before production before the Magistrate."
        )
        analysis = LegalFactAnalyzer.analyze_facts(text, category="Criminal Writ")
        fact_class = analysis["factClassification"]

        assert len(fact_class["userProvidedFacts"]) > 0
        assert len(fact_class["factsRequiringVerification"]) > 0
        assert any("grounds of arrest" in f.lower() for f in fact_class["factsRequiringVerification"])
        assert any("notice" in a.lower() for a in analysis["disputedActions"])

    def test_evidence_audit_checklist_status(self):
        text = "Accused arrested in cheating complaint under Section 318(4) BNS without grounds."
        analysis = LegalFactAnalyzer.analyze_facts(text, category="Criminal")
        audit = analysis["evidenceAudit"]

        assert len(audit) >= 3
        # Strict requirement: all evidence audit items must have status "Document to obtain / verify"
        for item in audit:
            assert item["status"] == "Document to obtain / verify"
            assert "documentName" in item
            assert "purpose" in item
            assert "relevanceNote" in item


class TestCitationGroundingValidator:
    """Tests citation grounding, anti-hallucination, and metric calculation."""

    @pytest.fixture
    def validator(self):
        return CitationGroundingValidator()

    def test_grounded_citation_validation(self, validator):
        test_arguments = [
            {
                "id": "arg-1",
                "groundNumber": "GROUND I",
                "heading": "Written Grounds of Arrest",
                "supportingPrecedents": [
                    {
                        "caseTitle": "Prabir Purkayastha v. State (NCT of Delhi)",
                        "citation": "2024 INSC 412",
                        "court": "Supreme Court of India"
                    }
                ]
            }
        ]

        validated, report = validator.validate_argument_citations(test_arguments)
        assert len(validated) == 1
        prec = validated[0]["supportingPrecedents"][0]
        assert prec["isCorpusGrounded"] is True
        assert prec["verificationStatus"] == "verified"
        assert report["totalCitationsCited"] == 1
        assert report["groundedCitationsCount"] == 1
        assert report["unverifiedCitationsCount"] == 0
        assert report["groundingRatio"] == 1.0

    def test_unverified_citation_not_substituted(self, validator):
        """Strict Condition 3: Unverified citations must NOT be replaced with unrelated cases."""
        fake_title = "Imaginary Nonexistent Case v. Imaginary State"
        fake_citation = "2099 FAKE SC 9999"

        test_arguments = [
            {
                "id": "arg-fake",
                "groundNumber": "GROUND II",
                "heading": "Fictional Precedent Test",
                "supportingPrecedents": [
                    {
                        "caseTitle": fake_title,
                        "citation": fake_citation,
                        "court": "Fictional Supreme Court"
                    }
                ]
            }
        ]

        validated, report = validator.validate_argument_citations(test_arguments)
        prec = validated[0]["supportingPrecedents"][0]

        # Citation must remain ungrounded and unverified
        assert prec["isCorpusGrounded"] is False
        assert prec["verificationStatus"] == "unverified"
        # STRICT: Must NOT substitute a random case!
        assert prec["caseTitle"] == fake_title
        assert prec["citation"] == fake_citation
        assert "warning" in prec.get("verificationWarning", "").lower()

        assert report["totalCitationsCited"] == 1
        assert report["groundedCitationsCount"] == 0
        assert report["unverifiedCitationsCount"] == 1
        assert report["groundingRatio"] == 0.0
        assert report["isFullyGrounded"] is False


class TestDirectLegalArgumentGenerator:
    """Tests Direct LLM argument generator, prompt purity (no RAG), and offline fallback."""

    @pytest.fixture
    def generator(self):
        return LegalArgumentGenerator()

    def test_direct_llm_prompt_excludes_retrieved_passages(self, generator):
        """Strict verification: LLM prompt receives structured case info and NO retrieved passages."""
        sample_text = (
            "Petitioner was arrested in FIR 45/2024 for cheating under Section 318(4) BNS without notice."
        )
        understanding = LegalFactAnalyzer.analyze_facts(sample_text, category="Criminal", court="Supreme Court of India")
        qol = generator._formulate_questions_of_law(sample_text, understanding, {})

        prompt = generator._build_direct_llm_prompt(
            text=sample_text,
            category="Criminal",
            court="Supreme Court of India",
            understanding=understanding,
            questions_of_law=qol,
            applicable_law={}
        )

        # 1. Verify structured case information and curated facts are present
        assert "Forum / Court: Supreme Court of India" in prompt
        assert "Category: Criminal" in prompt
        assert "CURATED CASE FACTS & EVIDENCE PROFILE:" in prompt
        assert "Material Facts:" in prompt
        assert "Party Allegations:" in prompt
        assert "Facts Requiring Verification:" in prompt
        assert "IDENTIFIED QUESTIONS OF LAW:" in prompt

        # 2. STRICT VERIFICATION: Raw narrative dump, retrieved authorities and judgment passages must NOT be in prompt!
        assert "NARRATIVE TEXT:" not in prompt
        assert "RETRIEVED AUTHORITIES" not in prompt
        assert "retrieved passages" not in prompt.lower()
        assert "precedent_context" not in prompt

    def test_offline_deterministic_fallback(self, generator):
        text = (
            "The petitioner was arrested on 12.08.2024 in FIR No. 89/2024 under Section 318(4) BNS. "
            "No notice under Section 35(3) BNSS was served prior to arrest, nor were written grounds "
            "of arrest furnished to the petitioner before Magisterial remand."
        )

        result = generator.generate_intelligence(
            text=text,
            category="Criminal Writ",
            court="High Court of Delhi"
        )

        # Verify generation metadata
        assert result["generationMode"] == "deterministic_offline"
        assert result["requiresAdvocateReview"] is True

        # Verify questions of law
        assert len(result["questionsOfLaw"]) >= 1
        qol_texts = [q["issue"] for q in result["questionsOfLaw"]]
        assert any("grounds of arrest" in q.lower() or "written grounds" in q.lower() for q in qol_texts)

        # Verify arguments schema
        args = result["legalArguments"]
        assert len(args) >= 2

        for arg in args:
            assert "groundNumber" in arg
            assert "heading" in arg
            assert "legalProposition" in arg
            assert "suggestedSubmission" in arg
            assert "draftDisclaimer" in arg
            assert "counterarguments" in arg
            assert len(arg["counterarguments"]) >= 1
            assert arg["generationMode"] == "deterministic_offline"

            # Verify counterarguments schema
            for ca in arg["counterarguments"]:
                assert "opposingGround" in ca
                assert "opposingLegalBasis" in ca
                assert "factualBasis" in ca
                assert "vulnerabilityAssessment" in ca
                assert "rebuttalStrategy" in ca

        # Verify evidence trace graph
        trace = result["evidenceTraceGraph"]
        assert len(trace) >= len(args)
        for node in trace:
            assert "traceId" in node
            assert "groundNumber" in node
            assert "sourcePassage" in node
            assert node["aiGenerated"] is True
            assert node["requiresAdvocateReview"] is True
            assert node["generationMode"] == "deterministic_offline"

        # Verify citation grounding report
        cg = result["citationGrounding"]
        assert "groundingRatio" in cg
        assert cg["totalCitationsCited"] > 0
        assert cg["groundedCitationsCount"] > 0


class TestLegalIntelligenceEndpoint:
    """Tests the dedicated POST /api/ml/legal-intelligence endpoint behavior."""

    def test_hybrid_retrieval_operates_independently(self):
        from app.services.api import hybrid_retriever
        sample_text = "arbitration clause appointment of arbitrator under section 11"
        precedents = hybrid_retriever.retrieve_similar(sample_text, top_k=5)
        assert len(precedents) > 0
        for p in precedents:
            assert "caseTitle" in p
            assert "citation" in p

    def test_handler_intelligence_payload_structure(self):
        from app.services.api import LegalFactAnalyzer, hybrid_retriever, argument_generator, extractor, verified_predictor

        sample_text = (
            "The petitioner was arrested on 14.10.2024 at 11:30 PM and was remanded to police custody "
            "by the Judicial Magistrate without grounds of arrest being communicated in writing."
        )
        category = "Criminal Writ"
        court = "High Court of Delhi"

        # Simulate the exact logic inside api.py for /api/ml/legal-intelligence
        case_understanding = LegalFactAnalyzer.analyze_facts(sample_text, category=category, court=court)
        # Hybrid retrieval runs independently for Authorities & Matches
        top_precedents = hybrid_retriever.retrieve_similar(sample_text, top_k=6)
        intelligence = argument_generator.generate_intelligence(
            text=sample_text,
            category=category,
            court=court,
            case_understanding=case_understanding,
            precedents_for_validation=top_precedents
        )
        entities = extractor.extract_entities(sample_text)
        prediction = verified_predictor.predict_outcome(sample_text, category=category)

        response = {
            **intelligence,
            "entities": entities,
            "precedents": top_precedents,
            "prediction": prediction,
            "statutoryEntityCounts": {
                "acts": len(entities.get("acts", [])),
                "sections": len(entities.get("sections", [])),
                "courts": len(entities.get("courts", []))
            }
        }

        # Check top-level contract
        assert response["generationMode"] in ("gemini_direct", "openai_direct", "deterministic_offline")
        assert "caseUnderstanding" in response
        assert "questionsOfLaw" in response
        assert "legalArguments" in response
        assert "evidenceTraceGraph" in response
        assert "citationGrounding" in response
        assert "entities" in response
        assert "precedents" in response
        assert len(response["precedents"]) > 0
        assert "prediction" in response
        assert "requiresAdvocateReview" in response
        assert response["requiresAdvocateReview"] is True

        # Model A and Model B preservation
        assert "modelA" in response["prediction"]
        assert "modelB" in response["prediction"]


class TestTransitionHandling:
    """Verifies BNSS / CrPC transition handling without blindly listing old and new codes."""

    def test_post_july_2024_applies_bnss_without_blindly_listing_crpc(self):
        text = (
            "The offence was allegedly committed on 10 August 2024. FIR was registered on 15 August 2024 under Section 318(4) BNS. "
            "The petitioner was arrested on 20 August 2024 without prior notice under Section 35(3) BNSS and without written grounds of arrest."
        )
        generator = LegalArgumentGenerator()
        app_law = {"regimeStatus": "post_july_2024_new_codes"}
        result = generator.generate_intelligence(
            text=text,
            category="Criminal",
            court="High Court of Delhi",
            applicable_law=app_law
        )

        args = result["legalArguments"]
        g1 = next(a for a in args if a["id"] == "arg-art22-grounds")
        # Confirms BNSS is present
        assert any("BNSS" in p or "Bharatiya Nagarik Suraksha" in p for p in g1["applicableProvisions"])
        # Confirms CrPC is NOT blindly listed alongside BNSS for a confirmed post-transition event
        assert not any("Section 50, Code of Criminal Procedure" in p for p in g1["applicableProvisions"])

    def test_pre_july_2024_applies_crpc_without_blindly_listing_bnss(self):
        text = (
            "The incident occurred on 12 May 2023. FIR was registered on 15 May 2023 under Section 420 IPC. "
            "Accused was arrested on 20 May 2023 without notice under Section 41A CrPC and without grounds of arrest."
        )
        generator = LegalArgumentGenerator()
        app_law = {"regimeStatus": "pre_july_2024_legacy_codes"}
        result = generator.generate_intelligence(
            text=text,
            category="Criminal",
            court="High Court of Punjab and Haryana",
            applicable_law=app_law
        )

        args = result["legalArguments"]
        g1 = next(a for a in args if a["id"] == "arg-art22-grounds")
        # Confirms CrPC is present
        assert any("Section 50, Code of Criminal Procedure" in p for p in g1["applicableProvisions"])
        # Confirms BNSS is NOT blindly listed alongside CrPC for a pre-transition event
        assert not any("Section 47, Bharatiya Nagarik Suraksha" in p for p in g1["applicableProvisions"])

