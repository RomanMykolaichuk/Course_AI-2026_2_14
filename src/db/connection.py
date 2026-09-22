from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Union

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = Path("data/airstrikes.db")

load_dotenv(PROJECT_ROOT / ".env")


PathLike = Union[str, Path]


def get_db_path(db_path: PathLike | None = None) -> Path:
    """Return an absolute path to the configured SQLite database."""
    configured = db_path or os.getenv("DATABASE_PATH") or DEFAULT_DATABASE_PATH
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def connect(db_path: PathLike | None = None) -> sqlite3.Connection:
    """Open a configured SQLite connection with project defaults."""
    path = get_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON;")
    connection.execute("PRAGMA busy_timeout = 5000;")
    return connection
