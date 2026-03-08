-- ── Performance indexes ────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_congestion_timestamp
  ON congestion(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_congestion_location
  ON congestion(location_id);

CREATE INDEX IF NOT EXISTS idx_congestion_loc_time
  ON congestion(location_id, timestamp DESC);

-- ── Row Level Security ─────────────────────────────────────
ALTER TABLE locations  ENABLE ROW LEVEL SECURITY;
ALTER TABLE congestion ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read locations"   ON locations;
DROP POLICY IF EXISTS "Public read congestion"  ON congestion;
DROP POLICY IF EXISTS "Allow insert congestion" ON congestion;

CREATE POLICY "Public read locations"   ON locations  FOR SELECT USING (true);
CREATE POLICY "Public read congestion"  ON congestion FOR SELECT USING (true);
CREATE POLICY "Allow insert congestion" ON congestion FOR INSERT WITH CHECK (true);