from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.db.check_db import check_database
from src.db.connection import get_db_path
from src.db.load_boundaries import load_boundary_reference
from src.db.load_primary import load_primary_snapshot
from src.ingestion.acquire_boundaries import acquire_adm1
from src.ingestion.acquire_primary import acquire_snapshot
from src.models.record_evaluation import record_historical_count_evaluation


def build_demo(
    db_path: str | Path | None = None,
    primary_from_dir: str | Path | None = None,
    force_downloads: bool = False,
    record_evaluation: bool = True,
) -> dict[str, Any]:
    """Build the reproducible local retrospective demo end to end.

    The workflow downloads historical/open source data, creates the generated
    SQLite store, records GIS provenance and optionally writes retrospective
    evaluation metrics. It does not start the web server and does not expose a
    live prediction surface.
    """
    primary_snapshot = acquire_snapshot(
        from_dir=primary_from_dir,
        force=force_downloads,
    )

    primary = load_primary_snapshot(
        snapshot_dir=primary_snapshot,
        db_path=db_path,
        replace_source=True,
    )

    boundary_snapshot = acquire_adm1(
        force=force_downloads,
        simplified=True,
    )
    boundaries = load_boundary_reference(
        snapshot_dir=boundary_snapshot,
        db_path=db_path,
    )

    evaluation = None
    if record_evaluation:
        evaluation = record_historical_count_evaluation(db_path)

    ok, checks = check_database(db_path)
    if not ok:
        raise RuntimeError(
            "Final SQLite integrity check failed:\n" + "\n".join(checks)
        )

    database = str(get_db_path(db_path))
    return {
        "status": "ready",
        "database": database,
        "primary_snapshot": str(primary_snapshot),
        "primary_build_id": primary["build_id"],
        "canonical_events": primary["stats"]["events"],
        "region_links": primary["stats"]["region_links"],
        "boundary_snapshot": str(boundary_snapshot),
        "boundary_id": boundaries["boundary_id"],
        "mapped_regions": boundaries["mapped_regions"],
        "model_evaluation": evaluation,
        "database_checks": checks,
        "serve_command": "uvicorn api.main:app --reload",
        "dashboard_url": "http://127.0.0.1:8000/",
        "scope": (
            "Retrospective educational analytics. No live/current operational "
            "forecast endpoint is created."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the complete local retrospective demo."
    )
    parser.add_argument("--db", dest="db_path", default=None)
    parser.add_argument(
        "--primary-from-dir",
        default=None,
        help="Use manually downloaded primary CSV files instead of KaggleHub.",
    )
    parser.add_argument(
        "--force-downloads",
        action="store_true",
        help="Replace existing source/GIS snapshots.",
    )
    parser.add_argument(
        "--skip-evaluation",
        action="store_true",
        help="Build analytics/GIS without recording retrospective ML metrics.",
    )
    args = parser.parse_args()

    result = build_demo(
        db_path=args.db_path,
        primary_from_dir=args.primary_from_dir,
        force_downloads=args.force_downloads,
        record_evaluation=not args.skip_evaluation,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
