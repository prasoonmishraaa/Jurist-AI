import sys
from pathlib import Path

# Add ml-service/scripts to path
sys.path.insert(0, str(Path("ml-service/scripts").resolve()))
from prototype_hardened_sanitizer import HardenedTargetLeakageSanitizer

sanitizer = HardenedTargetLeakageSanitizer()

# Positive Test Cases (Leakage that MUST be redacted or truncated)
positive_test_cases = [
    # 1. Bare terminal dispositions
    ("Bare dismissal", "Some facts here.\n\nAppeals dismissed.", True),
    ("Bare petition allowed", "Arguments ended.\n\nPetition allowed:", True),
    ("Bare SLP dismissed", "Heard counsel.\n\nSpecial Leave Petition dismissed.", True),
    
    # 2. Intervening adverbs
    ("Intervening therefore fails", "The evidence is weak. The appeal therefore fails and is hereby dismissed.", True),
    ("Intervening accordingly allowed", "The decree cannot stand. The appeal, accordingly, succeeds and is allowed.", True),
    ("Consequently dismissed", "For these reasons, the appeal consequently stands dismissed.", True),
    
    # 3. First-person active-voice judicial acts
    ("We dismiss the appeals", "In these circumstances, we dismiss the appeals without any order as to costs.", True),
    ("We allow this appeal", "For the reasons aforesaid, we allow this appeal and set aside the impugned order.", True),
    ("We set aside detention", "For these reasons we set aside the order of detention.", True),
    ("We remit the matter", "In the result, we remit the matter to the High Court for fresh disposal.", True),
    
    # 4. Decree and order reversal phrases
    ("Order is set aside", "Therefore, the impugned order of the High Court is hereby set aside.", True),
    ("Same are set aside", "The orders are arbitrary. The same are set aside and the appeal is allowed.", True),
    ("Matter remitted", "The matter be remitted to the High Court for fresh determination.", True),
    
    # 5. Scraper suffixes
    ("Scraper Kanoon header", "Costs quantified at Rs 25,000.\n\n[SECTION] ## Appeal allowed.", True),
    
    # 6. Older judgments without headings (concluding operative transition)
    ("Concluding transition", "Paragraph 19: Discussion of merits.\n\nFor the foregoing reasons, we do not differ from the view taken by the High Court in maintaining the conviction. The appeal therefore fails.", True),
]

# Negative Test Cases (Facts, arguments, statutes that MUST be preserved)
negative_test_cases = [
    # 1. Historical trial court narrative
    ("Historical High Court dismissal", 
     "The appellant was convicted by the Sessions Court under Section 302 IPC. The appellant then filed an appeal before the High Court. That appeal was dismissed by the High Court on 14.07.2015, affirming the life sentence. Aggrieved thereby, the appellant approached this Court.",
     ["Sessions Court", "Section 302 IPC", "affirming the life sentence", "approached this Court"]),
     
    # 2. Argument of Counsel
    ("Counsel argument for dismissal",
     "Mr. Rohatgi, learned Senior Counsel appearing for the State, vehemently contended that the appeal is devoid of merit and ought to be dismissed because the eyewitness testimony of PW-1 is consistent.",
     ["Mr. Rohatgi", "vehemently contended", "eyewitness testimony", "PW-1"]),
     
    # 3. Precedent discussion
    ("Precedent quotation",
     "In State of Haryana v. Bhajan Lal, 1992 Supp (1) SCC 335, this Court laid down the categories where extraordinary power under Article 226 can be exercised to prevent abuse of the process of any court.",
     ["Bhajan Lal", "1992 Supp (1) SCC 335", "Article 226", "abuse of the process"]),
     
    # 4. Statutory provision text
    ("Statutory provision recitation",
     "Section 100 of the Code of Civil Procedure mandates that a Second Appeal shall lie to the High Court only if the High Court is satisfied that the case involves a substantial question of law.",
     ["Section 100", "Code of Civil Procedure", "Second Appeal", "substantial question of law"]),
     
    # 5. Framing of issues
    ("Framing of legal question",
     "The primary question of law arising for our consideration is whether the period of limitation under Section 34 of the Arbitration Act can be extended by invoking Section 5 of the Limitation Act.",
     ["primary question of law", "Section 34", "Arbitration Act", "Limitation Act"]),
]

print("=== RUNNING POSITIVE LEAKAGE SANITIZATION TESTS ===")
positive_passed = 0
for name, text, expected_sanitized in positive_test_cases:
    # Pad text so it behaves like a normal judgment where operative is in second half
    full_text = "Factual narrative and pleadings here.\n" * 20 + text
    sanitized, meta = sanitizer.sanitize_judgment_text(full_text)
    
    # Check if any forbidden keyword remains in unredacted form
    has_leak = any(k in sanitized for k in ["Appeals dismissed", "Petition allowed:", "Special Leave Petition dismissed",
                                            "we dismiss the appeals", "we allow this appeal", "set aside the order of detention",
                                            "[SECTION] ##", "appeal therefore fails and is hereby dismissed"])
    if not has_leak:
        positive_passed += 1
        print(f"  [PASS] {name} - Leakage cleanly neutralized.")
    else:
        print(f"  [FAIL] {name} - Leakage detected in: {repr(sanitized[-100:])}")

print(f"Positive Test Result: {positive_passed}/{len(positive_test_cases)} passed.")

print("\n=== RUNNING NEGATIVE PRE-DECISION PRESERVATION TESTS ===")
negative_passed = 0
for name, text, required_phrases in negative_test_cases:
    sanitized, meta = sanitizer.sanitize_judgment_text(text)
    
    all_present = all(p in sanitized for p in required_phrases)
    if all_present:
        negative_passed += 1
        print(f"  [PASS] {name} - All pre-decision facts/arguments preserved.")
    else:
        missing = [p for p in required_phrases if p not in sanitized]
        print(f"  [FAIL] {name} - Erroneously redacted or missing: {missing}")

print(f"Negative Test Result: {negative_passed}/{len(negative_test_cases)} passed.")
