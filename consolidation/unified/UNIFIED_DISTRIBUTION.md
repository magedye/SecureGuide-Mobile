# Unified Security Artifact Library — legacy + curated

Pool: **1467** pinned candidates (706 neutral legacy-source + 761 curated). Discovery uses the release candidate loader, not source-specific staging batches.

## Review state

- `AIR-HUMAN-REVIEW`: **529**
- `AIR-AUTO-ACCEPTED`: **685**
- `AIR-HUMAN-APPROVED`: **4**

## Non-destructive equivalence projection

- Equivalence groups: **215**
- Cross-source groups: **24**
- Source rows participating in a group: **468**
- Duplicate source rows folded logically: **253**
- **Unified candidate projection: 1214**; installed catalog total with four governed seed artifacts: **1218**
- Logical deduplication rate: **17.2%**

All source and raw rows remain preserved. Detection is global and deterministic; similarity only proposes candidates and never silently merges. The 215 committed decisions retain explicit rationale and review metadata.

## Unified projection by USACM type

| type | count |
|---|---:|
| ART-CFG | 48 |
| ART-CTR | 583 |
| ART-MET | 1 |
| ART-OBJ | 5 |
| ART-OWN | 4 |
| ART-PLN | 15 |
| ART-POL | 25 |
| ART-PRC | 39 |
| ART-PRG | 17 |
| ART-PRI | 6 |
| ART-PRO | 9 |
| ART-REQ | 232 |
| ART-RSK | 1 |
| ART-STD | 5 |
| ART-THR | 226 |
| ART-TSK | 1 |
| ART-VUL | 1 |

## Unified projection by SDT domain

| domain | count |
|---|---:|
| SD-01 | 84 |
| SD-02 | 160 |
| SD-03 | 251 |
| SD-04 | 236 |
| SD-05 | 137 |
| SD-06 | 169 |
| SD-07 | 77 |
| SD-08 | 104 |

## Group size histogram

| members | groups |
|---:|---:|
| 2 | 186 |
| 3 | 21 |
| 4 | 7 |
| 5 | 1 |

## Validation

- Global exact-definition sets left outside one group: **0**
- Exact-definition sets with conflicting SDT classifications: **32** (human review required)
- Candidate population accounted for by the same pinned inputs as the deterministic release build
