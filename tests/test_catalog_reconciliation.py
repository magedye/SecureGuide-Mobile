from __future__ import annotations

import copy
import unittest

from scripts.rebuild_unified_equivalence import rebuild
from secureguide.catalog_validation import canonical_hash


class CatalogReconciliationTests(unittest.TestCase):
    def test_all_source_discovery_is_deterministic_and_evidence_bearing(self) -> None:
        first, first_stats = rebuild("consolidation/unified/equivalence.json")
        second, second_stats = rebuild("consolidation/unified/equivalence.json")
        self.assertEqual(canonical_hash(first), canonical_hash(second))
        self.assertEqual(first_stats, second_stats)
        self.assertEqual(first_stats["groups"], 215)
        self.assertEqual(first_stats["cross_source_groups"], 24)
        self.assertEqual(first_stats["unified_size"], 1214)
        for group in first:
            self.assertGreaterEqual(len(group["members"]), 2)
            self.assertIn(group["canonical"], group["members"])
            self.assertTrue(group["decision_method"])
            self.assertTrue(group["rationale"])
            self.assertTrue(group["requires_human_review"])

    def test_detection_does_not_mutate_committed_decisions(self) -> None:
        groups, _ = rebuild("consolidation/unified/equivalence.json")
        snapshot = copy.deepcopy(groups)
        rebuild("consolidation/unified/equivalence.json")
        self.assertEqual(groups, snapshot)


if __name__ == "__main__":
    unittest.main()
