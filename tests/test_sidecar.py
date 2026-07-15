"""Contract tests for the read-model HTTP sidecar.

The sidecar must return the *exact* `read-model-v1` payloads. We assert that by
finalizing each route's body (scrub + normalize) and comparing to the shared
golden fixtures — the same guard the Python and Dart contract tests use — so the
Python core, the transport, and the Dart client can never drift apart. A single
real-socket smoke test proves the HTTP path itself.
"""

from __future__ import annotations

import json
import threading
import unittest
import urllib.request
from pathlib import Path

from secureguide import (
    Database,
    ReadModel,
    SecureGuideService,
    WriteModel,
    apply_migrations,
)
from secureguide.read_models import CONTRACT_VERSION
from secureguide.sidecar import build_server, resolve, resolve_write
from scripts.dump_read_model_contract import build_read_model_dataset, finalize
from tests.test_profile_workflow import seed_catalog

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "read_models"

# Golden surface name -> (path, query) that must reproduce it. Parameterized
# routes (blueprint detail) are covered separately using the workflow context.
STATIC_ROUTES = {
    "profiles": ("/read/profiles", {}),
    "active_profile": ("/read/active-profile", {}),
    "dashboard": ("/read/dashboard", {"profileId": ["P-HQ"]}),
    "catalog": ("/read/catalog", {"profileId": ["P-HQ"], "locale": ["en"], "limit": ["50"]}),
    "profile_artifact": (
        "/read/profile-artifacts/A-IDENTITY",
        {"profileId": ["P-HQ"]},
    ),
    "blueprints": ("/read/blueprints", {"profileId": ["P-HQ"]}),
    "tasks": ("/read/tasks", {"profileId": ["P-HQ"]}),
    "report": ("/read/report", {"profileId": ["P-HQ"]}),
}


class SidecarContractTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "sidecar.db"
        apply_migrations(self.db_path, ROOT / "migrations")
        seed_catalog(self.db_path)
        self.service = SecureGuideService(Database(self.db_path))
        self.context = build_read_model_dataset(self.service)
        self.read_model = ReadModel(self.service)
        self.write_model = WriteModel(self.service)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _golden(self, name: str) -> dict:
        return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))

    def test_static_routes_return_their_golden_payloads(self) -> None:
        for name, (path, query) in STATIC_ROUTES.items():
            with self.subTest(route=path):
                status, payload = resolve(self.read_model, path, query)
                self.assertEqual(status, 200)
                self.assertEqual(finalize(payload), self._golden(name))

    def test_blueprint_detail_route_returns_its_golden_payload(self) -> None:
        path = f"/read/blueprints/{self.context['blueprint_id']}"
        status, payload = resolve(self.read_model, path, {"profileId": ["P-HQ"]})
        self.assertEqual(status, 200)
        self.assertEqual(finalize(payload), self._golden("blueprint_detail"))

    def test_unknown_route_is_404(self) -> None:
        status, payload = resolve(self.read_model, "/read/nope", {})
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "NotFound")

    def test_missing_blueprint_is_404(self) -> None:
        status, payload = resolve(
            self.read_model, "/read/blueprints/ABP-DOESNOTEXIST", {"profileId": ["P-HQ"]}
        )
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "NotFoundError")

    def test_bad_integer_query_is_400(self) -> None:
        status, payload = resolve(
            self.read_model, "/read/catalog", {"profileId": ["P-HQ"], "limit": ["abc"]}
        )
        self.assertEqual(status, 400)

    # -- write routes ------------------------------------------------------ #
    def test_create_profile_route_writes_and_reads_back(self) -> None:
        status, payload = resolve_write(
            self.write_model,
            "/write/profiles",
            {"name": "فرع جدة", "profileKind": "branch", "activate": True},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["contractVersion"], CONTRACT_VERSION)
        self.assertEqual(payload["profile"]["name"], "فرع جدة")
        self.assertTrue(payload["profile"]["isActive"])

        new_id = payload["profile"]["id"]
        self.assertEqual(self.read_model.active_profile()["profile"]["id"], new_id)
        ids = [p["id"] for p in self.read_model.profiles()["profiles"]]
        self.assertIn(new_id, ids)

    def test_create_profile_without_name_is_400(self) -> None:
        status, payload = resolve_write(self.write_model, "/write/profiles", {})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "ValidationError")

    def test_activate_profile_route_switches_active(self) -> None:
        status, payload = resolve_write(
            self.write_model, "/write/active-profile", {"profileId": "P-AUDIT"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["profile"]["id"], "P-AUDIT")
        self.assertTrue(payload["profile"]["isActive"])
        self.assertEqual(self.read_model.active_profile()["profile"]["id"], "P-AUDIT")

    def test_activate_unknown_profile_is_404(self) -> None:
        status, _ = resolve_write(
            self.write_model, "/write/active-profile", {"profileId": "PRF-NOPE"}
        )
        self.assertEqual(status, 404)

    def test_select_artifacts_route_selects_and_reads_back(self) -> None:
        # A-POLICY is seeded and APPROVED but not selected by the demo workflow.
        status, payload = resolve_write(
            self.write_model,
            "/write/select-artifacts",
            {"artifactIds": ["A-POLICY"], "selectedBy": "analyst", "profileId": "P-HQ"},
        )
        self.assertEqual(status, 200)
        selection = payload["selection"]
        self.assertEqual(selection["requested"], 1)
        self.assertEqual(selection["created"], 1)

        selected_ids = [
            item["id"]
            for item in self.read_model.catalog(profile_id="P-HQ", selected_only=True)["items"]
        ]
        self.assertIn("A-POLICY", selected_ids)

    def test_select_artifacts_without_actor_is_400(self) -> None:
        status, _ = resolve_write(
            self.write_model, "/write/select-artifacts", {"artifactIds": ["A-POLICY"]}
        )
        self.assertEqual(status, 400)

    def test_select_artifacts_with_no_ids_is_400(self) -> None:
        status, _ = resolve_write(
            self.write_model, "/write/select-artifacts", {"selectedBy": "analyst"}
        )
        self.assertEqual(status, 400)

    def test_assessment_route_updates_state_and_appends_history(self) -> None:
        status, payload = resolve_write(
            self.write_model,
            "/write/assessments",
            {
                "artifactId": "A-IDENTITY",
                "profileId": "P-HQ",
                "assessorName": "second-auditor",
                "implementationStatus": "STS-PARTIAL",
                "verificationStatus": "VER-FAIL",
                "effectiveness": "EFF-MEDIUM",
                "assignedOwner": "IAM Operations",
                "dueDate": "2026-11-30",
                "notes": "Remediation is assigned.",
                "priorityOverride": "PRI-CRITICAL",
                "reviewFrequencyOverride": "MONTHLY",
                "score": 55,
                "comments": "A remediation action remains open.",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["assessment"]["assessorName"], "second-auditor")
        self.assertEqual(payload["artifact"]["implementationStatus"], "STS-PARTIAL")
        self.assertEqual(payload["artifact"]["priorityOverride"], "PRI-CRITICAL")

        detail = self.read_model.profile_artifact("A-IDENTITY", profile_id="P-HQ")
        self.assertEqual(len(detail["assessments"]), 2)
        self.assertEqual(detail["assessments"][0]["assessorName"], "second-auditor")
        self.assertEqual(detail["artifact"]["exceptionStatus"], "EXC-NONE")

        status, cleared = resolve_write(
            self.write_model,
            "/write/assessments",
            {
                "artifactId": "A-IDENTITY",
                "profileId": "P-HQ",
                "assessorName": "second-auditor",
                "clearPriorityOverride": True,
                "clearReviewFrequencyOverride": True,
                "clearDueDate": True,
                "clearAssignedOwner": True,
                "clearNotes": True,
            },
        )
        self.assertEqual(status, 200)
        self.assertIsNone(cleared["artifact"]["priorityOverride"])
        self.assertIsNone(cleared["artifact"]["reviewFrequencyOverride"])
        self.assertIsNone(cleared["artifact"]["dueDate"])
        self.assertIsNone(cleared["artifact"]["assignedOwner"])
        self.assertIsNone(cleared["artifact"]["notes"])

    def test_assessment_route_rejects_invalid_or_cross_profile_writes(self) -> None:
        status, payload = resolve_write(
            self.write_model,
            "/write/assessments",
            {"artifactId": "A-IDENTITY", "profileId": "P-HQ"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "ValidationError")

        status, payload = resolve_write(
            self.write_model,
            "/write/assessments",
            {
                "artifactId": "A-IDENTITY",
                "profileId": "P-AUDIT",
                "assessorName": "auditor",
            },
        )
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "NotFoundError")

    def test_real_socket_post_creates_a_profile(self) -> None:
        server = build_server(self.db_path, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            body = json.dumps({"name": "فرع الدمام", "activate": True}).encode("utf-8")
            request = urllib.request.Request(
                f"http://{host}:{port}/write/profiles",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                created = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(created["profile"]["name"], "فرع الدمام")

            with urllib.request.urlopen(f"http://{host}:{port}/read/profiles", timeout=5) as resp:
                names = [p["name"] for p in json.loads(resp.read().decode("utf-8"))["profiles"]]
            self.assertIn("فرع الدمام", names)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_real_socket_serves_json_over_loopback(self) -> None:
        server = build_server(self.db_path, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address
            with urllib.request.urlopen(f"http://{host}:{port}/read/profiles", timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                self.assertEqual(resp.headers.get_content_charset(), "utf-8")
                data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["contractVersion"], CONTRACT_VERSION)
            self.assertEqual(len(data["profiles"]), 2)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
