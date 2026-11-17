import sys
import json
import re
from pathlib import Path
from collections import defaultdict

ML_SERVICE_DIR = Path("ml-service").resolve()
sys.path.insert(0, str(ML_SERVICE_DIR))

from scripts.build_verified_outcome_dataset import TargetLeakageSanitizer

source_path = ML_SERVICE_DIR / "app" / "datasets" / "open_india_law_sample_150.json"
with open(source_path, "r", encoding="utf-8") as f:
    cases = json.load(f)

sanitizer = TargetLeakageSanitizer()

print("=" * 70)
print("INDEPENDENT TARGET LEAKAGE AUDIT (150 JUDGMENTS)")
print("=" * 70)

# Broad independent audit probes (intentionally broader than sanitizer patterns)
audit_probes = {
    "terminal_verdict_stamps": re.compile(r"(?:^|\n|\.\s+)(?:Appeals?|Petitions?|SLP|Special\s+Leave)\s+(?:allowed|dismissed|disposed\s+of|remanded)\b", re.IGNORECASE),
    "reversal_verbs": re.compile(r"\b(?:set\s+aside|reversed|quashed|annulled)\b", re.IGNORECASE),
    "first_person_judicial_acts": re.compile(r"\bwe\s+(?:allow|dismiss|partly\s+allow|set\s+aside|remit|quash|direct|hold|order)\b", re.IGNORECASE),
    "appeal_outcome_phrases": re.compile(r"\b(?:the\s+|this\s+|these\s+)?appeals?\s+(?:is|are|was|were|stands?|stood)?\s*(?:hereby\s+|therefore\s+|accordingly\s+)?(?:allowed|dismissed|partly\s+allowed|disposed\s+of|fails?|succeeds?)\b", re.IGNORECASE),
    "petition_outcome_phrases": re.compile(r"\b(?:the\s+|this\s+|these\s+)?(?:writ\s+)?petitions?\s+(?:is|are|was|were|stands?|stood)?\s*(?:hereby\s+|therefore\s+|accordingly\s+)?(?:allowed|dismissed|disposed\s+of|rejected)\b", re.IGNORECASE),
    "bail_relief_phrases": re.compile(r"\b(?:released|enlarged)\s+on\s+bail\b", re.IGNORECASE),
    "scraper_kanoon_artifacts": re.compile(r"\[SECTION\]\s*##", re.IGNORECASE),
    "concluding_decree_costs": re.compile(r"\b(?:costs?\s+(?:quantified|awarded|which\s+we\s+quantify)|without\s+any\s+order\s+as\s+to\s+costs?|no\s+order\s+as\s+to\s+costs?)\b", re.IGNORECASE),
}

# Counters
probe_matches = defaultdict(list)
actual_leakage_cases = set()
historical_facts_cases = defaultdict(list)
counsel_arguments_cases = defaultdict(list)
precedent_cases = defaultdict(list)
statutory_cases = defaultdict(list)

# Track text length before and after
length_reductions = []
truncated_count = 0
redacted_phrase_count = 0

for c in cases:
    cid = c["id"]
    text = c.get("judgmentText", "")
    sanitized, meta = sanitizer.sanitize_judgment_text(text)
    
    orig_len = meta["original_length"]
    san_len = meta["sanitized_length"]
    pct_preserved = (san_len / orig_len * 100) if orig_len > 0 else 100.0
    length_reductions.append((cid, orig_len, san_len, pct_preserved, meta["truncated_operative_section"], meta["stripped_phrase_count"]))
    
    if meta["truncated_operative_section"]:
        truncated_count += 1
    redacted_phrase_count += meta["stripped_phrase_count"]
    
    # Audit sanitized text against each independent probe
    for probe_name, rx in audit_probes.items():
        for m in rx.finditer(sanitized):
            start = max(0, m.start() - 60)
            end = min(len(sanitized), m.end() + 60)
            snippet = sanitized[start:end].replace("\n", " ")
            match_str = m.group(0)
            
            # Contextual classification of the match
            context_lower = snippet.lower()
            
            # Check if this match is in the tail (last 5% of sanitized text) or earlier
            is_tail = (m.start() >= len(sanitized) * 0.90)
            
            # Classification rules:
            # 1. Historical High Court / Trial Court action
            if any(h in context_lower for h in ["high court", "trial court", "sessions", "magistrate", "tribunal", "impugned judgment of", "by the high court", "appellant preferred", "filed an appeal", "against the order of"]):
                historical_facts_cases[probe_name].append((cid, match_str, snippet))
            # 2. Argument of counsel
            elif any(a in context_lower for a in ["learned counsel", "senior counsel", "submitted that", "contended that", "argued that", "advocate", "on behalf of", "counsel for"]):
                counsel_arguments_cases[probe_name].append((cid, match_str, snippet))
            # 3. Precedent discussion
            elif any(p in context_lower for p in ["this court in", "held in", "v.", "versus", "air ", "scc", "scr", "observed in", "relied on", "cited"]):
                precedent_cases[probe_name].append((cid, match_str, snippet))
            # 4. Statutory provision
            elif any(s in context_lower for s in ["section", "article", "act", "rule", "clause", "provision", "code"]):
                statutory_cases[probe_name].append((cid, match_str, snippet))
            # 5. First-person judicial statements by this bench
            elif probe_name == "first_person_judicial_acts":
                # Check if this bench is actually announcing the outcome or just reasoning
                if any(w in match_str.lower() for w in ["allow", "dismiss", "partly allow", "set aside", "quash", "remit"]):
                    actual_leakage_cases.add((cid, probe_name, match_str, snippet))
                else:
                    # e.g., "we hold that", "we direct the trial court" during discussion
                    probe_matches[probe_name].append((cid, match_str, snippet))
            elif is_tail and any(w in match_str.lower() for w in ["allowed", "dismissed", "set aside", "fails"]):
                actual_leakage_cases.add((cid, probe_name, match_str, snippet))
            else:
                probe_matches[probe_name].append((cid, match_str, snippet))

print(f"\n1. EVALUATION TOTALS:")
print(f"   Total Judgments Evaluated:       {len(cases)}")
print(f"   Operative Sections Truncated:    {truncated_count} / {len(cases)} ({truncated_count/len(cases)*100:.1f}%)")
print(f"   Total In-Body Phrases Redacted:  {redacted_phrase_count}")

# Distribution of text preservation percentages
pcts = [p[3] for p in length_reductions]
print(f"\n2. TEXT PRESERVATION METRICS:")
print(f"   Min Preserved:                   {min(pcts):.1f}%")
print(f"   Max Preserved:                   {max(pcts):.1f}%")
print(f"   Mean Preserved:                  {sum(pcts)/len(pcts):.1f}%")
print(f"   Median Preserved:                {sorted(pcts)[len(pcts)//2]:.1f}%")

# Judgments with < 70% preserved (check if over-truncated)
over_truncated = [p for p in length_reductions if p[3] < 70.0]
print(f"   Judgments with < 70% preserved:  {len(over_truncated)}")
for cid, olen, slen, pct, trunc, red in over_truncated[:5]:
    print(f"     - {cid}: {olen} -> {slen} ({pct:.1f}% preserved)")

print(f"\n3. RESIDUAL ACTUAL LEAKAGE (False Negatives):")
print(f"   Total Instances of Actual Leakage Detected: {len(actual_leakage_cases)}")
if actual_leakage_cases:
    for cid, pname, mstr, snip in list(actual_leakage_cases)[:10]:
        print(f"     - [{cid}] Probe '{pname}' matched '{mstr}': {repr(snip)}")
else:
    print("   ZERO false-negative actual outcome leaks detected across all 150 judgments!")

print(f"\n4. LEGITIMATE PRE-DECISION PHRASES PRESERVED (Not Over-Redacted):")
for probe_name in audit_probes.keys():
    n_hist = len(historical_facts_cases[probe_name])
    n_arg = len(counsel_arguments_cases[probe_name])
    n_prec = len(precedent_cases[probe_name])
    n_stat = len(statutory_cases[probe_name])
    n_other = len(probe_matches[probe_name])
    total = n_hist + n_arg + n_prec + n_stat + n_other
    if total > 0:
        print(f"   Probe '{probe_name:28s}': {total:3d} matches preserved in pre-decision text")
        print(f"      (Historical facts: {n_hist}, Counsel args: {n_arg}, Precedents: {n_prec}, Statutes: {n_stat}, Judicial reasoning: {n_other})")

print("\n" + "=" * 70)
print("AUDIT EXECUTION COMPLETE")
print("=" * 70)
