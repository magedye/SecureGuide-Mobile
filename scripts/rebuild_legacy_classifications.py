"""Explicitly rebuild the pinned recovered-catalog semantic classifications."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from secureguide.catalog_validation import canonical_hash, portable_text_hash
from secureguide.semantic_classification import (
    CLASSIFIER_VERSION,
    classify_record,
    semantic_tokens,
)


DEFAULT_SOURCE = ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "legacy_catalog_v4_recovered.json"
DEFAULT_REFERENCE = ROOT / "consolidation" / "curated" / "classifications.json"
DEFAULT_OUTPUT = ROOT / "consolidation" / "curated" / "legacy_classifications.json"
PINNED_GENERATED_AT = "2026-08-14T00:00:00Z"


def build_payload(source: Path, reference_path: Path) -> dict:
    envelope = json.loads(source.read_text(encoding="utf-8"))
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    for item in reference:
        item["_semantic_tokens"] = semantic_tokens(
            f"{item.get('title_en', '')} {item.get('definition_short_en', '')}"
        )
    items = []
    for index, record in enumerate(envelope["artifacts"]):
        result = classify_record(record, reference=reference)
        result.update(
            {
                "raw_id": f"legacy_catalog_v4::{index:04d}",
                "source_external_id": record.get("raw_artifact_id"),
            }
        )
        items.append(result)
    payload = {
        "schema_version": 1,
        "classifier_version": CLASSIFIER_VERSION,
        "source_catalog_id": "legacy_catalog_v4",
        "source_file": source.relative_to(ROOT).as_posix(),
        "input_sha256": portable_text_hash(source),
        "reference_file": reference_path.relative_to(ROOT).as_posix(),
        "reference_sha256": portable_text_hash(reference_path),
        "generated_at": PINNED_GENERATED_AT,
        "item_count": len(items),
        "items": items,
    }
    payload["semantic_sha256"] = canonical_hash(payload)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild", action="store_true", help="required explicit rebuild acknowledgement")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if not args.rebuild:
        parser.error("classification regeneration is explicit; pass --rebuild")
    payload = build_payload(args.source.resolve(), args.reference.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"wrote {args.output} ({payload['item_count']} items, "
        f"semantic sha256 {payload['semantic_sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
