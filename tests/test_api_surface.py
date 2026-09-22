from __future__ import annotations

import unittest

from api.main import app


class ApiSurfaceTests(unittest.TestCase):
    def test_expected_routes_are_registered(self) -> None:
        paths = {route.path for route in app.routes}
        expected = {
            "/api/health",
            "/api/db/summary",
            "/api/build/latest",
            "/api/stats/overview",
            "/api/stats/daily",
            "/api/stats/categories",
            "/api/stats/models",
            "/api/stats/regions",
            "/api/stats/attribution",
            "",
        }
        self.assertTrue(expected.issubset(paths), paths)


if __name__ == "__main__":
    unittest.main()
