# JURIST AI — Final Demonstration & Academic Viva Presentation Script
**Project Title:** JURIST AI — AI-Powered Legal Intelligence & Litigation Workstation  
**Demonstration Length:** 15–20 Minutes  
**Audience:** Final-Year Engineering Project Evaluation Committee, External Examiners & Legal Domain Experts  
**Presenters:** Project Engineering Team  
**System Endpoints:**
- Frontend Workstation: `http://localhost:5173`
- Backend API Gateway: `http://localhost:5001`
- ML & Legal Intelligence Service: `http://localhost:8000`
- Database: MongoDB Atlas Sharded Cloud Cluster

---

## Stage-by-Stage Viva Demonstration Protocol

### STAGE 1: System Introduction & Architectural Philosophy (1 Minute)
- **Presenter Action:** Open browser to `http://localhost:5173`. Show the landing page and terminal dashboard indicating three operational microservices.
- **UI Observation:** Professional dark-navy and ivory legal workstation interface. Live status indicator shows all services connected.
- **Spoken Explanation:**
  > "Respected members of the committee, generic AI tools like ChatGPT or standard RAG pipelines fail critically in Indian law. They hallucinate non-existent Supreme Court citations, stuff thousands of confusing judgment pages into prompts, miss the July 2024 transition from IPC/CrPC to BNS/BNSS, and invent deceptive 'win percentages'. JURIST AI is an ethical, date-aware, and explainable legal intelligence workstation built specifically for Indian litigators. Our architecture strictly decouples precedent retrieval from LLM generation, ensuring zero hallucination and complete empirical traceability."
- **Technical & Legal Concept:** Decoupled multi-tier microservice architecture; Elimination of Retrieval-Augmented Generation (No-RAG paradigm) to prevent ratio decidendi conflation.

---

### STAGE 2: Litigator Registration & Multi-Tenant Authentication (1 Minute)
- **Presenter Action:** Click **Register**. Create account for `Advocate Ramesh Sharma` (`ramesh.sharma@delhibar.in`, Bar Enrollment: `D/1428/2015`, Password: `Password@123`). Click **Create Account**.
- **UI Observation:** Instant authentication; user redirected to `/dashboard/new` with a welcome banner displaying the advocate's enrollment credentials. JWT bearer token saved in encrypted browser storage.
- **Spoken Explanation:**
  > "Every advocate's chamber requires strict multi-tenant confidentiality. JURIST AI enforces stateless JSON Web Token authentication with bcrypt password hashing. All subsequent legal dossiers, uploaded evidentiary documents, and chamber research notes are cryptographically partitioned by user ID at both the API and database levels."
- **Technical & Legal Concept:** Stateless JWT Authentication; Horizontal privilege isolation; Section 126 Indian Evidence Act / Section 132 Bharatiya Sakshya Adhiniyam advocate-client confidentiality.

---

### STAGE 3: Matter Intake — Post-July 2024 Criminal Arrest Challenge (1.5 Minutes)
- **Presenter Action:** On `/dashboard/new`, fill out the intake form:
  - **Case Title:** `Bail & Remand Legality Challenge — Midnight Arrest without Written Grounds`
  - **Jurisdiction:** `High Court of Delhi`
  - **Case Category:** `Criminal Law`
  - **Procedural Posture:** Select `Post-Arrest / Custodial Remand`
  - **Narrative Text:** Paste sample facts:
    > *"An incident occurred on 2 August 2024 and FIR was registered on 5 August 2024. On 10 August 2024 at 23:30 hrs, the police arrested the Applicant from his residence without serving any written grounds of arrest under Article 22(1) or Section 47 BNSS. He was detained at the police station for 30 hours before being produced before the Judicial Magistrate, who remanded him to police custody without recording reasons."*
  - Attach sample document: `arrest_memo_fir_exhibit.pdf`.
  - Click **Analyze Matter & Generate Intelligence**.
- **UI Observation:** Progress indicator displays dynamic pipeline stages: Document Parsing $\rightarrow$ Script Classification $\rightarrow$ Fact Extraction $\rightarrow$ Hybrid Precedent Retrieval $\rightarrow$ Direct Pleading Generation $\rightarrow$ Citation Grounding.
- **Spoken Explanation:**
  > "Notice the dates we entered: the incident occurred in August 2024. Under Section 531 of the new Bharatiya Nagarik Suraksha Sanhita (BNSS), any FIR registered after July 1, 2024 must be governed by the BNSS, not the repealed 1973 CrPC. Our system automatically parses these temporal markers."
- **Technical & Legal Concept:** Date-aware statutory transition engine; Temporal regex extraction; Multipart stream intake.

---

### STAGE 4: Real-Time Document Intelligence & Multimodal OCR (1.5 Minutes)
- **Presenter Action:** Navigate to the **Document Intelligence** tab of the newly generated dossier.
- **UI Observation:**
  - File Metadata: `arrest_memo_fir_exhibit.pdf`, 2 Pages, Digital Native + OCR Scanned.
  - Diagnostic Table: Page 1 (Native Digital, 100% confidence), Page 2 (Scanned Order Sheet, 94.6% confidence).
  - Uncertain Token Chips: Demonstrates flagged low-confidence words (e.g. `[?malkhana?]`, `[?challan?]`).
- **Spoken Explanation:**
  > "Indian court filings are notoriously messy, containing mixtures of digital petitions and faded photocopies of police memos. JURIST AI's document pipeline automatically classifies each page as digital native or scanned. For scanned pages, it audits Character Error Rate (CER). If an OCR token falls below 75% confidence, it is marked with `[?token?]` chips, warning counsel to cross-examine physical manuscripts before quoting them in court."
- **Technical & Legal Concept:** Hybrid PyMuPDF / OpenCV / Tesseract OCR pipeline; Character Error Rate (CER) and Word Error Rate (WER) diagnostics; Evidentiary uncertainty tagging.

---

### STAGE 5: Bilingual Legal Translation Workspace (1 Minute)
- **Presenter Action:** In the Document Intelligence tab, click the **Multilingual Document Intelligence (English • हिन्दी)** control. Select **Translate into Hindi**, then toggle **Side-by-Side** view.
- **UI Observation:** Side-by-side pane rendering original English on the left and fluent Hindi legal translation on the right. Point out that `Section 47 BNSS`, `Article 22(1)`, and dates remain intact.
- **Spoken Explanation:**
  > "In district courts across North India, vernacular Hindi FIRs and statements are standard. Generic translation APIs frequently butcher legal citations—translating 'Section 138' into meaningless Hindi words. JURIST AI uses regex-anchored token shielding to guarantee 100% preservation of statutory provisions, case citations, and monetary amounts while providing fluent Devanagari translation."
- **Technical & Legal Concept:** Token shielding algorithm; Bilingual legal dictionary mapping; Legal review tag compliance.

---

### STAGE 6: Fact Classification & Procedural Posture Analysis (1 Minute)
- **Presenter Action:** Scroll down to the **Case Understanding & Fact Intelligence** section.
- **UI Observation:**
  - Facts categorized into distinct color-coded badges: **Neutral Chronological Facts** vs. **Party Allegations**.
  - Custody Status: Automatically tagged as `in_custody_arrested`.
  - Available Remedies: `Challenge to Remand Legality (Vihaan Kumar / Prabir Purkayastha principles)` and `Regular Bail under Section 480 BNSS`.
  - Notice alert: *"Anticipatory bail is NOT maintainable as accused is already in custody."*
- **Spoken Explanation:**
  > "One of the most dangerous errors junior advocates make is filing for anticipatory bail when the client is already arrested. Our procedural posture analyzer recognizes that custodial arrest has occurred, warns against invalid remedies, and directs counsel immediately toward habeas corpus and remand illegality challenges."
- **Technical & Legal Concept:** Semantic fact classification; Procedural posture state machine; Evidentiary gap auditing.

---

### STAGE 7: Questions of Law & Statutory Transition Logic (1 Minute)
- **Presenter Action:** Direct attention to the **Questions of Law Formulated** card.
- **UI Observation:**
  - Question 1: *"Whether failure to furnish written grounds of arrest to the arrestee prior to remand violates Article 22(1) and vitiates subsequent custody?"*
  - Statutory Provision: `Article 22(1), Constitution of India read with Section 47, Bharatiya Nagarik Suraksha Sanhita, 2023`.
  - Transitional Note: Accurately identifies that CrPC Section 50 is replaced by Section 47 BNSS for post-July 2024 matters.
- **Spoken Explanation:**
  > "The engine formulates the exact questions of law that an appellate judge will adjudicate. Most importantly, it applies Section 47 of the BNSS rather than the legacy CrPC, completely avoiding statutory anachronism."
- **Technical & Legal Concept:** Natural Language Legal Problem Formulation; Rule-based statutory transition resolver.

---

### STAGE 8: Independent Hybrid Precedent Retrieval (1.5 Minutes)
- **Presenter Action:** Click the **Judicial Treatment & Precedent Retrieval** tab.
- **UI Observation:**
  - Top retrieved precedents displayed:
    1. *Prabir Purkayastha v. State (NCT of Delhi)* [2024 INSC 412] — Supreme Court of India.
    2. *Arnesh Kumar v. State of Bihar* [(2014) 8 SCC 273] — Supreme Court of India.
    3. *Satender Kumar Antil v. CBI* [(2022) 10 SCC 51] — Supreme Court of India.
  - Multi-Modal Signal Badge: `TF-IDF Rank #1 | BM25 Rank #2 | Dense BGE-small Rank #1 | Combined RRF Score: 0.048`.
- **Spoken Explanation:**
  > "Here is our independent retrieval engine at work. It simultaneously evaluates lexical frequency (TF-IDF), term saturation (Okapi BM25), and deep semantic embeddings using a locally quantized BGE-small transformer. Through Reciprocal Rank Fusion, it achieves 96.67% recall, correctly surfacing Prabir Purkayastha—the definitive 2024 Supreme Court authority on written grounds of arrest."
- **Technical & Legal Concept:** Three-Way Hybrid Search; Dense BGE ONNX inference; Reciprocal Rank Fusion ($k=60$).

---

### STAGE 9: Strict Citation Grounding & Anti-Hallucination Audit (1.5 Minutes)
- **Presenter Action:** Point to the **Official Verified** badge next to *Prabir Purkayastha*. Click the **Official SCI PDF** link.
- **UI Observation:** The browser opens the authentic Supreme Court of India digital portal (`https://digiscr.sci.gov.in`). Show that the citation, bench composition, and paragraph references match the primary court record.
- **Spoken Explanation:**
  > "Notice this green 'Official Verified' badge. JURIST AI never hallucinates citations. Every cited authority is checked against our 176-case verified Indian legal corpus. If an LLM ever suggests a citation not in the verified corpus, JURIST AI flags it with an amber 'Corpus Unverified Citation' warning badge. We never silently substitute landmark cases for unverified authorities."
- **Technical & Legal Concept:** Citation Grounding Validator; Normalized citation regex index; Strict anti-hallucination safeguard.

---

### STAGE 10: Direct AI Pleadings Generation Without RAG (1.5 Minutes)
- **Presenter Action:** Click the **Legal Arguments & Pleadings** tab. Expand **Ground I: Vitiation of Arrest & Remand**.
- **UI Observation:**
  - Ground Heading, Constitutional Proposition, Relevant Facts, Supporting Precedent, and Suggested Court Submission.
  - Callout: *"DRAFT LEGAL SUBMISSION: IT IS MOST RESPECTFULLY SUBMITTED that the arrest and subsequent remand of the Petitioner are patently illegal and void ab initio, being in direct violation of Article 22(1) of the Constitution and Section 47 of the BNSS, 2023..."*
- **Spoken Explanation:**
  > "This pleading was generated via our No-RAG direct generation pipeline. The LLM received only the structured facts, custody posture, and statutory provisions. It did NOT receive retrieved precedent text in its prompt, eliminating context window bloat and preventing ratio mixing. The resulting pleading reads like an experienced Supreme Court advocate's chamber draft."
- **Technical & Legal Concept:** No-RAG Prompt Purity; High-precision structured few-shot legal prompting; Deterministic template parity.

---

### STAGE 11: Adversarial Counterarguments & Vulnerability Audit (1 Minute)
- **Presenter Action:** Inside Ground I, scroll down to the **Adversarial Counterarguments Matrix**.
- **UI Observation:**
  - Opposing Ground: *"Substantial Compliance and Oral Information at Remand"*
  - Legal Basis: Doctrine of substantial compliance.
  - Factual Basis: Prosecution will argue that remand application was read out in open court.
  - Vulnerability Assessment: Moderate vulnerability if Magistrate's order sheet notes counsel's presence.
  - Rebuttal Strategy: Cite *Prabir Purkayastha* holding that oral communication or reading remand orders does not satisfy personal written service upon the arrestee.
- **Spoken Explanation:**
  > "A complete legal briefing tool must prepare advocates for what the Public Prosecutor will argue. JURIST AI generates realistic opposing counterarguments, assesses case vulnerabilities, and arms litigators with pre-emptive rebuttal strategies."
- **Technical & Legal Concept:** Adversarial perspective modeling; Vulnerability risk quantification.

---

### STAGE 12: Dual Experimental Outcome Prediction Panel (1.5 Minutes)
- **Presenter Action:** Click on the **Outcome & Disposition Meter** tab.
- **UI Observation:**
  - Dual Cards:
    - **Model A (Judicial Disposition):** Estimated Ruling: `Petition Allowed` (Correlation Score: 42%). Macro-F1: 0.256, N=43. Precedent correlation distribution across 4 classes.
    - **Model B (Prevailing Party):** Estimated Party: `Petitioner` (Correlation Score: 58%). Macro-F1: 0.366, N=37.
  - Prominent Disclaimers: *"Experimental prototype trained on 46 human-verified Indian judgments with target leakage sanitization. Uncalibrated scores represent historical precedent vocabulary correlations rather than empirical win probabilities or legal advice."*
- **Spoken Explanation:**
  > "Notice what is NOT on this screen: there is NO deceptive '85% Win Probability' bar. Legal outcomes cannot be reduced to binary betting odds. We deploy two decoupled experimental classifiers: Model A predicts disposition, while Model B predicts prevailing party. Both are trained with target leakage sanitization—decretal orders were stripped prior to training. Where cases are civil or non-adversarial, Model B explicitly abstains."
- **Technical & Legal Concept:** Target leakage sanitization; 5-fold Stratified Group Cross-Validation; Decoupled classification; Domain abstention.

---

### STAGE 13: Interactive Evidence Traceability Graph (1 Minute)
- **Presenter Action:** Switch to the **Evidence Traceability** tab.
- **UI Observation:** Interactive node graph rendering: `Document Page 1 (FIR Memo)` $\rightarrow$ `Fact (Arrest at 23:30)` $\rightarrow$ `Question of Law (Written Grounds)` $\rightarrow$ `Statute (Article 22(1) / S. 47 BNSS)` $\rightarrow$ `Precedent (Prabir Purkayastha)` $\rightarrow$ `Ground I Pleading`.
- **Spoken Explanation:**
  > "Every legal argument in JURIST AI is mathematically and visually grounded. Through this Evidence Trace Graph, a judge or senior counsel can trace any sentence in our draft submission back to the exact page of the uploaded FIR, the governing statute, and the binding Supreme Court authority."
- **Technical & Legal Concept:** Explainable AI (XAI); Directed Bipartite Evidence Graphs; Provenance tracking.

---

### STAGE 14: Editable Dossier, Chamber Notes & MongoDB Atlas Live Persistence (1.5 Minutes)
- **Presenter Action:**
  1. Scroll to **Chamber Research Notes**. Type: *"Note: Summon General Diary entry register from PS Cyber Crime to disprove oral notice."*
  2. In Ground I, click **Edit Draft Submission**. Modify the text.
  3. Click **Save Modifications & Notes**.
  4. Navigate to **Case History** (`/dashboard/history`).
- **UI Observation:**
  - Case History displays the newly saved dossier. Persistence badge shows: `MongoDB Atlas Live Sharded Cluster`.
  - Open the dossier: Chamber notes and edited draft text are perfectly preserved.
- **Spoken Explanation:**
  > "Litigation is iterative. Advocates modify drafts and add chamber notes over months. All modifications are persisted to a live MongoDB Atlas sharded cloud database. If cloud connectivity is ever severed, our system transparently falls back to session-bound memory without crashing."
- **Technical & Legal Concept:** RESTful PATCH API; MongoDB Atlas sharded cloud persistence; High-availability fallback.

---

### STAGE 15: Cross-User Security Guard & Simulated Microservice Resiliency (1.5 Minutes)
- **Presenter Action:**
  1. Copy the current dossier URL (`/dashboard/analysis/<id>`).
  2. Click **Logout**.
  3. Register or log in as **User B** (`Advocate Priya Singh`, `priya.singh@delhibar.in`).
  4. Attempt to paste and navigate directly to User A's dossier URL.
- **UI Observation:** The application rejects access with a clean `404 Dossier Not Found or Access Denied` alert. User B's Case History shows zero records.
- **Spoken Explanation:**
  > "To conclude our demonstration, notice that when Advocate Priya Singh attempts to access Advocate Ramesh Sharma's case URL, she is blocked immediately with a 404 access denial. Neither the frontend nor the backend leaks client metadata. JURIST AI is hardened, secure, legally grounded, and ready for deployment."
- **Technical & Legal Concept:** Horizontal data isolation; Zero-trust multi-tenancy; Graceful microservice failover.
