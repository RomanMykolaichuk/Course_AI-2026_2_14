PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS regions (
    region_code TEXT PRIMARY KEY,
    name_uk TEXT NOT NULL,
    name_en TEXT,
    boundary_source TEXT,
    boundary_version TEXT
);

CREATE TABLE IF NOT EXISTS attack_events (
    event_id TEXT PRIMARY KEY,
    time_start TEXT NOT NULL,
    time_end TEXT,
    weapon_model TEXT,
    weapon_category TEXT,
    launch_place TEXT,
    target_raw TEXT,
    carrier TEXT,
    launched INTEGER CHECK (launched IS NULL OR launched >= 0),
    destroyed INTEGER CHECK (destroyed IS NULL OR destroyed >= 0),
    not_reach_goal INTEGER CHECK (not_reach_goal IS NULL OR not_reach_goal >= 0),
    border_crossing INTEGER CHECK (border_crossing IS NULL OR border_crossing >= 0),
    border_crossing_raw TEXT,
    still_attacking INTEGER CHECK (still_attacking IS NULL OR still_attacking >= 0),
    source_name TEXT NOT NULL,
    source_url TEXT,
    source_record_id TEXT,
    source_snapshot TEXT NOT NULL,
    ingested_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS attack_event_regions (
    event_id TEXT NOT NULL,
    region_code TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    attribution_method TEXT NOT NULL,
    attribution_quality TEXT,
    PRIMARY KEY (event_id, region_code, relation_type),
    FOREIGN KEY (event_id) REFERENCES attack_events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (region_code) REFERENCES regions(region_code)
);

CREATE TABLE IF NOT EXISTS alert_intervals (
    alert_id TEXT PRIMARY KEY,
    region_code TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    source_name TEXT NOT NULL,
    source_snapshot TEXT NOT NULL,
    CHECK (finished_at IS NULL OR finished_at >= started_at),
    FOREIGN KEY (region_code) REFERENCES regions(region_code)
);

CREATE TABLE IF NOT EXISTS weather_observations (
    observed_at TEXT NOT NULL,
    region_code TEXT NOT NULL,
    temperature_c REAL,
    wind_speed_ms REAL,
    wind_direction_deg REAL,
    precipitation_mm REAL,
    cloud_cover_pct REAL,
    surface_pressure_hpa REAL,
    source_name TEXT NOT NULL,
    aggregation_method TEXT NOT NULL,
    PRIMARY KEY (observed_at, region_code, source_name),
    FOREIGN KEY (region_code) REFERENCES regions(region_code)
);

CREATE TABLE IF NOT EXISTS dataset_builds (
    build_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_snapshot TEXT NOT NULL,
    source_sha256 TEXT,
    code_commit_sha TEXT,
    transformation_version TEXT,
    built_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    rows_loaded INTEGER CHECK (rows_loaded IS NULL OR rows_loaded >= 0),
    notes TEXT
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

CREATE INDEX IF NOT EXISTS idx_dataset_builds_source
    ON dataset_builds (source_name, built_at);