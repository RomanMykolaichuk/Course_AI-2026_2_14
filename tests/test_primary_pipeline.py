from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.preprocessing.primary_dataset import transform_primary_dataset
from src.preprocessing.regions import extract_region_codes


class RegionParsingTests(unittest.TestCase):
    def test_explicit_oblasts_are_extracted(self) -> None:
        self.assertEqual(
            extract_region_codes("Kyiv Oblast and Odesa Oblast"),
            ["kyiv_oblast", "odesa_oblast"],
        )

    def test_bare_city_is_not_forced_into_oblast(self) -> None:
        self.assertEqual(extract_region_codes("Kyiv"), [])


class PrimaryTransformationTests(unittest.TestCase):
    def test_transform_builds_event_and_region_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            attacks = root / "missile_attacks_daily.csv"
            weapons = root / "missiles_and_uavs.csv"

            pd.DataFrame(
                [
                    {
                        "time_start": "2026-01-10 20:00",
                        "time_end": "2026-01-11 08:00",
                        "model": "Training UAV",
                        "launch_place": "Example launch area",
                        "target": "Ukraine",
                        "affected_region": "Kyiv Oblast and Odesa Oblast",
                        "carrier": None,
                        "launched": 10,
                        "destroyed": 8,
                        "not_reach_goal": 1,
                        "border_crossing": "{'poland': 8}",
                        "still_attacking": 1,
                        "source": "https://example.org/report",
                    }
                ]
            ).to_csv(attacks, index=False)

            pd.DataFrame(
                [{"model": "Training UAV", "category": "UAV"}]
            ).to_csv(weapons, index=False)

            events, links, stats = transform_primary_dataset(
                attacks,
                weapons,
                source_snapshot="test/snapshot",
            )

            self.assertEqual(len(events), 1)
            self.assertEqual(events.iloc[0]["weapon_category"], "UAV")
            self.assertEqual(events.iloc[0]["border_crossing"], 8)
            self.assertEqual(events.iloc[0]["border_crossing_raw"], "{'poland': 8}")
            self.assertTrue(str(events.iloc[0]["time_start"]).endswith("Z"))
            self.assertEqual(stats["events_with_explicit_regions"], 1)

            self.assertEqual(
                set(links["region_code"]),
                {"kyiv_oblast", "odesa_oblast"},
            )
            self.assertEqual(set(links["relation_type"]), {"affected"})


if __name__ == "__main__":
    unittest.main()