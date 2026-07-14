# Unified Security Artifact Library — amani + curated

Pool: **1467** candidates (706 amani + 761 curated) on `catalog_work.db`.

## Review state

- NEEDS_REVIEW: **1309**
- CLASSIFIED (not grouped): **158**
- Approved or ready for promotion: **0**

## Non-destructive equivalence projection

- Equivalence groups: **220**
- Cross-source groups: **15**
- Source rows participating in a group: **464**
- Duplicate source rows folded logically: **244**
- **Unified artifact projection (canonicals + standalone): 1223**
- Logical deduplication rate: **16.6%**

All source and raw rows remain preserved. Every equivalence decision requires human review.

## Unified projection by USACM type

| type | count |
|---|---:|
| ART-AST | 1 |
| ART-CFG | 11 |
| ART-CTR | 891 |
| ART-MET | 1 |
| ART-OBJ | 5 |
| ART-OWN | 2 |
| ART-PLN | 9 |
| ART-POL | 20 |
| ART-PRC | 26 |
| ART-PRG | 9 |
| ART-PRI | 5 |
| ART-PRO | 4 |
| ART-REQ | 113 |
| ART-RSK | 1 |
| ART-STD | 3 |
| ART-THR | 120 |
| ART-TSK | 1 |
| ART-VUL | 1 |

## Unified projection by SDT domain

| domain | count |
|---|---:|
| SD-01 | 78 |
| SD-02 | 121 |
| SD-03 | 247 |
| SD-04 | 295 |
| SD-05 | 131 |
| SD-06 | 172 |
| SD-07 | 97 |
| SD-08 | 82 |

## Group size histogram

| members | groups |
|---:|---:|
| 2 | 200 |
| 3 | 17 |
| 4 | 2 |
| 5 | 1 |

## Validation

- Global exact-definition sets left outside one group: **0**
- Exact-definition sets with conflicting SDT classifications: **89** (human review required)
- Production database: verified against committed SHA-256 baseline
