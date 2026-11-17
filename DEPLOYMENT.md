# JURIST AI — Production Deployment & Operations Guide

**System:** JURIST AI — Intelligent Legal Analysis & Outcome Likelihood Estimation System  
**Version:** 2.0.0 (Production Architecture)  
**Date:** November 2026  

---

## 1. System Architecture Overview

JURIST AI is an enterprise-grade legal research and predictive intelligence platform composed of three loosely coupled subsystems:

```
                                  ┌────────────────────────┐
                                  │   Browser / Client     │
                                  └───────────┬────────────┘
                                              │ HTTPS
                                              ▼
                                 ┌──────────────────────────┐
                                 │ React + Vite SPA         │
                                 │ (Vercel / Nginx / Static)│
                                 └────────────┬─────────────┘
                                              │ HTTPS / REST
                                              ▼
                                 ┌──────────────────────────┐
                                 │ Node.js + Express API    │
                                 │ (Render / Container)     │
                                 └──────┬────────────┬──────┘
                                        │            │
                  ┌─────────────────────┘            └──────────────────────┐
                  │ Internal REST                                           │ TLS
                  ▼                                                         ▼
    ┌───────────────────────────┐                             ┌───────────────────────────┐
    │ Python ML & OCR Service   │                             │ MongoDB Atlas             │
    │ (Tesseract, PyMuPDF,      │                             │ (Shared M0 / Dedicated M10│
    │  TF-IDF & Calibrated LR)  │                             │  Session & Record Store)  │
    └───────────────────────────┘                             └───────────────────────────┘
```

1. **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, and Web Speech API. Hosted on Vercel, Render Static Site, AWS S3/CloudFront, or Nginx.
2. **Backend REST API**: Node.js 20, Express, TypeScript, Helmet, express-rate-limit, Multer memory storage, and Mongoose. Hosted on Render Web Service, AWS ECS, or Docker VPS.
3. **Python ML & OCR Microservice**: Python 3.11/3.12, PyMuPDF, Tesseract OCR, Scikit-learn, Pandas, NumPy, and Joblib. Exposes REST endpoints for multi-page document intelligence, OCR, bilingual Hindi/English extraction, and dual-model outcome prediction.
4. **Database Store**: MongoDB Atlas (replica set) for persistent storage of user accounts, analyzed dossiers, bookmarks, and draft revisions, with built-in zero-downtime fallback to non-persistent in-memory mode if disconnected.

---

## 2. Production Topology & Hosting Options

### Option A: 100% Free-Tier Architecture (Strict ₹0 Budget)
- **Frontend**: [Vercel](https://vercel.com) (Hobby Free Tier) — Edge CDN, 100 GB bandwidth/mo, zero cost.
- **Backend API**: [Render](https://render.com) (Free Web Service tier, 512 MB RAM) or [Koyeb](https://koyeb.com) (Free tier) — Auto-spins down after 15m idle; wakes automatically.
- **Python ML Service**:
  - **Preferred (High Performance)**: [Hugging Face Spaces](https://huggingface.co/spaces) (Docker SDK) — **2 vCPU, 16 GB RAM**, 50 GB storage, 100% Free forever with full ONNX + Tesseract OCR support.
  - **Alternative**: [Render](https://render.com) (Free Docker tier, 512 MB RAM) — TF-IDF + BM25 + Tesseract OCR mode.
- **Database**: [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (M0 Free Sandbox) — 512 MB storage, shared replica set, TLS encryption, ₹0 forever.

### Option B: High-Throughput Paid Cloud (When Budget Allows)
- **Frontend**: Vercel Pro ($20/mo) or Render Static.
- **Backend API**: Render Standard (1 vCPU, 2 GB RAM, $25/mo) or AWS ECS.
- **Python ML Service**: Render Standard (1 vCPU, 2 GB RAM, $25/mo) or AWS EC2.
- **Database**: MongoDB Atlas M10 Dedicated Replica Set (~$57/mo).

### Option C: Single Self-Hosted Server (Docker Compose on Local Server or VPS)
- Fully orchestrated via root [docker-compose.yml](file:///c:/Users/Gungun/Downloads/Jurist-AI-Team/docker-compose.yml).
- Can run on an on-premise workstation or cloud VM (Ubuntu 22.04 LTS, 4 GB+ RAM).

### Option D: Zero-Budget Serverless Hybrid Topology (Vercel + Atlas)
- Uses `vercel.json` and the serverless Express adapter in `api/index.ts`.
- Node.js backend serves both API routes and embedded TypeScript inference engine using exported dual-model JSON artifacts (`dual_model_artifacts.json`).

---

## 3. Production Environment Variables Reference

### 3.1 Backend Service (`backend/.env`)
| Variable | Required | Production Default / Example | Purpose |
|---|---|---|---|
| `PORT` | Yes | `5001` (or injected `$PORT`) | Port for the Express server to bind |
| `NODE_ENV` | Yes | `production` | Enforces production error masking & strict security |
| `MONGODB_URI` | Yes | `mongodb+srv://user:pass@cluster.mongodb.net/jurist_ai` | MongoDB connection string |
| `JWT_SECRET` | Yes | `64-character-hex-string` | Cryptographic key for signing JWT auth tokens |
| `JWT_EXPIRES_IN` | No | `7d` | Token expiry lifespan |
| `ML_SERVICE_URL` | Yes | `https://jurist-ai-ml.onrender.com` | URL of the Python ML/OCR microservice |
| `INTERNAL_ML_SECRET` | Yes | `shared-random-secret-key` | Shared secret header (`x-internal-secret`) |
| `CORS_ORIGIN` | Yes | `https://jurist-ai.vercel.app` | Comma-separated allowed frontend origins |
| `ALLOW_VERCEL_PREVIEW`| No | `true` | Allows `*.vercel.app` preview deployments |
| `MAX_FILE_SIZE_MB` | No | `15` | Maximum upload document size in megabytes |
| `DOCUMENT_EXTRACTION_TIMEOUT_MS` | No | `60000` | Timeout for deep OCR extraction (ms) |
| `GOOGLE_TRANSLATION_API_KEY` | Optional | `AIzaSy...` | Optional cloud translation key (user-consented only) |

### 3.2 Frontend Application (`frontend/.env`)
| Variable | Required | Production Default / Example | Purpose |
|---|---|---|---|
| `VITE_API_URL` | Yes | `https://jurist-ai-api.onrender.com/api/v1` | Publicly reachable backend API base URL |

*Note: For single-domain reverse proxy or Vercel rewrite deployment, set `VITE_API_URL=/api/v1`.*

### 3.3 Python ML Service (`ml-service/.env`)
| Variable | Required | Production Default / Example | Purpose |
|---|---|---|---|
| `PORT` / `ML_PORT` | Yes | `8000` (or platform `$PORT`) | Port for the Python HTTP service |
| `INTERNAL_ML_SECRET` | Yes | `shared-random-secret-key` | Must match backend's `INTERNAL_ML_SECRET` |
| `DEBUG` | No | `false` | Disables debug stack traces |

---

## 4. Hardware & Runtime Sizing Requirements

### 4.1 Python ML & OCR Service
- **Runtime**: Python 3.11 or 3.12 64-bit.
- **System Packages**: `tesseract-ocr`, `tesseract-ocr-hin` (for scanned Hindi documents).
- **RAM Requirements**:
  - Baseline idle with models & TF-IDF matrices loaded: **~220 MB**.
  - Peak processing during multi-page 15 MB PDF OCR rendering: **~480 MB – 650 MB**.
  - Minimum allocation: **512 MB** (Standard tier). Recommended: **1 GB – 2 GB**.
- **CPU**: 1 vCPU (2+ vCPU recommended for concurrent OCR uploads).
- **Disk Storage**: ~500 MB for Python virtualenv, scikit-learn, PyMuPDF, and model artifacts.

### 4.2 Node.js Backend Service
- **Runtime**: Node.js 20 LTS.
- **RAM Requirements**: ~120 MB idle, ~280 MB under heavy concurrent analysis.
- **CPU**: 0.5 – 1 vCPU.
- **Disk Storage**: ~200 MB for node_modules and compiled `dist/`.

### 4.3 Database (MongoDB Atlas)
- **Initial Dataset**: 27 verified landmark records (~150 KB).
- **Projected Storage**: ~15 KB per analyzed case with full evidence trace graph.
- **Index Requirements**: Indexes on `userId`, `caseId`, `email`, and `createdAt` (automatically maintained by Mongoose).
- **Connection Pool**: Default 10 connections.

---

## 5. Step-by-Step Deployment Procedures

### 5.1 Deployment Sequence
To prevent service discovery failures, deploy services in the following order:

```
Step 1: MongoDB Atlas Cluster Provisioning
   ↓
Step 2: Python ML & OCR Microservice Deployment
   ↓
Step 3: Node.js Backend REST API Deployment
   ↓
Step 4: React Vite Frontend Deployment
   ↓
Step 5: End-to-End System Health Verification
```

---

### 5.2 Deploying via Render (Option A)

#### Step 1: Deploy Python ML Service
1. In Render Dashboard, click **New + ➔ Web Service**.
2. Connect your repository.
3. Configure settings:
   - **Root Directory**: `ml-service`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `python app/services/api.py`
   - **Plan**: Standard (1 vCPU, 2 GB RAM)
4. Add Environment Variables:
   - `INTERNAL_ML_SECRET`: `<generate-secure-random-token>`
   - `DEBUG`: `false`
5. Note the assigned public URL (e.g. `https://jurist-ai-ml.onrender.com`).

#### Step 2: Deploy Backend API
1. In Render Dashboard, click **New + ➔ Web Service**.
2. Connect your repository.
3. Configure settings:
   - **Root Directory**: `backend`
   - **Environment**: `Node`
   - **Build Command**: `npm ci && npm run build`
   - **Start Command**: `npm start`
   - **Plan**: Standard
4. Add Environment Variables:
   - `NODE_ENV`: `production`
   - `MONGODB_URI`: `<your-mongodb-atlas-uri>`
   - `JWT_SECRET`: `<generate-secure-256-bit-key>`
   - `JWT_EXPIRES_IN`: `7d`
   - `ML_SERVICE_URL`: `https://jurist-ai-ml.onrender.com`
   - `INTERNAL_ML_SECRET`: `<same-token-as-ml-service>`
   - `CORS_ORIGIN`: `https://your-frontend-domain.vercel.app`
   - `MAX_FILE_SIZE_MB`: `15`
5. Note the assigned public URL (e.g. `https://jurist-ai-backend.onrender.com`).

#### Step 3: Deploy Frontend on Vercel
1. In Vercel Dashboard, click **Add New... ➔ Project**.
2. Import repository and set:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add Environment Variable:
   - `VITE_API_URL`: `https://jurist-ai-backend.onrender.com/api/v1`
4. Click **Deploy**.

---

### 5.3 Deploying via Docker Compose (Option B)

```bash
# 1. Clone the repository on your production server
git clone https://github.com/your-org/Jurist-AI.git
cd Jurist-AI

# 2. Configure production secrets in .env
cat <<EOF > .env
JWT_SECRET=$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")
INTERNAL_ML_SECRET=$(node -e "console.log(require('crypto').randomBytes(32).toString('hex'))")
EOF

# 3. Build and launch all 4 services in the background
docker-compose up -d --build

# 4. Verify running containers
docker-compose ps

# 5. Check logs
docker-compose logs -f backend
```

---

## 6. Health Checks & Monitoring

Verify the following health endpoints after deployment:

### Backend Health Check
```bash
curl -f https://your-backend.onrender.com/api/v1/health
```
**Expected Response (HTTP 200)**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "service": "Jurist AI Research API",
    "version": "2.0.0",
    "persistenceMode": "mongodb",
    "verifiedPrecedentCount": 176,
    "mlService": {
      "status": "healthy",
      "retrievalEngine": "Hybrid RRF (TF-IDF + BM25 + Semantic)"
    }
  }
}
```

### Python ML Service Health Check
```bash
curl -f https://your-ml-service.onrender.com/health
```
**Expected Response (HTTP 200)**:
```json
{
  "status": "healthy",
  "service": "Jurist-AI ML & NLP Engine",
  "ocrAvailable": true,
  "pymupdfAvailable": true,
  "outcomePrediction": {
    "statisticalModelTrained": true,
    "predictionMode": "statistical_verified"
  }
}
```

---

## 7. Security Hardening Checklist

- [x] **No Secret Leakage**: Stack traces and internal error payloads are hidden when `NODE_ENV=production`.
- [x] **Rate Limiting Active**: 200 requests / 15 min globally; 30 requests / 15 min on `/api/v1/auth/login` and `/register`.
- [x] **Strict CORS**: Only designated domains in `CORS_ORIGIN` are permitted to query the API.
- [x] **File Upload Security**: `multer.memoryStorage()` prevents disk path traversal; strict MIME and extension allowlist (`.pdf`, `.docx`, `.txt`, `.png`, `.jpg`).
- [x] **Authentication Isolation**: JWT verification on all `/api/v1/analysis`, `/cases`, and `/saved-cases` endpoints.
- [x] **Password Protection**: Passwords hashed using bcrypt (10 rounds); hashes never returned in API payloads (`select: false`).
- [x] **Data Privacy**: Legal documents remain on-premise; external Google Translation is only triggered if explicitly enabled by the user with active consent.

---

## 8. Troubleshooting & Rollback Procedures

### Common Issues & Resolutions

| Symptom | Cause | Resolution |
|---|---|---|
| `connect ECONNREFUSED 127.0.0.1:8000` | Backend cannot reach ML service | Verify `ML_SERVICE_URL` in backend env matches the public/internal URL of the ML service. |
| `401 Unauthorized internal request` | Secret key mismatch | Ensure `INTERNAL_ML_SECRET` in `backend` matches `INTERNAL_ML_SECRET` in `ml-service`. |
| `persistenceMode: "in_memory_fallback"` | MongoDB connection refused or IP blocked | In MongoDB Atlas, verify **Network Access** IP Access List includes your backend's outbound IPs (or `0.0.0.0/0` with strong password). |
| `CORS error in browser console` | Origin not in allowlist | Update `CORS_ORIGIN` in backend environment to include the exact frontend domain protocol and host. |
| Port in use on restart | Previous process lingering | In production, server halts cleanly on `EADDRINUSE`. Kill zombie process or restart container. |

### Rollback Strategy
1. **Frontend**: In Vercel or Render Static Site dashboard, select the previous successful deployment and click **Promote to Production** (instant zero-downtime rollback).
2. **Backend**:
   - Docker: `docker-compose up -d --no-deps backend=<previous-image-tag>`
   - Render: Select previous build under **Deploys** and click **Rollback to this deploy**.
3. **Database**: If schema migrations were run, restore point-in-time snapshot from MongoDB Atlas Backup Manager.
