"""Build deterministic semantic-audit evidence from pinned raw catalogs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from secureguide.catalog_validation import canonical_hash
from secureguide.catalog_curation import (
    build_projection,
    final_artifact_id,
    load_curation_candidates,
    prepare_curation_database,
)
from secureguide.semantic_classification import (
    canonical_text,
    classify_record,
    normalize_text,
    semantic_tokens,
)


ROOT = Path(__file__).resolve().parent.parent
CSF_SOURCES = (
    ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "nist_csf_2_0.json",
    ROOT / "SecureGuide_Mobile_Docs" / "Raw_Catalogs" / "the_nist_cybersecurity_framework_csf_2_0.json",
)
CSF_SOURCE_IDS = (
    "nist_csf_2_0",
    "the_nist_cybersecurity_framework_csf_2_0",
)
CSF_OUTCOME_ID = re.compile(r"\b(?:GV|ID|PR|DE|RS|RC)\.[A-Z]{2}-\d+\b", re.IGNORECASE)


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


def _decision_hash(material: dict[str, Any]) -> str:
    return canonical_hash({**material, "ledger_sha256": None})


def _new_candidate(row: Any, result: dict[str, Any]) -> dict[str, Any]:
    artifact_type = result["proposed_type"]
    artifact_id = f"SG-{artifact_type[4:]}-SRC-{str(row['content_hash'])[:12].upper()}"
    title = result["title_en"]
    if not any(character.isalpha() for character in title):
        title = f"{row['source_document'] or row['source_catalog_id']} {row['source_section'] or title}"
    candidate = {
        "artifact_id": artifact_id,
        "candidate_id": f"STG-SRC-{str(row['content_hash'])[:12].upper()}",
        "source_key": "SRC",
        "raw_id": row["id"],
        "external_raw_id": row["external_raw_id"],
        "source_catalog_id": row["source_catalog_id"],
        "source_document": row["source_document"] or row["source_catalog_id"],
        "source_type_raw": row["source_type"] or "DOCUMENT",
        "source_version": row["source_version"] or "UNKNOWN",
        "source_section": row["source_section"],
        "title_en": title,
        "definition_short_en": result["definition_short_en"],
        "definition_full_en": canonical_text(row["raw_text_en"] or "") or None,
        "type": artifact_type,
        "abstraction_level": result["proposed_abstraction_level"],
        "primary_domain": result["proposed_primary_domain"],
        "sub_domain": result["proposed_sub_domain"],
        "obligation_level": result["proposed_obligation_level"],
        "requirement_type": result["proposed_requirement_type"],
        "control_nature": result["proposed_control_nature"],
        "control_function": result["proposed_control_function"],
        "testability": result["proposed_testability"],
        "priority": result["proposed_priority"],
        "classification_confidence": result["classification_confidence"],
        "classification_rationale": result["classification_rationale"],
        "requires_human_review": result["requires_human_review"],
        "mappings": [], "tags": [], "relationships": [], "actions": [],
        "external_references": result["external_references"],
    }
    return candidate


def _semantic_identifier(source_catalog_id: str, section: str | None, title: str) -> str | None:
    """Return only source-owned identifiers that can be independent evidence."""

    if source_catalog_id in CSF_SOURCE_IDS:
        matched = CSF_OUTCOME_ID.search(f"{section or ''} {title}")
        if matched:
            return f"CSF:{matched.group(0).upper()}"
    return None


def _title_key(title: str) -> str:
    """Ignore generated provenance suffixes, never meaningful source wording."""

    return normalize_text(re.sub(r"\s*\[RAW-[^\]]+\]\s*$", "", title, flags=re.IGNORECASE))


def _compatible(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return all(
        left[field] == right[field]
        for field in ("type", "primary_domain", "sub_domain", "abstraction_level")
    )


def _global_reconciliation(
    contexts: dict[str, dict[str, Any]], decisions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Discover global candidates and apply only identifier-backed equivalence.

    Lexical similarity is deliberately recorded as discovery evidence only.  A
    merge requires the two official CSF exports to name the same outcome and to
    contain the same normalized statement with compatible USACM/SDT semantics.
    """

    by_raw = {decision["raw_id"]: decision for decision in decisions}
    by_exact_statement: dict[tuple[str, str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    by_identifier: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for context in contexts.values():
        by_exact_statement[(
            context["type"], context["primary_domain"], context["sub_domain"],
            context["abstraction_level"], _title_key(context["title"]), context["statement_key"],
        )].append(context)
        if context.get("source_identifier"):
            by_identifier[context["source_identifier"]].append(context)

    reconciliations: list[dict[str, Any]] = []
    canonicalized: set[tuple[str, str]] = set()
    for members in by_exact_statement.values():
        targets = {member["target_artifact_id"] for member in members}
        if len(targets) < 2:
            continue
        # Stable curated identities have upgrade aliases already; retaining one
        # avoids creating a new identifier when the exact source content is
        # already represented.  Otherwise prefer the primary CSF export.
        target = min(
            members,
            key=lambda member: (
                member.get("target_is_preexisting") is not True,
                member["source_catalog_id"] != "the_nist_cybersecurity_framework_csf_2_0",
                member["raw_id"],
            ),
        )
        for source in members:
            pair = tuple(sorted((source["raw_id"], target["raw_id"])))
            if source is target or pair in canonicalized:
                continue
            source_decision = by_raw[source["raw_id"]]
            source_decision.pop("new_canonical", None)
            source_decision.update({
                "target_artifact_id": target["target_artifact_id"],
                "mapping_strength": "DIRECT",
                "decision_method": "NORMALIZED_EXACT_GLOBAL_EQUIVALENCE_V1",
                "confidence_state": "1.00",
                "rationale": (
                    f"Normalized title and atomic statement exactly match raw record {target['raw_id']}; "
                    f"the compatible canonical {target['target_artifact_id']} retains both source lineages."
                ),
            })
            source["target_artifact_id"] = target["target_artifact_id"]
            reconciliations.append({
                "rawIds": list(pair),
                "decision": "CANONICALIZE",
                "targetArtifactId": target["target_artifact_id"],
                "evidence": {
                    "titleMatch": "NORMALIZED_EXACT",
                    "statementMatch": "NORMALIZED_EXACT",
                    "semanticCompatibility": "TYPE_DOMAIN_LEVEL_EXACT",
                },
                "rationale": "The two source records express the same atomic statement with compatible semantics.",
            })
            canonicalized.add(pair)
    for identifier, members in sorted(by_identifier.items()):
        primary = [
            member for member in members
            if member["source_catalog_id"] == "the_nist_cybersecurity_framework_csf_2_0"
        ]
        duplicate = [member for member in members if member["source_catalog_id"] == "nist_csf_2_0"]
        if len(primary) != 1 or not duplicate:
            continue
        target = primary[0]
        for source in duplicate:
            if not _compatible(source, target):
                continue
            source_decision = by_raw[source["raw_id"]]
            target_decision = by_raw[target["raw_id"]]
            target_id = target_decision.get("target_artifact_id")
            if not target_id:
                continue
            source_decision.pop("new_canonical", None)
            source_decision.update({
                "target_artifact_id": target_id,
                "mapping_strength": "DIRECT",
                "decision_method": "AUTHORITATIVE_SOURCE_IDENTIFIER_EQUIVALENCE_V1",
                "confidence_state": "1.00",
                "rationale": (
                    f"Official CSF outcome {identifier[4:]} has the same normalized statement "
                    f"as the primary CSF export record {target['raw_id']}; both retain source lineage."
                ),
            })
            source["target_artifact_id"] = target_id
            reconciliations.append({
                "rawIds": [source["raw_id"], target["raw_id"]],
                "decision": "CANONICALIZE",
                "targetArtifactId": target_id,
                "evidence": {
                    "sourceIdentifier": identifier,
                    "statementMatch": "NORMALIZED_EXACT" if source["statement_key"] == target["statement_key"] else "SOURCE_VARIANT",
                    "semanticCompatibility": "TYPE_DOMAIN_LEVEL_EXACT",
                },
                "rationale": "The duplicate official CSF export is the same atomic framework outcome.",
            })
            canonicalized.add(tuple(sorted((source["raw_id"], target["raw_id"]))))

    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for context in contexts.values():
        groups[(
            context["type"], context["primary_domain"], context["sub_domain"],
            context["abstraction_level"],
        )].append(context)
    for group in groups.values():
        for left, right in combinations(sorted(group, key=lambda item: item["raw_id"]), 2):
            pair = tuple(sorted((left["raw_id"], right["raw_id"])))
            if pair in canonicalized or left["source_catalog_id"] == right["source_catalog_id"]:
                continue
            if left["target_artifact_id"] == right["target_artifact_id"]:
                continue
            left_tokens = semantic_tokens(f"{left['title']} {left['statement']}")
            right_tokens = semantic_tokens(f"{right['title']} {right['statement']}")
            union = left_tokens | right_tokens
            overlap = len(left_tokens & right_tokens)
            similarity = overlap / len(union) if union else 0.0
            left_title = semantic_tokens(left["title"])
            right_title = semantic_tokens(right["title"])
            title_union = left_title | right_title
            title_similarity = len(left_title & right_title) / len(title_union) if title_union else 0.0
            if not ((similarity >= 0.55 and overlap >= 4) or title_similarity >= 0.70):
                continue
            reconciliations.append({
                "rawIds": list(pair),
                "decision": "KEEP_SEPARATE",
                "targetArtifactIds": [left["target_artifact_id"], right["target_artifact_id"]],
                "evidence": {
                    "statementTokenJaccard": round(similarity, 4),
                    "titleTokenJaccard": round(title_similarity, 4),
                    "semanticCompatibility": "TYPE_DOMAIN_LEVEL_EXACT",
                },
                "rationale": (
                    "Lexical similarity is discovery evidence only; no authoritative crosswalk or "
                    "source-identifier equivalence establishes that these separately scoped source "
                    "statements are the same atomic security concept."
                ),
            })
    reconciliations.sort(key=lambda item: (item["decision"], item["rawIds"]))
    report = {
        "schema_version": 1,
        "reconciliation_sha256": None,
        "scope": {
            "rawRecordsConsidered": len(decisions),
            "reconciledRecords": len(contexts),
            "explicitlyDeferredRecords": len(decisions) - len(contexts),
            "sourceCatalogs": sorted({item["source_catalog_id"] for item in contexts.values()}),
            "methods": [
                "SOURCE_IDENTIFIER_AND_EXACT_STATEMENT",
                "NORMALIZED_EXACT_TITLE_AND_STATEMENT",
                "TOKEN_LEXICAL_DISCOVERY",
                "TYPE_DOMAIN_LEVEL_COMPATIBILITY",
            ],
        },
        "decisions": reconciliations,
        "counts": dict(sorted(Counter(item["decision"] for item in reconciliations).items())),
    }
    report["reconciliation_sha256"] = canonical_hash(report)
    return report


def build_semantic_ledger(base_database: Path) -> dict[str, Any]:
    """Create one source-hash-bound decision per record from pinned inputs."""

    import sqlite3
    from tempfile import TemporaryDirectory

    candidates = load_curation_candidates()
    projection = build_projection(candidates)
    existing_targets = {
        raw_id: final_artifact_id(candidates[selected])
        for raw_id, selected in projection["rawToCandidate"].items()
    }
    selected_candidates_by_final = {
        final_artifact_id(candidates[selected]): candidates[selected]
        for selected in projection["selected"]
    }
    with TemporaryDirectory() as temporary:
        database = Path(temporary) / "raw.db"
        prepare_curation_database(base_database, database)
        conn = sqlite3.connect(database)
        conn.row_factory = sqlite3.Row
        try:
            # Legacy staging mappings carry source lineage for any catalog row
            # outside the selected curated/legacy inputs.
            for row in conn.execute(
                "SELECT promoted_artifact_id, proposed_mappings_json FROM staging_artifacts "
                "WHERE promoted_artifact_id IS NOT NULL"
            ):
                for mapping in json.loads(row["proposed_mappings_json"] or "[]"):
                    if mapping.get("raw_id"):
                        existing_targets.setdefault(mapping["raw_id"], row["promoted_artifact_id"])
            for row in conn.execute(
                "SELECT raw_artifact_id,artifact_id FROM artifact_source_lineage"
            ):
                existing_targets.setdefault(row["raw_artifact_id"], row["artifact_id"])
            existing_signatures = {
                (normalize_text(row["title_en"]), normalize_text(row["definition_short_en"])): row["id"]
                for row in conn.execute("SELECT id,title_en,definition_short_en FROM security_artifacts")
            }
            used_titles = {
                normalize_text(row["title_en"])
                for row in conn.execute("SELECT title_en FROM security_artifacts")
            }
            used_titles.update(
                normalize_text(candidates[candidate_id]["title_en"])
                for candidate_id in projection["selected"]
            )
            generated_signatures: dict[tuple[str, str, str, str], str] = {}
            decisions: list[dict[str, Any]] = []
            contexts: dict[str, dict[str, Any]] = {}
            for row in conn.execute("SELECT * FROM raw_artifacts ORDER BY id"):
                raw_id = row["id"]
                target = existing_targets.get(raw_id)
                if target:
                    existing = conn.execute(
                        """SELECT title_en,definition_short_en,type,primary_domain,sub_domain,
                                  abstraction_level FROM security_artifacts WHERE id=?""",
                        (target,),
                    ).fetchone()
                    if existing is None and target in selected_candidates_by_final:
                        selected = selected_candidates_by_final[target]
                        existing = {
                            "title_en": selected["title_en"],
                            "definition_short_en": selected["definition_short_en"],
                            "type": selected["type"],
                            "primary_domain": selected["primary_domain"],
                            "sub_domain": selected["sub_domain"],
                            "abstraction_level": selected["abstraction_level"],
                        }
                    decisions.append({
                        "raw_id": raw_id, "source_content_sha256": row["content_hash"],
                        "disposition": "SUPPORTS_CANONICAL", "target_artifact_id": target,
                        "mapping_strength": "DIRECT", "decision_method": "PINNED_EXISTING_LINEAGE_V1",
                        "confidence_state": "1.00", "rationale": f"Pinned existing lineage selects canonical {target}.",
                    })
                    if existing:
                        statement = canonical_text(existing["definition_short_en"] or "")
                        contexts[raw_id] = {
                            "raw_id": raw_id, "target_artifact_id": target,
                            "source_catalog_id": row["source_catalog_id"],
                            "source_identifier": _semantic_identifier(row["source_catalog_id"], row["source_section"], existing["title_en"]),
                            "statement_key": hashlib.sha256(normalize_text(statement).encode("utf-8")).hexdigest(),
                            "statement": statement, "title": existing["title_en"],
                            "type": existing["type"], "primary_domain": existing["primary_domain"],
                            "sub_domain": existing["sub_domain"], "abstraction_level": existing["abstraction_level"],
                            "target_is_preexisting": target in selected_candidates_by_final or target == existing_targets.get(raw_id),
                        }
                    continue
                raw = json.loads(row["raw_json"])
                raw.setdefault("source_metadata", {})["source_catalog_id"] = row["source_catalog_id"]
                try:
                    result = classify_record(raw)
                except ValueError as error:
                    decisions.append({
                        "raw_id": raw_id, "source_content_sha256": row["content_hash"],
                        "disposition": "DEFERRED", "decision_method": "SEMANTIC_BOUNDARY_REVIEW_V1",
                        "confidence_state": "UNSCORED", "deferred_reason_code": "UNRESOLVED_SEMANTIC_BOUNDARY",
                        "rationale": f"{raw_id} has no defensible SDT classification from its own statement and approved source tie-breakers: {error}.",
                    })
                    continue
                signature = (normalize_text(result["title_en"]), normalize_text(result["definition_short_en"]))
                existing = existing_signatures.get(signature)
                if existing:
                    decisions.append({
                        "raw_id": raw_id, "source_content_sha256": row["content_hash"],
                        "disposition": "SUPPORTS_CANONICAL", "target_artifact_id": existing,
                        "mapping_strength": "DIRECT", "decision_method": "EXACT_SEMANTIC_MATCH_V1",
                        "confidence_state": "1.00", "rationale": f"Exact normalized title and statement match existing canonical {existing}.",
                    })
                    statement = canonical_text(result["definition_short_en"])
                    contexts[raw_id] = {
                        "raw_id": raw_id, "target_artifact_id": existing,
                        "source_catalog_id": row["source_catalog_id"],
                        "source_identifier": _semantic_identifier(row["source_catalog_id"], row["source_section"], result["title_en"]),
                        "statement_key": hashlib.sha256(normalize_text(statement).encode("utf-8")).hexdigest(),
                        "statement": statement, "title": result["title_en"],
                        "type": result["proposed_type"], "primary_domain": result["proposed_primary_domain"],
                        "sub_domain": result["proposed_sub_domain"], "abstraction_level": result["proposed_abstraction_level"],
                        "target_is_preexisting": target in selected_candidates_by_final,
                    }
                    continue
                generated_signature = (
                    result["proposed_type"], result["proposed_primary_domain"],
                    result["proposed_sub_domain"], *signature,
                )
                target = generated_signatures.get(generated_signature)
                if target:
                    decisions.append({
                        "raw_id": raw_id, "source_content_sha256": row["content_hash"],
                        "disposition": "SUPPORTS_CANONICAL", "target_artifact_id": target,
                        "mapping_strength": "DIRECT", "decision_method": "EXACT_CROSS_SOURCE_MATCH_V1",
                        "confidence_state": "1.00", "rationale": f"Exact normalized atomic statement matches generated canonical {target}.",
                    })
                    statement = canonical_text(result["definition_short_en"])
                    contexts[raw_id] = {
                        "raw_id": raw_id, "target_artifact_id": target,
                        "source_catalog_id": row["source_catalog_id"],
                        "source_identifier": _semantic_identifier(row["source_catalog_id"], row["source_section"], result["title_en"]),
                        "statement_key": hashlib.sha256(normalize_text(statement).encode("utf-8")).hexdigest(),
                        "statement": statement, "title": result["title_en"],
                        "type": result["proposed_type"], "primary_domain": result["proposed_primary_domain"],
                        "sub_domain": result["proposed_sub_domain"], "abstraction_level": result["proposed_abstraction_level"],
                        "target_is_preexisting": target in selected_candidates_by_final,
                    }
                    continue
                candidate = _new_candidate(row, result)
                normalized_title = normalize_text(candidate["title_en"])
                if normalized_title in used_titles:
                    source_identity = row["external_raw_id"] or row["source_section"] or raw_id
                    candidate["title_en"] = f"{candidate['title_en']} [{source_identity}]"
                    normalized_title = normalize_text(candidate["title_en"])
                used_titles.add(normalized_title)
                target = candidate["artifact_id"]
                generated_signatures[generated_signature] = target
                decisions.append({
                    "raw_id": raw_id, "source_content_sha256": row["content_hash"],
                    "disposition": "SUPPORTS_CANONICAL", "target_artifact_id": target,
                    "new_canonical": candidate, "mapping_strength": "DIRECT",
                    "decision_method": "ATOMIC_SOURCE_CANONICAL_V1",
                    "confidence_state": f"{result['classification_confidence']:.2f}",
                    "rationale": (
                        f"Atomic source statement was classified as {result['proposed_type']} / "
                        f"{result['proposed_sub_domain']} and has no exact existing canonical match."
                    ),
                })
                statement = canonical_text(result["definition_short_en"])
                contexts[raw_id] = {
                    "raw_id": raw_id, "target_artifact_id": target,
                    "source_catalog_id": row["source_catalog_id"],
                    "source_identifier": _semantic_identifier(row["source_catalog_id"], row["source_section"], result["title_en"]),
                    "statement_key": hashlib.sha256(normalize_text(statement).encode("utf-8")).hexdigest(),
                    "statement": statement, "title": result["title_en"],
                    "type": result["proposed_type"], "primary_domain": result["proposed_primary_domain"],
                    "sub_domain": result["proposed_sub_domain"], "abstraction_level": result["proposed_abstraction_level"],
                    "target_is_preexisting": False,
                }
        finally:
            conn.close()
    reconciliation = _global_reconciliation(contexts, decisions)
    material = {
        "schema_version": 1, "ledger_sha256": None, "decisions": decisions,
        "global_reconciliation_sha256": reconciliation["reconciliation_sha256"],
    }
    material["ledger_sha256"] = _decision_hash(material)
    return {"ledger": material, "global_reconciliation": reconciliation}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "consolidation" / "semantic_audit.json")
    parser.add_argument("--rebuild-ledger", action="store_true")
    parser.add_argument("--base-database", type=Path, default=ROOT / "catalog.db")
    parser.add_argument(
        "--global-output", type=Path,
        default=ROOT / "consolidation" / "global_semantic_reconciliation.json",
    )
    args = parser.parse_args()
    if args.rebuild_ledger:
        result = build_semantic_ledger(args.base_database)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.global_output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result["ledger"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        args.global_output.write_text(json.dumps(result["global_reconciliation"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({
            "decisions": len(result["ledger"]["decisions"]),
            "ledgerSha256": result["ledger"]["ledger_sha256"],
            "globalReconciliationSha256": result["global_reconciliation"]["reconciliation_sha256"],
            "globalCounts": result["global_reconciliation"]["counts"],
        }, indent=2))
        return
    report = build_csf_audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("totalRecords", "resolvedRecords", "unresolvedRecords", "auditSha256")}, indent=2))


if __name__ == "__main__":
    main()
