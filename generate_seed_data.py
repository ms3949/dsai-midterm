"""
data/generate_seed_data.py
Adds MORE synthetic readings to your existing Supabase tables.

Your tables already have data starting 2026-02-22.
This script adds readings for the past 30 days from today.

Run:
  pip install supabase python-dotenv
  python generate_seed_data.py
"""

import os
import random
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]   # service_role key recommended for seeding

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── Fetch existing locations ────────────────────────────────────────────────────
def get_locations():
    res = supabase.table("locations").select("id, name, zone").execute()
    return res.data

# ── Realistic congestion model ──────────────────────────────────────────────────
def congestion_for_hour(hour: int, dow: int, base: float) -> float:
    """
    Produces values roughly in the 1–20 range (matching your existing data).
    Morning peak 7–9, evening peak 17–19, low overnight.
    Weekends ~30% lower.
    """
    weekend = 0.70 if dow >= 5 else 1.0

    if 7 <= hour <= 9:
        peak = 14.0 + random.uniform(-1.5, 1.5)
    elif 10 <= hour <= 11:
        peak = 8.0 + random.uniform(-1.0, 1.0)
    elif 12 <= hour <= 13:
        peak = 7.0 + random.uniform(-1.0, 1.0)
    elif 17 <= hour <= 19:
        peak = 15.5 + random.uniform(-1.5, 1.5)
    elif 20 <= hour <= 22:
        peak = 6.0 + random.uniform(-1.0, 1.0)
    elif hour >= 23 or hour <= 5:
        peak = 2.0 + random.uniform(-0.5, 0.5)
    else:
        peak = 5.0 + random.uniform(-1.0, 1.0)

    level = peak * weekend * (base / 8.0)
    level += random.gauss(0, 0.8)
    return round(max(0.5, level), 1)

def speed_from_congestion(level: float) -> float:
    speed = 65 - (min(level, 20) / 20) * 60
    return round(max(2.0, speed + random.gauss(0, 1.5)), 1)

def volume_from_congestion(level: float) -> int:
    vol = int(10 + level * 2.5 + random.gauss(0, 5))
    return max(5, vol)


def seed_readings(days_back: int = 30, interval_minutes: int = 30):
    locations = get_locations()
    if not locations:
        print("ERROR: No locations found. Check your SUPABASE_URL / SUPABASE_KEY.")
        return

    print(f"Found {len(locations)} locations: {[l['name'] for l in locations]}")

    # Fetch the current maximum ID from the congestion table
    try:
        res = supabase.table("congestion").select("id").order("id", desc=True).limit(1).execute()
        current_id = res.data[0]["id"] if res.data else 0
    except Exception as e:
        print(f"Warning: Could not fetch max ID, starting from 0. Error: {e}")
        current_id = 0

    print(f"Starting seeding from ID: {current_id + 1}")

    now   = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days_back)

    baselines = {l["id"]: random.uniform(5.0, 11.0) for l in locations}

    records = []
    batch_size = 500
    current = start
    total_intervals = (days_back * 24 * 60) // interval_minutes
    print(f"Generating ~{total_intervals * len(locations):,} readings over {days_back} days…")

    while current <= now:
        hour = current.hour
        dow  = current.weekday()
        for loc in locations:
            level = congestion_for_hour(hour, dow, baselines[loc["id"]])
            current_id += 1
            records.append({
                "id":                current_id,
                "location_id":       loc["id"],
                "timestamp":         current.isoformat(),
                "congestion_level":  level,
                "speed_mph":         speed_from_congestion(level),
                "vehicle_volume":    volume_from_congestion(level),
            })
            if len(records) >= batch_size:
                supabase.table("congestion").insert(records).execute()
                print(f"  … inserted {batch_size} rows (up to {current.strftime('%Y-%m-%d %H:%M')} UTC)")
                records = []
        current += timedelta(minutes=interval_minutes)

    if records:
        supabase.table("congestion").insert(records).execute()

    print(f"\n✅ Done! Readings added from {start.date()} to {now.date()}.")


if __name__ == "__main__":
    seed_readings(days_back=30, interval_minutes=30)
