from __future__ import annotations

import unittest

from scripts.validate_catalog_identity import scan


class CatalogIdentityTests(unittest.TestCase):
    def test_retired_identity_is_confined_to_compatibility_evidence(self) -> None:
        self.assertEqual(scan(), [])


if __name__ == "__main__":
    unittest.main()
