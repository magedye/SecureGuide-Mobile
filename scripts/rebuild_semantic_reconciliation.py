"""Build deterministic semantic-audit evidence from pinned raw catalogs."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from secureguide.catalog_validation import canonical_hash
from secureguide.semantic_classification import classify_record


ROOT = Path(__file__).resolve().parent.parent
CSF_SOURCES = (
    ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "nist_csf_2_0.json",
    ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "the_nist_cybersecurity_framework_csf_2_0.json",
)


def _raw_hash(record: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def build_csf_audit(sources: tuple[Path, ...] = CSF_SOURCES) -> dict[str, Any]:
    """Classify every pinned CSF outcome independently and retain no source prose."""

    records: list[dict[str, Any]] = []
    before: Counter[str] = Counter()
    after: Counter[str] = Counter()
    unresolved: list[dict[str, str]] = []
    for source in sources:
        envelope = json.loads(source.read_text(encoding="utf-8"))
        catalog_id = str((envelope.get("extraction_metadata") or {}).get("source_catalog_id"))
        for index, raw in enumerate(envelope.get("artifacts") or []):
            item = json.loads(json.dumps(raw))
            item.setdefault("source_metadata", {})["source_catalog_id"] = catalog_id
            raw_id = f"{catalog_id}::{index:04d}"
            before[str((raw.get("classification_status") or {}).get("usacm_type_assigned") or "UNCLASSIFIED")] += 1
            try:
                result = classify_record(item)
            except ValueError as error:
                unresolved.append({"rawId": raw_id, "rawHash": _raw_hash(raw), "reason": str(error)})
                continue
            after[result["proposed_type"]] += 1
            records.append({
                "rawId": raw_id,
                "rawHash": _raw_hash(raw),
                "type": result["proposed_type"],
                "abstractionLevel": result["proposed_abstraction_level"],
                "primaryDomain": result["proposed_primary_domain"],
                "subDomain": result["proposed_sub_domain"],
                "confidence": result["classification_confidence"],
                "requiresHumanReview": result["requires_human_review"],
                "method": result["classification_method"],
            })
    material = {
        "contract": "secureguide-csf-record-audit-v1",
        "sourceFiles": [source.relative_to(ROOT).as_posix() for source in sources],
        "totalRecords": len(records) + len(unresolved),
        "resolvedRecords": len(records),
        "unresolvedRecords": len(unresolved),
        "typeDistributionBefore": dict(sorted(before.items())),
        "typeDistributionAfter": dict(sorted(after.items())),
        "records": records,
        "unresolved": unresolved,
    }
    material["auditSha256"] = canonical_hash({**material, "auditSha256": None})
    return material


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "consolidation" / "semantic_audit.json")
    args = parser.parse_args()
    report = build_csf_audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("totalRecords", "resolvedRecords", "unresolvedRecords", "auditSha256")}, indent=2))


if __name__ == "__main__":
    main()
