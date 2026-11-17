"""
Unit Tests for Text Preprocessing & Cleaning
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.preprocessing.text_cleaner import (
    clean_legal_text,
    tokenize_sentences,
    tokenize_words,
    extract_statutory_provisions
)


class TestTextCleaner(unittest.TestCase):
    def test_clean_legal_text(self):
        raw = "Petitioner filed appeal u/s 482 of Cr.P.C.   before Hon'ble  Court. Page 1 of 42"
        cleaned = clean_legal_text(raw)
        self.assertIn("under section 482", cleaned)
        self.assertNotIn("Page 1 of 42", cleaned)
        self.assertNotIn("   ", cleaned)

    def test_tokenize_sentences(self):
        text = "The appeal is allowed. The conviction under S. 138 is set aside! Ordered accordingly."
        sentences = tokenize_sentences(text)
        self.assertEqual(len(sentences), 3)

    def test_tokenize_words(self):
        text = "Supreme Court of India quashed the criminal proceedings."
        tokens = tokenize_words(text, remove_stopwords=True)
        self.assertIn("supreme", tokens)
        self.assertIn("quashed", tokens)
        self.assertNotIn("the", tokens)
        self.assertNotIn("of", tokens)

    def test_extract_statutory_provisions(self):
        text = "Accused was charged under Section 498A of Indian Penal Code and Article 21 of Constitution."
        provisions = extract_statutory_provisions(text)
        self.assertTrue(any("498A" in p for p in provisions))
        self.assertTrue(any("Article 21" in p for p in provisions))


if __name__ == "__main__":
    unittest.main()
