"""
api/main.py  —  City Congestion Tracker REST API
Run locally:  uvicorn main:app --reload --port 8000

Actual Supabase schema:
  locations:  id (int8 PK), name (text), lat (float8), lng (float8), zone (text)
  congestion: id (int8 PK), location_id (int8 FK → locations.id),
              timestamp (timestamptz), congestion_level (float8),
              speed_mph (float8), vehicle_volume (int8)
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
import openai
from dotenv import load_dotenv

load_dotenv()

# ── Init ────────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
OPENAI_KEY   = os.environ.get("OPENAI_API_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(
    title="City Congestion Tracker API",
    description="REST API for querying and summarising city traffic congestion data.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pydantic models ─────────────────────────────────────────────────────────────
class ReadingIn(BaseModel):
    location_id: int
    congestion_level: float
    speed_mph: Optional[float] = None
    vehicle_volume: Optional[int] = None

class SummaryRequest(BaseModel):
    hours_back: Optional[int] = 24
    location_id: Optional[int] = None
    zone: Optional[str] = None

# ── Helpers ─────────────────────────────────────────────────────────────────────
def utc_ago(hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

def severity_label(level: float) -> str:
    """
    Severity computed in Python (no generated column in your table).
    Scale adjusted for data that goes above 10.
      low      < 4
      moderate  4–8
      high      8–12
      severe   >= 12
    """
    if level < 4:   return "low"
    if level < 8:   return "moderate"
    if level < 12:  return "high"
    return "severe"

def enrich(rows: list) -> list:
    for r in rows:
        r["severity"] = severity_label(r.get("congestion_level", 0))
    return rows

# ── Routes ──────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "message": "Congestion Tracker API is running 🚦"}


@app.get("/locations", tags=["Locations"])
def get_locations():
    """All tracked locations."""
    res = supabase.table("locations").select("*").order("zone").execute()
    return res.data


@app.get("/congestion/current", tags=["Congestion"])
def get_current(
    zone: Optional[str] = Query(None),
    min_level: Optional[float] = Query(None, ge=0),
):
    """Latest congestion reading per location (last 2 hours)."""
    since = utc_ago(2)
    res = (
        supabase.table("congestion")
        .select("*, locations(id, name, zone, lat, lng)")
        .gte("timestamp", since)
        .order("timestamp", desc=True)
        .limit(2000)
        .execute()
    )

    # Deduplicate — keep most-recent reading per location
    seen: dict = {}
    for row in res.data:
        lid = row["location_id"]
        if lid not in seen:
            seen[lid] = row

    results = enrich(list(seen.values()))

    if zone:
        results = [r for r in results
                   if (r.get("locations") or {}).get("zone", "").lower() == zone.lower()]
    if min_level is not None:
        results = [r for r in results if r["congestion_level"] >= min_level]

    results.sort(key=lambda r: r["congestion_level"], reverse=True)
    return {"count": len(results), "data": results}


@app.get("/congestion/worst", tags=["Congestion"])
def get_worst(top_n: int = Query(5, ge=1, le=20)):
    """Top N most congested locations right now."""
    current = get_current()
    return {"top_n": top_n, "data": current["data"][:top_n]}


@app.get("/congestion/history", tags=["Congestion"])
def get_history(
    location_id: Optional[int] = Query(None),
    zone: Optional[str] = Query(None),
    hours_back: int = Query(24, ge=1, le=720),
    severity: Optional[str] = Query(None, description="low | moderate | high | severe"),
    limit: int = Query(500, ge=1, le=5000),
):
    """Historical readings with optional filters."""
    since = utc_ago(hours_back)
    query = (
        supabase.table("congestion")
        .select("*, locations(id, name, zone)")
        .gte("timestamp", since)
        .order("timestamp", desc=True)
        .limit(limit)
    )
    if location_id:
        query = query.eq("location_id", location_id)

    data = enrich(query.execute().data)

    if zone:
        data = [r for r in data
                if (r.get("locations") or {}).get("zone", "").lower() == zone.lower()]
    if severity:
        data = [r for r in data if r["severity"] == severity.lower()]

    return {"count": len(data), "hours_back": hours_back, "data": data}


@app.get("/congestion/stats", tags=["Congestion"])
def get_stats(
    hours_back: int = Query(24, ge=1, le=720),
    group_by: str = Query("location", description="location | zone | hour"),
):
    """Aggregated stats grouped by location, zone, or hour of day."""
    since = utc_ago(hours_back)
    res = (
        supabase.table("congestion")
        .select("location_id, congestion_level, timestamp, locations(name, zone)")
        .gte("timestamp", since)
        .execute()
    )
    rows = res.data
    if not rows:
        return {"count": 0, "data": []}

    from collections import defaultdict
    buckets: dict = defaultdict(list)

    for r in rows:
        loc = r.get("locations") or {}
        if group_by == "location":
            key = loc.get("name") or str(r["location_id"])
        elif group_by == "zone":
            key = loc.get("zone") or "Unknown"
        else:  # hour
            try:
                ts = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
                key = f"{ts.hour:02d}:00"
            except Exception:
                key = "??"
        buckets[key].append(r["congestion_level"])

    stats = [
        {
            "group":          k,
            "avg_congestion": round(sum(v) / len(v), 2),
            "max_congestion": round(max(v), 2),
            "min_congestion": round(min(v), 2),
            "reading_count":  len(v),
            "severity":       severity_label(sum(v) / len(v)),
        }
        for k, v in buckets.items()
    ]
    stats.sort(key=lambda x: x["avg_congestion"], reverse=True)
    return {"count": len(stats), "group_by": group_by, "data": stats}


@app.post("/congestion/reading", tags=["Congestion"])
def post_reading(reading: ReadingIn):
    """Submit a new congestion reading."""
    loc = supabase.table("locations").select("id").eq("id", reading.location_id).execute()
    if not loc.data:
        raise HTTPException(404, detail=f"location_id {reading.location_id} not found")

    row = {
        "location_id":      reading.location_id,
        "congestion_level": round(reading.congestion_level, 2),
        "speed_mph":        reading.speed_mph,
        "vehicle_volume":   reading.vehicle_volume,
    }
    res = supabase.table("congestion").insert(row).execute()
    return {"inserted": res.data}


@app.post("/congestion/summary", tags=["AI Summary"])
def get_ai_summary(req: SummaryRequest):
    """AI-generated plain-language congestion summary via OpenAI."""
    if not OPENAI_KEY:
        raise HTTPException(503, detail="OPENAI_API_KEY not configured")

    since = utc_ago(req.hours_back)
    query = (
        supabase.table("congestion")
        .select("location_id, congestion_level, timestamp, locations(name, zone)")
        .gte("timestamp", since)
    )
    if req.location_id:
        query = query.eq("location_id", req.location_id)
    rows = enrich(query.execute().data)

    if req.zone:
        rows = [r for r in rows
                if (r.get("locations") or {}).get("zone", "").lower() == req.zone.lower()]

    if not rows:
        return {"summary": "No data found for the selected filters."}

    from collections import defaultdict, Counter
    loc_levels: dict = defaultdict(list)
    for r in rows:
        name = (r.get("locations") or {}).get("name") or str(r["location_id"])
        loc_levels[name].append(r["congestion_level"])

    top_locs = sorted(
        [(n, round(sum(v)/len(v), 2), round(max(v), 2)) for n, v in loc_levels.items()],
        key=lambda x: x[1], reverse=True
    )[:8]

    severity_counts = Counter(r["severity"] for r in rows)
    total   = len(rows)
    avg_all = round(sum(r["congestion_level"] for r in rows) / total, 2)

    context = f"""
Time window: last {req.hours_back} hours | Total readings: {total}
Overall average congestion index: {avg_all}
Severity breakdown: {dict(severity_counts)}

Top congested locations (name, avg, peak):
{chr(10).join(f'  {i+1}. {n}: avg={a}, peak={p}' for i,(n,a,p) in enumerate(top_locs))}
"""

    client = openai.OpenAI(api_key=OPENAI_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful urban traffic analyst. Be concise and actionable."},
            {"role": "user",   "content": (
                f"Based on this congestion data, write a 3–5 sentence plain-language report "
                f"for a city transportation dashboard. Highlight the worst areas, notable patterns, "
                f"and one or two actionable recommendations.\n\nData:\n{context}"
            )}
        ],
        max_tokens=300,
        temperature=0.6,
    )
    return {
        "summary": response.choices[0].message.content.strip(),
        "data_context": {
            "total_readings":     total,
            "avg_congestion":     avg_all,
            "severity_breakdown": dict(severity_counts),
            "top_locations":      top_locs,
        }
    }
