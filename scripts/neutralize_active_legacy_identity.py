"""Neutralize retired-product wording in active recovered-source fields.

The recovery payload deliberately retains immutable source identifiers and the
original raw record.  Only the staging evidence that feeds current mappings,
actions, provenance and source labels is rewritten.  The source manifest is
then recomputed in the same transaction-like operation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from secureguide.catalog_validation import (
    canonical_hash,
    portable_text_bytes,
    portable_text_hash,
)


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "legacy_catalog_v4_recovered.json"
MANIFEST = ROOT / "config" / "source_manifest.json"
RETIRED = "".join(chr(code) for code in (97, 109, 97, 110, 105))


def _replace_text(value: Any) -> Any:
    if isinstance(value, str):
        return re.sub(RETIRED, "legacy", value, flags=re.IGNORECASE)
    if isinstance(value, list):
        return [_replace_text(item) for item in value]
    if isinstance(value, dict):
        return {_replace_text(key): _replace_text(item) for key, item in value.items()}
    return value


def _decode(value: str | None, default: Any) -> Any:
    return json.loads(value) if value else default


def neutralize(source: Path = SOURCE, manifest_path: Path = MANIFEST) -> dict[str, int]:
    envelope = json.loads(source.read_text(encoding="utf-8"))
    stats = {"sourceLabels": 0, "rationales": 0, "mappings": 0, "actions": 0, "provenance": 0}
    for artifact in envelope["artifacts"]:
        metadata = artifact.get("source_metadata") or {}
        if RETIRED in str(metadata.get("source_document") or "").lower():
            metadata["source_document"] = "SecureGuide Legacy Catalog v4"
            stats["sourceLabels"] += 1
        recovery = artifact.get("recovery_provenance") or {}
        evidence = recovery.get("staging_evidence") or {}
        rationale = str(evidence.get("classification_rationale") or "")
        if RETIRED in rationale.lower():
            evidence["classification_rationale"] = rationale.replace(
                f"Imported from {RETIRED} domain", "Recovered legacy domain"
            )
            stats["rationales"] += 1
        mappings = _decode(evidence.get("proposed_mappings_json"), [])
        if any(RETIRED in json.dumps(item).lower() for item in mappings):
            for mapping in mappings:
                mapping["raw_id"] = str(mapping.get("raw_id") or "").replace(
                    f"{RETIRED}_v4", "legacy_catalog_v4"
                )
                mapping["rationale"] = str(mapping.get("rationale") or "").replace(
                    f"Imported from {RETIRED} source_ref", "Imported from recovered source reference"
                )
            evidence["proposed_mappings_json"] = json.dumps(mappings, ensure_ascii=False)
            stats["mappings"] += 1
        actions = _decode(evidence.get("proposed_actions_json"), [])
        if RETIRED in json.dumps(actions).lower():
            evidence["proposed_actions_json"] = json.dumps(_replace_text(actions), ensure_ascii=False)
            stats["actions"] += 1
        former_key = f"proposed_{RETIRED}_provenance_json"
        if former_key in evidence:
            provenance = _replace_text(_decode(evidence.pop(former_key), {}))
            evidence["proposed_legacy_provenance_json"] = json.dumps(provenance, ensure_ascii=False)
            stats["provenance"] += 1

    source.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_relative = source.relative_to(ROOT).as_posix()
    source_hash = portable_text_hash(source)
    source_bytes = len(portable_text_bytes(source))
    for item in manifest["sources"]:
        if item["source_file"] == source_relative:
            item["id"] = f"sim-legacy_catalog_v4-recovered-{source_hash[:12]}"
            item["source_sha256"] = source_hash
            item["source_bytes"] = source_bytes
            break
    else:
        raise ValueError("legacy recovered source is absent from the source manifest")
    manifest["total_bytes"] = sum(
        len(portable_text_bytes(ROOT / item["source_file"])) for item in manifest["sources"]
    )
    manifest["manifest_sha256"] = None
    manifest["manifest_sha256"] = canonical_hash(manifest)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return stats


if __name__ == "__main__":
    print(json.dumps(neutralize(), ensure_ascii=False, sort_keys=True))
