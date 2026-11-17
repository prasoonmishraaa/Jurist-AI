import json

with open("ml-service/app/datasets/open_india_law_sample_150.json", "r", encoding="utf-8") as f:
    source_cases = {c["id"]: c for c in json.load(f)}

# 1. Case 1
q1 = "For the foregoing reasons, we do not differ from the view taken by the High Court in maintaining the conviction of the appellant. The appeal therefore fails and is hereby dismissed. The appellant is on bail. He shall surrender to his bail bonds."
print("Case 1 in text?", q1 in source_cases["OIL-SC-1996_INSC_503"]["judgmentText"])

# 2. Case 2
q2 = "we are of the opinion that the impugned judgment cannot be sustained and this should be set aside and the matter be remitted to the High Court for consideration of the Second Appeal afresh after formulating an appropriate substantial question of law arising, if any. The appeal is allowed."
print("Case 2 in text?", q2 in source_cases["OIL-SC-2007_INSC_31"]["judgmentText"])

# 3. Case 3
q3 = "For the reasons aforementioned the impugned judgment cannot be c sustained. The appeal is allowed. We, however, before taking any punitive action against the contemnors at this stage, would like to issue a direction upon them to fully implement the orders of this Court as modified by this Court on the same terms as was done in the case of employees similarly D situated. In facts and circumstances of the case the appellants shall also be entitled to costs which we quantify at Rs. 25,000/-."
print("Case 3 in text?", q3 in source_cases["OIL-SC-2007_INSC_1082"]["judgmentText"])

# 4. Case 4
q4 = "In these circumstances, we dismiss the appeals without ariy order as to costs.\n\nD N.J.\n\nAppeals dismissed."
print("Case 4 in text?", q4 in source_cases["OIL-SC-2003_INSC_88"]["judgmentText"])

# 5. Case 5
q5 = "For these reasons we set aside ihe order of detention. We had ear· lier directed on the conclusion of the arguments that the petitioner be set at liberty forthwith."
print("Case 5 in text?", q5 in source_cases["OIL-SC-1973_INSC_203"]["judgmentText"])
