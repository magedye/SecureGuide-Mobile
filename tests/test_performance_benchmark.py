"""Tests for the non-mutating release-catalog benchmark harness."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from scripts.benchmark_release_catalog import run_benchmark


ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "mobile" / "assets" / "catalog.db"
BUDGET = ROOT / "consolidation" / "performance_budget.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PerformanceBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.budget = json.loads(BUDGET.read_text(encoding="utf-8"))

    def test_smoke_benchmark_is_measured_but_not_qualified(self) -> None:
        before = _sha256(DATABASE)
        result = run_benchmark(
            DATABASE,
            self.budget,
            mode="smoke",
            warmups=0,
            iterations=3,
        )
        self.assertEqual(result["status"], "SMOKE_ONLY")
        self.assertFalse(result["qualified"])
        self.assertEqual(result["population"]["catalogRowsDuplicated"], 0)
        self.assertEqual(result["source"]["approvedActiveArtifacts"], 4)
        self.assertEqual(_sha256(DATABASE), before)
        self.assertTrue(result["queryPlans"]["catalogSearch"])

    def test_qualification_fails_closed_on_starter_catalog(self) -> None:
        result = run_benchmark(
            DATABASE,
            self.budget,
            mode="qualification",
            warmups=0,
            iterations=3,
        )
        self.assertEqual(result["status"], "BLOCKED_CATALOG_TOO_SMALL")
        self.assertFalse(result["population"]["sufficient"])


if __name__ == "__main__":
    unittest.main()
