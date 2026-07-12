# SADP v1.0 — Conformance Mapping & Resolutions

> How the SecureGuide catalog database conforms to [SADP v1.0](SADP_v1.0.md). This
> document is the **§2.6 change-control record** for every fallback value and the
> `THR-*` dimension introduced to reach conformance. Governing decisions were
> approved by the product owner on adoption.

## 1. Conformance status by mandate

| SADP | Requirement | Status | Where |
|---|---|---|---|
| §2.1 | No user state / calculated props in catalog | **Conforms** | Catalog holds baseline only; user state joined at runtime by `scoring.py` (headless). See §3 below. |
| §2.2 | Every classification populated, no NULLs | **Enforced at gate** | `_promote_common.promotion_blockers` rejects any promotion with a NULL classification; fallbacks fill non-applicable dims. |
| §2.3 | Universal fallbacks `*-NA/*-UNKNOWN/*-MULTI` | **Conforms** | `migrations/011_universal_fallbacks.sql` seeds the triple across every artifact-level classification list. |
| §2.4 | No free-form tags; Threat = `THR-*` | **Conforms** | Tags retired from the write path; `lk_threat` + `artifact_threats` added (§3.1). Provenance moved to typed tables. |
| §2.5 | Configurable UI visibility | **Conforms** | `classification_visibility(dimension, is_visible, sort_order)` — hide a dimension without a schema change. |
| §2.6 | Change control | **Conforms** | This document records every added value; no dimension/value added outside it. |
| §3 | Mandatory columns present | **Conforms** | All 19 columns exist (`source` = obligation_source; `type` = artifact_type; `relationship_type`/`mapping_strength` normalized in child tables). |
| §3.1 | Threat multiplicity normalized | **Conforms** | `artifact_threats(artifact_id, threat_code)` — never a JSON array in the catalog. |

## 2. Gap analysis (pre-adoption) → resolution
The schema (migrations 001–010) already carried ~all §3 columns with USACM-style
codes. Four gaps were closed:

1. **Sparse fallbacks (§2.3)** → migration 011 seeds the systematic triple.
2. **Missing `THR-*` dimension (§2.4/§3.1)** → `lk_threat` + `artifact_threats` (migrations 012/013).
3. **Nullable classification columns (§2.2)** → enforced-populated (with fallbacks) at the promotion gate; schema columns left as-is (additive-only principle; no rebuild of the frozen core table).
4. **Tags present & used (§2.4)** → retired from the write path; amani provenance that previously rode on tags moved to typed tables (`catalog_amani_provenance`, `catalog_amani_assets`, `artifact_platforms`, `artifact_threats`); amani priority now stored losslessly in the `priority` (`PRI-*`) column.

## 3. Internal-tension resolution: §2.1 vs §3
§2.1 prohibits storing user/effective state, yet §3 mandates `implementation_status`,
`verification_status`, `effectiveness` columns. **Resolution:** these columns hold
the catalog's **intrinsic baseline** (e.g., `STS-NOT-APPLIED`, `VER-NOT-VERIFIED`,
`EFF-UNKNOWN`) — a per-artifact default, never a user's assessment. A user's actual
status and any *effective* (computed) priority live outside the catalog and are
joined at runtime. The headless `scoring.py` demonstrates this: it reads the
catalog as reference and takes user status from a separate states map.

## 4. Approved fallback values (§2.3 / §2.6 record)
The triple is added by prefix; existing equivalents are reused, not duplicated.

| Dimension (list) | NA | UNKNOWN | MULTI | Notes |
|---|---|---|---|---|
| control_nature (`lk_control_nature`) | NAT-NA | NAT-UNKNOWN | NAT-MULTI | |
| control_function (`lk_control_function`) | FUN-NA | FUN-UNKNOWN | FUN-MULTI | |
| testability (`lk_testability`) | TST-NA* | TST-UNKNOWN | TST-MULTI | *TST-NA already existed |
| requirement_type (`lk_requirement_type`) | RQT-NA | RQT-UNKNOWN | RQT-MULTI | |
| priority (`lk_priority`) | PRI-NA | PRI-UNKNOWN | PRI-MULTI | |
| obligation_source (`lk_obligation_source`) | SRC-NA | SRC-UNKNOWN | SRC-MULTI | |
| obligation_level (`lk_obligation_level`) | OBL-NA | OBL-UNKNOWN | OBL-MULTI | |
| abstraction_level (`lk_abstraction_level`) | ABS-NA | ABS-UNKNOWN | ABS-MULTI | |
| granularity_level (`lk_granularity_level`) | GRN-NA | GRN-UNKNOWN | GRN-MULTI | |
| effectiveness (`lk_effectiveness`) | EFF-NA | EFF-UNKNOWN* | EFF-MULTI | *already existed |
| exception_status (`lk_exception_status`) | EXC-NOT-APPLICABLE* | EXC-UNKNOWN | EXC-MULTI | *NA equivalent + EXC-NONE existed |
| threat (`lk_threat`) | THR-NA | THR-UNKNOWN | THR-MULTI | new dimension (§5) |
| review_frequency (`lk_review_frequency`) | NA | UNKNOWN | MULTI | unprefixed list |
| mapping_strength (`lk_mapping_strength`) | NA | UNKNOWN | MULTI | unprefixed list |

**Excluded from fallbacks (always determinable):** `lk_sdt_domain`, `lk_sdt_subdomain`,
`lk_artifact_type`. These must carry a real value — the gate rejects NULL/fallback here.

## 5. Approved `THR-*` threat taxonomy (§2.6 record)
The canonical threat classification replacing the retired `Threat` tag. Full code
list and the `amani_threat_alias` (amani free-text → THR-*) live in
`migrations/013_threat_reference.sql`, generated by `scripts/build_threat_reference.py`.
Any new `THR-*` value or alias must be added there and recorded in this section.
