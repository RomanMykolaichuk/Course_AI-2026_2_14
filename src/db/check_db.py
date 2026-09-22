from __future__ import annotations

import argparse
from pathlib import Path

from .connection import connect, get_db_path


EXPECTED_TABLES = {
    "regions",
    "attack_events",
    "attack_event_regions",
    "alert_intervals",
    "weather_observations",
    "dataset_builds",
    "model_evaluations",
}


def check_database(db_path: str | Path | None = None) -> tuple[bool, list[str]]:
    """Validate schema presence, integrity, foreign keys and connection settings."""
    path = get_db_path(db_path)
    messages: list[str] = []

    if not path.exists():
        return False, [f"Database does not exist: {path}"]

    with connect(path) as connection:
        foreign_keys = connection.execute("PRAGMA foreign_keys;").fetchone()[0]
        if foreign_keys != 1:
            messages.append("FAIL: foreign_keys pragma is disabled.")
        else:
            messages.append("PASS: foreign_keys pragma is enabled.")

        integrity = connection.execute("PRAGMA integrity_check;").fetchone()[0]
        if integrity != "ok":
            messages.append(f"FAIL: integrity_check = {integrity}")
        else:
            messages.append("PASS: integrity_check = ok.")

        fk_issues = connection.execute("PRAGMA foreign_key_check;").fetchall()
        if fk_issues:
            messages.append(f"FAIL: {len(fk_issues)} foreign-key issue(s) found.")
        else:
            messages.append("PASS: foreign_key_check found no issues.")

        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            ).fetchall()
        }
        missing = EXPECTED_TABLES - tables
        if missing:
            messages.append("FAIL: missing tables: " + ", ".join(sorted(missing)))
        else:
            messages.append("PASS: all expected tables exist.")

    ok = not any(message.startswith("FAIL:") for message in messages)
    return ok, messages


def main() -> None:
    parser = argparse.ArgumentParser(description="Check the project SQLite database.")
    parser.add_argument("--db", dest="db_path", default=None)
    args = parser.parse_args()

    ok, messages = check_database(args.db_path)
    print(f"Database: {get_db_path(args.db_path)}")
    for message in messages:
        print(message)

    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()