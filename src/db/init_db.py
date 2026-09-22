from __future__ import annotations

import argparse
from pathlib import Path

from .connection import PROJECT_ROOT, connect, get_db_path


SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"


def initialize_database(db_path: str | Path | None = None) -> Path:
    """Create/update the local SQLite schema and return the database path."""
    target = get_db_path(db_path)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with connect(target) as connection:
        connection.execute("PRAGMA journal_mode = WAL;")
        connection.executescript(schema_sql)
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
