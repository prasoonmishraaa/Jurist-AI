import json
import os
import unittest
from scripts.verify_sources import audit_record_structure, DEFAULT_CORPUS_PATH


class TestJudgmentSources(unittest.TestCase):
    def setUp(self):
        with open(DEFAULT_CORPUS_PATH, "r", encoding="utf-8") as f:
            self.corpus = json.load(f)

    def test_corpus_non_empty(self):
        self.assertGreaterEqual(len(self.corpus), 25)

    def test_all_records_pass_structural_source_audit(self):
        errors = []
        for record in self.corpus:
            errors.extend(audit_record_structure(record))
        self.assertEqual(errors, [], f"Structural source issues found: {errors}")

    def test_no_deprecated_main_sci_links(self):
        for record in self.corpus:
            self.assertNotIn("main.sci.gov.in", record.get("sourceUrl", ""))
            self.assertNotIn("main.sci.gov.in", record.get("officialSourceUrl", ""))

    def test_key_arrest_and_privacy_authorities_present(self):
        titles = " | ".join(r.get("caseTitle", "") for r in self.corpus)
        for required in ["Puttaswamy", "Arnesh Kumar", "D.K. Basu", "Satender Kumar Antil", "Prabir Purkayastha", "Vihaan Kumar"]:
            self.assertIn(required, titles)


if __name__ == "__main__":
    unittest.main()
