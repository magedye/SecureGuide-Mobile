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

The qualification also records database open/first-read startup, database
size, traced process memory, catalog-content migration duration, SQLite
integrity duration and result, foreign-key violations, target-host details, and
comparison with the pinned baseline. Categories without an owner-approved
threshold remain evidence-only; the runner does not invent limits for them.

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
SLAs. Synthetic duplication of catalog rows is prohibited.

## Qualified RC1 result

The released database is `mobile/assets/catalog.db`, contains 1,227 approved
active ضوابط, and has SHA-256
`51e940debba2c7c664e779dd27f9b478b253068b784b553bc8d31deedf05be35`.
The 30-sample qualification passed the three established P95 budgets:

| Path | Budget | Qualified P95 |
|---|---:|---:|
| Catalog search | 250 ms | 37.400 ms |
| Profile dashboard | 500 ms | 129.628 ms |
| HTML report | 1,500 ms | 428.324 ms |

Startup P95 was 19.910 ms, database size was 10,563,584 bytes, peak traced
Python memory was 4,330,599 bytes, content upgrade took 6,743.899 ms, integrity
validation took 696.645 ms, `integrity_check` returned `ok`, and foreign-key
violations were zero. The exact baseline, comparison, variance record, and
canonical report hashes are in:

- `consolidation/performance_baseline.json`
- `consolidation/performance_qualification.json`
- `consolidation/PERFORMANCE_QUALIFICATION.md`

Physical Android/iOS startup, memory, frame rendering, and PDF rendering still
require representative-device acceptance. The host result does not claim that
separate acceptance.
