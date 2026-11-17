# JURIST AI — Local Development & Setup Guide

This guide walks you through setting up and running JURIST AI locally on your development machine.

## Prerequisites
- Node.js (v18.0 or later, v20/v22 recommended)
- npm (v9.0 or later)
- Python 3.10+ (for ML scripts, notebooks, and optional Python REST microservice)
- (Optional) MongoDB local or MongoDB Atlas free URI

---

## 1. Clone & Quick Start

```bash
git clone https://github.com/prasoonmishraaa/Jurist-AI.git
cd Jurist-AI
```

---

## 2. Install Dependencies

Install root, backend, and frontend packages:
```bash
# In the root repository directory
npm install --workspace=backend
npm install --workspace=frontend
```

Set up Python environment for NLP/ML (optional for local research & testing):
```bash
cd ml-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

---

## 3. Configure Environment Variables

Create `.env` in `backend/`:
```bash
cp backend/.env.example backend/.env
```
Default parameters allow running immediately without a live MongoDB database using memory store fallbacks.

To connect to your MongoDB Atlas Free cluster, edit `backend/.env`:
```env
MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/jurist_ai?retryWrites=true&w=majority
```

---

## 4. Run the Full Application

### Option A: Run Backend & Frontend Concurrently

Terminal 1 (Backend API):
```bash
cd backend
npm run dev
# Server starts on http://localhost:5000
# Health check: http://localhost:5000/api/v1/health
```

Terminal 2 (Frontend Client):
```bash
cd frontend
npm run dev
# Client starts on http://localhost:5173
```

Open `http://localhost:5173` in your browser.

---

## 5. Seed Precedents into MongoDB

If connected to MongoDB Atlas, seed the 22 verified landmark Indian court judgments:
```bash
cd backend
npm run seed
```

---

## 6. Run Test Suites

Run Backend Integration Tests:
```bash
cd backend
npm test
```

Run Python NLP/ML Tests:
```bash
cd ml-service
python3 -m unittest discover -s tests -v
```

Evaluate Precedent Retrieval & ML Outcome Classifier:
```bash
cd ml-service
python3 app/evaluation/evaluate_models.py
```

Export Serverless Model Artifacts:
```bash
cd ml-service
python3 scripts/export_model_artifacts.py
```
