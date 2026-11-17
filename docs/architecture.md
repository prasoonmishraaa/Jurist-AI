# JURIST AI — System Architecture

## 1. System Overview

**JURIST AI** (Intelligent Legal Analysis & Outcome Likelihood Estimation System) is a modular, zero-budget, full-stack legal intelligence platform engineered for Indian legal research. It extracts statutory provisions, identifies key legal concepts, retrieves relevant precedents from Indian court jurisprudence, and computes empirical outcome probabilities.

```
┌─────────────────────────────────────────────────────────────┐
│                    React 18 + Vite Frontend                 │
│      Tailwind CSS • TanStack Query • Lucide • Recharts      │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTPS / JSON REST
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Node.js / Express Backend                   │
│        JWT Auth • Zod Validation • Multer Document OCR      │
│                                                             │
│  ┌────────────────────────┐    ┌─────────────────────────┐  │
│  │   MongoDB Atlas (M0)   │    │  Local Serverless ML    │  │
│  │ Users, Cases, Analyses │    │  TF-IDF + Cosine Sim    │  │
│  │    Precedents Library  │    │  LogReg Inference       │  │
│  └────────────────────────┘    └────────────┬────────────┘  │
└─────────────────────────────────────────────┼───────────────┘
                                              │ Optional Internal REST
                                              ▼
┌─────────────────────────────────────────────────────────────┐
│             Python NLP & ML Research Pipeline               │
│   Scikit-learn • TF-IDF • Stratified K-Fold • spaCy Rules   │
│   e-SCR / eCourts Data Ingestion • Colab/Kaggle Checkpoints │
└─────────────────────────────────────────────────────────────┘
```

## 2. Component Separation & Responsibilities

1. **Frontend (`frontend/`)**: Single-Page Application (SPA) built using React 18, TypeScript, Vite, Tailwind CSS, Lucide icons, and Recharts. Handles user onboarding, case description authoring, PDF/DOCX file attachments, interactive entity inspection, precedent browsing, and outcome visualization.
2. **Backend (`backend/`)**: Node.js REST API providing authenticated user sessions, role-based access control, file text extraction, case management, bookmarking, and legal analysis orchestration.
3. **ML Service (`ml-service/`)**: Python pipeline for legal corpus curation, text preprocessing, legal terminology extraction, TF-IDF vectorization, Logistic Regression outcome modeling, model evaluation, and artifact serialization.
4. **Vercel Adapter (`api/index.ts` & `vercel.json`)**: Serverless entrypoint connecting Vercel routing directly to the backend with pure TypeScript in-memory model execution.

## 3. Communication Contracts

- Frontend to Backend: Standard REST/JSON over HTTPS with Bearer token authentication in `Authorization` headers.
- Backend to ML Service: Optional internal REST (`/api/ml/analyze`, `/api/ml/similarity`, `/api/ml/predict`) with automatic fallback to `LocalLegalInferenceEngine` when deployed serverless.
- Backend to Database: Mongoose ODM connecting to MongoDB Atlas Free Tier (M0) or in-memory fallback.
