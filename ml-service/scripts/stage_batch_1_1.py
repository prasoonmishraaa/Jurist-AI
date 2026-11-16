import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path("ml-service").resolve()))
from app.prediction.outcome_annotation_session import (
    OutcomeAnnotationSessionManager,
    VALID_DISPOSITIONS,
    VALID_SUCCESSFUL_PARTIES,
    AnnotationValidationError,
)

session = OutcomeAnnotationSessionManager()

with open("ml-service/app/datasets/open_india_law_sample_150.json", "r", encoding="utf-8") as f:
    source_cases = {c["id"]: c for c in json.load(f)}

# Let's inspect each case's concluding operative text to extract verbatim quotes matching the user's evidence:
cases_to_stage = [
    {
        "case_id": "OIL-SC-1996_INSC_503",
        "action": "accept",
        "disposition": "appeal_dismissed",
        "successful_party": "state_prosecution",
        "user_evidence": "Operative order affirming conviction and dismissing the appeal.",
        "note": "The appellant was directed to surrender to his bail bonds.",
        "verbatim_search": "maintaining the conviction of the appellant"
    },
    {
        "case_id": "OIL-SC-2007_INSC_31",
        "action": "correct",
        "disposition": "remanded",
        "successful_party": "none_procedural",
        "user_evidence": "Operative order remitting the matter to the High Court for fresh consideration under Section 100 CPC.",
        "note": "Do not classify this as a substantive merits victory merely because the formal order says the appeal is allowed.",
        "verbatim_search": "remitted to the High Court for consideration of the Second Appeal afresh"
    },
    {
        "case_id": "OIL-SC-2007_INSC_1082",
        "action": "accept",
        "disposition": "appeal_allowed",
        "successful_party": "petitioner",
        "user_evidence": "Appeal allowed, directions issued for implementation of modified pay terms, and costs of Rs. 25,000 awarded.",
        "note": "Resolve the previously unresolved successful-party field.",
        "verbatim_search": "The appeal is allowed. We, however, before taking any punitive action"
    },
    {
        "case_id": "OIL-SC-2003_INSC_88",
        "action": "accept",
        "disposition": "appeal_dismissed",
        "successful_party": "respondent",
        "user_evidence": "Operative order dismissing the appeals.",
        "note": "Confirm the complete concluding operative order is present in the source text before staging. Resolve the previously unresolved successful-party field.",
        "verbatim_search": "In these circumstances, we dismiss the appeals without"
    },
    {
        "case_id": "OIL-SC-1973_INSC_203",
        "action": "accept",
        "disposition": "petition_allowed",
        "successful_party": "petitioner",
        "user_evidence": "Detention order set aside and petitioner directed to be released forthwith.",
        "note": "Habeas corpus petition allowed; preventive detention quashed.",
        "verbatim_search": "For these reasons we set aside ihe order of detention"
    }
]

print("=== VERIFYING EVIDENCE IN SOURCE JUDGMENT TEXT ===")
staged_payloads = []
for item in cases_to_stage:
    cid = item["case_id"]
    s = source_cases[cid]
    jtext = s["judgmentText"]

    # Verify presence of verbatim phrase in source text
    search_term = item["verbatim_search"]
    idx = jtext.find(search_term)
    if idx == -1:
        # Check without strict typo
        print(f"FAILED to find exact search term for {cid}: '{search_term}'")
    else:
        # Extract a clean context window around the verbatim phrase
        start = max(0, idx - 100)
        end = min(len(jtext), idx + 250)
        excerpt = jtext[start:end].strip()
        print(f"\n[FOUND] {cid}:")
        print(f"  Title: {s['caseTitle']}")
        print(f"  Date:  {s['judgmentDate']}")
        print(f"  Excerpt:\n    {excerpt}")

    # Build the full evidence string pairing user summary with primary verbatim quote
    # Let's extract the exact concluding operative sentences from the text:
    if cid == "OIL-SC-1996_INSC_503":
        verbatim_quote = "For the foregoing reasons, we do not differ from the view taken by the High Court in maintaining the conviction of the appellant. The appeal therefore fails and is hereby dismissed. The appellant is on bail. He shall surrender to his bail bonds. Appeal dismissed."
    elif cid == "OIL-SC-2007_INSC_31":
        verbatim_quote = "we are of the opinion that the impugned judgment cannot be sustained and this should be set aside and the matter be remitted to the High Court for consideration of the Second Appeal afresh after formulating an appropriate substantial question of law arising, if any. The appeal is allowed."
    elif cid == "OIL-SC-2007_INSC_1082":
        verbatim_quote = "The appeal is allowed. We, however, before taking any punitive action against the contemnors at this stage, would like to issue a direction upon them to fully implement the orders of this Court as modified by this Court on the same terms as was done in the case of employees similarly situated. In facts and circumstances of the case the appellants shall also be entitled to costs which we quantify at Rs. 25,000/-."
    elif cid == "OIL-SC-2003_INSC_88":
        verbatim_quote = "In these circumstances, we dismiss the appeals without ariy order as to costs. Appeals dismissed."
    elif cid == "OIL-SC-1973_INSC_203":
        verbatim_quote = "For these reasons we set aside ihe order of detention. We had earlier directed on the conclusion of the arguments that the petitioner be set at liberty forthwith. Petition allowed:"

    full_evidence = f"{item['user_evidence']} Verbatim: \"{verbatim_quote}\""
    
    payload = {
        "case_id": cid,
        "action": item["action"],
        "disposition": item["disposition"],
        "successful_party": item["successful_party"],
        "evidence": full_evidence,
        "notes": item["note"]
    }

    # Validate payload through session validator
    try:
        session._validate_decision_payload(payload)
        print(f"  Validation: PASSED for {cid}")
        staged_payloads.append(payload)
    except Exception as e:
        print(f"  Validation: FAILED for {cid}: {e}")

print(f"\nTotal validated staged payloads: {len(staged_payloads)} / 5")
