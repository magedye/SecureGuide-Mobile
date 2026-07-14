"""Tests for the workflow-role authorization seam."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from secureguide import (
    Database,
    MappingAuthorizer,
    SecureGuideService,
    TrustingAuthorizer,
    apply_migrations,
)
from secureguide.errors import AuthorizationError, SecureGuideError
from tests.test_profile_workflow import seed_catalog


ROOT = Path(__file__).resolve().parent.parent


class AuthorizationSeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "authz.db"
        apply_migrations(self.path, ROOT / "migrations")
        seed_catalog(self.path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _service(self, authorizer=None) -> SecureGuideService:
        service = SecureGuideService(Database(self.path), authorizer=authorizer)
        # Profile setup is not role-gated; reuse a fresh trusting service for it
        # so tests can target the authorizer purely on the governed operations.
        return service

    def _seed_profile(self) -> None:
        setup = SecureGuideService(Database(self.path))
        setup.create_profile(name="Profile One", profile_id="P1", activate=True)
        setup.select_artifacts(["A-IDENTITY"], profile_id="P1", selected_by="selector")

    def test_default_is_trusting_and_preserves_behavior(self) -> None:
        self._seed_profile()
        service = self._service()  # default TrustingAuthorizer
        self.assertIsInstance(service.authorizer, TrustingAuthorizer)
        draft = service.create_blueprint_draft(
            "A-IDENTITY", profile_id="P1", created_by="anyone"
        )
        self.assertEqual(draft["workflow_status"], "DRAFT")

    def test_mapping_authorizer_blocks_ungranted_role(self) -> None:
        self._seed_profile()
        # 'alice' may author but not approve; 'bob' may approve but not author.
        authz = MappingAuthorizer({"alice": ["AUTHOR"], "bob": ["APPROVER", "REVIEWER"]})
        service = self._service(authz)

        with self.assertRaises(AuthorizationError):
            service.create_blueprint_draft(
                "A-IDENTITY", profile_id="P1", created_by="bob"
            )
        draft = service.create_blueprint_draft(
            "A-IDENTITY", profile_id="P1", created_by="alice"
        )
        service.submit_blueprint(draft["id"], profile_id="P1", submitted_by="alice")

        # alice cannot approve — not entitled to APPROVER.
        with self.assertRaises(AuthorizationError):
            service.approve_blueprint(
                draft["id"], profile_id="P1", approved_by="alice", actor_role="APPROVER"
            )
        approved = service.approve_blueprint(
            draft["id"], profile_id="P1", approved_by="bob"
        )
        self.assertEqual(approved["workflow_status"], "APPROVED")

        # Task materialization is APPROVER-gated too.
        with self.assertRaises(AuthorizationError):
            service.materialize_blueprint_tasks(
                draft["id"], profile_id="P1", created_by="alice"
            )
        result = service.materialize_blueprint_tasks(
            draft["id"], profile_id="P1", created_by="bob"
        )
        self.assertGreaterEqual(result["created"], 1)

    def test_unknown_actor_is_denied(self) -> None:
        self._seed_profile()
        service = self._service(MappingAuthorizer({"alice": ["AUTHOR"]}))
        with self.assertRaises(AuthorizationError):
            service.create_blueprint_draft(
                "A-IDENTITY", profile_id="P1", created_by="stranger"
            )

    def test_enrichment_is_authorized(self) -> None:
        self._seed_profile()
        service = self._service(MappingAuthorizer({"alice": ["AUTHOR"]}))
        draft = service.create_blueprint_draft(
            "A-IDENTITY", profile_id="P1", created_by="alice"
        )
        pattern_id = service.search_operational_patterns(limit=1)["results"][0]["patternId"]
        with self.assertRaises(AuthorizationError):
            service.enrich_blueprint_from_pattern(
                draft["id"], profile_id="P1", pattern_id=pattern_id,
                selected_by="mallory", selection_reason="not entitled",
            )
        detail = service.enrich_blueprint_from_pattern(
            draft["id"], profile_id="P1", pattern_id=pattern_id,
            selected_by="alice", selection_reason="entitled author",
        )
        self.assertEqual(len(detail["pattern_enrichments"]), 1)

    def test_authorization_error_is_presentation_safe(self) -> None:
        # AuthorizationError must be catchable as the CLI's base error (exit code 2).
        self.assertTrue(issubclass(AuthorizationError, SecureGuideError))


if __name__ == "__main__":
    unittest.main()
