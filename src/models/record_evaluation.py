from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.db.connection import connect
from src.db.init_db import initialize_database
from src.db.queries import get_latest_build

from .historical_count_backtest import run_historical_count_backtest


TASK = "offline_historical_national_source_event_count_backtest"


def _evaluation_id(source_build_id: str | None, result: dict[str, Any]) -> str:
    payload = {
        "source_build_id": source_build_id,
        "task": result["task"],
        "target": result["target"],
        "comparison": result["comparison"],
        "evaluation": result["evaluation"],
        "deployment_gate": result["deployment_gate"],
    }
    digest = hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return "eval-" + digest[:20]


def record_historical_count_evaluation(
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run the offline backtest and persist metrics/provenance only."""
    database = initialize_database(db_path)
    result = run_historical_count_backtest(database)
    source_build = get_latest_build(database)
    source_build_id = source_build["build_id"] if source_build else None
    evaluation_id = _evaluation_id(source_build_id, result)
    evaluated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    notes = {
        "target_semantics": result["target_semantics"],
        "training_policy": result["training_policy"],
        "artifact_policy": result["artifact_policy"],
        "deployment_gate": result["deployment_gate"],
    }

    with connect(database) as connection:
        connection.execute(
            """
            INSERT INTO model_evaluations (
                evaluation_id,
                source_build_id,
                task,
                target_name,
                evaluated_at,
                deployment_status,
                comparison_json,
                validation_json,
                test_json,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(evaluation_id) DO UPDATE SET
                evaluated_at = excluded.evaluated_at,
                deployment_status = excluded.deployment_status,
                comparison_json = excluded.comparison_json,
                validation_json = excluded.validation_json,
                test_json = excluded.test_json,
                notes = excluded.notes;
            """,
            (
                evaluation_id,
                source_build_id,
                result["task"],
                result["target"],
                evaluated_at,
                result["deployment_gate"]["status"],
                json.dumps(result["comparison"], ensure_ascii=False),
                json.dumps(
                    result["evaluation"]["validation"],
                    ensure_ascii=False,
                ),
                json.dumps(
                    result["evaluation"]["test"],
                    ensure_ascii=False,
                ),
                json.dumps(notes, ensure_ascii=False),
            ),
        )
        connection.commit()

    return {
        "evaluation_id": evaluation_id,
        "source_build_id": source_build_id,
        "task": result["task"],
        "target": result["target"],
        "evaluated_at": evaluated_at,
        "deployment_status": result["deployment_gate"]["status"],
        "comparison": result["comparison"],
        "validation": result["evaluation"]["validation"],
        "test": result["evaluation"]["test"],
        "notes": notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run and record retrospective model metrics. "
            "No fitted model is persisted."
        )
    )
    parser.add_argument("--db", dest="db_path", default=None)
    args = parser.parse_args()

    print(
        json.dumps(
            record_historical_count_evaluation(args.db_path),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
