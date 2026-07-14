# SADP v1.0 — Conformance Mapping & Resolutions

> How the SecureGuide catalog database conforms to [SADP v1.0](SADP_v1.0.md). This
> document is the **§2.6 change-control record** for every fallback value and the
> `THR-*` dimension introduced to reach conformance. Governing decisions were
> approved by the product owner on adoption.

## 1. Conformance status by mandate

| SADP | Requirement | Status | Where |
|---|---|---|---|
| §2.1 | No user state / calculated props in catalog | **Conforms** | Catalog holds baseline only; user state joined at runtime by `scoring.py` (headless). See §3 below. |
| §2.2 | Every applicable classification populated | **Enforced at gate** | `_promote_common.promotion_blockers` rejects missing mandatory classifications; type-conditional structural `NULL` is allowed only where the normative schema requires it. |
| §2.3 | Governed fallbacks `*-NA/*-UNKNOWN/*-MULTI` | **Conforms** | Migration 011 seeds the review vocabulary; migration 018 records whether each value is publishable, structural, review-only, or normalized. |
| §2.4 | No free-form tags; Threat = `THR-*` | **Conforms** | Tags retired from the write path; `lk_threat` + `artifact_threats` added (§3.1). Provenance moved to typed tables. |
| §2.5 | Configurable UI visibility | **Conforms** | `classification_visibility(dimension, is_visible, sort_order)` — hide a dimension without a schema change. |
| §2.6 | Change control | **Conforms** | This document records every added value; no dimension/value added outside it. |
| §3 | Mandatory columns present | **Conforms** | All 19 columns exist (`source` = obligation_source; `type` = artifact_type; `relationship_type`/`mapping_strength` normalized in child tables). |
| §3.1 | Threat multiplicity normalized | **Conforms** | `artifact_threats(artifact_id, threat_code)` — never a JSON array in the catalog. |

## 2. Gap analysis (pre-adoption) → resolution
The schema (migrations 001–010) already carried ~all §3 columns with USACM-style
codes. Four gaps were closed:

1. **Sparse fallbacks (§2.3)** → migration 011 seeds the systematic review vocabulary; migration 018 prevents lookup membership from being mistaken for publication permission.
2. **Missing `THR-*` dimension (§2.4/§3.1)** → `lk_threat` + `artifact_threats` (migrations 012/013).
3. **Nullable classification columns (§2.2)** → populated at the promotion gate: `review_frequency` receives the `AD-HOC` baseline and the threat dimension always carries ≥1 row (`THR-NA` when genuinely not applicable). **Type-conditional dimensions** (`control_nature`, `control_function`, `requirement_type`) use schema-enforced structural `NULL` outside their applicable artifact types. `UNKNOWN/MULTI` never promote; legitimate multiplicity uses normalized child rows. The normative core table therefore needs no weakening or rebuild.
4. **Tags present & used (§2.4)** → retired from the write path; amani provenance that previously rode on tags moved to typed tables (`catalog_amani_provenance`, `catalog_amani_assets`, `artifact_platforms`, `artifact_threats`); amani priority now stored losslessly in the `priority` (`PRI-*`) column.

## 3. Internal-tension resolution: §2.1 vs §3
§2.1 prohibits storing user/effective state, yet §3 mandates `implementation_status`,
`verification_status`, `effectiveness` columns. **Resolution:** these columns hold
the catalog's **intrinsic baseline** (e.g., `STS-NOT-APPLIED`, `VER-NOT-VERIFIED`,
`EFF-UNKNOWN`) — a per-artifact default, never a user's assessment. A user's actual
status and any *effective* (computed) priority live outside the catalog and are
joined at runtime. The headless `scoring.py` demonstrates this: it reads the
catalog as reference and takes user status from a separate states map.

## 4. Governed fallback values (§2.3 / §2.6 record)
The triple is added by prefix for intake/review; existing equivalents are reused,
not duplicated. The disposition column below is normative for approved catalog
content and is stored in `classification_fallback_policy`.

| Dimension | NA disposition | UNKNOWN disposition | MULTI disposition |
|---|---|---|---|
| control_nature / control_function / requirement_type | Structural `NULL` outside the applicable type | Review only | Review only |
| testability | `TST-NA` publishable native value | Review only | Review only |
| effectiveness | Review only | `EFF-UNKNOWN` publishable native baseline | Review only |
| exception_status | `EXC-NOT-APPLICABLE` publishable native profile state | Review only | Review only |
| threat | `THR-NA` publishable when genuinely not applicable | Review only | Normalize into multiple `artifact_threats` rows |
| mapping_strength | Review only | Review only | Normalize into multiple mapping rows |
| abstraction, obligation source/level, granularity, priority, review frequency | Review only | Review only | Review only |

**Excluded from fallbacks (always determinable):** `lk_sdt_domain`, `lk_sdt_subdomain`,
`lk_artifact_type`. These must carry a real value — the gate rejects NULL/fallback here.

Migration 018 also records the native-only dimensions (implementation,
verification, relationships, publication, AI review, source type, asset type,
maturity, cost, import status, and tag type) so the exclusion is machine-testable.

## 5. Approved `THR-*` threat taxonomy (§2.6 record)
The canonical threat classification replacing the retired `Threat` tag. Full code
list and the `amani_threat_alias` (amani free-text → THR-*) live in
`migrations/013_threat_reference.sql`, generated by `scripts/build_threat_reference.py`.
Any new `THR-*` value or alias must be added there and recorded in this section.
