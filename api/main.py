from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from src.db.connection import connect, get_db_path
from src.db.map_data import build_region_geojson
from src.db.queries import (
    get_attribution_coverage,
    get_category_summary,
    get_daily_counts,
    get_database_summary,
    get_latest_build,
    get_latest_model_evaluation,
    get_model_summary,
    get_overview,
    get_region_summary,
)


WEB_DIR = Path(__file__).resolve().parents[1] / "web"

app = FastAPI(
    title="Ukraine Air Strike Analytics API",
    version="0.6.0",
    description="Educational API for retrospective analytics and ML demonstrations.",
)


def _require_database():
    db_path = get_db_path()
    if not db_path.exists():
        raise HTTPException(
            status_code=503,
            detail="SQLite database is not initialized. Run: python -m src.db.init_db",
        )
    return db_path


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
    return get_database_summary(_require_database())


@app.get("/api/build/latest")
def latest_build() -> dict:
    result = get_latest_build(_require_database())
    if result is None:
        raise HTTPException(status_code=404, detail="No dataset builds recorded yet.")
    return result


@app.get("/api/stats/overview")
def stats_overview() -> dict:
    return get_overview(_require_database())


@app.get("/api/stats/daily")
def stats_daily() -> list[dict]:
    return get_daily_counts(_require_database())


@app.get("/api/stats/categories")
def stats_categories() -> list[dict]:
    return get_category_summary(_require_database())


@app.get("/api/stats/models")
def stats_models(
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict]:
    return get_model_summary(_require_database(), limit=limit)


@app.get("/api/stats/regions")
def stats_regions() -> list[dict]:
    return get_region_summary(_require_database())


@app.get("/api/stats/attribution")
def stats_attribution() -> dict:
    return get_attribution_coverage(_require_database())


@app.get("/api/ml/evaluation/latest")
def latest_model_evaluation() -> dict:
    result = get_latest_model_evaluation(_require_database())
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No retrospective model evaluation recorded. Run: "
                "python -m src.models.record_evaluation"
            ),
        )
    return result


@app.get("/api/map/regions")
def region_map() -> dict:
    db_path = _require_database()
    try:
        return build_region_geojson(db_path)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "ADM1 geometry is not initialized. Run: "
                "python -m src.ingestion.acquire_boundaries"
            ),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"ADM1 geometry mapping failed: {exc}",
        ) from exc


app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")