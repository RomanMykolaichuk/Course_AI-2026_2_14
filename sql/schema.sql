CREATE TABLE IF NOT EXISTS regions (
    region_code TEXT PRIMARY KEY,
    name_uk TEXT NOT NULL,
    name_en TEXT,
    boundary_source TEXT,
    boundary_version TEXT
);

CREATE TABLE IF NOT EXISTS attack_events (
    event_id TEXT PRIMARY KEY,
    time_start TIMESTAMPTZ NOT NULL,
    time_end TIMESTAMPTZ,
    weapon_model TEXT,
    weapon_category TEXT,
    launch_place TEXT,
    target_raw TEXT,
    carrier TEXT,
    launched INTEGER CHECK (launched IS NULL OR launched >= 0),
    destroyed INTEGER CHECK (destroyed IS NULL OR destroyed >= 0),
    not_reach_goal INTEGER CHECK (not_reach_goal IS NULL OR not_reach_goal >= 0),
    border_crossing INTEGER CHECK (border_crossing IS NULL OR border_crossing >= 0),
    still_attacking INTEGER CHECK (still_attacking IS NULL OR still_attacking >= 0),
    source_name TEXT NOT NULL,
    source_url TEXT,
    source_record_id TEXT,
    source_snapshot TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (time_end IS NULL OR time_end >= time_start)
);

CREATE TABLE IF NOT EXISTS attack_event_regions (
    event_id TEXT NOT NULL REFERENCES attack_events(event_id) ON DELETE CASCADE,
    region_code TEXT NOT NULL REFERENCES regions(region_code),
    relation_type TEXT NOT NULL,
    attribution_method TEXT NOT NULL,
    attribution_quality TEXT,
    PRIMARY KEY (event_id, region_code, relation_type)
);

CREATE TABLE IF NOT EXISTS alert_intervals (
    alert_id TEXT PRIMARY KEY,
    region_code TEXT NOT NULL REFERENCES regions(region_code),
    alert_type TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    source_name TEXT NOT NULL,
    source_snapshot TEXT NOT NULL,
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE IF NOT EXISTS weather_observations (
    observed_at TIMESTAMPTZ NOT NULL,
    region_code TEXT NOT NULL REFERENCES regions(region_code),
    temperature_c DOUBLE PRECISION,
    wind_speed_ms DOUBLE PRECISION,
    wind_direction_deg DOUBLE PRECISION,
    precipitation_mm DOUBLE PRECISION,
    cloud_cover_pct DOUBLE PRECISION,
    surface_pressure_hpa DOUBLE PRECISION,
    source_name TEXT NOT NULL,
    aggregation_method TEXT NOT NULL,
    PRIMARY KEY (observed_at, region_code, source_name)
);

CREATE INDEX IF NOT EXISTS idx_attack_events_time_start
    ON attack_events (time_start);

CREATE INDEX IF NOT EXISTS idx_attack_events_weapon_category
    ON attack_events (weapon_category);

CREATE INDEX IF NOT EXISTS idx_attack_event_regions_region
    ON attack_event_regions (region_code);

CREATE INDEX IF NOT EXISTS idx_alert_intervals_region_time
    ON alert_intervals (region_code, started_at);

CREATE INDEX IF NOT EXISTS idx_weather_observations_region_time
    ON weather_observations (region_code, observed_at);
