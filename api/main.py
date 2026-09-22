from fastapi import FastAPI, HTTPException

from src.db.connection import connect, get_db_path
from src.db.queries import get_database_summary


app = FastAPI(
    title="Ukraine Air Strike Analytics API",
    version="0.2.0",
    description="Educational API for retrospective analytics and ML demonstrations.",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    db_path = get_db_path()
    if not db_path.exists():
        return {"status": "ok", "database": "not_initialized"}

    try:
        with connect(db_path) as connection:
            result = connection.execute("PRAGMA quick_check;").fetchone()[0]
    except Exception:
        return {"status": "degraded", "database": "error"}

    return {
        "status": "ok" if result == "ok" else "degraded",
        "database": "ready" if result == "ok" else "integrity_error",
    }


@app.get("/api/db/summary")
def database_summary() -> dict:
    db_path = get_db_path()
    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail="SQLite database is not initialized. Run: python -m src.db.init_db",
        )
    return get_database_summary(db_path)
