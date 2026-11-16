import json
from pathlib import Path

source_path = Path("ml-service/app/datasets/open_india_law_sample_150.json")
with open(source_path, "r", encoding="utf-8") as f:
    source_cases = {c["id"]: c for c in json.load(f)}

# Let's test each quote candidate
quotes = {
    "OIL-SC-2000_INSC_110": (
        "In view of what we have concluded ano the said decision which squarely apply, we have no hesitation to hold that courts below have rightly decreed the suit for eviction as against the appellant and change of user of the business by the appellant's from radios, cycles, fans, clocks and· steel furniture to grocery business is in contradiction to the specific term of the agreement. Thus such tenant would be covered by Section 10(2)(ii)(b). Hence the appellant is liable for eviction which the courts below have rightly decreed. This appeal accordingly fails and is dismissed. Costs on the parties.-\n\nHeard learned counsel for the parties. Tenant may vacate the premises by or before 31st Dec. 2000 subject to the usual undertaking within six weeks from today"
    ),
    "OIL-SC-2016_INSC_467": (
        "18. In view of the above, we allow this appeal, set aside the impugned judgment and direct disposal of the writ petitions of the respondents in terms of the judgment of this Court in Savitri Devi (supra). There will be no order as to costs.\n\nB Appeal allowed."
    ),
    "OIL-SC-1973_INSC_247": (
        "Where, however, as in the present case the requisite details of the activity for which the order for detention was made.. have been conveyed to the detenu B at1d he is not shown to have been prejudiced or handicapped in making an effective representation, the argument about the vague,. ness of grounds of detention must plainly be held to be not tenable.\n\nThe petition consequently fails and is dismissed. S.B.W. Petition dismisJed. c"
    ),
    "OIL-SC-1979_INSC_85": (
        "For the foregoing reasons, we allow this appeal, set aside the judgment of the High Court and pass a preliminary decree for parti-tion and separate possession in favour of the plaintiff with respect to her l/3rd share in the snit property. In the circumstances of the case, the parties are left to pay and bear !heir own costs.\n\nP.B.R.\n\n[SECTION] ## Appeal allowed."
    ),
    "OIL-SC-1998_INSC_267": (
        "This being the position the appellant having superannuated prior to the C Rule corning into force cannot claim the right to pension under the Rules with the help of the decision of this Court in Nakara (supra) and further in view of our conclusion that the Rules do not have any retrospective operation the relief sought for by the appellant to get pension under the Rules cannot be granted.\n\nD In the premises, as aforesaid, the appeal fails and is dismissed. But in the circumstances there will no order as to costs.\n\nv.s.s.\n\nAppeal dismissed."
    )
}

print("=== VERIFYING PROPOSED EVIDENCE AS EXACT SUBSTRINGS ===")
for cid, quote in quotes.items():
    case = source_cases.get(cid)
    if not case:
        print(f"ERROR: {cid} not found in source dataset!")
        continue
    text = case["judgmentText"]
    idx = text.find(quote)
    if idx != -1:
        print(f"[EXACT MATCH] {cid}: found at character offset {idx} (length: {len(quote)} chars)")
    else:
        print(f"[MISMATCH] {cid}: quote not found exactly as string! Searching for partial matches...")
        # debug
        for line in quote.split("\n"):
            line_str = line.strip()
            if line_str and line_str not in text:
                print(f"   Line missing: '{line_str}'")
