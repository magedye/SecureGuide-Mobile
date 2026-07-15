"""Contract tests for the read-model / DTO layer.

These lock down the *shape* of the ``read-model-v1`` wire contract, not volatile
values: golden fixtures are compared after scrubbing ids and timestamps, keys
are asserted to be ``camelCase``, every payload is asserted to be versioned, and
the layer is asserted to recompute nothing it received from the service.
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from secureguide import (
    CONTRACT_VERSION,
    Database,
    ReadModel,
    SecureGuideService,
    apply_migrations,
)
from secureguide.read_models import (
    AssessmentRecord,
    BlueprintDetail,
    BlueprintSummary,
    CatalogItem,
    DashboardCounts,
    GapItem,
    OperationalItem,
    ProfileSummary,
    RecommendationItem,
    ScoreView,
    TaskItem,
)
from secureguide.errors import NotFoundError
from scripts.dump_read_model_contract import (
    SURFACES,
    build_read_model_dataset,
    finalize,
)
from tests.test_profile_workflow import seed_catalog

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "read_models"

_CAMEL = re.compile(r"^[a-z][a-zA-Z0-9]*$")
# Dicts whose *keys* are data (e.g. domain codes), not contract field names.
_DATA_MAP_KEYS = {"domainScores"}


class ReadModelContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        db_path = Path(self.temp.name) / "read_model.db"
        apply_migrations(db_path, ROOT / "migrations")
        seed_catalog(db_path)
        self.service = SecureGuideService(Database(db_path))
        self.context = build_read_model_dataset(self.service)
        self.read_model = ReadModel(self.service)

    def tearDown(self) -> None:
        self.temp.cleanup()

    # -- golden fixtures --------------------------------------------------- #
    def test_every_surface_has_a_committed_golden(self) -> None:
        on_disk = {path.stem for path in FIXTURES.glob("*.json")}
        self.assertEqual(set(SURFACES), on_disk)

    def test_surfaces_match_scrubbed_goldens(self) -> None:
        for name, render in SURFACES.items():
            with self.subTest(surface=name):
                golden = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
                actual = finalize(render(self.read_model, self.context))
                self.assertEqual(
                    golden,
                    actual,
                    f"{name} drifted from its golden; regenerate with "
                    "`python -m scripts.dump_read_model_contract` after an intended change",
                )

    # -- envelope + naming convention -------------------------------------- #
    def test_every_payload_is_versioned(self) -> None:
        self.assertEqual(CONTRACT_VERSION, "read-model-v1")
        for name, render in SURFACES.items():
            with self.subTest(surface=name):
                payload = render(self.read_model, self.context)
                self.assertEqual(payload.get("contractVersion"), CONTRACT_VERSION)

    def test_all_keys_are_camel_case(self) -> None:
        for name, render in SURFACES.items():
            with self.subTest(surface=name):
                self._assert_camel(render(self.read_model, self.context), name)

    def _assert_camel(self, node: object, path: str, parent_key: str | None = None) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if parent_key not in _DATA_MAP_KEYS:
                    self.assertRegex(key, _CAMEL, f"non-camelCase key at {path}.{key}")
                self._assert_camel(value, f"{path}.{key}", parent_key=key)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                self._assert_camel(item, f"{path}[{index}]", parent_key=parent_key)

    # -- purity: the layer recomputes nothing ------------------------------ #
    def test_dashboard_passes_service_values_through_unchanged(self) -> None:
        raw = self.service.dashboard(profile_id=self.context["profile_id"])
        wire = self.read_model.dashboard(profile_id=self.context["profile_id"])
        self.assertEqual(wire["score"]["overall"], raw["score"]["overall"])
        self.assertEqual(wire["score"]["domainScores"], raw["score"]["domain_scores"])
        self.assertEqual(wire["counts"]["totalItems"], raw["counts"]["total_items"])
        self.assertEqual(wire["counts"]["openGaps"], raw["counts"]["open_gaps"])
        self.assertEqual(len(wire["gaps"]), len(raw["gaps"]))
        self.assertEqual(wire["gaps"][0]["artifactId"], raw["gaps"][0]["artifact_id"])

    def test_sqlite_int_flags_become_real_booleans(self) -> None:
        detail = self.read_model.blueprint(
            self.context["blueprint_id"], profile_id=self.context["profile_id"]
        )["blueprint"]
        self.assertIs(detail["generationRequiresReview"], False)
        self.assertIsInstance(detail["actions"][0]["taskable"], bool)
        self.assertIsInstance(detail["evidence"][0]["mandatory"], bool)

    def test_catalog_is_selected_flag_reflects_join(self) -> None:
        page = self.read_model.catalog(profile_id=self.context["profile_id"], limit=50)
        selected = {item["id"]: item["isSelected"] for item in page["items"]}
        self.assertTrue(selected["A-IDENTITY"])  # selected in the workflow
        self.assertFalse(selected["A-POLICY"])  # never selected

    # -- resilience: DTOs tolerate absent columns -------------------------- #
    def test_dtos_tolerate_missing_columns(self) -> None:
        dtos = [
            ProfileSummary,
            ScoreView,
            DashboardCounts,
            GapItem,
            RecommendationItem,
            OperationalItem,
            AssessmentRecord,
            CatalogItem,
            BlueprintSummary,
            BlueprintDetail,
            TaskItem,
        ]
        for dto in dtos:
            with self.subTest(dto=dto.__name__):
                wire = dto.from_row({}).to_wire()
                self.assertIsInstance(wire, dict)
                self.assertTrue(wire)  # a stable key set even with no input

    def test_missing_active_profile_returns_null_profile(self) -> None:
        empty_path = Path(self.temp.name) / "empty.db"
        apply_migrations(empty_path, ROOT / "migrations")
        empty = SecureGuideService(Database(empty_path))
        payload = ReadModel(empty).active_profile()
        self.assertEqual(payload["contractVersion"], CONTRACT_VERSION)
        self.assertIsNone(payload["profile"])

    def test_profile_artifact_history_is_profile_scoped_and_newest_first(self) -> None:
        payload = self.read_model.profile_artifact(
            "A-IDENTITY", profile_id=self.context["profile_id"]
        )
        self.assertEqual(payload["profileId"], "P-HQ")
        self.assertEqual(payload["artifact"]["artifactId"], "A-IDENTITY")
        self.assertEqual(len(payload["assessments"]), 1)
        self.assertEqual(payload["assessments"][0]["assessorName"], "auditor")

        with self.assertRaises(NotFoundError):
            self.read_model.profile_artifact("A-IDENTITY", profile_id="P-AUDIT")


if __name__ == "__main__":
    unittest.main()
