# 🚦 City Congestion Tracker

> DL Challenge 2026 — Full-stack congestion monitoring system  
> **Stack:** Supabase · FastAPI · Streamlit · OpenAI GPT-4o-mini

---

## Architecture

```
Supabase DB  ←──►  FastAPI (REST API)  ←──►  Streamlit Dashboard
                         │
                    OpenAI GPT-4o-mini
                    (AI summary endpoint)
```

| Component | Technology | Hosts |
|-----------|-----------|-------|
| Database  | Supabase (PostgreSQL) | Supabase Cloud |
| REST API  | FastAPI + Python | Render (free tier) |
| Dashboard | Streamlit | Streamlit Cloud (free) |
| AI        | OpenAI GPT-4o-mini | API call from FastAPI |

---

## Quick Start (Local)

### 1. Clone & set up environment
```bash
git clone https://github.com/YOUR_USERNAME/congestion-tracker
cd congestion-tracker
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY in .env
```

### 2. Set up Supabase database
1. Go to [supabase.com](https://supabase.com) → your project → **SQL Editor**
2. Paste and run `sql/schema.sql`
3. Copy your **Project URL** and **anon key** (or service_role key for seeding)

### 3. Seed with synthetic data
```bash
cd data
pip install supabase python-dotenv
python generate_seed_data.py
# Generates ~29,000 readings across 10 locations over 30 days
```

### 4. Run the API
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### 5. Run the Dashboard
```bash
cd dashboard
pip install -r requirements.txt
API_BASE_URL=http://localhost:8000 streamlit run app.py
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/locations` | All tracked locations |
| GET | `/congestion/current` | Latest reading per location |
| GET | `/congestion/worst?top_n=5` | Top N most congested right now |
| GET | `/congestion/history` | Historical readings (filterable) |
| GET | `/congestion/stats?group_by=location\|zone\|hour` | Aggregated stats |
| POST | `/congestion/reading` | Submit a new reading |
| POST | `/congestion/summary` | AI-generated plain-language summary |

### Example queries

```bash
# Current congestion, Downtown zone
GET /congestion/current?zone=Downtown

# Last 7 days of history for location L01
GET /congestion/history?location_id=L01&hours_back=168

# Stats grouped by hour of day
GET /congestion/stats?group_by=hour&hours_back=168

# AI summary for last 24h
POST /congestion/summary
{"hours_back": 24, "zone": "Midtown"}
```

---

## Deployment

### Deploy FastAPI → Render (free)
1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New Web Service** → connect repo
3. Set **Root Directory** to `api`
4. Add env vars: `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`
5. Deploy — you get a public URL like `https://congestion-api.onrender.com`

### Deploy Dashboard → Streamlit Cloud (free)
1. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
2. Connect GitHub repo, set **Main file path** to `dashboard/app.py`
3. In **Advanced settings → Secrets**, add:
```toml
API_BASE_URL = "https://your-api.onrender.com"
SUPABASE_URL = "..."
SUPABASE_KEY = "..."
OPENAI_API_KEY = "..."
```
4. Deploy — you get a public URL to submit for your midterm!

---

## Data Schema

### `locations` table
| Column | Type | Description |
|--------|------|-------------|
| location_id | TEXT PK | e.g. "L01" |
| name | TEXT | "5th Ave & 42nd St" |
| zone | TEXT | "Midtown", "Downtown", etc. |
| lat / lng | NUMERIC | For map display |

### `congestion_readings` table
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL PK | Auto ID |
| location_id | TEXT FK | References locations |
| timestamp | TIMESTAMPTZ | When reading was taken |
| congestion_level | NUMERIC 0–10 | 0 = free flow, 10 = standstill |
| speed_mph | NUMERIC | Estimated speed |
| volume | INT | Vehicles/hour |
| severity | TEXT (computed) | low / moderate / high / severe |

---

## Dashboard Features

- **📍 Live Overview** — Map + ranked table of current congestion
- **📈 Historical Trends** — Line charts, zone comparison, hour-of-day patterns
- **🤖 AI Summary** — GPT-4o-mini plain-language analysis with recommendations

---

## Project Structure

```
congestion-tracker/
├── sql/
│   └── schema.sql              # Run in Supabase SQL Editor
├── data/
│   └── generate_seed_data.py   # Creates 30 days of synthetic data
├── api/
│   ├── main.py                 # FastAPI app
│   └── requirements.txt
├── dashboard/
│   ├── app.py                  # Streamlit dashboard
│   ├── requirements.txt
│   └── .streamlit/
│       └── secrets.toml        # Add secrets here for deployment
├── render.yaml                 # One-click Render deployment
├── .env.example                # Copy to .env for local dev
└── README.md
```
