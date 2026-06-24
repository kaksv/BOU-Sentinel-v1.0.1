# 🛡️ BOU Sentinel

**Real-Time Fraud Detection & Regulatory Oversight Platform for the Bank of Uganda**

A dual-layered financial platform that combines an AI-powered fraud detection engine (micro-layer) with a real-time regulatory oversight dashboard (macro-layer). Built for the Bank of Uganda Hackathon.

---

## 🔍 What It Does

### Micro-Layer: Real-Time AI Fraud Detection
- **Incoming transactions** are scored by an Isolation Forest anomaly detection model
- **Risk scores** (0.0 – 1.0) are assigned in milliseconds
- **Fraud flags** trigger real-time alerts on the dashboard
- **Live WebSocket streaming** pushes scored transactions to all connected dashboards instantly

### Macro-Layer: Regulatory Oversight Dashboard
- **Transaction Volume vs Fraud Volume** chart (Recharts)
- **Live Transaction Feed** with color-coded risk indicators
- **AI Risk Score Gauge** with animated needle
- **Fraud Activity Heatmap** showing concentration of risk
- **System Status Bar** showing backend health (WebSocket, Redis, Model)

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        BOU Sentinel                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    HTTP POST    ┌──────────────────────────┐   │
│  │   Mock      │ ──────────────▶ │     FastAPI Backend       │   │
│  │ Generator   │                 │  ┌────────────────────┐  │   │
│  │  (Python)   │                 │  │  Isolation Forest   │  │   │
│  └─────────────┘                 │  │  AI Fraud Engine    │  │   │
│                                   │  └────────────────────┘  │   │
│                                   │           │              │   │
│                                   │           ▼              │   │
│                                   │  ┌────────────────────┐  │   │
│                                   │  │  PostgreSQL         │  │   │
│                                   │  │  (Transaction Store)│  │   │
│                                   │  └────────────────────┘  │   │
│                                   │                            │   │
│                                   │  ┌────────────────────┐  │   │
│                                   │  │  ConnectionManager  │  │   │
│                                   │  │  (WebSocket Hub)    │  │   │
│                                   │  └──────────┬─────────┘  │   │
│                                   └─────────────┼────────────┘   │
│                                                 │                 │
│                                    WebSocket   │                 │
│                                    (JSON)      │                 │
│                                                 ▼                 │
│                                   ┌────────────────────┐       │
│                                   │   React Frontend   │       │
│                                   │   (Vite + Tailwind)│       │
│                                   │                     │       │
│                                   │  ┌───────────────┐  │       │
│                                   │  │  Live Feed    │  │       │
│                                   │  │  Risk Gauge   │  │       │
│                                   │  │  Volume Chart │  │       │
│                                   │  │  Fraud Map    │  │       │
│                                   │  └───────────────┘  │       │
│                                   └────────────────────┘       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
mock_generator.py ──POST──▶ /api/transactions ──▶ FastAPI
                                                      │
                                                      ├──▶ AI Model.score() → Risk Score
                                                      │
                                                      ├──▶ PostgreSQL (save)
                                                      │
                                                      └──▶ WebSocket.broadcast() ──▶ React Dashboard
```

---

## 🚀 Quick Start

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| PostgreSQL | 14+ | Transaction database |
| npm / yarn | latest | Frontend package manager |

### 1. Clone the repo

```bash
git clone git@github.com:kaksv/BOU-Sentinel-v1.0.1.git
cd BOU-Sentinel
```

### 2. Start the backend

```bash
cd backend
pip install -r requirements.txt

# Ensure PostgreSQL is running locally
# Then start the API server:
uvicorn app.main:app --reload
```

API will be at `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### 3. Start the frontend (in a new terminal)

```bash
cd frontend
npm install
npm run dev
```

Dashboard will open at `http://localhost:5173`

### 4. Feed live data

```bash
cd backend
python mock_generator.py --rate 2
```

---

## 📦 Tech Stack

### Backend
| Tool | Version | Purpose |
|------|---------|---------|
| **FastAPI** | 0.104.1 | REST API + WebSocket server |
| **SQLAlchemy** | 2.0.36+ | ORM for PostgreSQL |
| **scikit-learn** | 1.5.0+ | Isolation Forest anomaly detection |
| **pandas** | 2.2.0+ | Data processing |
| **uvicorn** | 0.24.0 | ASGI server (production) |
| **WebSockets** | 12.0 | Real-time bidirectional streaming |

### Frontend
| Tool | Version | Purpose |
|------|---------|---------|
| **React** | 18.3 | UI library |
| **Vite** | 6.x | Build tool & dev server |
| **Tailwind CSS** | 3.4 | Dark-theme styling |
| **Recharts** | 2.12 | Volume/Fraud time-series chart |
| **Fonts** | Plus Jakarta Sans + JetBrains Mono | Premium dashboard typography |

### Infrastructure
| Tool | Purpose |
|------|---------|
| **Render** | Backend hosting (Web Service + PostgreSQL) |
| **Vercel** | Frontend hosting |
| **GitHub** | Source control & CI/CD |
| **PostgreSQL** | Persistent transaction storage |

---

## 📁 Project Structure

```
BOU-Sentinel/
├── README.md                 # ← You are here
├── DEPLOYMENT.md             # Step-by-step deploy guide
├── .gitignore                # Excludes venv, node_modules, .env
├── render.yaml               # Render Blueprint (root deploy)
│
├── backend/                  # ← FastAPI Backend
│   ├── .env.example          # Environment variable template
│   ├── Procfile              # Render start command (legacy)
│   ├── requirements.txt      # Python dependencies
│   ├── mock_generator.py     # ← Run this to generate test transactions
│   └── app/
│       ├── __init__.py
│       ├── config.py         # Pydantic settings (DATABASE_URL)
│       ├── database.py        # SQLAlchemy engine + session factory
│       ├── main.py            # FastAPI app + WebSocket + endpoints
│       ├── fraud_model.py     # Isolation Forest scorer
│       ├── models.py          # SQLAlchemy Transaction model
│       └── schemas.py         # Pydantic request/response schemas
│
└── frontend/                 # ← React Frontend
    ├── index.html             # Google Fonts (Plus Jakarta Sans, JetBrains Mono)
    ├── package.json
    ├── vite.config.js         # Dev proxy to backend + env var injection
    ├── vercel.json            # SPA routing for Vercel
    ├── tailwind.config.js     # Custom colors (bou, fraud, gold)
    ├── postcss.config.js
    ├── .env.production        # Production env vars (VITE_API_URL)
    └── src/
        ├── main.jsx           # React entry point
        ├── index.css          # Tailwind + custom component classes
        ├── App.jsx             # Dashboard layout + WebSocket client
        ├── Header.jsx          # BOU Sentinel logo, clock, WS status
        ├── StatCard.jsx        # Reusable stats card (4 color themes)
        ├── LiveTransactionFeed.jsx  # Scrolling feed with fraud pulse
        ├── RiskScoreGauge.jsx  # SVG arc gauge with animated needle
        ├── FraudHeatmap.jsx    # 8-column intensity grid
        └── FraudAlertBanner.jsx # Siren-animated fraud alert popup
```

---

## 📡 API Documentation

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Full system health (DB, model, Redis) |
| `GET` | `/api/status` | Fast status for the mock generator |
| `POST` | `/api/transactions` | Submit a transaction → AI scores → saves → broadcasts |
| `GET` | `/api/transactions` | Paginated transaction history |
| `GET` | `/api/transactions/fraud` | Fraud-only transactions |
| `GET` | `/api/stats` | Aggregate stats + recent activity data |

### WebSocket

| Path | Description |
|------|-------------|
| `WS /ws` | Connect to receive live scored transactions |

**Client message protocol:**
- Send `"ping"` → receives `"pong"`
- Send `"stats"` → receives WS client count + timestamp
- Any other message is ignored

**Server push format (JSON):**
```json
{
  "id": "uuid",
  "transaction_id": "TXN-abc123",
  "timestamp": "2024-01-15T10:30:00Z",
  "sender_account": "0123456789",
  "receiver_account": "9876543210",
  "amount": 2500000.0,
  "transaction_type": "transfer",
  "location": "Kampala",
  "risk_score": 0.87,
  "is_fraud": true,
  "fraud_reason": "High-value transaction: UGX 2,500,000",
  "model_version": "isolation_forest_v1"
}
```

---

## 🤖 The AI Model

**Algorithm:** Isolation Forest (Unsupervised Anomaly Detection)

**Features engineered from each transaction:**
| Feature | Description |
|---------|-------------|
| `amount` | Log-transformed transaction value (UGX) |
| `transaction_type_encoded` | transfer=0, deposit=1, withdrawal=2, payment=3 |
| `hour_of_day` | 0–23 (night transactions flagged) |
| `day_of_week` | 0–6 (weekend patterns) |
| `is_international` | Binary flag for non-Ugandan locations |
| `amount_velocity` | Transaction speed context (placeholder) |
| `is_high_value` | Binary: UGX > 10,000,000 |

**Training:** Auto-bootstrapped on first run with 5,000 synthetic transactions (5% injected anomalies). Model is cached to disk as `models/fraud_model.pkl`.

**Scoring:**
- Decision function → normalized to 0.0–1.0
- `risk_score > 0.75` → **FRAUD**
- `0.5 < risk_score ≤ 0.75` → **SUSPICIOUS**
- `risk_score ≤ 0.5` → **CLEAN**

**Fallback:** If the model is unavailable, a heuristic rule engine applies domain knowledge (high-value thresholds, international transactions, off-hours flagging).

---

## 🎮 Mock Data Generator

```bash
cd backend
pip install -r requirements.txt
```

### Modes

| Command | What it does |
|---------|-------------|
| `python mock_generator.py` | Continuous stream: 1 tx/sec, auto fraud spikes every 50–250 txns |
| `python mock_generator.py --rate 5` | Faster: 5 tx/sec |
| `python mock_generator.py --spike` | **Demo mode:** 50 coordinated fraud transactions in ~15 seconds |
| `python mock_generator.py --spike --count 100` | Custom spike size |
| `python mock_generator.py --single` | Generate and POST one transaction, then exit |

### Targeting the deployed API
```bash
python mock_generator.py --api https://bou-sentinel-api.onrender.com --rate 2
```

### Fraud Spike Pattern
The `--spike` mode simulates a **coordinated fraud attack**:
- Single compromised account reused across transactions
- Shared attacker device ID
- Known fraud hotspots (Lagos, Nairobi)
- Amounts: UGX 20M–80M
- Burst speed: 2–3 tx/sec

---

## 🧑‍💻 Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run dev server with auto-reload
uvicorn app.main:app --reload

# In another terminal, feed data:
python mock_generator.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` — the Vite dev server proxies `/api` and `/ws` to `http://localhost:8000`.

---

## 🚢 Deployment

Full step-by-step guide: **[DEPLOYMENT.md](./DEPLOYMENT.md)**

### What we deploy

| Platform | What | Cost |
|----------|------|------|
| **Render** | FastAPI backend + PostgreSQL | $0 (Free tier) |
| **Vercel** | React frontend | $0 (Hobby) |

### One-time setup

```bash
# 1. Push to GitHub
git init
git remote add origin https://github.com/USERNAME/bou-sentinel.git
git push -u origin main

# 2. Render: New + → PostgreSQL → copy Internal URL
#    Render: New + → Web Service → connect repo → paste DB URL as env var
#    Render: New + → Redis (optional, app works without it)

# 3. Vercel: Import repo → root = frontend → add VITE_API_URL
```

### Running the live demo
```bash
cd backend
python mock_generator.py --api https://bou-sentinel-api.onrender.com --rate 2

# In another terminal:
python mock_generator.py --api https://bou-sentinel-api.onrender.com --spike --count 50
```

---

## 🎨 Design Philosophy

The dashboard is built to look like a **premium, enterprise-grade central bank tool**:

- **Dark slate-900 background** — reduces eye strain for 24/7 monitoring
- **Gold accents** — institutional, premium feel (Bank of Uganda branding)
- **Muted red for fraud** — urgent but not alarmist
- **JetBrains Mono** for numbers — financial precision typography
- **Plus Jakarta Sans** for headings — modern, authoritative
- **Pulsing animations** on fraud — draws attention without being distracting
- **Minimal chrome** — data-first, no decorative clutter

### Color Palette

| Role | Color | Hex |
|------|-------|-----|
| Background | Slate 900 | `#0f172a` |
| Card | Slate 800 | `#1e293b` |
| Primary | BOU Blue | `#4c6ef5` |
| Success | Emerald | `#10b981` |
| Warning | Amber | `#f59e0b` |
| Danger | Fraud Red | `#ef4444` |
| Accent | Gold | `#d4a843` |

---

## 🐛 Known Issues & Workarounds

| Issue | Workaround |
|-------|-----------|
| Render free tier spins down after 15 min idle | Upgrade to Starter ($7/mo) for hackathon |
| `psycopg2-binary` on Python 3.14 needs 2.9.10+ | Already fixed in requirements.txt |
| `sqlalchemy` on Python 3.14 needs 2.0.36+ | Already fixed in requirements.txt |
| `scikit-learn` needs 1.5.0+ on Python 3.14 | Already fixed in requirements.txt |
| Redis not available on Render free tier | App works without Redis — WebSocket broadcasts directly |

---

## 📊 Sample Health Check Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "redis": "not_configured",
  "model_loaded": true
}
```

`redis: "not_configured"` is expected — the app streams via WebSocket without Redis on Render.

---

## 🤝 Contributing

This project was built in 48 hours for the Bank of Uganda Hackathon.

1. Fork it
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT — built for the Bank of Uganda Hackathon.

---

## 🙏 Credits

- **Backend AI engine:** scikit-learn Isolation Forest
- **Frontend charts:** Recharts
- **Design inspiration:** Central banking dashboards (Federal Reserve, ECB, BoU)
- **Deployment:** Render + Vercel free tier

---

## 📞 Contact

For questions about this project, open an issue on GitHub.

**Built for the Bank of Uganda.**