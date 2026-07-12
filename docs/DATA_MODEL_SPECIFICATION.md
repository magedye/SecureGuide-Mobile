# مواصفات نموذج البيانات (Data Model Specification) — SecureGuide

> وثيقة مكتملة توضّح: **(أ)** نوع وشكل ومضمون البيانات المصدرية التي نبني عليها، و**(ب)** تفاصيل جداول وأعمدة وحقول قاعدة البيانات النموذجية مع عيّنات بيانات لكل جدول.
> استثناء: جدول العناصر الأمنية `security_artifacts` تُعرض له **10 أسطر كأمثلة فقط** (لأنه الجدول المحوري كبير الحقول).
> المرجع المعياري: USACM v2.2.1 + SDT v2.2.1. المخطط القاطع: `migrations/001…006`. التاريخ: 2026-07-12.

---

## 0. المبادئ الحاكمة للبيانات
- **فصل المرجع عن التشغيل:** الكتالوج (`security_artifacts` وأبناؤه) يصف "ما هو" العنصر؛ الحالة التشغيلية لكل مؤسسة في `profile_artifacts`.
- **قيم مضبوطة:** كل الحقول المصنِّفة تُقيَّد بقوائم USACM/SDT (مُطبّقة عبر `CHECK` + جداول `lk_*`).
- **مجال واحد:** لكل عنصر `primary_domain` واحد و`sub_domain` واحد ينتمي إليه.
- **حفظ النسب:** `raw_artifacts` لا يُحذف/يُعدّل؛ النسب: raw → staging → catalog + `framework_mappings`.
- **offline-first / SQLite** هو نموذج التخزين المعياري.

---

# الجزء الأول: بيانات المصدر (Raw_Catalogs)

## 1.1 الشكل العام
21 ملف JSON في `SecureGuide_Mobile_Docs/Raw_Catalogs/`، بإجمالي **2,798 عنصراً خاماً**، كلها **مسودّات قبل التصنيف** (التطبيق هو من يضيف تصنيف USACM/SDT ويعيد الصياغة). كل ملف بغلاف موحّد:

```json
{
  "extraction_metadata": { "source_document": "CIS Controls v8", "total_artifacts": 29 },
  "artifacts": [ { ...عنصر خام... }, ... ]
}
```

## 1.2 بنية العنصر الخام (نوعان)
**النوع النحيل (16 ملفاً):**
```json
{
  "raw_artifact_id": "RAW-BATCH-95C84370",
  "source_metadata": { "source_document": "...", "source_type": "FRAMEWORK",
                       "source_version": "...", "source_section": "1.1" },
  "original_content": { "raw_text_en": "...", "original_heading": "...", "context_paragraph": "..." },
  "extracted_elements": { "title_draft": "1.1", "description_draft": "...", "keywords": ["Asset Inventory", "Hardware"] }
}
```
**النوع الغني (5 ملفات)** يضيف: `source_metadata.{source_url, issuing_authority, publication_date, language}`، `original_content.raw_text_ar`، `extracted_elements.entities_mentioned{technologies,roles,systems,threats,assets}`، و`collection_metadata`، و`classification_status{usacm_type_assigned, sdt_domain_assigned, sdt_subdomain_assigned, requires_classification, ...}`، و`quality_flags{is_complete, needs_human_review, is_ambiguous, ambiguity_reason}`.

## 1.3 ملاحظات على المضمون
- `source_type` القِيَم الفعلية: `FRAMEWORK, STANDARD, THREAT_INTEL, GUIDELINE, POLICY_TEMPLATE`.
- **تصنيف الإطار مدفون** داخل `context_paragraph` (أحياناً JSON: `{"function":"GOVERN (GV)","category":"...","tags":[...]}`، وأحياناً نص حر).
- أكبر المصادر: NIST SP 800-53 (1196)، MITRE ATT&CK Enterprise (858)، OWASP ASVS (345)، ECC 2024 (108)، NIST CSF 2.0 (106).
- عناصر NIST 800-53 قد تحوي عناصر نائبة `{{ insert: param, ... }}` تُنظَّف عند الصياغة، لا تُنشر كما هي.

---

# الجزء الثاني: قاعدة البيانات النموذجية

## خريطة الطبقات (50+ جدولاً + 37 lookup + 6 views)
| الطبقة | الجداول |
|---|---|
| 1. الإدخال | `source_catalogs`, `raw_artifacts` |
| 2. الكتالوج المرجعي | `security_artifacts` + 10 أبناء |
| 3. القوالب | `templates`, `template_items` |
| 4. التشغيل | `enterprise_profiles`, `profile_artifacts`, `profile_assessments`, `profile_evidence`, `profile_exceptions` |
| A. الأصول | `ref_asset_types`, `enterprise_assets`, `asset_controls`, `asset_vulnerabilities`, `asset_threats` |
| B. المؤشرات | `threat_intelligence_sources`, `detection_tools`, `threat_indicators`, `indicator_vulnerabilities`, `indicator_controls`, `indicator_tools`, `indicator_recommended_actions` |
| C. التضمين | `artifact_embeddings`, `equivalence_groups`, `equivalence_group_members`, `duplicate_candidates` |
| R. المرجعية | 37 جدول `lk_*` |
| Q. التنسيق | `schema_migrations`, `curation_batches`, `staging_artifacts`, `consolidation_decisions`, `consolidation_members`, `curation_lessons` |
| P. الترقية | `promotion_batches`, `promotion_batch_items`, `promotion_audit_log` |
| V. العروض | `v_review_queue`, `v_duplicate_candidates`, `v_catalog_curation`, `v_artifact_detail`, `v_profile_dashboard`, `v_gap_analysis` |

---

## الطبقة 1 — الإدخال

### `source_catalogs` — سجل المصادر
| الحقل | النوع | القيم/القيد |
|---|---|---|
| `id` | TEXT PK | slug من اسم الملف |
| `name` | TEXT NOT NULL | اسم المصدر |
| `source_type` | TEXT | FRAMEWORK/STANDARD/THREAT_INTEL/GUIDELINE/POLICY_TEMPLATE/REGULATION/DOCUMENT/SYSTEM/TOOL |
| `version` | TEXT | — |
| `source_url`, `issuing_authority`, `publication_date` | TEXT | ميتاداتا (النوع الغني) |
| `imported_at` | TEXT | datetime |

**عيّنة (حقيقية، 21 صفاً):**
| id | name | source_type | version |
|---|---|---|---|
| cis_controls_v8 | CIS Controls v8 | FRAMEWORK | Unknown |
| nist_sp_800_53_rev_5_… | NIST SP 800-53 Rev. 5 | STANDARD | Release 5.2.0 |
| nca_ecc_1_2018 | NCA ECC-1:2018 | FRAMEWORK | 1:2018 |

### `raw_artifacts` — الحفظ الخام (المصدر لا يُمسّ)
| الحقل | النوع | ملاحظة |
|---|---|---|
| `id` | TEXT PK | حتمي `<catalog>::<index>` مثل `cis_controls_v8::0000` |
| `source_catalog_id` | TEXT FK | → source_catalogs |
| `external_raw_id` | TEXT | `raw_artifact_id` من المصدر |
| `source_document/type/section/version/url` | TEXT | نسب المصدر |
| `title_draft`, `description_draft` | TEXT | مسودّة العنصر |
| `raw_text_en`, `raw_text_ar`, `original_heading`, `context_paragraph` | TEXT | المحتوى الأصلي كما هو |
| `keywords_json`, `entities_mentioned_json` | TEXT(JSON) | مصفوفات |
| `usacm_type_assigned`, `sdt_domain_assigned`, `sdt_subdomain_assigned` | TEXT | تلميحات التصنيف (النوع الغني) |
| `requires_classification`, `needs_human_review`, `is_ambiguous` | INT(0/1) | أعلام |
| `raw_json` | TEXT NOT NULL | الغلاف الأصلي كاملاً |
| `source_file`, `content_hash` | TEXT | الملف المصدر + sha256 (idempotency) |
| `promoted_artifact_id` | TEXT FK | نسب إلى الكتالوج بعد الترقية |

**عيّنة (حقيقية، 2798 صفاً):**
| id | source_section | title_draft | raw_text_en (مقتطف) | content_hash |
|---|---|---|---|---|
| cis_controls_v8::0000 | 1.1 | 1.1 | Establish and maintain an accurate… inventory of all enterprise assets… | 813f580ffec6… |
| cis_controls_v8::0001 | 1.2 | 1.2 | Ensure that a process exists to address unauthorized assets… | 1d37ba11989a… |

---

## الطبقة 2 — الكتالوج المرجعي

### `security_artifacts` — (10 أسطر كأمثلة فقط)
> الجدول المحوري (~76 عموداً: هوية ثنائية اللغة + حقول صياغة + تصنيف USACM/SDT + دورة حياة + مساءلة AI + نسب). التفاصيل الكاملة في [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md). أدناه **10 أمثلة** (الأربعة الأولى حقيقية مُرقّاة، والباقي توضيحي):

| id | type | title_en | primary_domain | sub_domain | obligation | ai_review_status | publication_status |
|---|---|---|---|---|---|---|---|
| SG-CTR-AI-02 | ART-CTR | Asset Inventory Currency Maintenance | SD-02 | SD-02.01 | OBL-MND | AIR-HUMAN-APPROVED | APPROVED |
| SG-CTR-AI-05 | ART-CTR | Unauthorized Asset Detection | SD-02 | SD-02.01 | OBL-MND | AIR-HUMAN-APPROVED | APPROVED |
| SG-REQ-AI-06 | ART-REQ | Software Inventory | SD-02 | SD-02.02 | OBL-MND | AIR-HUMAN-APPROVED | APPROVED |
| SG-POL-AI-08 | ART-POL | Acceptable Use of Assets Policy | SD-08 | SD-08.05 | OBL-MND | AIR-HUMAN-APPROVED | APPROVED |
| SG-REQ-AST-001 | ART-REQ | Enterprise Asset Inventory | SD-02 | SD-02.01 | OBL-MND | AIR-HUMAN-APPROVED | PUBLISHED |
| SG-CFG-SSH-001 | ART-CFG | SSH Root Login Restriction | SD-04 | SD-04.03 | OBL-MND | AIR-HUMAN-APPROVED | PUBLISHED |
| SG-REQ-MFA-001 | ART-REQ | Multi-Factor Authentication for Admins | SD-03 | SD-03.02 | OBL-MND | AIR-AUTO-ACCEPTED | APPROVED |
| SG-EVD-LOG-001 | ART-EVD | Privileged Access Review Evidence | SD-03 | SD-03.04 | OBL-REC | AIR-HUMAN-APPROVED | APPROVED |
| SG-MET-COV-001 | ART-MET | Asset Coverage Percentage | SD-02 | SD-02.01 | OBL-OPT | AIR-HUMAN-APPROVED | APPROVED |
| SG-RSK-LEG-001 | ART-RSK | Legacy System Exposure Risk | SD-04 | SD-04.02 | OBL-CON | AIR-HUMAN-REVIEW | DRAFT |

### `artifact_tags` — وسوم ثانوية (سياق لا تصنيف)
| الحقل | القيد |
|---|---|
| `artifact_id` FK, `tag_type`, `tag_value` (PK مركّب) | `tag_type` ∈ Technology, Framework, Concept, Context, Threat, Data, Party |

**عيّنة (توضيحية):** `(SG-CFG-SSH-001, Technology, Linux)` · `(SG-REQ-MFA-001, Concept, Zero Trust)` · `(SG-REQ-AST-001, Framework, CIS)`

### `artifact_relationships` — رسم العلاقات
| الحقل | القيد |
|---|---|
| `source_id`, `target_id` FK · `relation_type` | 12 كود REL-*؛ REL-CNF يتطلب `resolution_status`+`resolution_note` |

**عيّنة (توضيحية):** `(SG-EVD-LOG-001, SG-CTR-AI-05, REL-VER)` (دليل يتحقق من ضابط) · `(SG-CFG-SSH-001, SG-CTR-AI-05, REL-IMP)`

### `framework_mappings` — الربط بالأطر (النسب)
| الحقل | القيد |
|---|---|
| `artifact_id` FK, `framework`, `version`, `reference`, `mapping_strength`, `rationale` | strength ∈ DIRECT/INDIRECT/PARTIAL/INFORMATIVE؛ غير DIRECT يتطلب rationale |

**عيّنة (حقيقية، 6 صفوف):**
| artifact_id | framework | reference | mapping_strength |
|---|---|---|---|
| SG-CTR-AI-02 | NIST SP 800-53 Rev. 5 | Control CM-8(1) | DIRECT |
| SG-CTR-AI-02 | NIST SP 800-53 Rev. 5 | Control CM-8(2) | DIRECT |
| SG-CTR-AI-05 | CIS Controls v8 | 1.2 | DIRECT |
| SG-POL-AI-08 | Essential Cybersecurity Controls (ECC 2-2024) | Control 2-1-4 | INDIRECT (rationale) |

### باقي الأبناء المرجعيين
| الجدول | أعمدة رئيسية | قيد | عيّنة توضيحية |
|---|---|---|---|
| `artifact_applicability_scope` | artifact_id, scope_type, scope_value | scope_type ∈ 8 (ORGANIZATION_SIZE…EXCLUSION) | (SG-REQ-AST-001, ORGANIZATION_SIZE, ENTERPRISE) |
| `artifact_self_assessments` | artifact_id, status, score, assessed_by | status ∈ NOT_ASSESSED/IN_PROGRESS/COMPLETED/NEEDS_REVIEW؛ score 0-100 | (SG-CTR-AI-05, COMPLETED, 80, auditor) |
| `technical_dependencies` | artifact_id, dependency_type, dependency_name, dependency_status | type ∈ SYSTEM/PLATFORM/VENDOR/SKILL/BUDGET | (SG-REQ-MFA-001, SYSTEM, Active Directory, AVAILABLE) |
| `verification_tools` | artifact_id, tool_name, tool_type, verification_method | tool_type ∈ SIEM/EDR/IAM/VULNERABILITY/CSPM/MANUAL | (SG-EVD-LOG-001, Splunk, SIEM, LOG) |
| `stakeholders` | artifact_id, role, responsibility | responsibility ∈ OWNER/REVIEWER/APPROVER/CONSULTED/INFORMED | (SG-POL-AI-08, CISO, OWNER) |
| `remediation_actions` | artifact_id, action, priority, responsible_role | priority ∈ PRI-* | (SG-RSK-LEG-001, "Isolate legacy host", PRI-HIGH, SysAdmin) |
| `external_references` | artifact_id, type, title, url | type ∈ ARTICLE/BLOG/TOOL/VIDEO/STUDY/BENCHMARK | (SG-CFG-SSH-001, BENCHMARK, "CIS Linux Benchmark", https://…) |

---

## الطبقة 3 — القوالب
| الجدول | أعمدة | قيد |
|---|---|---|
| `templates` | id, name, version, scope_note | — |
| `template_items` | template_id, artifact_id, inclusion_status, inclusion_reason, applicability_condition, priority_override, review_frequency_override | inclusion_status ∈ MANDATORY/RECOMMENDED/OPTIONAL/CONDITIONAL |

**عيّنة (توضيحية):**
- templates: `(TPL-ESS-01, "Cybersecurity Essentials", 1.0, "SMEs")`
- template_items: `(TPL-ESS-01, SG-REQ-AST-001, MANDATORY, "Baseline asset visibility", NULL, PRI-HIGH, ANNUAL)`

---

## الطبقة 4 — التشغيل (الحقيقة لكل مؤسسة)
| الجدول | أعمدة رئيسية | قيد |
|---|---|---|
| `enterprise_profiles` | id, name, profile_kind, organization_size, industry, country, target_maturity_level, source_template_id | maturity ∈ INITIAL…OPTIMIZED |
| `profile_artifacts` | profile_id, artifact_id, **implementation_status, verification_status, effectiveness, exception_status**, priority_override, current_maturity_level, assigned_owner, due_date, notes | الحالات الأربع مضبوطة؛ UNIQUE(profile,artifact) |
| `profile_assessments` | profile_artifact_id, assessment_date, assessor_name, score, لقطة الحالات | score 0-100 |
| `profile_evidence` | profile_artifact_id, assessment_id, evidence_type, evidence_url | type ∈ DOCUMENT/SCREENSHOT/LOG/REPORT/CONFIG/ATTESTATION/LINK/OTHER |
| `profile_exceptions` | profile_artifact_id, exception_status, justification, approved_by, expiry_date | EXC غير NONE |

**عيّنة (توضيحية):**
- enterprise_profiles: `(PRF-ACME, "ACME Bank", "organization", LARGE, FINANCE, SA, MANAGED, TPL-ESS-01)`
- profile_artifacts: `(PA-001, PRF-ACME, SG-REQ-AST-001, STS-PARTIAL, VER-NOT-VERIFIED, EFF-UNKNOWN, EXC-NONE, PRI-HIGH, DEFINED, "GRC Team", 2026-09-30, "قيد الجرد")`
- profile_assessments: `(AS-001, PA-001, 2026-07-01, "Internal Auditor", 60, STS-PARTIAL, VER-NOT-VERIFIED, EFF-MEDIUM, EXC-NONE)`
- profile_evidence: `(EV-001, PA-001, AS-001, REPORT, "s3://…/inventory.pdf", "تقرير الجرد الربعي")`
- profile_exceptions: `(EX-001, PA-002, EXC-RISK-ACCEPTED, "نظام قديم يُستبدل 2027", "CISO", 2027-01-01)`

---

## الوحدة A — ذكاء الأصول (تشغيلي)
| الجدول | أعمدة رئيسية | قيد |
|---|---|---|
| `ref_asset_types` | id, name_en, name_ar, category | category ∈ أنواع أصول USACM |
| `enterprise_assets` | id, profile_id, name, asset_type, criticality, exposure, owner, environment, catalog_artifact_id | asset_type (10)/criticality (CRITICAL,HIGH,MEDIUM,LOW) |
| `asset_controls` | asset_id, artifact_id, coverage_status | ∈ COVERED/PARTIAL/PLANNED/GAP |
| `asset_vulnerabilities` | asset_id, artifact_id, cve_id, cvss_score, status | cvss 0-10؛ status ∈ OPEN/MITIGATED/ACCEPTED/FALSE_POSITIVE/RESOLVED |
| `asset_threats` | asset_id, artifact_id, relevance | relevance ∈ CRITICAL/HIGH/MEDIUM/LOW |

**عيّنة (توضيحية):**
- enterprise_assets: `(AST-DB01, PRF-ACME, "Core Banking DB", DATA, CRITICAL, INTERNAL, "DBA Team", PRODUCTION, NULL)`
- asset_controls: `(AST-DB01, SG-CTR-AI-05, COVERED)` · asset_vulnerabilities: `(AST-DB01, NULL, "CVE-2024-1234", 9.8, OPEN)`

---

## الوحدة B — مؤشرات التهديد (استخبارات)
| الجدول | أعمدة رئيسية | قيد |
|---|---|---|
| `threat_intelligence_sources` | id, name, source_type, url, reliability | reliability ∈ HIGH/MEDIUM/LOW/UNKNOWN |
| `detection_tools` | id, name, tool_type, vendor, capabilities | tool_type ∈ SIEM/EDR/XDR/NDR/SOAR/… |
| `threat_indicators` | id, profile_id, catalog_artifact_id, title, indicator_class, ioc_type, ioc_value, severity_level, confidence_score, status, mitre_tactic, mitre_technique_id, primary_domain, sub_domain | class (7 طبقات), severity (CRITICAL…INFO), status (ACTIVE…EXPIRED), confidence 0-1, SDT مع انتماء |
| `indicator_vulnerabilities` | indicator_id, artifact_id, cve_id, cvss_score | cvss 0-10 |
| `indicator_controls` | indicator_id, artifact_id, control_role, coverage_pct | role ∈ DETECTIVE/PREVENTIVE/CORRECTIVE/COMPENSATING؛ pct 0-100 |
| `indicator_tools` | indicator_id, detection_tool_id, coverage_pct | 0-100 |
| `indicator_recommended_actions` | indicator_id, action, priority, status | priority PRI-*؛ status ∈ PENDING/IN_PROGRESS/DONE/DISMISSED |

**عيّنة (توضيحية):**
- threat_indicators: `(IND-PHISH-01, PRF-ACME, NULL, "Phishing wave", IOC, DOMAIN, "evil.example", HIGH, 0.9, ACTIVE, "Initial Access", "T1566", SD-06, SD-06.02)`
- indicator_controls: `(IND-PHISH-01, SG-REQ-MFA-001, PREVENTIVE, 80)` · indicator_recommended_actions: `(IND-PHISH-01, "Block sender domain", PRI-HIGH, PENDING)`

---

## الوحدة C — التضمين وكشف التكرار
| الجدول | أعمدة رئيسية | قيد |
|---|---|---|
| `artifact_embeddings` | artifact_id, model_name, model_version, dim, embedding(BLOB), source_text_hash | `length(embedding)=dim*4`؛ PK(artifact_id, model_name, model_version) |
| `equivalence_groups` | id, label, canonical_artifact_id, concept_domain | concept_domain ∈ SD-01..08 |
| `equivalence_group_members` | group_id, artifact_id, member_role, similarity | role ∈ CANONICAL/MEMBER؛ similarity [-1,1] |
| `duplicate_candidates` | artifact_id_a, artifact_id_b, similarity, detection_method, status, resolution | a<b؛ method ∈ EMBEDDING/EXACT_MATCH/FUZZY/MANUAL؛ status ∈ PENDING/CONFIRMED/REJECTED |

**عيّنة:** equivalence_groups (حقيقية): `(EG-AI-AI-02, "Asset Inventory Currency Maintenance", NULL, SD-02)`. artifact_embeddings (توضيحية): `(SG-REQ-AST-001, multilingual-e5-small, 1, 384, <BLOB 1536B>, ab12…)`.

---

## الطبقة R — البيانات المرجعية (37 جدول `lk_*`)
كل جداول الـlookup بنية موحّدة: `code TEXT PK, name_en TEXT, name_ar TEXT, sort_order INT` (و`lk_sdt_subdomain` يضيف `domain_code` FK). القائمة: `lk_artifact_type` (22)، `lk_abstraction_level` (7)، `lk_obligation_source/level`، `lk_exception_status`، `lk_granularity_level`، `lk_control_nature/function`، `lk_testability`، `lk_implementation/verification/effectiveness_status`، `lk_priority`، `lk_relationship_type` (12)، `lk_ai_review_status`، `lk_requirement_type`، `lk_mapping_strength`، `lk_tag_type`، `lk_review_frequency`، `lk_publication_status`، `lk_source_type`، `lk_asset_type` (10)، `lk_maturity_level`، `lk_cost_category`، `lk_import_status`، `lk_applicability_scope_type`، `lk_dependency_type/status`، `lk_verification_tool_type/method`، `lk_stakeholder_responsibility`، `lk_external_reference_type`، `lk_self_assessment_status`، `lk_resolution_status`، `lk_catalog_source_type`، `lk_sdt_domain` (8)، `lk_sdt_subdomain` (40). إجمالي **268 صفاً**.

**عيّنة (حقيقية):**
| جدول | code | name_en | name_ar |
|---|---|---|---|
| lk_artifact_type | ART-REQ | Requirement | متطلب |
| lk_sdt_domain | SD-02 | Assets, Data & Privacy | الأصول والبيانات والخصوصية |
| lk_sdt_subdomain | SD-02.01 | Asset Inventory & Management | جرد وإدارة الأصول (domain_code=SD-02) |

---

## الطبقة Q — التنسيق (Curation)
| الجدول | أعمدة رئيسية | قيد |
|---|---|---|
| `schema_migrations` | version PK, description, applied_at | مبذور 001-006 |
| `curation_batches` | id, source_catalog_id, status, item_count, snapshot_ref | status ∈ OPEN/PROCESSING/COMPLETED/ROLLED_BACK |
| `staging_artifacts` | id, raw_artifact_id, صياغة إنجليزية، `proposed_*` (type/domain/sub/obligation/requirement_type/control_*), classification_confidence, merge_action, curation_status, quality_score, **final_review_status, ready_for_promotion, promotion_blockers, content_hash**, promoted_artifact_id | curation_status (7)؛ merge_action (6 قرارات)؛ proposed_* مضبوطة |
| `consolidation_decisions` | id, decision, canonical_artifact_id, rationale | decision ∈ CANONICALIZE/EQUIVALENCE_GROUP/CROSSWALK_ONLY/RELATE_ONLY/KEEP_SEPARATE/DEPRECATE_DERIVED |
| `consolidation_members` | decision_id, artifact_id, role | role ∈ CANONICAL/MEMBER/SOURCE |
| `curation_lessons` | lesson_type, pattern, example, action | lesson_type مضبوط |

**عيّنة (حقيقية، staging):**
| id | title_en | proposed_type | proposed_sub_domain | final_review_status | ready |
|---|---|---|---|---|---|
| STG-CANON-AI-02 | Asset Inventory Currency Maintenance | ART-CTR | SD-02.01 | APPROVED | 1 |
| STG-CANON-AI-03 | Asset Ownership Accountability | ART-CTR | SD-02.01 | REJECTED | 0 |
| STG-CANON-AI-01 | Enterprise Asset Inventory | ART-REQ | SD-02.01 | DEFERRED | 0 |

---

## الطبقة P — الترقية (Promotion)
| الجدول | أعمدة رئيسية | قيد |
|---|---|---|
| `promotion_batches` | id, plan_hash, status, item_count, applied_at, rolled_back_at | status ∈ PLANNED/APPLIED/COMPLETED/ROLLED_BACK/FAILED |
| `promotion_batch_items` | batch_id, staging_id, final_artifact_id, source_staging_hash, action, mappings/tags/relationships_created | action ∈ INSERT/UPDATE/SKIP |
| `promotion_audit_log` | batch_id, event, detail, at | event ∈ PLAN/APPLY/APPLY_SKIP/ROLLBACK/REJECT/ERROR |

**عيّنة (حقيقية):**
- promotion_batches: `(AI-INV-PROD-20260711, e411524714…, COMPLETED, 4, 2026-07-11 20:42:58)`
- promotion_batch_items: `(AI-INV-PROD-20260711, STG-CANON-AI-02, SG-CTR-AI-02, INSERT, 2)`
- promotion_audit_log: `(AI-INV-PROD-20260711, APPLY, "STG-CANON-AI-02 -> SG-CTR-AI-02 (+2 mappings)", 2026-07-11 20:40:42)`

---

## الطبقة V — العروض (Read-only)
| العرض | الغرض |
|---|---|
| `v_review_queue` | طابور المراجعة (staging منخفض الثقة + كتالوج يحتاج مراجعة) |
| `v_duplicate_candidates` | مرشّحات التكرار المعلّقة (الأقوى أولاً) |
| `v_catalog_curation` | تقدّم التنسيق (أعداد حسب الحالة/المجال + متوسط الثقة/الجودة) |
| `v_artifact_detail` | تفاصيل العنصر + وسوم مجمّعة + عدد mappings/relationships |
| `v_profile_dashboard` | ملخّص تشغيلي لكل ملف |
| `v_gap_analysis` | فجوات الملف (غير مطبّق كلياً وبلا استثناء) |

**عيّنة (حقيقية من `v_artifact_detail`):** `(SG-CTR-AI-02, ART-CTR, SD-02.01, tags=NULL, mapping_count=2, relationship_count=0)`

---

## 3. الحالة الفعلية الحالية (catalog.db)
| المقياس | القيمة |
|---|---|
| source_catalogs | 21 |
| raw_artifacts | 2,798 |
| **security_artifacts (مُرقّاة)** | **4** |
| framework_mappings | 6 |
| staging_artifacts | 11 (4 معتمدة، 1 مرفوض، 4 مؤجّلة، 2 مقسّمة) |
| lk_* rows | 268 |
| الجداول الفارغة (جاهزة) | القوالب، التشغيل، الأصول، المؤشرات، التضمين — تُملأ في المراحل التالية |

> الجداول الفارغة أعلاه **مُنشأة ومُقيَّدة ومُختبَرة** (عيّناتها توضيحية)؛ تُملأ عند تفعيل القوالب/الملفات/الأصول/المؤشرات/التضمين.
