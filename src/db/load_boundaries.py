from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.preprocessing.boundaries import canonicalize_boundaries, load_boundary_snapshot

from .connection import connect
from .init_db import initialize_database
from .seed_regions import seed_regions


def load_boundary_reference(
    snapshot_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> dict:
    """Validate ADM1 geometry and record its provenance on canonical regions."""
    database = initialize_database(db_path)
    seed_regions(database)

    geometry, metadata = load_boundary_snapshot(snapshot_dir)
    _, report = canonicalize_boundaries(geometry)

    if report["mapped_count"] != report["feature_count"]:
        raise ValueError(
            f"Unmapped ADM1 features: {report['unmapped_names']}"
        )
    if report["duplicate_region_codes"]:
        raise ValueError(
            "Duplicate ADM1 mappings: "
            + ", ".join(report["duplicate_region_codes"])
        )

    boundary_id = str(metadata.get("boundaryID") or "").strip()
    if not boundary_id:
        raise ValueError("Boundary metadata is missing boundaryID")

    source_label = "geoBoundaries gbOpen"
    region_codes = report["mapped_region_codes"]

    with connect(database) as connection:
        connection.executemany(
            """
            UPDATE regions
            SET boundary_source = ?,
                boundary_version = ?
            WHERE region_code = ?;
            """,
            [
                (source_label, boundary_id, region_code)
                for region_code in region_codes
            ],
        )
        connection.commit()

    return {
        "boundary_id": boundary_id,
        "boundary_year_represented": metadata.get("boundaryYearRepresented"),
        "boundary_build_date": metadata.get("buildDate"),
        "boundary_license": metadata.get("boundaryLicense"),
        "mapped_regions": len(region_codes),
        "database": str(database),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Record the acquired UKR ADM1 boundary version in SQLite."
    )
    parser.add_argument("--snapshot-dir", default=None)
    parser.add_argument("--db", dest="db_path", default=None)
    args = parser.parse_args()

    result = load_boundary_reference(
        snapshot_dir=args.snapshot_dir,
        db_path=args.db_path,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
