# JURIST AI — Judicial Outcome Annotation Protocol & Quality Guidelines

**Version:** 1.0.0 (Feature 4.3 Human-in-the-Loop Verification)  
**Target Domain:** Indian Judicial Decisions (Supreme Court of India, High Courts)  
**Audience:** Legal Annotators, Domain Experts, ML Quality Engineers  
**Dataset Reference:** [`ml-service/app/datasets/open_india_law_sample_150.json`](file:///c:/Users/Gungun/Downloads/Jurist-AI-Team/ml-service/app/datasets/open_india_law_sample_150.json)

---

## 1. Objective and Operating Principles

This protocol governs the human verification of provisional candidate judicial dispositions extracted by the automated extraction engine (`label_extractor.py`).

### Core Annotation Mandates:
1. **Never Assume Ground Truth:** Machine-extracted candidates are provisional suggestions only. An automated candidate label must never be used for supervised model training without explicit human reviewer sign-off.
2. **Grounded in Final Operative Text Only:** Dispositions must reflect the bench's concluding holding, not historical trial court orders, party prayers, or hypothetical conditional reasoning.
3. **No Universal Binary Reduction:** Indian court rulings cannot be collapsed into a naive `Allowed / Dismissed` binary. Procedural posture, bail liberty, quashing, remand, and infructuous disposals carry distinct legal consequences.
4. **Party Context Determines Success:** An *"appeal dismissed"* is favorable to the accused when the State is the appellant, but unfavorable to the accused when the accused appealed against conviction.

---

## 2. Defining Operative Dispositions vs Interlocutory Orders

### 2.1. Final Operative Dispositions
A **final operative disposition** disposes of the appeal, petition, or application on its merits or through a final conclusive procedural order that terminates the proceedings before that court.

**Typical Concluding Formulations:**
- *"In the result, the appeal is allowed and the judgment of conviction is set aside."*
- *"We find no ground to interfere. The appeal fails and is dismissed."*
- *"Accordingly, the applicant is directed to be released on bail on furnishing a personal bond..."*
- *"FIR No. 101/2020 and all consequential proceedings emanating therefrom are hereby quashed."*
- *"With the aforesaid directions, the writ petition is finally disposed of."*

### 2.2. Interlocutory & Non-Dispositive Orders (Mark as `unknown` or `interlocutory_reference`)
Do not assign a merits outcome to orders that do not finally resolve the proceeding:
- **Reference to Larger Bench:** *"In view of conflicting two-judge bench decisions, let these papers be placed before Hon'ble the Chief Justice for constitution of a Larger Bench."* (e.g. `OIL-SC-2015_INSC_559` Puttaswamy interim Aadhaar order).
- **Framing of Questions / Notice:** Orders framing questions of law or issuing notice to respondents without a final holding.
- **Interim Stay Pending Hearing:** *"Interim protection granted on 12.01.2021 shall continue until the next date of hearing."*
- **Text Truncation:** If the judgment text was capped at 40,000 characters during ingestion and the concluding order is missing, annotators must label the record `unknown` (sub-reason: `deferred_needs_full_text`) rather than guessing from earlier text.

---

## 3. Detailed Category Classification Rules

### 3.1. Appeals (`appeal_allowed`, `appeal_dismissed`)
- **`appeal_allowed`**:
  - The appellate court reverses, modifies, or sets aside the decree, conviction, or order appealed against.
  - *Applicability:* Criminal Appeals (BNSS / CrPC), Civil Appeals (CPC), Special Leave Appeals (Art. 136).
- **`appeal_dismissed`**:
  - The appellate court rejects the appeal and affirms the judgment of the lower court.
  - *Critical Rule on Party Success:* Check whether the appellant is the **State** or the **Accused**.
    - If State v. Accused $\to$ State Appeal Dismissed = **Favorable to Accused** (`favorable_to_accused`).
    - If Accused v. State $\to$ Accused Appeal Dismissed = **Unfavorable to Accused** (`unfavorable_to_accused`).

### 3.2. Bail Applications (`bail_granted`, `bail_rejected`)
- Bail applications (under Sections 437, 438, 439 CrPC or Sections 480, 482, 483 BNSS) address provisional liberty, **not guilt or innocence**.
- **`bail_granted`**: Accused is admitted/enlarged on regular bail, anticipatory bail, or interim bail.
  - *Successful Party:* `accused` / `applicant`.
  - *Legal Status:* Does NOT constitute acquittal or quashing of charges.
- **`bail_rejected`**: Bail application is dismissed, rejected, or refused.
  - *Successful Party:* `state_prosecution`.

### 3.3. Quashing Petitions (`proceedings_quashed`)
- Inherent jurisdiction petitions under Section 482 CrPC (or Section 528 BNSS) / Article 226 seeking quashing of FIR, charge-sheet, or criminal complaints.
- **`proceedings_quashed`**: Assigned only when the High Court terminates the criminal proceedings or FIR against the accused/petitioner.
  - *Successful Party:* `accused` / `petitioner`.

### 3.4. Partly Allowed Matters (`partly_allowed`)
- Assigned when relief is granted in part and denied in part:
  - Conviction under Section 302 IPC (Murder) is altered/reduced to Section 304 Part I (Culpable Homicide), and sentence reduced from life imprisonment to 10 years (e.g. `OIL-SC-2023_INSC_1034`).
  - Compensation in motor accident claims (MAC.APP.) is enhanced or reduced, but liability maintained.
  - Fine is set aside while imprisonment is sustained.
- *Successful Party:* Record as `unresolved` / `partial_relief` — do not force into win/loss binary.

### 3.5. Remand Orders (`remanded`)
- The appellate/revisional court sets aside the impugned decision without deciding the dispute on merits, and sends the case back to the subordinate court for fresh adjudication.
  - *Formulation:* *"The matter is remanded back to the High Court for fresh disposal in accordance with law."*
  - *Successful Party:* Record as `none_procedural` or `unresolved`.

### 3.6. Disposals with Directions (`disposed_with_directions`)
Disposals under writ or inherent jurisdiction must be divided into three distinct sub-types:
1. **`disposed_with_substantive_directions`**:
   - The court directs public authorities to perform a duty, grant protection, or decide a representation within a set time frame (e.g. police directed to protect matrimonial petitioners; representation directed to be decided in 60 days).
   - *Successful Party:* `petitioner` (substantive relief obtained).
2. **`dismissed_as_infructuous` / `disposed_as_infructuous`**:
   - The cause of action has ceased to exist by efflux of time or subsequent compliance (e.g., detenue already released; investigation concluded; election term completed).
   - *Successful Party:* `none_procedural`.
3. **`disposed_procedural`**:
   - Generic procedural closure without substantive relief or explicit directions.

### 3.7. Withdrawn Petitions (`withdrawn`)
- The petitioner or appellant requests and is granted leave to withdraw the proceedings (e.g. *"Counsel seeks leave to withdraw. The petition is dismissed as withdrawn."*).
- *Successful Party:* `unresolved` / `none_procedural`.

---

## 4. Handling Unknown and Ambiguous Cases

### 4.1. When to Use `unknown`
Assign `unknown` when:
1. The judgment text in the dataset is truncated before the final operative order (e.g. text length is $\ge 39,900$ characters).
2. The judgment ends mid-sentence or lacks a final holding.
3. The order is an interlocutory reference to a Larger Bench or notice-stage proceeding.
4. The text discusses legal philosophy or statutory interpretation without an order concluding the underlying case.

### 4.2. When to Use `ambiguous`
Assign `ambiguous` when:
1. Contradictory orders appear in the same case (e.g. Appeal No. 1 is allowed, but Appeal No. 2 is dismissed, without an overall unifying holding).
2. The text contains both *"allowed"* and *"dismissed"* in hypothetical or conditional phrasing that cannot be safely resolved without external primary judgment verification.

### 4.3. When to Use `rejected`
Mark a candidate label as `rejected` in `review_status` when the automated extractor made a clear false-positive error (e.g. extractor labeled an order `appeal_allowed` based on historical quotation of a lower court holding, whereas the actual High Court dismissed the appeal).

---

## 5. Party Success & Legal Role Mapping Matrix

| Proceeding Type | Petitioner / Appellant Identity | Court Ruling | Candidate Label | Successful Party (`human_successful_party`) | Suitable for Supervised Outcome Training? |
| :--- | :--- | :--- | :--- | :--- | :---: |
| Criminal Appeal | Accused | Appeal Allowed | `appeal_allowed` | `accused` | **Yes** |
| Criminal Appeal | Accused | Appeal Dismissed | `appeal_dismissed` | `state_prosecution` | **Yes** |
| Criminal Appeal | State / Prosecution | Appeal Dismissed | `appeal_dismissed` | `accused` | **Yes** |
| Criminal Appeal | State / Prosecution | Appeal Allowed | `appeal_allowed` | `state_prosecution` | **Yes** |
| Bail Application | Accused / Applicant | Bail Granted | `bail_granted` | `accused` | **Yes** (Bail specific) |
| Bail Application | Accused / Applicant | Bail Rejected | `bail_rejected` | `state_prosecution` | **Yes** (Bail specific) |
| Section 482 Petition | Accused | Proceedings Quashed | `proceedings_quashed` | `accused` | **Yes** |
| Writ Petition | Citizen / Detenu | Petition Allowed | `petition_allowed` | `petitioner` | **Yes** |
| Writ Petition | Citizen | Petition Dismissed | `petition_dismissed` | `respondent` | **Yes** |
| Any Criminal Case | Accused | Partly Allowed | `partly_allowed` | `unresolved` | **No** (Exclude or distinct class) |
| Any Proceeding | Either | Remanded | `remanded` | `none_procedural` | **No** (Procedural) |
| Any Proceeding | Petitioner | Dismissed as Infructuous | `dismissed_as_infructuous` | `none_procedural` | **No** (Mootness) |
| Any Proceeding | Petitioner | Dismissed as Withdrawn | `withdrawn` | `none_procedural` | **No** (Voluntary withdrawal) |
| Any Proceeding | Unknown / Truncated | Truncated / Capped | `unknown` | `unresolved` | **No** (Insufficient evidence) |

---

## 6. Human Review CSV Field Instructions

Annotators must complete the review spreadsheet [`outcome_label_review_v2.csv`](file:///c:/Users/Gungun/Downloads/Jurist-AI-Team/ml-service/app/datasets/outcome_label_review_v2.csv) according to these instructions:

1. **`review_status`**: Update from `"pending_review"` to:
   - `"approved"` (if candidate disposition and party success are fully correct).
   - `"corrected"` (if candidate disposition was adjusted or normalized).
   - `"rejected"` (if candidate disposition was completely invalid).
   - `"deferred_needs_full_text"` (if judgment text is truncated or missing).
2. **`human_approved_label`**: Enter the verified normalized disposition category from Section 3.
3. **`human_successful_party`**: Enter `accused`, `state_prosecution`, `petitioner`, `respondent`, `none_procedural`, or `unresolved`.
4. **`human_notes`**: Record brief justification (e.g., *"State appeal against acquittal dismissed; respondent acquitted"*, *"Conviction converted from 302 to 304 Part I"*, *"Text truncated at 40k cap; full order verified on Supreme Court website"*).
5. **`reviewer_reference`**: Enter reviewer initials and date (e.g. `JD-2026-11-13`).

---

## 7. Sign-off and Data Quality Checklist

Before finalizing any verified batch:
- [ ] Has every candidate disposition been verified against the exact concluding paragraph?
- [ ] Has the appellant's role (State vs Accused) been verified before determining party success?
- [ ] Have infructuous dismissals been distinguished from merits dismissals?
- [ ] Have truncated judgments been deferred rather than guessed?
- [ ] Have partial allowances been prevented from entering binary win/loss models?
