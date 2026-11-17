"""
Natural Language Processing and Intelligence Modules
Jurist AI
"""

from app.nlp.entity_extractor import LegalEntityExtractor
from app.nlp.issue_identifier import identify_legal_issues
from app.nlp.fact_analyzer import LegalFactAnalyzer
from app.nlp.citation_grounder import CitationGroundingValidator
from app.nlp.legal_argument_generator import LegalArgumentGenerator

__all__ = [
    "LegalEntityExtractor",
    "identify_legal_issues",
    "LegalFactAnalyzer",
    "CitationGroundingValidator",
    "LegalArgumentGenerator"
]
