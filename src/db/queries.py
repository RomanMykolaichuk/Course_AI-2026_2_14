from __future__ import annotations

from pathlib import Path
from typing import Any

from .connection import connect


CORE_TABLES = (
    "regions",
    "attack_events",
    "attack_event_regions",
    "alert_intervals",
    "weather_observations",
    "dataset_builds",
)


def _rows_to_dicts(rows) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def get_table_counts(db_path: str | Path | None = None) -> dict[str, int]:
    """Return row counts for the project's core tables."""
    counts: dict[str, int] = {}
    with connect(db_path) as connection:
        for table in CORE_TABLES:
            row = connection.execute(f"SELECT COUNT(*) AS n FROM {table};").fetchone()
            counts[table] = int(row["n"])
    return counts


def get_database_summary(db_path: str | Path | None = None) -> dict[str, Any]:
    """Return a small runtime summary useful for diagnostics and the API."""
    return {
        "table_counts": get_table_counts(db_path),
    }


def get_latest_build(db_path: str | Path | None = None) -> dict[str, Any] | None:
    """Return provenance for the most recently recorded dataset build."""
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT
                build_id,
                source_name,
                source_snapshot,
                source_sha256,
                code_commit_sha,
                transformation_version,
                built_at,
                rows_loaded,
                notes
            FROM dataset_builds
            ORDER BY built_at DESC, build_id DESC
            LIMIT 1;
            """
        ).fetchone()
    return dict(row) if row else None


def get_overview(db_path: str | Path | None = None) -> dict[str, Any]:
    """Return top-level retrospective statistics for canonical attack events."""
    with connect(db_path) as connection:
        row = connection.execute(
            """
            WITH linked AS (
                SELECT DISTINCT event_id
                FROM attack_event_regions
            )
            SELECT
                COUNT(*) AS events,
                MIN(substr(time_start, 1, 10)) AS first_date,
                MAX(substr(time_start, 1, 10)) AS last_date,
                COUNT(DISTINCT weapon_model) AS weapon_models,
                COUNT(DISTINCT weapon_category) AS weapon_categories,
                SUM(CASE WHEN launched IS NOT NULL THEN launched ELSE 0 END) AS launched_known_total,
                SUM(CASE WHEN destroyed IS NOT NULL THEN destroyed ELSE 0 END) AS destroyed_known_total,
                SUM(CASE WHEN event_id IN (SELECT event_id FROM linked) THEN 1 ELSE 0 END) AS events_with_region_link
            FROM attack_events;
            """
        ).fetchone()

    result = dict(row)
    events = int(result["events"] or 0)
    linked = int(result["events_with_region_link"] or 0)
    result["region_link_coverage_pct"] = round((linked / events * 100), 2) if events else 0.0
    return result


def get_daily_counts(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return canonical event counts grouped by source calendar date."""
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                substr(time_start, 1, 10) AS date,
                COUNT(*) AS events,
                SUM(CASE WHEN launched IS NOT NULL THEN launched ELSE 0 END) AS launched_known_total,
                SUM(CASE WHEN destroyed IS NOT NULL THEN destroyed ELSE 0 END) AS destroyed_known_total
            FROM attack_events
            WHERE time_start IS NOT NULL
            GROUP BY substr(time_start, 1, 10)
            ORDER BY date;
            """
        ).fetchall()
    return _rows_to_dicts(rows)


def get_category_summary(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return historical event/count summary by normalized weapon category."""
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                COALESCE(NULLIF(trim(weapon_category), ''), 'Unknown') AS category,
                COUNT(*) AS events,
                SUM(CASE WHEN launched IS NOT NULL THEN launched ELSE 0 END) AS launched_known_total,
                SUM(CASE WHEN destroyed IS NOT NULL THEN destroyed ELSE 0 END) AS destroyed_known_total
            FROM attack_events
            GROUP BY COALESCE(NULLIF(trim(weapon_category), ''), 'Unknown')
            ORDER BY events DESC, category;
            """
        ).fetchall()
    return _rows_to_dicts(rows)


def get_model_summary(
    db_path: str | Path | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return the most frequently represented historical weapon models."""
    if limit < 1:
        raise ValueError("limit must be >= 1")

    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                COALESCE(NULLIF(trim(weapon_model), ''), 'Unknown') AS model,
                COALESCE(NULLIF(trim(weapon_category), ''), 'Unknown') AS category,
                COUNT(*) AS events,
                SUM(CASE WHEN launched IS NOT NULL THEN launched ELSE 0 END) AS launched_known_total,
                SUM(CASE WHEN destroyed IS NOT NULL THEN destroyed ELSE 0 END) AS destroyed_known_total
            FROM attack_events
            GROUP BY
                COALESCE(NULLIF(trim(weapon_model), ''), 'Unknown'),
                COALESCE(NULLIF(trim(weapon_category), ''), 'Unknown')
            ORDER BY events DESC, model
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()
    return _rows_to_dicts(rows)


def get_region_summary(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return only region relations that exist in the canonical link table.

    This query does not infer oblasts from bare city names or missing geography.
    """
    with connect(db_path) as connection:
        rows = connection.execute(
            """
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
                END) AS medium_confidence_events,
                COUNT(DISTINCT CASE
                    WHEN aer.attribution_quality = 'low' THEN aer.event_id
                END) AS low_confidence_events
            FROM attack_event_regions aer
            JOIN regions r ON r.region_code = aer.region_code
            GROUP BY r.region_code, r.name_uk, r.name_en
            ORDER BY events DESC, r.name_en;
            """
        ).fetchall()
    return _rows_to_dicts(rows)


def get_attribution_coverage(db_path: str | Path | None = None) -> dict[str, Any]:
    """Describe how much of the event table has canonical region evidence."""
    with connect(db_path) as connection:
        row = connection.execute(
            """
            WITH per_event AS (
                SELECT
                    ae.event_id,
                    MAX(CASE WHEN aer.event_id IS NOT NULL THEN 1 ELSE 0 END) AS linked,
                    MAX(CASE WHEN aer.attribution_quality = 'high' THEN 1 ELSE 0 END) AS high,
                    MAX(CASE WHEN aer.attribution_quality = 'medium' THEN 1 ELSE 0 END) AS medium,
                    MAX(CASE WHEN aer.attribution_quality = 'low' THEN 1 ELSE 0 END) AS low
                FROM attack_events ae
                LEFT JOIN attack_event_regions aer ON aer.event_id = ae.event_id
                GROUP BY ae.event_id
            )
            SELECT
                COUNT(*) AS events,
                SUM(linked) AS events_with_region_link,
                SUM(high) AS events_with_high_confidence_region,
                SUM(medium) AS events_with_medium_confidence_region,
                SUM(low) AS events_with_low_confidence_region
            FROM per_event;
            """
        ).fetchone()

    result = {key: int(value or 0) for key, value in dict(row).items()}
    total = result["events"]
    linked = result["events_with_region_link"]
    result["coverage_pct"] = round((linked / total * 100), 2) if total else 0.0
    return result
