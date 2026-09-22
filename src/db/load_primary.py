from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.ingestion.acquire_primary import sha256_file
from src.preprocessing.primary_dataset import SOURCE_NAME, transform_primary_dataset

from .check_db import check_database
from .connection import PROJECT_ROOT, connect, get_db_path
from .init_db import initialize_database
from .seed_regions import seed_regions


RAW_SOURCE_ROOT = PROJECT_ROOT / "data" / "raw" / "piterfm_massive_missile_attacks"
PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed" / "primary"


def _latest_snapshot() -> Path:
    candidates = sorted(
        path for path in RAW_SOURCE_ROOT.glob("*")
        if path.is_dir()
    )
    if not candidates:
        raise FileNotFoundError(
            "No primary snapshots found. Run: python -m src.ingestion.acquire_primary"
        )
    return candidates[-1]


def _git_commit_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def _build_id(attacks_sha256: str) -> str:
    return "primary-" + attacks_sha256[:16]


def _write_processed(
    snapshot_dir: Path,
    events: pd.DataFrame,
    links: pd.DataFrame,
    manifest: dict,
) -> Path:
    output_dir = PROCESSED_ROOT / snapshot_dir.name
    output_dir.mkdir(parents=True, exist_ok=True)

    events.to_csv(output_dir / "attack_events.csv", index=False)
    links.to_csv(output_dir / "attack_event_regions.csv", index=False)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_dir


def _rows(df: pd.DataFrame, columns: list[str]) -> list[tuple]:
    if df.empty:
        return []
    return [
        tuple(None if pd.isna(value) else value for value in row)
        for row in df[columns].itertuples(index=False, name=None)
    ]


def load_primary_snapshot(
    snapshot_dir: str | Path | None = None,
    db_path: str | Path | None = None,
    replace_source: bool = True,
) -> dict:
    snapshot = Path(snapshot_dir).expanduser().resolve() if snapshot_dir else _latest_snapshot()
    attacks_csv = snapshot / "missile_attacks_daily.csv"
    weapons_csv = snapshot / "missiles_and_uavs.csv"

    for required in (attacks_csv, weapons_csv):
        if not required.exists():
            raise FileNotFoundError(f"Required snapshot file not found: {required}")

    try:
        snapshot_label = str(snapshot.relative_to(PROJECT_ROOT))
    except ValueError:
        snapshot_label = str(snapshot)

    events, links, stats = transform_primary_dataset(
        attacks_csv,
        weapons_csv,
        source_snapshot=snapshot_label,
    )

    attacks_sha = sha256_file(attacks_csv)
    weapons_sha = sha256_file(weapons_csv)
    commit_sha = _git_commit_sha()
    build_id = _build_id(attacks_sha)
    built_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    manifest = {
        "build_id": build_id,
        "built_at": built_at,
        "source_name": SOURCE_NAME,
        "source_snapshot": snapshot_label,
        "source_files": {
            "missile_attacks_daily.csv": attacks_sha,
            "missiles_and_uavs.csv": weapons_sha,
        },
        "code_commit_sha": commit_sha,
        "transformation_version": "primary-v1",
        "stats": stats,
    }
    processed_dir = _write_processed(snapshot, events, links, manifest)

    database = initialize_database(db_path)
    seed_regions(database)

    event_columns = [
        "event_id",
        "time_start",
        "time_end",
        "weapon_model",
        "weapon_category",
        "launch_place",
        "target_raw",
        "carrier",
        "launched",
        "destroyed",
        "not_reach_goal",
        "border_crossing",
        "still_attacking",
        "source_name",
        "source_url",
        "source_record_id",
        "source_snapshot",
    ]
    link_columns = [
        "event_id",
        "region_code",
        "relation_type",
        "attribution_method",
        "attribution_quality",
    ]

    with connect(database) as connection:
        if replace_source:
            connection.execute(
                "DELETE FROM attack_events WHERE source_name = ?;",
                (SOURCE_NAME,),
            )

        connection.executemany(
            f"""
            INSERT INTO attack_events ({", ".join(event_columns)})
            VALUES ({", ".join("?" for _ in event_columns)})
            ON CONFLICT(event_id) DO UPDATE SET
                time_start = excluded.time_start,
                time_end = excluded.time_end,
                weapon_model = excluded.weapon_model,
                weapon_category = excluded.weapon_category,
                launch_place = excluded.launch_place,
                target_raw = excluded.target_raw,
                carrier = excluded.carrier,
                launched = excluded.launched,
                destroyed = excluded.destroyed,
                not_reach_goal = excluded.not_reach_goal,
                border_crossing = excluded.border_crossing,
                still_attacking = excluded.still_attacking,
                source_url = excluded.source_url,
                source_record_id = excluded.source_record_id,
                source_snapshot = excluded.source_snapshot;
            """,
            _rows(events, event_columns),
        )

        if not links.empty:
            connection.executemany(
                f"""
                INSERT INTO attack_event_regions ({", ".join(link_columns)})
                VALUES ({", ".join("?" for _ in link_columns)})
                ON CONFLICT(event_id, region_code, relation_type) DO UPDATE SET
                    attribution_method = excluded.attribution_method,
                    attribution_quality = excluded.attribution_quality;
                """,
                _rows(links, link_columns),
            )

        connection.execute(
            """
            INSERT INTO dataset_builds (
                build_id, source_name, source_snapshot, source_sha256,
                code_commit_sha, transformation_version, built_at,
                rows_loaded, notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(build_id) DO UPDATE SET
                source_snapshot = excluded.source_snapshot,
                code_commit_sha = excluded.code_commit_sha,
                built_at = excluded.built_at,
                rows_loaded = excluded.rows_loaded,
                notes = excluded.notes;
            """,
            (
                build_id,
                SOURCE_NAME,
                snapshot_label,
                attacks_sha,
                commit_sha,
                "primary-v1",
                built_at,
                len(events),
                json.dumps(
                    {
                        "weapons_sha256": weapons_sha,
                        "region_links": len(links),
                        "processed_dir": str(processed_dir),
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        connection.commit()

    ok, messages = check_database(database)
    if not ok:
        raise RuntimeError("Database check failed after load:\n" + "\n".join(messages))

    result = {
        **manifest,
        "database": str(get_db_path(database)),
        "processed_dir": str(processed_dir),
        "database_check": messages,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transform the latest primary snapshot and load it into SQLite."
    )
    parser.add_argument("--snapshot-dir", default=None)
    parser.add_argument("--db", dest="db_path", default=None)
    parser.add_argument(
        "--append",
        action="store_true",
        help="Do not replace existing rows from the primary source.",
    )
    args = parser.parse_args()

    result = load_primary_snapshot(
        snapshot_dir=args.snapshot_dir,
        db_path=args.db_path,
        replace_source=not args.append,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
