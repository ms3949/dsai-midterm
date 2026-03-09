# 🚦 City Congestion Tracker
### DL Challenge 2026 — Midterm Submission

> A full-stack congestion monitoring system for city transportation authorities.  
> **Live Dashboard:** https://ms3949-dsai-midterm-app.streamlit.app  
> **Live API:** https://congestion-app.vercel.app/docs  
> **GitHub:** https://github.com/ms3949/dsai-midterm

---

## 🏗️ System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│   Supabase DB   │────▶│  FastAPI (Vercel) │────▶│ Streamlit Dashboard│
│  (PostgreSQL)   │     │   REST API        │     │ (Streamlit Cloud)  │
└─────────────────┘     └────────┬─────────┘     └───────────────────┘
                                 │
                         ┌───────▼────────┐
                         │ OpenAI GPT-4o  │
                         │ mini (AI layer)│
                         └────────────────┘
```

**Pipeline:** Database → API → Dashboard → AI

| Component | Technology | Deployed At |
|-----------|-----------|-------------|
| Database | Supabase (PostgreSQL) | Supabase Cloud |
| REST API | FastAPI + Python | Vercel |
| Dashboard | Streamlit | Streamlit Cloud |
| AI Layer | OpenAI GPT-4o-mini | Via FastAPI |

---

## 🎯 Use Case

A **city transportation authority** needs real-time visibility into where congestion is building across the city. This system:
- Stores timestamped congestion readings for 15 intersections across 5 zones
- Exposes a REST API for querying by location, time window, zone, or severity
- Delivers an interactive dashboard with live maps, trend charts, and AI analysis
- Uses GPT-4o-mini to generate plain-language summaries and actionable recommendations

**Target user:** Transportation authority analysts and city planners

---

## 🚀 Quick Start (Local)

### Prerequisites
```bash
git clone https://github.com/ms3949/dsai-midterm
cd dsai-midterm
pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file:
```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
OPENAI_API_KEY=sk-...
API_BASE_URL=http://localhost:8000
```

### 1. Set up Database
Run `schema.sql` in your Supabase SQL Editor.

### 2. Seed Synthetic Data
```bash
python generate_seed_data.py
# Generates 30 days of readings across 15 locations
```

### 3. Run the API
```bash
uvicorn main:app --reload --port 8000
# Interactive docs: http://localhost:8000/docs
```

### 4. Run the Dashboard
```bash
API_BASE_URL=http://localhost:8000 streamlit run app.py
# Opens at: http://localhost:8501
```

---

## 🔌 API Endpoints

Base URL: `https://congestion-app.vercel.app`

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/` | Health check | — |
| GET | `/locations` | All 15 tracked locations | — |
| GET | `/congestion/current` | Latest reading per location | `zone`, `min_level` |
| GET | `/congestion/worst` | Top N most congested spots | `top_n` (default 5) |
| GET | `/congestion/history` | Historical readings | `location_id`, `zone`, `hours_back`, `severity`, `limit` |
| GET | `/congestion/stats` | Aggregated stats | `hours_back`, `group_by` (location/zone/hour) |
| POST | `/congestion/reading` | Submit a new reading | `location_id`, `congestion_level`, `speed_mph`, `vehicle_volume` |
| POST | `/congestion/summary` | AI-generated summary | `hours_back`, `location_id`, `zone` |

---

## ✅ Test Executions

### Test 1 — Current Congestion
```
GET https://congestion-app.vercel.app/congestion/current
```
Returns latest congestion reading per location with severity labels.

### Test 2 — Worst Spots Right Now
```
GET https://congestion-app.vercel.app/congestion/worst?top_n=5
```
Returns top 5 most congested intersections at this moment.

### Test 3 — Historical Stats by Hour of Day
```
GET https://congestion-app.vercel.app/congestion/stats?group_by=hour&hours_back=168
```
Returns average congestion for each hour of the day over the past 7 days — useful for identifying peak periods.

### Test 4 — Downtown Zone History
```
GET https://congestion-app.vercel.app/congestion/history?zone=Downtown&hours_back=24&limit=100
```
Returns last 24 hours of readings for Downtown zone only.

### Test 5 — AI Summary
```
POST https://congestion-app.vercel.app/congestion/summary
Content-Type: application/json

{"hours_back": 24, "zone": null, "location_id": null}
```
Returns a GPT-4o-mini generated plain-language summary of current congestion conditions with recommendations.

---

## 📊 Dashboard Features

| Page | Description |
|------|-------------|
| 📍 Live Overview | Interactive map + ranked table of current congestion levels across all 15 locations |
| 📈 Historical Trends | Line charts by location, bar charts by zone, hourly breakdown heatmap |
| 🤖 AI Summary | GPT-4o-mini analysis with worst areas, patterns, and actionable recommendations |

**User inputs required:**
- Zone filter (optional dropdown)
- Time window slider (1–168 hours)
- AI summary: hours to analyse + optional zone/location focus

---

## 📁 File Structure & Codebook

```
dsai-midterm/
├── main.py                  # FastAPI REST API — all endpoints
├── app.py                   # Streamlit dashboard — all 3 pages
├── generate_seed_data.py    # Synthetic data generator (30 days)
├── schema.sql               # Supabase table definitions + indexes + RLS
├── requirements.txt         # Python dependencies
├── vercel.json              # Vercel deployment config for FastAPI
└── README.md                # This file
```

### File Descriptions

**`main.py`** — FastAPI backend
- `get_locations()` — fetches all locations from Supabase
- `get_current()` — latest reading per location, filtered by zone/severity
- `get_worst()` — top N most congested locations right now
- `get_history()` — paginated historical readings with filters
- `get_stats()` — aggregated averages grouped by location, zone, or hour
- `post_reading()` — insert a new congestion reading
- `get_ai_summary()` — builds data context and calls OpenAI for narrative summary
- `severity_label()` — helper: maps congestion level to low/moderate/high/severe
- `enrich()` — helper: adds severity field to rows returned from Supabase

**`app.py`** — Streamlit dashboard
- `fetch()` — cached GET request wrapper to the FastAPI
- `post_json()` — POST request wrapper for AI summary endpoint
- Page 1: Live Overview — map, KPI metrics, ranked bar chart
- Page 2: Historical Trends — line chart by location, zone bar chart, hour heatmap
- Page 3: AI Summary — parameter inputs + GPT-4o-mini narrative output

**`generate_seed_data.py`** — Data seeder
- `get_locations()` — reads existing locations from Supabase
- `congestion_for_hour()` — models realistic peak/off-peak congestion by hour and day-of-week
- `speed_from_congestion()` — derives speed estimate from congestion level
- `volume_from_congestion()` — derives vehicle volume from congestion level
- `seed_readings()` — inserts batched readings every 30 min for 30 days

**`schema.sql`** — Database setup
- Creates performance indexes on `timestamp` and `location_id`
- Enables Row Level Security with public read + insert policies

---

## 🗄️ Data Codebook

### `locations` table
| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `id` | int8 PK | Unique location identifier | `1` |
| `name` | text | Intersection name | `"Main St & 1st Ave"` |
| `lat` | float8 | Latitude coordinate | `40.7128` |
| `lng` | float8 | Longitude coordinate | `-74.006` |
| `zone` | text | City zone name | `"Downtown"` |

**Zones:** Downtown, Midtown, Waterfront, Westside, Uptown, Industrial

### `congestion` table
| Variable | Type | Description | Range/Example |
|----------|------|-------------|---------------|
| `id` | int8 PK | Auto-incrementing row ID | `1, 2, 3...` |
| `location_id` | int8 FK | References `locations.id` | `1–15` |
| `timestamp` | timestamptz | UTC timestamp of reading | `2026-03-08T14:00:00+00` |
| `congestion_level` | float8 | Congestion index score | `0.5–20.0` (higher = worse) |
| `speed_mph` | float8 | Estimated vehicle speed | `2–65 mph` |
| `vehicle_volume` | int8 | Estimated vehicles per hour | `5–200` |

**Severity thresholds (computed in API):**
- `low` — congestion_level < 4
- `moderate` — 4 ≤ level < 8
- `high` — 8 ≤ level < 12
- `severe` — level ≥ 12

### Data Generation Method
Synthetic data generated by `generate_seed_data.py` using a realistic traffic model:
- **Morning peak:** 7–9 AM (avg level ~14)
- **Evening peak:** 5–7 PM (avg level ~15.5)
- **Midday:** 10 AM–1 PM (avg level ~7–8)
- **Overnight:** 11 PM–5 AM (avg level ~2)
- **Weekends:** ~30% lower than weekdays
- Gaussian noise (σ=0.8) added to all readings for realism

---

## 🔁 Reproducing This Project

1. Fork/clone `https://github.com/ms3949/dsai-midterm`
2. Create a free Supabase project at [supabase.com](https://supabase.com)
3. Run `schema.sql` in the Supabase SQL Editor
4. Add your credentials to `.env`
5. Run `python generate_seed_data.py` to populate data
6. Run `uvicorn main:app --reload` for the API
7. Run `streamlit run app.py` for the dashboard
8. Deploy API to Vercel, dashboard to Streamlit Cloud

All dependencies listed in `requirements.txt`. Python 3.11+ recommended.
