"""
Unit Tests for Legal NLP Entity Extraction & Issue Identification
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.nlp.entity_extractor import LegalEntityExtractor
from app.nlp.issue_identifier import identify_legal_issues


class TestNLP(unittest.TestCase):
    def setUp(self):
        self.extractor = LegalEntityExtractor()

    def test_extract_courts_and_statutes(self):
        text = "In the Supreme Court of India, Writ Petition under Article 21 regarding the Information Technology Act, 2000."
        entities = self.extractor.extract_entities(text)

        self.assertIn("Supreme Court of India", entities["courts"])
        self.assertTrue(any("Information Technology Act" in s for s in entities["statutes"]))
        self.assertTrue(any("Article 21" in s for s in entities["sections"]))

    def test_extract_parties(self):
        text = "Shreya Singhal v. Union of India dated 24th March 2015"
        entities = self.extractor.extract_entities(text)
        self.assertIn("Shreya Singhal", entities["parties"]["petitioners"])
        self.assertIn("Union of India", entities["parties"]["respondents"])

    def test_extract_legal_terms(self):
        text = "The petitioner prayed for quashing of FIR and anticipatory bail citing lack of mens rea."
        entities = self.extractor.extract_entities(text)
        terms = [t["term"] for t in entities["legalTerms"]]
        self.assertIn("Quashing", terms)
        self.assertIn("Anticipatory Bail", terms)
        self.assertIn("Mens Rea", terms)

    def test_identify_legal_issues(self):
        text = "Husband filed petition challenging arrest under Section 498A without Section 41 notice from police officer."
        issues = identify_legal_issues(text)
        self.assertGreater(len(issues), 0)
        top_issue = issues[0]["issue"]
        self.assertIn("Arrest", top_issue)

    def test_cheating_arrest_does_not_hallucinate_498a(self):
        text = (
            "Police arrested the complainant's former business partner on 15 October 2024 for alleged cheating "
            "without furnishing written grounds of arrest and kept custody over 24 hours without Magistrate remand."
        )
        issues = identify_legal_issues(text)
        issue_titles = [i["issue"] for i in issues]
        self.assertTrue(any("Arrest" in t for t in issue_titles))
        self.assertFalse(any("498A" in t for t in issue_titles))

    def test_extract_bns_bnss_entities(self):
        text = "FIR registered under Section 318(4) BNS and Section 47 BNSS before Chief Judicial Magistrate."
        entities = self.extractor.extract_entities(text)
        self.assertIn("Bharatiya Nyaya Sanhita, 2023", entities["statutes"])
        self.assertIn("Bharatiya Nagarik Suraksha Sanhita, 2023", entities["statutes"])


if __name__ == "__main__":
    unittest.main()
