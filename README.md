# JURIST AI

**Indian Legal Research, Statutory Mapping & Litigation Support Workspace**

**JURIST AI** is a web platform for advocates, judicial researchers, and law students preparing structured legal research and draft court submissions in Indian law. It transforms raw factual narratives and uploaded documents (`.pdf`, `.docx`, `.txt`) into organized chronologies, date-aware legislation analyses (pre- vs. post-1 July 2024 codes), source-verified Supreme Court and High Court authorities under Article 141, editable draft grounds, and anticipated opposing arguments with rebuttals.

---

## Core Capabilities

1. **Fact vs. Allegation Structuring & Evidence Audit**
   - Separates user-provided facts, unproved party allegations, reasonable inferences, and missing dates/records without fabricating litigant names.
   - Identifies custody posture (`in_custody_arrested`, `apprehending_arrest`, `released_on_bail`, `civil_or_non_custodial`) before outlining maintainable legal remedies.
   - Extracts text from searchable `.pdf`, `.docx`, and `.txt` uploads and rejects empty or image-only scanned PDFs with clear error guidance.

2. **Date-Aware Legislation Engine (IPC/CrPC/IEA vs. BNS/BNSS/BSA)**
   - Extracts offence, FIR, arrest, and remand dates against the **1 July 2024** commencement cutoff.
   - Separates substantive law (**IPC 1860** vs. **BNS 2023**), procedural safeguards (**CrPC 1973** vs. **BNSS 2023**, including Section 35 pre-arrest notice, Section 47 written grounds of arrest, Section 58 / 187 remand timelines, and Section 531 transitional savings), and evidence law (**IEA 1872** vs. **BSA 2023**).

3. **Source-Verified Precedent Corpus (27 Landmark Rulings)**
   - Centralized source registry (`backend/src/utils/judgmentRegistry.ts` and `ml-service/app/datasets/indian_judgments.json`).
   - Transparently displays **`Official Source Verified`** for live-verified court PDFs (`10` records) and **`Official source not verified`** with secondary Indian Kanoon reference links (`17` records).
   - Provides Article 141 binding ratio analysis, obiter/factual scope distinctions, and subsequent judicial treatment.

4. **Editable Court Submissions & Opposing Counsel Rebuttals**
   - Generates structured legal grounds tailored to the supplied facts and forum.
   - Supports inline editing of draft submissions and counsel research notes (`PATCH /api/v1/analysis/:id`), bookmarking with persistent notes (`PATCH /api/v1/saved-cases/:id`), and export to Markdown (`.md`), Plain Text (`.txt`), and Print Dossier layout.

5. **Qualitative Judicial Treatment Assessment**
   - Replaces misleading win/loss probability scores with a qualitative breakdown of supporting authorities, distinguishing/potentially adverse authorities, factual determinants, and research limitations.

---

## Architecture

| Layer | Technologies | Responsibilities |
|---|---|---|
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS | Responsive workspace UI, 7-section dossier viewer, editable drafts, Markdown/TXT/Print export |
| **Backend API** | Node.js, Express, TypeScript, Zod | REST API (`/api/v1`), JWT authentication, Multer/PDF/DOCX extraction, Legislation & Argument engines |
| **NLP & Precedents** | Python 3 / Scikit-learn + TypeScript Local Engine | Multi-signal TF-IDF + statutory matching, deterministic Indian legal entity & issue matching |
| **Persistence** | MongoDB (Mongoose) + Session Memory Fallback | User-isolated dossiers & bookmarks (`persistenceMode` explicitly reported in health & UI) |

---

## Automated Verification Suites

### 1. Python NLP, Similarity & Source Integrity Tests (`22/22 Passed`)
```bash
cd ml-service
python3 -m unittest discover -s tests -v
python3 scripts/verify_sources.py
```

### 2. Backend TypeScript REST & Integration Tests (`20/20 Passed`)
```bash
cd backend
npm test
```

### 3. Monorepo Build
```bash
npm run build
```

---

## Local Development Setup

```bash
# Install dependencies
npm install --workspace=backend
npm install --workspace=frontend

# Start Backend REST API (Default port 5001 to avoid macOS AirPlay conflict on port 5000)
cd backend && npm run dev

# Start Frontend SPA (http://localhost:5173)
cd frontend && npm run dev
```

*(Optional persistence: configure `MONGODB_URI` and `JWT_SECRET` in `backend/.env`. Without `MONGODB_URI`, the server runs with non-persistent in-memory session storage and displays a session storage banner in the UI).*

---

## Legal Notice

JURIST AI provides structured legal research and draft-preparation support only. It is not a law firm, does not establish an advocate–client relationship, and does not provide formal legal advice. Advocates and researchers must verify primary statutory amendments, rules, and certified judicial orders independently prior to court filing.
