from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.db.connection import connect
from src.db.init_db import initialize_database
from src.db.seed_regions import seed_regions
from src.models.historical_count_backtest import run_historical_count_backtest


class HistoricalCountBacktestTests(unittest.TestCase):
    def test_backtest_returns_retrospective_metrics_only(self) -> None:
        temp = tempfile.TemporaryDirectory()
        try:
            db = Path(temp.name) / "model.db"
            initialize_database(db)
            seed_regions(db)

            rows = []
            dates = pd.date_range("2026-01-01", periods=70, freq="D")
            for day_index, date in enumerate(dates):
                count = 1 + (day_index % 5)
                for event_index in range(count):
                    rows.append(
                        (
                            f"d{day_index}-e{event_index}",
                            date.strftime("%Y-%m-%d"),
                            "Model",
                            "UAV",
                            count,
                            "test",
                            "snapshot",
                        )
                    )

            with connect(db) as connection:
                connection.executemany(
                    """
                    INSERT INTO attack_events (
                        event_id, time_start, weapon_model, weapon_category,
                        launched, source_name, source_snapshot
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    rows,
                )
                connection.execute(
                    """
                    INSERT INTO dataset_builds (
                        build_id, source_name, source_snapshot,
                        transformation_version, rows_loaded
                    )
                    VALUES (
                        'model-build', 'test', 'snapshot', 'test-v1', ?
                    );
                    """,
                    (len(rows),),
                )
                connection.commit()

            result = run_historical_count_backtest(db)

            self.assertEqual(
                result["task"],
                "offline_historical_national_source_event_count_backtest",
            )
            self.assertIn("does not save", result["artifact_policy"])
            self.assertEqual(
                set(result["evaluation"]["test"]["models"]),
                {"naive_lag1", "dummy_median", "random_forest_fixed"},
            )
            for model_metrics in result["evaluation"]["test"]["models"].values():
                self.assertIn("mae", model_metrics)
                self.assertIn("rmse", model_metrics)
                self.assertIn("r2", model_metrics)
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
