# BOU Sentinel — Deployment Guide

## Architecture

```
Vercel (Frontend) ──HTTP/WS──▶ Render (Backend API)
                                │
                          ┌─────┴──────┐
                          │  PostgreSQL │
                          │  Redis      │
                          └────────────┘
```

## Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: BOU Sentinel - Real-Time Fraud Detection"
git remote add origin https://github.com/YOUR_USERNAME/bou-sentinel.git
git push -u origin main
```

---

## Step 2: Deploy Backend to Render

### Option A: One-click Blueprint (Auto-creates Web Service + PostgreSQL)

The `render.yaml` at the repo root auto-creates:
- **Web Service** — FastAPI backend (builds from `backend/` directory)
- **PostgreSQL** — Free tier database

1. Go to **[render.com](https://render.com)** → sign in with GitHub
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repo
4. Click **"Apply"** — Render auto-creates the web service + database
5. ✅ Web service + PostgreSQL are done

### Step 2b: Add Redis (Blueprint doesn't support Redis — do manually)

After Blueprint finishes:

1. In Render Dashboard, click **"New +"** → **"Redis"**
2. **Name:** `bou-sentinel-redis`
3. **Plan:** **Free**
4. Click **"Create Redis"**

### Step 2c: Link Redis to Web Service

1. Go to your **Web Service** (`bou-sentinel-api`) dashboard
2. Click **"Environment"** tab
3. Add env var:
   - **Key:** `REDIS_URL`
   - **Value:** Paste the **Internal Connection String** from the Redis dashboard
4. Click **"Save Changes"** → Render will redeploy

### Option B: Full Manual Setup (if Blueprint doesn't work)

#### 2a. Create PostgreSQL Database
- Dashboard → **New +** → **PostgreSQL**
- Name: `bou-sentinel-db`
- Plan: **Free**
- Copy the **Internal Database URL** (will need this)

#### 2b. Create Redis Instance
- Dashboard → **New +** → **Redis**
- Name: `bou-sentinel-redis`
- Plan: **Free**
- Copy the **Internal Redis URL**

#### 2c. Create Web Service
- Dashboard → **New +** → **Web Service**
- Connect your GitHub repo
- **Name:** `bou-sentinel-api`
- **Runtime:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
- **Plan:** **Free**

#### 2d. Set Environment Variables
In the Web Service dashboard, add:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Paste the Internal Database URL from step 2a |
| `REDIS_URL` | Paste the Internal Redis URL from step 2b |

#### 2e. Deploy
Click **"Deploy"**. First build takes ~3 minutes.

### After Deploy — Verify Backend

```bash
# Test health endpoint
curl https://bou-sentinel-api.onrender.com/health

# You should see:
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected",
  "model_loaded": true
}
```

📝 **Note your Render URL** — it will be something like:
`https://bou-sentinel-api.onrender.com`

---

## Step 3: Deploy Frontend to Vercel

1. Go to **[vercel.com](https://vercel.com)** and sign in with GitHub
2. Click **"Add New"** → **"Project"**
3. Import your GitHub repo
4. **Root Directory:** Select `frontend` (click "Edit" → set to `frontend`)
5. **Framework Preset:** Vite should auto-detect. If not, select **"Vite"**
6. **Build & Output Settings** (auto-filled from `vercel.json`):
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`
7. **Environment Variables** — Add:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://bou-sentinel-api.onrender.com` |
| `VITE_WS_URL` | `wss://bou-sentinel-api.onrender.com/ws` |

8. Click **"Deploy"**

> ⏱️ First deploy takes ~1 minute.

### After Deploy — Open Your App

Your Vercel URL will be something like:
`https://bou-sentinel.vercel.app`

---

## Step 4: Run the Mock Data Generator

The backend has **no data** until you run the mock generator. You can run it locally to feed data:

### Locally (Recommended for dev/demo)
```bash
cd backend
python mock_generator.py --api https://bou-sentinel-api.onrender.com --rate 2
```

### For Demo: Trigger a Fraud Spike
```bash
python mock_generator.py --api https://bou-sentinel-api.onrender.com --spike --count 50
```

> 💡 **For the hackathon judges:** Run the continuous generator, then trigger `--spike` to show the dashboard reacting in real-time!

---

## Updating After Deployment

```bash
# Make changes, then:
git add .
git commit -m "Your changes"
git push

# Render auto-deploys on push to main branch
# Vercel auto-deploys on push to main branch
```

---

## Architecture Flow (Production)

```
┌──────────────────────┐       HTTP/WS        ┌──────────────────────┐
│   Vercel (Frontend)  │◄─────────────────────│   Render (Backend)   │
│   bou-sentinel.      │                      │   bou-sentinel-api.  │
│   vercel.app         │                      │   onrender.com       │
│                      │                      │                      │
│  React + Recharts    │                      │  FastAPI + Uvicorn   │
│  WebSocket Client    │                      │  Isolation Forest   │
│  Tailwind Dark       │                      │  Redis Pub/Sub      │
│                      │                      │  SQLAlchemy + PG    │
└──────────────────────┘                      └───────┬──────────────┘
                                                      │
                                              ┌───────┴───────┐
                                              │  Render Add-ons │
                                              │  ┌───────────┐  │
                                              │  │ PostgreSQL │  │
                                              │  │ (Free Tier)│  │
                                              │  └───────────┘  │
                                              │  ┌───────────┐  │
                                              │  │   Redis    │  │
                                              │  │ (Free Tier)│  │
                                              │  └───────────┘  │
                                              └─────────────────┘
```

## Cost Breakdown

| Service | Plan | Cost |
|---------|------|------|
| **Render** Web Service | Free | $0 |
| **Render** PostgreSQL | Free (1 GB) | $0 |
| **Render** Redis | Free (25 MB) | $0 |
| **Vercel** Frontend | Hobby | $0 |
| **Total** | | **$0/month** |

> ⚠️ **Render free tier caveats:** After 15 minutes of inactivity, the web service spins down. First request after idle takes ~30 seconds to cold start. Consider upgrading to **Starter** ($7/month) for no spin-down during the hackathon.