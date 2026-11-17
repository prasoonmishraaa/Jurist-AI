import json
from app.prediction.verified_outcome_model import VerifiedOutcomePredictor

predictor = VerifiedOutcomePredictor()

# 1. Test OIL-SC-2021_INSC_327
with open('app/datasets/open_india_law_sample_150.json', 'r', encoding='utf-8') as f:
    sample_cases = {c['id']: c for c in json.load(f)}

c1 = sample_cases.get('OIL-SC-2021_INSC_327')
if c1:
    res1 = predictor.predict_outcome(c1['judgmentText'], category='Criminal Law')
    print("=== OIL-SC-2021_INSC_327 (State of UP v. Dr. Manoj Kumar Sharma) ===")
    print("Model A:", res1.get('modelA', {}).get('prediction'), res1.get('modelA', {}).get('uncalibratedScores'))
    print("Model B:", res1.get('modelB', {}).get('prediction'), res1.get('modelB', {}).get('uncalibratedScores'))

# 2. Test Aarav Mehta variants
texts = {
    "Aarav Mehta Narrative 1 (e2e-probe)": (
        "The applicant was arrested on 15 August 2024 for alleged offences under Sections 318(4) and 316(2) of the "
        "Bharatiya Nyaya Sanhita 2023. Investigating officer did not serve notice under Section 35 of the "
        "Bharatiya Nagarik Suraksha Sanhita 2023 prior to custodial arrest. Applicant seeks regular bail under Section 480 BNSS 2023."
    ),
    "Aarav Mehta Narrative 2 (dualModelOutcome test)": (
        "An offence was alleged on 5 October 2024 in a commercial supply dispute. "
        "FIR was registered on 10 October 2024 alleging cheating and dishonestly inducing delivery of property. "
        "Police arrested the Accused Aarav Mehta on 14 October 2024 without serving pre-arrest notice, "
        "did not communicate written grounds of arrest under Article 22(1) / Section 47 BNSS, "
        "and produced him before the Magistrate beyond 24 hours for remand."
    ),
    "Aarav Mehta Narrative 3 (with Writ title/text)": (
        "IN THE HIGH COURT OF JUDICATURE AT BOMBAY\nCRIMINAL APPELLATE JURISDICTION\n"
        "WRIT PETITION (CRIMINAL) NO. 450 OF 2024\n"
        "Aarav Mehta ... Petitioner\nVersus\nState of Maharashtra ... Respondent\n\n"
        "The petitioner was arrested on 15 August 2024 for alleged offences under Sections 318(4) and 316(2) of BNS 2023. "
        "The investigating officer failed to furnish written grounds of arrest contrary to Article 22(1) and Section 47 BNSS. "
        "The remand order was passed mechanically by the Magistrate. The petitioner prays for a writ of habeas corpus or quashing."
    ),
    "Aarav Mehta Narrative 4 (Criminal Appeal / Bail Appeal)": (
        "IN THE HIGH COURT OF JUDICATURE AT BOMBAY\nCRIMINAL APPELLATE JURISDICTION\n"
        "CRIMINAL APPEAL NO. 450 OF 2024\n"
        "Aarav Mehta ... Appellant\nVersus\nState of Maharashtra ... Respondent\n\n"
        "This Criminal Appeal is filed challenging the rejection of bail by the Sessions Court. "
        "The appellant was arrested on 15 August 2024 under Sections 318(4) and 316(2) BNS 2023. "
        "The investigating officer violated Section 35 BNSS. The appellant seeks regular bail."
    ),
    "Aarav Mehta Narrative 5 (Arrest brief alone)": (
        "Criminal arrest and remand brief: Aarav Mehta was arrested by police in FIR No. 112/2024 under Section 318(4) BNS. "
        "No grounds of arrest served in writing. Remanded to judicial custody. Seeking release."
    )
}

for name, t in texts.items():
    for cat in ['Criminal Law', 'criminal', 'Constitutional Law', 'Civil Writ', None]:
        res = predictor.predict_outcome(t, category=cat)
        mA = res.get('modelA', {})
        mB = res.get('modelB', {})
        if mA.get('prediction') == 'appeal_dismissed' or mB.get('prediction') == 'respondent':
            print(f"\n--- MATCH FOUND: {name} (cat: {cat}) ---")
            print("Domain:", res.get('domainDetected'))
            print("Model A pred:", mA.get('prediction'), "Scores:", mA.get('uncalibratedScores'))
            print("Model A raw:", mA.get('rawScores'))
            print("Model B pred:", mB.get('prediction'), "Scores:", mB.get('uncalibratedScores'))
            print("Model B raw:", mB.get('rawScores'))
