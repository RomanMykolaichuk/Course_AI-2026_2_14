CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_date DATE NOT NULL,
    event_time TIME,
    region TEXT NOT NULL,
    weapon_category TEXT,
    weapon_type TEXT,
    count INTEGER,
    status TEXT,
    source TEXT NOT NULL,
    source_url TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_date
    ON events (event_date);

CREATE INDEX IF NOT EXISTS idx_events_region
    ON events (region);

CREATE INDEX IF NOT EXISTS idx_events_weapon_category
    ON events (weapon_category);
