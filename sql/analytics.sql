-- Retrospective analytics examples for the canonical SQLite database.
-- These queries are intentionally read-only and mirror src/db/queries.py.

-- 1. Overview
SELECT
    COUNT(*) AS events,
    MIN(substr(time_start, 1, 10)) AS first_date,
    MAX(substr(time_start, 1, 10)) AS last_date,
    COUNT(DISTINCT weapon_model) AS weapon_models,
    COUNT(DISTINCT weapon_category) AS weapon_categories
FROM attack_events;

-- 2. Daily timeline
SELECT
    substr(time_start, 1, 10) AS date,
    COUNT(*) AS events
FROM attack_events
GROUP BY substr(time_start, 1, 10)
ORDER BY date;

-- 3. Weapon categories
SELECT
    COALESCE(NULLIF(trim(weapon_category), ''), 'Unknown') AS category,
    COUNT(*) AS events,
    SUM(CASE WHEN launched IS NOT NULL THEN launched ELSE 0 END) AS launched_known_total,
    SUM(CASE WHEN destroyed IS NOT NULL THEN destroyed ELSE 0 END) AS destroyed_known_total
FROM attack_events
GROUP BY COALESCE(NULLIF(trim(weapon_category), ''), 'Unknown')
ORDER BY events DESC, category;

-- 4. Region attribution coverage
-- IMPORTANT: this measures available canonical links, not complete geographic truth.
WITH per_event AS (
    SELECT
        ae.event_id,
        MAX(CASE WHEN aer.event_id IS NOT NULL THEN 1 ELSE 0 END) AS linked,
        MAX(CASE WHEN aer.attribution_quality = 'high' THEN 1 ELSE 0 END) AS high,
        MAX(CASE WHEN aer.attribution_quality = 'medium' THEN 1 ELSE 0 END) AS medium
    FROM attack_events ae
    LEFT JOIN attack_event_regions aer ON aer.event_id = ae.event_id
    GROUP BY ae.event_id
)
SELECT
    COUNT(*) AS events,
    SUM(linked) AS events_with_region_link,
    SUM(high) AS events_with_high_confidence_region,
    SUM(medium) AS events_with_medium_confidence_region
FROM per_event;

-- 5. Regions with available evidence
SELECT
    r.region_code,
    r.name_uk,
    r.name_en,
    COUNT(DISTINCT aer.event_id) AS events,
    COUNT(DISTINCT CASE
        WHEN aer.attribution_quality = 'high' THEN aer.event_id
    END) AS high_confidence_events,
    COUNT(DISTINCT CASE
        WHEN aer.attribution_quality = 'medium' THEN aer.event_id
    END) AS medium_confidence_events
FROM attack_event_regions aer
JOIN regions r ON r.region_code = aer.region_code
GROUP BY r.region_code, r.name_uk, r.name_en
ORDER BY events DESC, r.name_en;
