"""Reproducible SecureGuide release-catalog performance qualification.

The source database is never mutated. A temporary copy receives a synthetic
*profile state* selecting every approved artifact; catalog artifacts themselves
are never duplicated. This preserves the distinction between governed reference
data and operational benchmark data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import shutil
import sqlite3
import statistics
import sys
import tempfile
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from secureguide import SecureGuideService
from secureguide.catalog_upgrade import upgrade_catalog
from secureguide.database import apply_migrations


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE = ROOT / "mobile" / "assets" / "catalog.db"
DEFAULT_BUDGET = ROOT / "consolidation" / "performance_budget.json"
DEFAULT_OUTPUT = ROOT / "dist" / "performance-benchmark.json"
PROFILE_ID = "PERF-QUALIFICATION-PROFILE"


SEARCH_PLAN_SQL = """
SELECT a.id,a.type,COALESCE(loc.title,a.title_en,a.title_ar) AS title,
       COALESCE(pa.priority_override,pa.template_priority_default,a.priority)
         AS effective_priority,
       pa.id AS profile_artifact_id
  FROM security_artifacts a
  LEFT JOIN artifact_localizations loc
    ON loc.artifact_id=a.id AND loc.locale=?
  LEFT JOIN profile_artifacts pa
    ON pa.artifact_id=a.id AND pa.profile_id=?
 WHERE a.is_active=1
   AND a.publication_status IN ('APPROVED','PUBLISHED')
   AND (
     lower(COALESCE(loc.title,a.title_en,a.title_ar)) LIKE ?
     OR lower(COALESCE(loc.definition_short,a.definition_short_en,
                       a.definition_short_ar,'')) LIKE ?
     OR lower(COALESCE(a.source_document,'')) LIKE ?
     OR EXISTS (
       SELECT 1 FROM artifact_tags tag
        WHERE tag.artifact_id=a.id AND lower(tag.tag_value) LIKE ?
     )
   )
 ORDER BY title,a.id
 LIMIT 100 OFFSET 0
"""

DASHBOARD_PLAN_SQL = (
    "SELECT * FROM v_profile_dashboard WHERE profile_id=?",
    """
    SELECT a.id,a.primary_domain,a.priority,a.scoring_weight,a.risk_reduction,
           a.tier,pa.implementation_status,pa.verification_status,
           pa.effectiveness,pa.exception_status
      FROM security_artifacts a
      JOIN profile_artifacts pa ON a.id=pa.artifact_id
     WHERE pa.profile_id=?
    """,
)

REPORT_PLAN_SQL = (
    (
        "SELECT * FROM v_profile_operational_items WHERE profile_id=? "
        "ORDER BY artifact_id",
        (PROFILE_ID,),
    ),
    (
        "SELECT * FROM v_gap_analysis WHERE profile_id=? "
        "ORDER BY CASE priority "
        "WHEN 'PRI-CRITICAL' THEN 1 WHEN 'PRI-HIGH' THEN 2 "
        "WHEN 'PRI-MEDIUM' THEN 3 ELSE 4 END,"
        "due_date IS NULL,due_date,artifact_id LIMIT ?",
        (PROFILE_ID, 200),
    ),
    (
        "SELECT * FROM v_profile_task_queue WHERE profile_id=?",
        (PROFILE_ID,),
    ),
)


@dataclass(frozen=True)
class Measurement:
    samples_ms: list[float]

    @property
    def minimum(self) -> float:
        return min(self.samples_ms)

    @property
    def median(self) -> float:
        return statistics.median(self.samples_ms)

    @property
    def p95(self) -> float:
        ordered = sorted(self.samples_ms)
        return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]

    @property
    def maximum(self) -> float:
        return max(self.samples_ms)

    def to_json(self) -> dict[str, Any]:
        return {
            "samples": len(self.samples_ms),
            "minMs": round(self.minimum, 3),
            "p50Ms": round(self.median, 3),
            "p95Ms": round(self.p95, 3),
            "maxMs": round(self.maximum, 3),
        }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _report_path(path: Path) -> str:
    """Keep durable evidence portable when the project root moves."""
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def _result_sha256(result: dict[str, Any]) -> str:
    """Bind a benchmark report to its exact canonical JSON payload."""
    payload = json.dumps(
        result,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _measure(
    operation: Callable[[], object], *, warmups: int, iterations: int
) -> Measurement:
    for _ in range(warmups):
        operation()
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        operation()
        samples.append((time.perf_counter_ns() - started) / 1_000_000)
    return Measurement(samples)


def _seed_profile(database: Path) -> int:
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        artifact_ids = [
            row[0]
            for row in connection.execute(
                """SELECT id FROM security_artifacts
                     WHERE is_active=1
                       AND publication_status IN ('APPROVED','PUBLISHED')
                     ORDER BY id"""
            )
        ]
        connection.execute(
            "INSERT INTO enterprise_profiles(id,name,profile_kind) VALUES(?,?,?)",
            (PROFILE_ID, "Performance qualification", "SYSTEM"),
        )
        statuses = ("STS-NOT-APPLIED", "STS-PARTIAL", "STS-FULL")
        rows = []
        for index, artifact_id in enumerate(artifact_ids):
            implementation = statuses[index % len(statuses)]
            verification = "VER-PASS" if implementation == "STS-FULL" else "VER-NOT-VERIFIED"
            effectiveness = "EFF-HIGH" if implementation == "STS-FULL" else "EFF-UNKNOWN"
            rows.append(
                (
                    f"PERF-PA-{index:08d}",
                    PROFILE_ID,
                    artifact_id,
                    implementation,
                    verification,
                    effectiveness,
                    "EXC-NONE",
                )
            )
        connection.executemany(
            """INSERT INTO profile_artifacts(
                   id,profile_id,artifact_id,implementation_status,
                   verification_status,effectiveness,exception_status
               ) VALUES(?,?,?,?,?,?,?)""",
            rows,
        )
        connection.execute("ANALYZE")
        connection.commit()
        return len(artifact_ids)
    finally:
        connection.close()


def _plan(
    connection: sqlite3.Connection, sql: str, parameters: Iterable[object]
) -> list[str]:
    return [
        str(row[3])
        for row in connection.execute("EXPLAIN QUERY PLAN " + sql, tuple(parameters))
    ]


def _query_plans(database: Path) -> dict[str, list[str]]:
    connection = sqlite3.connect(database)
    try:
        needle = "%__secureguide_no_match__%"
        plans = {
            "catalogSearch": _plan(
                connection,
                SEARCH_PLAN_SQL,
                ("en", PROFILE_ID, needle, needle, needle, needle),
            ),
            "profileDashboard": [],
            "htmlReport": [],
        }
        for statement in DASHBOARD_PLAN_SQL:
            plans["profileDashboard"].extend(
                _plan(connection, statement, (PROFILE_ID,))
            )
        for statement, parameters in REPORT_PLAN_SQL:
            plans["htmlReport"].extend(_plan(connection, statement, parameters))
        return plans
    finally:
        connection.close()


def _startup(database: Path, *, warmups: int, iterations: int) -> Measurement:
    def open_and_read() -> None:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        try:
            connection.execute(
                "SELECT id,title_en FROM security_artifacts "
                "WHERE is_active=1 ORDER BY id LIMIT 1"
            ).fetchone()
        finally:
            connection.close()

    return _measure(open_and_read, warmups=warmups, iterations=iterations)


def _memory_peak(service: SecureGuideService) -> dict[str, int]:
    tracemalloc.start()
    try:
        service.search_catalog(profile_id=PROFILE_ID, locale="en", query="__secureguide_no_match__", limit=100)
        service.dashboard(profile_id=PROFILE_ID)
        service.report_html(profile_id=PROFILE_ID)
        current, peak = tracemalloc.get_traced_memory()
        return {"currentBytes": int(current), "peakBytes": int(peak)}
    finally:
        tracemalloc.stop()


def _integrity_measure(database: Path) -> tuple[float, str, int]:
    connection = sqlite3.connect(database)
    try:
        started = time.perf_counter_ns()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        duration = (time.perf_counter_ns() - started) / 1_000_000
        return duration, str(integrity), foreign_keys
    finally:
        connection.close()


def _upgrade_measure(candidate: Path, baseline: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="secureguide-upgrade-performance-") as temp:
        installed = Path(temp) / "installed.db"
        shutil.copy2(baseline, installed)
        started = time.perf_counter_ns()
        result = upgrade_catalog(installed, candidate, actor="performance-qualification")
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        return {
            "status": "MEASURED",
            "durationMs": round(elapsed, 3),
            "oldArtifactCount": result["oldArtifactCount"],
            "newArtifactCount": result["newArtifactCount"],
            "operationalSnapshotPreserved": (
                result["operationalSnapshotBefore"] == result["operationalSnapshotAfter"]
            ),
        }


def _upgrade_not_measured(reason: str) -> dict[str, Any]:
    return {
        "status": reason,
        "durationMs": None,
        "oldArtifactCount": None,
        "newArtifactCount": None,
        "operationalSnapshotPreserved": None,
    }


def _baseline_comparison(result: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    if not baseline:
        return {"status": "BASELINE_NOT_ESTABLISHED", "comparisons": {}}
    observed = {
        "catalogSearchP95Ms": result["measurements"]["catalogSearch"]["p95Ms"],
        "profileDashboardP95Ms": result["measurements"]["profileDashboard"]["p95Ms"],
        "htmlReportP95Ms": result["measurements"]["htmlReport"]["p95Ms"],
        "startupP95Ms": result["startup"]["p95Ms"],
        "databaseSizeBytes": result["databaseSize"]["bytes"],
        "memoryPeakBytes": result["memory"]["peakBytes"],
        "catalogUpgradeDurationMs": result["migration"]["durationMs"],
        "integrityDurationMs": result["integrityValidation"]["durationMs"],
    }
    comparisons = {}
    for name, value in observed.items():
        reference = baseline.get(name)
        comparisons[name] = {
            "baseline": reference,
            "observed": value,
            "deltaPercent": (
                None if reference in (None, 0) or value is None
                else round((float(value) - float(reference)) / float(reference) * 100, 3)
            ),
        }
    return {"status": "COMPARED", "baselineId": baseline.get("id"), "comparisons": comparisons}


def run_benchmark(
    database: Path,
    budget: dict[str, Any],
    *,
    mode: str,
    warmups: int | None = None,
    iterations: int | None = None,
    minimum_artifacts: int | None = None,
) -> dict[str, Any]:
    database = database.resolve()
    if not database.is_file():
        raise FileNotFoundError(database)
    source_hash = _sha256(database)
    warmup_count = warmups if warmups is not None else int(budget["warmupIterations"])
    sample_count = iterations if iterations is not None else int(budget["sampleIterations"])
    artifact_floor = (
        minimum_artifacts
        if minimum_artifacts is not None
        else int(budget["qualificationMinimumArtifacts"])
    )
    if warmup_count < 0 or sample_count < 3 or artifact_floor < 1:
        raise ValueError("invalid benchmark iteration or artifact settings")

    with tempfile.TemporaryDirectory(prefix="secureguide-performance-") as temp:
        working = Path(temp) / "catalog.db"
        shutil.copy2(database, working)
        artifact_count = _seed_profile(working)
        service = SecureGuideService(str(working))
        needle = "__secureguide_no_match__"
        measurements = {
            "catalogSearch": _measure(
                lambda: service.search_catalog(
                    profile_id=PROFILE_ID,
                    locale="en",
                    query=needle,
                    limit=100,
                ),
                warmups=warmup_count,
                iterations=sample_count,
            ),
            "profileDashboard": _measure(
                lambda: service.dashboard(profile_id=PROFILE_ID),
                warmups=warmup_count,
                iterations=sample_count,
            ),
            "htmlReport": _measure(
                lambda: service.report_html(profile_id=PROFILE_ID),
                warmups=warmup_count,
                iterations=sample_count,
            ),
        }
        plans = _query_plans(working)
        startup = _startup(
            database,
            warmups=warmup_count,
            iterations=sample_count,
        )
        memory = _memory_peak(service)
        integrity_duration, integrity_check, foreign_key_violations = _integrity_measure(working)
        connection = sqlite3.connect(working)
        try:
            raw_count = connection.execute("SELECT COUNT(*) FROM raw_artifacts").fetchone()[0]
            schema_version = connection.execute("PRAGMA user_version").fetchone()[0]
        finally:
            connection.close()

    migration_baseline = Path(
        budget.get("migrationBaselineDatabase", str(ROOT / "catalog.db"))
    )
    if not migration_baseline.is_absolute():
        migration_baseline = ROOT / migration_baseline
    population_sufficient = artifact_count >= artifact_floor
    if mode == "qualification" and population_sufficient:
        migration = _upgrade_measure(database, migration_baseline)
    elif mode == "qualification":
        migration = _upgrade_not_measured("NOT_MEASURED_CATALOG_TOO_SMALL")
    else:
        migration = _upgrade_not_measured("NOT_MEASURED_SMOKE")

    if _sha256(database) != source_hash:
        raise RuntimeError("source release database changed during benchmark")

    thresholds = budget["thresholdsMs"]
    threshold_results = {
        "catalogSearch": measurements["catalogSearch"].p95
        <= float(thresholds["catalogSearchP95"]),
        "profileDashboard": measurements["profileDashboard"].p95
        <= float(thresholds["profileDashboardP95"]),
        "htmlReport": measurements["htmlReport"].p95
        <= float(thresholds["htmlReportP95"]),
    }
    thresholds_passed = all(threshold_results.values())
    if mode == "qualification" and not population_sufficient:
        status = "BLOCKED_CATALOG_TOO_SMALL"
    elif not thresholds_passed:
        status = "FAILED_PERFORMANCE_BUDGET"
    elif mode == "qualification":
        status = "QUALIFIED"
    else:
        status = "SMOKE_ONLY"

    result = {
        "status": status,
        "qualified": status == "QUALIFIED",
        "mode": mode,
        "source": {
            "path": _report_path(database),
            "sha256": source_hash,
            "schemaVersion": schema_version,
            "approvedActiveArtifacts": artifact_count,
            "rawArtifacts": raw_count,
        },
        "population": {
            "requiredArtifacts": artifact_floor,
            "actualArtifacts": artifact_count,
            "sufficient": population_sufficient,
            "catalogRowsDuplicated": 0,
            "temporaryProfileSelections": artifact_count,
        },
        "environment": {
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(),
        },
        "targetProfile": budget.get("targetProfile", {}),
        "iterations": {"warmup": warmup_count, "samples": sample_count},
        "thresholdsMs": thresholds,
        "thresholdResults": threshold_results,
        "measurements": {
            name: measurement.to_json()
            for name, measurement in measurements.items()
        },
        "startup": startup.to_json(),
        "databaseSize": {
            "bytes": database.stat().st_size,
            "baselineBytes": (budget.get("baseline") or {}).get("databaseSizeBytes"),
        },
        "memory": memory,
        "migration": migration,
        "integrityValidation": {
            "durationMs": round(integrity_duration, 3),
            "integrityCheck": integrity_check,
            "foreignKeyViolations": foreign_key_violations,
        },
        "queryPlans": plans,
        "limitations": [
            "Host-side regression benchmark; device rendering and PDF rasterization are not measured.",
            "SMOKE_ONLY is not release-catalog performance qualification.",
        ],
    }
    result["baselineComparison"] = _baseline_comparison(result, budget.get("baseline"))
    result["reportSha256"] = _result_sha256(result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--budget", type=Path, default=DEFAULT_BUDGET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--mode", choices=("qualification", "smoke"), default="qualification")
    parser.add_argument("--warmups", type=int)
    parser.add_argument("--iterations", type=int)
    parser.add_argument("--minimum-artifacts", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    budget = json.loads(args.budget.read_text(encoding="utf-8"))
    result = run_benchmark(
        args.database,
        budget,
        mode=args.mode,
        warmups=args.warmups,
        iterations=args.iterations,
        minimum_artifacts=args.minimum_artifacts,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["status"] == "BLOCKED_CATALOG_TOO_SMALL":
        return 2
    return 0 if result["qualified"] or result["status"] == "SMOKE_ONLY" else 1


if __name__ == "__main__":
    sys.exit(main())
