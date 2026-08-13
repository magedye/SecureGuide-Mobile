# Release catalog performance qualification

`scripts/benchmark_release_catalog.py` measures the governed SQLite catalog
without modifying or duplicating its reference rows. It works on a temporary
database copy, creates one benchmark enterprise profile, selects every approved
artifact into that profile, warms each path, then records repeated samples and
`EXPLAIN QUERY PLAN` evidence.

Measured paths are worst-case no-match catalog search, full profile dashboard
calculation, and self-contained HTML report generation. Budgets and the
provisional minimum population are versioned in
`consolidation/performance_budget.json`.

Run a non-qualifying development smoke measurement:

```powershell
py -3 -m scripts.benchmark_release_catalog --mode smoke
```

Run the release gate:

```powershell
py -3 -m scripts.benchmark_release_catalog --mode qualification
```

The qualification command exits `2` and records
`BLOCKED_CATALOG_TOO_SMALL` when the governed release catalog does not meet the
declared population. It exits `1` when any p95 budget fails. Only a result with
`status: QUALIFIED` is release-catalog performance evidence.

The current budgets are host-side regression limits, not mobile rendering
SLAs. Final release qualification must also record representative Android/iOS
device model, OS/API level, build mode, and UI trace for catalog rendering and
PDF preview. Synthetic duplication of the four approved starter artifacts is
not accepted as a substitute for the governed full catalog.
