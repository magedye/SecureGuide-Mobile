"""Functional and governance tests for the transient blueprint MVP."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_blueprint_rule_pack import build_rules
from secureguide import Database, SecureGuideService, apply_migrations
from secureguide.blueprints import BlueprintEngine, ClassificationContext, load_rule_pack
from secureguide.blueprints.rules import RulePackError
from secureguide.database import connect


ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = ROOT / "reference" / "blueprint_rules_mvp_v1.json"


def context(
    artifact_type: str,
    nature: str | None = None,
    function: str | None = None,
    *,
    domain: str = "SD-01",
    obligation: str = "OBL-MND",
    confidence: float | None = .9,
    review: str = "AIR-HUMAN-APPROVED",
) -> ClassificationContext:
    return ClassificationContext(
        artifact_id=f"TEST-{artifact_type}", artifact_type=artifact_type,
        primary_domain=domain, sub_domain=f"{domain}.01",
        obligation_level=obligation, control_nature=nature,
        control_function=function, classification_confidence=confidence,
        ai_review_status=review,
    )


class RulePackTests(unittest.TestCase):
    def test_committed_rule_pack_matches_builder(self) -> None:
        payload = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["rules"], build_rules())
        self.assertEqual(len(payload["rules"]), 30)
        self.assertTrue((ROOT / "reference" / "blueprint_rule_schema_v1.json").exists())

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text(
                '{"ruleSetId":"x","ruleSetId":"y","ruleSetVersion":"1",'
                '"engineCompatibility":"1","status":"ACTIVE","rules":[]}',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RulePackError, "duplicate JSON key"):
                load_rule_pack(path)

    def test_modifier_cannot_change_action_plan_type(self) -> None:
        payload = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        payload["rules"][8]["then"]["actionPlanType"] = "ILLEGAL_OVERRIDE"
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad-stage.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(RulePackError, "only ARTIFACT_TYPE"):
                load_rule_pack(path)


class BlueprintEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = BlueprintEngine()

    def test_all_mvp_artifact_types_select_the_expected_plan(self) -> None:
        expected = {
            "ART-POL": "POLICY_LIFECYCLE",
            "ART-STD": "STANDARD_BASELINE",
            "ART-PRC": "PROCEDURE_EXECUTION",
            "ART-CTR": "CONTROL_IMPLEMENTATION",
            "ART-REQ": "REQUIREMENT_SATISFACTION",
            "ART-EVD": "EVIDENCE_MANAGEMENT",
            "ART-MET": "METRIC_LIFECYCLE",
            "ART-RSK": "RISK_TREATMENT",
        }
        for artifact_type, plan_type in expected.items():
            with self.subTest(artifact_type=artifact_type):
                item = self.engine.generate(context(artifact_type))
                self.assertEqual(item.action_plan_type, plan_type)
                self.assertFalse(item.authoritative)
                self.assertEqual(item.approval_status, "GENERATED")
                self.assertGreaterEqual(len(item.actions), 4)
                self.assertGreaterEqual(len(item.evidence), 3)
                self.assertTrue(all(action.source_rule_ids for action in item.actions))
                self.assertTrue(all(evidence.source_rule_ids for evidence in item.evidence))

    def test_seven_required_examples_and_alias_governance(self) -> None:
        examples = [
            ("ART-POL", "NAT-GOV", "FUN-DIR", True),
            ("ART-CTR", "NAT-TEC", "FUN-PRV", False),
            ("ART-PRC", "NAT-OPS", "FUN-DET", True),
            ("ART-STD", "NAT-TEC", "FUN-COR", False),
            ("ART-REQ", "NAT-LEG", "FUN-COMP", True),
            ("ART-EVD", "NAT-OPS", None, True),
            ("ART-RSK", "NAT-GOV", None, False),
        ]
        for artifact_type, nature, function, needs_review in examples:
            with self.subTest(artifact_type=artifact_type, nature=nature, function=function):
                item = self.engine.generate(context(artifact_type, nature, function))
                self.assertEqual(item.requires_human_review, needs_review)
                self.assertEqual(
                    [rule.stage for rule in item.applied_rules],
                    sorted(
                        [rule.stage for rule in item.applied_rules],
                        key={"ARTIFACT_TYPE": 0, "CONTROL_NATURE": 1, "CONTROL_FUNCTION": 2, "SECURITY_DOMAIN": 3, "OBLIGATION_LEVEL": 4}.get,
                    ),
                )

    def test_semantic_dedup_merges_source_rule_ids(self) -> None:
        payload = json.loads(RULES_PATH.read_text(encoding="utf-8"))
        duplicate = copy.deepcopy(payload["rules"][8])
        duplicate["ruleId"] = "BR-NAT-ORG-DEDUP-TEST"
        duplicate["priority"] = 99
        duplicate["when"] = {"controlNatures": ["NAT-TEC"]}
        duplicate["then"] = {"actions": [{
            "actionCode": "ACT-CTR-DESIGN", "semanticKey": "control.design",
            "title": "تصميم الضابط", "description": "تخصيص التصميم التقني",
            "category": "IMPLEMENTATION", "phase": "IMPLEMENT", "taskable": True,
        }]}
        payload["rules"].append(duplicate)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "dedup.json"
            path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            generated = BlueprintEngine(load_rule_pack(path)).generate(
                context("ART-CTR", "NAT-TEC", "FUN-PRE", domain="SD-04")
            )
        items = [item for item in generated.actions if item.semantic_key == "control.design"]
        self.assertEqual(len(items), 1)
        self.assertEqual(set(items[0].source_rule_ids), {"BR-ART-CTR", "BR-NAT-ORG-DEDUP-TEST"})

    def test_confidence_is_technical_and_not_an_approval_signal(self) -> None:
        low = self.engine.generate(context(
            "ART-CTR", "NAT-TEC", "FUN-PRE", confidence=.65,
            review="AIR-HUMAN-REVIEW",
        ))
        approved_classification = self.engine.generate(context(
            "ART-CTR", "NAT-TEC", "FUN-PRE", confidence=.65,
            review="AIR-HUMAN-APPROVED",
        ))
        self.assertTrue(low.requires_human_review)
        self.assertGreater(approved_classification.confidence, low.confidence)
        self.assertEqual(low.approval_status, approved_classification.approval_status)
        self.assertFalse(approved_classification.authoritative)
        self.assertAlmostEqual(sum({
            "completeness": .22, "specificity": .20, "classificationQuality": .20,
            "conflictFree": .15, "ruleMaturity": .13, "normalizationQuality": .10,
        }.values()), 1.0)

    def test_mvp_solutions_are_vendor_neutral(self) -> None:
        generated = self.engine.generate(context("ART-CTR", "NAT-TEC", "FUN-PRE"))
        self.assertTrue(generated.suggested_solutions)
        self.assertTrue(all(item.vendor_neutral for item in generated.suggested_solutions))


class BlueprintServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "service.db"
        apply_migrations(self.path, ROOT / "migrations")
        conn = connect(self.path)
        try:
            conn.execute(
                """INSERT INTO security_artifacts(
                    id,type,title_en,primary_domain,sub_domain,abstraction_level,
                    source,source_type,obligation_level,granularity_level,
                    control_nature,control_function,testability,priority,priority_weight,
                    publication_status,source_document,source_section,
                    classification_confidence,classification_rationale,
                    ai_review_status,requires_human_review)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                ("A-BP", "ART-CTR", "Blueprint test", "SD-04", "SD-04.01", "ABS-CTR",
                 "SRC-STD", "STANDARD", "OBL-MND", "GRN-DETAILED",
                 "NAT-TEC", "FUN-PRE", "TST-MAN", "PRI-HIGH", 7, "APPROVED",
                 "Test standard", "Section 1", .95, "Reviewed classification",
                 "AIR-HUMAN-APPROVED", 0),
            )
        finally:
            conn.close()
        self.service = SecureGuideService(Database(self.path))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_generation_is_read_only_and_not_in_official_report(self) -> None:
        conn = connect(self.path)
        try:
            before = dict(conn.execute(
                "SELECT (SELECT COUNT(*) FROM security_artifacts) artifacts, "
                "(SELECT COUNT(*) FROM enterprise_profiles) profiles, "
                "(SELECT COUNT(*) FROM promotion_audit_log) audit_events"
            ).fetchone())
        finally:
            conn.close()
        result = self.service.generate_blueprint("A-BP")
        self.assertFalse(result["authoritative"])
        self.assertNotIn("Test standard", [item.get("sourceCitation") for item in result["evidence"]])
        conn = connect(self.path)
        try:
            after = dict(conn.execute(
                "SELECT (SELECT COUNT(*) FROM security_artifacts) artifacts, "
                "(SELECT COUNT(*) FROM enterprise_profiles) profiles, "
                "(SELECT COUNT(*) FROM promotion_audit_log) audit_events"
            ).fetchone())
        finally:
            conn.close()
        self.assertEqual(before, after)
        profile = self.service.create_profile(name="Report test", activate=True)
        report = self.service.report(profile_id=profile["id"])
        rendered = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("GeneratedBlueprint", rendered)
        self.assertNotIn("blueprintId", rendered)


if __name__ == "__main__":
    unittest.main()
