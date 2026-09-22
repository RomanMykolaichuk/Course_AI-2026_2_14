from __future__ import annotations

import argparse
from pathlib import Path

from .connection import PROJECT_ROOT, connect, get_db_path


SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"


def _apply_lightweight_migrations(connection) -> None:
    """Keep generated local databases compatible with additive schema changes."""
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(attack_events);").fetchall()
    }
    if "border_crossing_raw" not in columns:
        connection.execute("ALTER TABLE attack_events ADD COLUMN border_crossing_raw TEXT;")


def initialize_database(db_path: str | Path | None = None) -> Path:
    """Create/update the local SQLite schema and return the database path."""
    target = get_db_path(db_path)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with connect(target) as connection:
        connection.execute("PRAGMA journal_mode = WAL;")
        connection.executescript(schema_sql)
        _apply_lightweight_migrations(connection)
        connection.commit()

    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the project SQLite database.")
    parser.add_argument(
        "--db",
        dest="db_path",
        default=None,
        help="Optional database path. Defaults to DATABASE_PATH or data/airstrikes.db.",
    )
    args = parser.parse_args()

    target = initialize_database(args.db_path)
    print(f"SQLite database initialized: {target}")


if __name__ == "__main__":
    main()
