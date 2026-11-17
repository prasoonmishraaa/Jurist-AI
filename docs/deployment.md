# JURIST AI — Deployment Guide (Vercel & Zero-Budget Cloud)

## 1. Zero-Budget Deployment Topology

| Component | Target Platform | Plan Tier | Notes |
|---|---|---|---|
| **Frontend** | Vercel | Hobby (Free) | Static React/Vite SPA hosted at global CDN edge |
| **Backend API** | Vercel Serverless Functions | Hobby (Free) | Node.js Express serverless adapter (`api/index.ts`) |
| **Database** | MongoDB Atlas | M0 Sandbox (Free) | 512 MB shared storage, TLS encryption, automated backups |
| **ML/NLP Inference** | Vercel Serverless / Node | Hobby (Free) | High-performance in-memory TF-IDF + Calibrated Logistic Regression inference using exported artifacts |
| **ML Training & Experiments** | Google Colab / Kaggle | Free Notebooks | CPU/GPU training and evaluation with checkpointing |

---

## 2. Vercel Configuration (`vercel.json`)

```json
{
  "version": 2,
  "buildCommand": "npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "/api/index.ts"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

---

## 3. Environment Variables Configuration for Vercel

In the Vercel Project Dashboard (under Settings ➔ Environment Variables), add the following keys:

| Variable Name | Example Value | Description |
|---|---|---|
| `MONGODB_URI` | `mongodb+srv://user:pass@cluster0.mongodb.net/jurist_ai` | MongoDB Atlas M0 connection string |
| `JWT_SECRET` | `your-secure-random-256-bit-key` | JWT signature secret |
| `JWT_EXPIRES_IN` | `7d` | Token lifespan |
| `NODE_ENV` | `production` | Production environment flag |
| `CORS_ORIGIN` | `https://jurist-ai.vercel.app` | Allowed origins |

---

## 4. Step-by-Step Vercel Deployment Instructions

1. Push your changes to GitHub on the `develop` or `main` branch.
2. Sign in to [Vercel](https://vercel.com) using your GitHub account (Free Hobby tier).
3. Click **Add New... ➔ Project** and import the `Jurist-AI` repository.
4. Set the **Framework Preset** to `Vite`.
5. Enter the Environment Variables listed in Section 3 above.
6. Click **Deploy**. Vercel will:
   - Run `npm run build` (compiling the TypeScript backend into `dist/` and Vite frontend into `frontend/dist`).
   - Bundle `api/index.ts` as a serverless function.
   - Deploy the frontend to the edge CDN.
7. Verify deployment by visiting:
   - `https://your-project.vercel.app/`
   - `https://your-project.vercel.app/api/v1/health`
