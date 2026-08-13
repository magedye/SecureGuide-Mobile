# Catalog performance qualification

## Qualified candidate

- Candidate: `mobile/assets/catalog.db`
- Candidate SHA-256: `51e940debba2c7c664e779dd27f9b478b253068b784b553bc8d31deedf05be35`
- Population: 1,227 approved active catalog artifacts; no synthetic catalog duplication
- Target: `WINDOWS-HOST-SQLITE-QUALIFICATION-V1`
- Samples: 5 warm-ups and 30 measured iterations
- Result: `QUALIFIED`

| Gate | Budget P95 | Baseline P95 | Qualification P95 | Result |
|---|---:|---:|---:|---|
| Catalog search | 250 ms | 67.251 ms | 37.400 ms | PASS |
| Profile dashboard | 500 ms | 439.803 ms | 129.628 ms | PASS |
| HTML report | 1,500 ms | 509.737 ms | 428.324 ms | PASS |

The qualification also recorded startup P95 at 19.910 ms, database size at
10,563,584 bytes, peak traced Python memory at 4,330,599 bytes, catalog-content
upgrade duration at 6,743.899 ms, integrity-check duration at 696.645 ms,
`PRAGMA integrity_check=ok`, and zero foreign-key violations. These additional
measures are evidence-only until the owner approves explicit thresholds.

The immutable measurement payloads are
`consolidation/performance_baseline.json` and
`consolidation/performance_qualification.json`. Each carries a canonical report
hash and only relative project paths.

## Variance and rejected optimization attempt

Two full runs made while another Gradle build saturated the host were rejected
as environmental observations: one produced dashboard P95 526.807 ms and the
next produced search P95 285.860 ms. Component isolation measured the dashboard
work near 100 ms and an earlier three-sample run measured dashboard P95 171.603
ms. No speculative query optimization was retained. Qualification was repeated
unchanged after host saturation ended and passed twice, first as the bound
baseline and then against that baseline.

This is a host-side SQLite regression qualification. Physical Android/iOS
startup, memory, frame rendering, and PDF rendering remain separate device
acceptance activities and are not claimed by this result.
