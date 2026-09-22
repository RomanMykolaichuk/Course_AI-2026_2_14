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
