-- Marine Pollution Detection: SQLite schema (paper §3.5: every alert keeps provenance)
CREATE TABLE IF NOT EXISTS scenes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id TEXT NOT NULL UNIQUE,      -- satellite product identifier
  sensor TEXT NOT NULL CHECK (sensor IN ('Sentinel-1 SAR','Sentinel-2 MSI')),
  region TEXT NOT NULL,
  acquired_at TEXT NOT NULL,            -- ISO-8601 UTC
  cloud_fraction REAL DEFAULT 0,
  wind_ms REAL,                         -- contextual data (paper §3.1)
  preprocessing_version TEXT NOT NULL,
  is_synthetic INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scene_id INTEGER NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('oil_like','suspected_debris')),
  lat REAL NOT NULL, lon REAL NOT NULL,
  area_km2 REAL NOT NULL,
  confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  flags TEXT NOT NULL DEFAULT '[]',     -- JSON list: look-alike / quality warnings
  polygon TEXT NOT NULL,                -- GeoJSON geometry
  model_version TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','confirmed','rejected','field_check')),
  analyst_note TEXT DEFAULT '',
  reviewed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_kind_conf ON alerts(kind, confidence);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
