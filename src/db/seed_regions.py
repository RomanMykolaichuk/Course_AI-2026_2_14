from __future__ import annotations

from pathlib import Path

from src.preprocessing.regions import REGIONS

from .connection import connect


def seed_regions(db_path: str | Path | None = None) -> int:
    """Insert/update canonical Ukrainian administrative regions."""
    rows = [
        (region.code, region.name_uk, region.name_en)
        for region in REGIONS
    ]

    with connect(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO regions (region_code, name_uk, name_en)
            VALUES (?, ?, ?)
            ON CONFLICT(region_code) DO UPDATE SET
                name_uk = excluded.name_uk,
                name_en = excluded.name_en;
            """,
            rows,
        )
        connection.commit()

    return len(rows)
