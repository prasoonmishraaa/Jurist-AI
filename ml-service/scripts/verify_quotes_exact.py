import json
from pathlib import Path

with open("ml-service/app/datasets/open_india_law_sample_150.json", "r", encoding="utf-8") as f:
    source_cases = {c["id"]: c for c in json.load(f)}

# Case 3
jtext_3 = source_cases["OIL-SC-2007_INSC_1082"]["judgmentText"]
# Find the exact ending
idx_3 = jtext_3.find("For the reasons aforementioned the impugned judgment cannot be")
print("Case 3 index:", idx_3)
slice_3 = jtext_3[idx_3:]
print("Case 3 tail slice:")
print(repr(slice_3))

# Let's isolate the operative holding without [SECTION] ## Appeal allowed.
# Find where [SECTION] starts or where Rs. 25,000/- ends
idx_3_end = slice_3.find("Rs. 25,000/-.")
if idx_3_end != -1:
    exact_contiguous_3 = slice_3[:idx_3_end + len("Rs. 25,000/-.")].strip()
    print("\nCase 3 exact contiguous clean quote:")
    print(repr(exact_contiguous_3))
    print("Is exact_contiguous_3 in jtext_3?", exact_contiguous_3 in jtext_3)

# Case 4
jtext_4 = source_cases["OIL-SC-2003_INSC_88"]["judgmentText"]
idx_4 = jtext_4.find("In these circumstances, we dismiss the appeals without")
print("\nCase 4 index:", idx_4)
slice_4 = jtext_4[idx_4:]
print("Case 4 tail slice:")
print(repr(slice_4))

# Let's isolate the contiguous quote:
# "In these circumstances, we dismiss the appeals without ariy order as to costs.\n\nD N.J.\n\nAppeals dismissed."
idx_4_end = slice_4.find("Appeals dismissed.")
if idx_4_end != -1:
    exact_contiguous_4 = slice_4[:idx_4_end + len("Appeals dismissed.")].strip()
    print("\nCase 4 exact contiguous quote:")
    print(repr(exact_contiguous_4))
    print("Is exact_contiguous_4 in jtext_4?", exact_contiguous_4 in jtext_4)
