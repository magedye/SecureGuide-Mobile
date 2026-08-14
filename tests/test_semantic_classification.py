"""Semantic-classification regression tests for recovered catalog controls."""

from __future__ import annotations

import unittest

from secureguide.semantic_classification import classify_record


def record(title: str, description: str, section: str = "GRC-GOV") -> dict:
    return {
        "extracted_elements": {
            "title_draft": title,
            "description_draft": description,
        },
        "source_metadata": {"source_section": section},
        "recovery_provenance": {
            "original_raw_record": {"source_refs": ["NIST"]},
            "staging_evidence": {"proposed_priority": "PRI-MEDIUM"},
        },
    }


class SemanticClassificationTests(unittest.TestCase):
    def test_distinguishes_threat_requirement_configuration_and_policy(self) -> None:
        cases = (
            (
                record(
                    "T1556.003 - Authentication Modules",
                    "Adversaries may modify authentication modules to obtain credentials.",
                    "IAM-AUTH",
                ),
                "ART-THR",
            ),
            (
                record(
                    "V2.1.1 - Password Security",
                    "Verify that passwords are at least fifteen characters long.",
                    "APP-WEB",
                ),
                "ART-REQ",
            ),
            (
                record(
                    "Enforce Modern TLS",
                    "Disable TLS 1.0 and enforce TLS 1.2 or TLS 1.3.",
                    "IPS-CFG",
                ),
                "ART-CFG",
            ),
            (
                record(
                    "Acceptable Use Policy",
                    "An acceptable use policy must be established and communicated.",
                    "GRC-POLICY",
                ),
                "ART-POL",
            ),
        )
        for source, expected in cases:
            with self.subTest(expected=expected):
                result = classify_record(source)
                self.assertEqual(result["proposed_type"], expected)
                self.assertTrue(result["classification_rationale"])
                self.assertTrue(result["rejected_alternatives"])

    def test_item_semantics_override_misleading_source_section(self) -> None:
        source = record(
            "Quarterly vulnerability scans",
            "Perform automated vulnerability scans every quarter and remediate findings.",
            "IAM-PAM",
        )
        result = classify_record(source)
        self.assertEqual(result["proposed_primary_domain"], "SD-06")
        self.assertEqual(result["proposed_sub_domain"], "SD-06.03")
        self.assertNotEqual(result["proposed_primary_domain"], "SD-03")

    def test_classifies_metric_vulnerability_process_procedure_and_control(self) -> None:
        cases = (
            (record("Patch latency KPI", "Measure mean time to remediate vulnerabilities.", "IPS-VULN"), "ART-MET"),
            (record("Weak session identifier", "A weakness in session identifiers allows account takeover.", "APP-WEB"), "ART-VUL"),
            (record("Access review process", "Establish and maintain a process for access reviews.", "IAM-REVIEW"), "ART-PRO"),
            (record("Incident containment playbook", "Use a playbook with step by step containment actions.", "RCR-INC"), "ART-PRC"),
            (record("Network segmentation", "Separate sensitive networks to reduce lateral movement.", "IPS-NET"), "ART-CTR"),
        )
        for source, expected in cases:
            with self.subTest(expected=expected):
                result = classify_record(source)
                self.assertEqual(result["proposed_type"], expected)
                self.assertTrue(result["classification_rationale"])

    def test_low_confidence_tie_breaker_is_explicitly_reviewable(self) -> None:
        result = classify_record(
            record("Maintain safeguards", "Maintain safeguards.", "RCR-BCP")
        )
        self.assertLessEqual(result["classification_confidence"], 0.70)
        self.assertTrue(result["requires_human_review"])
        self.assertEqual(result["ai_review_status"], "AIR-HUMAN-REVIEW")

    def test_technique_identifier_is_threat_without_adversary_boilerplate(self) -> None:
        result = classify_record(record(
            "T1171 - LLMNR Poisoning",
            "Link-Local Multicast Name Resolution is an alternate host identification method.",
            "IPS-NET",
        ))
        self.assertEqual(result["proposed_type"], "ART-THR")

    def test_source_markup_moves_to_external_references(self) -> None:
        result = classify_record(record(
            "T1557 - Adversary in the Middle",
            "Adversaries may use [Network Sniffing](https://attack.example/T1040). (Citation: Source Note)",
            "IPS-NET",
        ))
        self.assertEqual(result["definition_short_en"], "Adversaries may use Network Sniffing.")
        self.assertEqual(result["external_references"], [{
            "type": "ARTICLE",
            "title": "Network Sniffing",
            "url": "https://attack.example/T1040",
        }])


if __name__ == "__main__":
    unittest.main()
