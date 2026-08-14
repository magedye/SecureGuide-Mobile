import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MOBILE_LIB = REPO_ROOT / "mobile" / "lib"
ARABIC_TEXT = re.compile(r"[\u0600-\u06ff]")


class MobileLocalizationTests(unittest.TestCase):
    def test_arabic_and_english_catalogs_have_matching_message_keys(self) -> None:
        catalogs = {}
        for language in ("ar", "en"):
            path = MOBILE_LIB / "l10n" / f"app_{language}.arb"
            data = json.loads(path.read_text(encoding="utf-8"))
            catalogs[language] = {key for key in data if not key.startswith("@")}

        self.assertEqual(catalogs["ar"], catalogs["en"])

    def test_ui_sources_do_not_embed_arabic_copy(self) -> None:
        sources = [MOBILE_LIB / "main.dart"]
        sources.extend(sorted((MOBILE_LIB / "src" / "screens").glob("*.dart")))

        embedded = {}
        for path in sources:
            matches = [
                (line_number, line.strip())
                for line_number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), start=1
                )
                if ARABIC_TEXT.search(line)
            ]
            if matches:
                embedded[str(path.relative_to(REPO_ROOT))] = matches

        self.assertEqual({}, embedded)

    def test_screen_sources_use_generated_localizations(self) -> None:
        for path in sorted((MOBILE_LIB / "src" / "screens").glob("*.dart")):
            with self.subTest(screen=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertIn("app_localizations.dart", source)


if __name__ == "__main__":
    unittest.main()
