"""Generate the Dart bundle for SecureGuide's embedded database migrations."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "migrations"
OUTPUT = ROOT / "mobile" / "lib" / "core" / "database" / "generated_migrations.dart"
FIRST_MOBILE_MIGRATION = 17


def _dart_raw_string(value: str) -> str:
    if "'''" in value:
        raise ValueError("migration contains an unsupported triple-quote sequence")
    return "r'''" + value + "'''"


def generate() -> None:
    paths = [
        path
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))
        if int(path.name[:3]) >= FIRST_MOBILE_MIGRATION
    ]
    if not paths:
        raise RuntimeError("no mobile migrations found")

    output = [
        "// GENERATED CODE - DO NOT EDIT.",
        "// Run: python -m scripts.generate_mobile_migrations",
        "",
        "final class EmbeddedMigration {",
        "  const EmbeddedMigration({",
        "    required this.version,",
        "    required this.filename,",
        "    required this.sha256,",
        "    required this.sql,",
        "  });",
        "",
        "  final String version;",
        "  final String filename;",
        "  final String sha256;",
        "  final String sql;",
        "}",
        "",
        "const embeddedMigrations = <EmbeddedMigration>[",
    ]

    for path in paths:
        sql = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        output.extend(
            [
                "  EmbeddedMigration(",
                f"    version: '{path.name[:3]}',",
                f"    filename: '{path.name}',",
                f"    sha256: '{digest}',",
                "    sql:",
                f"        {_dart_raw_string(sql)},",
                "  ),",
            ]
        )

    output.extend(["];"])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    generate()
