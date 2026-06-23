# BOU Sentinel — Manual Deployment Guide

## What we're building on Render

| Resource | What it costs | What it does |
|----------|--------------|--------------|
| **Web Service** | Free | Runs our FastAPI backend |
| **PostgreSQL** | Free (1 per account) | Stores transaction data |

---

## Step 1: Push your code to GitHub

```bash
git add .
git commit -m "Initial commit: BOU Sentinel"
git remote add origin https://github.com/YOUR_USERNAME/bou-sentinel.git
git push -u origin main
```

> Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Step 2: Create the PostgreSQL Database (on Render)

1. Go to **[render.com](https://render.com)** and sign in with GitHub
2. Click the **"New +"** button (top right)
3. Select **"PostgreSQL"**
4. Fill in:
   - **Name:** `bou-sentinel-db`
   - **Database:** leave default
   - **User:** leave default
   - **Plan:** **Free**
   - **Region:** Oregon
5. Click **"Create Database"**
6. ⏱️ Wait ~1 minute
7. Once ready, copy the **"Internal Database URL"** (starts with `postgresql://...`). Paste it somewhere — you'll need it in Step 4.

> ⚠️ Render only allows **one** free PostgreSQL database per account. If you already have one, reuse it.

---

## Step 3: Create the Web Service (on Render)

1. Click **"New +"** button again
2. Select **"Web Service"**
3. **Connect your GitHub repo:**
   - If prompted, install Render GitHub App and select your `bou-sentinel` repo
4. Fill in the form:

| Field | Value |
|-------|-------|
| **Name** | `bou-sentinel-api` |
| **Runtime** | **Python 3** |
| **Region** | Oregon |
| **Branch** | `main` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1` |
| **Plan** | **Free** |

5. Click **"Advanced"** (bottom of the form)
6. Click **"Add Environment Variable"**
7. Add this variable:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Paste the Internal Database URL from Step 2 |

8. Click **"Create Web Service"**
9. ⏱️ Wait ~3 minutes for first deployment

### ✅ Verify it's working

Once deployed, click the URL or run:

```bash
curl https://bou-sentinel-api.onrender.com/health
```

You should see:
```json
{
  "status": "healthy",
  "database": "connected",
  "model_loaded": true
}
```

📝 **Copy your Render URL** — it will be something like:
`https://bou-sentinel-api.onrender.com`

---

## Step 4: Deploy Frontend to Vercel

1. Go to **[vercel.com](https://vercel.com)** and sign in with GitHub
2. Click **"Add New"** → **"Project"**
3. Import your `bou-sentinel` repo
4. **Root Directory:** Click "Edit" → select **`frontend`**
5. **Framework Preset:** It should auto-detect **"Vite"**
6. **Build Command:** `npm run build` (auto-filled)
7. **Output Directory:** `dist` (auto-filled)
8. Click **"Environment Variables"** → Add these two:

| Key | Value |
|-----|-------|
| `VITE_API_URL` | `https://bou-sentinel-api.onrender.com` |
| `VITE_WS_URL` | `wss://bou-sentinel-api.onrender.com/ws` |

9. Click **"Deploy"**
10. ⏱️ Wait ~1 minute

### ✅ Open your app

Your Vercel URL will look like:
`https://bou-sentinel.vercel.app`

Open it. You'll see the dashboard but with **no data yet** (that's normal).

---

## Step 5: Feed live data from your laptop

The backend needs transactions to display. Run the mock generator locally:

```bash
# First, install backend dependencies
cd backend
pip install -r requirements.txt

# Start generating normal transactions (2 per second)
python mock_generator.py --api https://bou-sentinel-api.onrender.com --rate 2
```

### 🎯 For the hackathon demo: Trigger a Fraud Spike

Open a **second terminal** and run:

```bash
cd backend
python mock_generator.py --api https://bou-sentinel-api.onrender.com --spike --count 50
```

Watch the dashboard react in real-time:
- 🔴 Transaction feed shows pulsing red rows
- 📊 Volume chart spikes with a red line
- 🚨 Fraud alert banner pops up
- 🎯 Risk gauge needle swings to CRITICAL

---

## Updating after deployment

```bash
# Make changes, commit, push
git add .
git commit -m "Description of changes"
git push

# ✅ Render auto-deploys (takes ~2 min)
# ✅ Vercel auto-deploys (takes ~1 min)
```

---

## Summary of what we just created

```
Vercel                            Render
─────────                         ──────
bou-sentinel.vercel.app  ────▶   bou-sentinel-api.onrender.com
  │                                │
  │  React + Recharts              │  FastAPI
  │  WebSocket client              │  Isolation Forest AI
  │  Tailwind dark theme           │  SQLAlchemy + PostgreSQL
```

## Cost: **$0/month** (all free tier)