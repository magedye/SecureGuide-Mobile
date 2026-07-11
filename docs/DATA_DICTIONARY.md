# قاموس البيانات (Data Dictionary)

المصدر المرجعي القاطع للمخطط هو [`migrations/001_initial_schema.sql`](../migrations/001_initial_schema.sql). يلتزم المخطط بـ **USACM v2.2.1 §8** (النموذج المعياري لـ SQLite) و **SDT v2.2.1**، ويطبّق سياسة الصياغة الموحدة في [`AUTHORING_POLICY.md`](AUTHORING_POLICY.md) وسياسة التوحيد والدمج في [`CONSOLIDATION_POLICY.md`](CONSOLIDATION_POLICY.md).

## المبدأ الحاكم: فصل المرجع عن التشغيل
- **الكتالوج المرجعي** (`security_artifacts` وجداوله الفرعية) يصف **"ما هو" العنصر الأمني**. القيم التشغيلية عليه (implementation/verification/effectiveness/exception) هي **قيم افتراضية مرجعية فقط**.
- **الطبقة التشغيلية** (`profile_artifacts` وما يتبعها) تحمل **الحالة الحقيقية لكل مؤسسة**. لا تُخزَّن الحالة التشغيلية للمؤسسة داخل الكتالوج المرجعي أبداً (AGENTS.md قاعدة 1 و8).

## خريطة الطبقات والجداول (20 جدولاً)
| الطبقة | الجداول |
|---|---|
| 1. الإدخال | `source_catalogs`, `raw_artifacts` |
| 2. الكتالوج المرجعي | `security_artifacts` + 10 جداول فرعية: `artifact_tags`, `artifact_relationships`, `framework_mappings`, `artifact_applicability_scope`, `artifact_self_assessments`, `technical_dependencies`, `verification_tools`, `stakeholders`, `remediation_actions`, `external_references` |
| 3. القوالب | `templates`, `template_items` |
| 4. التشغيل | `enterprise_profiles`, `profile_artifacts`, `profile_assessments`, `profile_evidence`, `profile_exceptions` |

> الأصول والمخاطر والتهديدات والثغرات تُنمذَج كأنواع `ART-AST` / `ART-RSK` / `ART-THR` / `ART-VUL` داخل `security_artifacts`، وتُربط عبر `artifact_relationships` (REL-MIT, REL-AFF) — لا جداول منفصلة.

---

## جدول: `security_artifacts` (الكتالوج المرجعي)
### الهوية والمحتوى (سياسة الصياغة، English-first)

حقول الإنجليزية هي حقول الاعتماد الأساسية في الـMVP. حقول العربية اختيارية ومؤجلة كطبقة ترجمة/إثراء لاحقة، مع بقائها في المخطط لدعم RTL والترجمة المستقبلية.
| الحقل | المعنى | النوع | ملاحظات |
|---|---|---|---|
| `id` | المعرف الفريد | TEXT PK | - |
| `source_catalog_id` | مصدر العنصر | TEXT FK | → `source_catalogs` |
| `source_artifact_id`, `temp_id` | معرفات نسب الاستيراد | TEXT | للحفاظ على الأصل عند الدمج |
| `type` | نوع العنصر (USACM) | TEXT NOT NULL | 22 كوداً `ART-*` |
| `title_en` / `title_ar` | العنوان المختصر | TEXT | `title_en` إلزامي |
| `description_en` / `description_ar` | الوصف المستورد | TEXT | - |
| `canonical_statement` | النص الموحد الرسمي | TEXT | - |
| `definition_short_en` / `_ar` | تعريف مختصر (20-35 كلمة) | TEXT | - |
| `definition_full_en` / `_ar` | تعريف مطول (80-180 كلمة) | TEXT | - |
| `objective_en` / `_ar` | الهدف الأمني | TEXT | - |
| `applicability_note` | متى/أين ينطبق | TEXT | - |
| `implementation_guidance` | إرشاد تطبيقي غير إلزامي | TEXT | - |
| `verification_method_note` | آلية التحقق (نص حر) | TEXT | راجع أيضاً `verification_tools` |
| `evidence_required` | الأدلة المتوقعة | TEXT | - |
| `common_misinterpretations` | منع سوء الفهم الشائع | TEXT | - |
| `source_quote` | مقتطف مصدر قصير واختياري | TEXT | لا يستخدم لنشر النص الأصلي الكامل؛ النسب المنظم هو المرجع الأساسي |

### التصنيف (USACM + SDT)
| الحقل | القيم المسموحة |
|---|---|
| `primary_domain` | SD-01 … SD-08 |
| `sub_domain` | 40 قيمة `SD-XX.YY` — ويُشترط `substr(sub_domain,1,5)=primary_domain` |
| `abstraction_level` | ABS-GOV, ABS-RIS, ABS-POL, ABS-CTR, ABS-PRO, ABS-TEC, ABS-EVM |
| `source` (مصدر الإلزام) | SRC-REG, SRC-LEG, SRC-CON, SRC-STD, SRC-INT, SRC-BST, SRC-RSK |
| `source_type` | DOCUMENT, SYSTEM, TOOL, INTERVIEW, OBSERVATION, STANDARD, REGULATION |
| `obligation_level` | OBL-MND, OBL-CON, OBL-REC, OBL-OPT |
| `requirement_type` | RQT-* (إلزامي لـ ART-REQ فقط، وممنوع لغيره) |
| `granularity_level` | GRN-HIGH, GRN-MEDIUM, GRN-DETAILED, GRN-EXECUTABLE, GRN-TECHNICAL, GRN-EVIDENTIARY, GRN-METRIC |
| `control_nature` | NAT-ORG, NAT-HUM, NAT-PHY, NAT-TEC (إلزامي لـ ART-CTR/ART-CTE) |
| `control_function` | FUN-PRE, FUN-DET, FUN-COR, FUN-REC, FUN-DRR, FUN-COM (إلزامي لـ ART-CTR/ART-CTE) |
| `testability` | TST-AUTO, TST-MAN, TST-DOC, TST-INT, TST-NA (إلزامي لـ ART-CTR/ART-CTE) |

### الأولوية المرجعية ودورة الحياة
| الحقل | القيم |
|---|---|
| `priority` / `priority_weight` | PRI-CRITICAL=10, PRI-HIGH=7, PRI-MEDIUM=4, PRI-LOW=1 (متطابقة إجبارياً) |
| `review_frequency` | DAILY…CONTINUOUS (يتطلب `next_review_date` إن لم يكن AD-HOC) |
| `publication_status` | DRAFT, UNDER_REVIEW, APPROVED, PUBLISHED, DEPRECATED, WITHDRAWN |
| `asset_type` / `asset_criticality` | إلزامي لـ ART-AST (10 أنواع أصول / CRITICAL,HIGH,MEDIUM,LOW) |
| `required_maturity_level` | INITIAL, REPEATABLE, DEFINED, MANAGED, OPTIMIZED |
| `cost_category` / `cost_estimate*` / `effort_estimate` | تقديرات التكلفة والجهد (غير سالبة؛ max ≥ min) |

### مساءلة الذكاء الاصطناعي (قيم افتراضية مرجعية)
| الحقل | القيم/القاعدة |
|---|---|
| `classification_confidence` | 0.0–1.0؛ إن وُجدت فـ `classification_rationale` إلزامي |
| `ai_review_status` | AIR-AUTO-ACCEPTED, AIR-HUMAN-REVIEW, AIR-HUMAN-APPROVED, AIR-HUMAN-REJECTED |
| `requires_human_review` | 0/1 — إن كانت الثقة ≤ 0.70 يجب أن تكون 1 و`ai_review_status=AIR-HUMAN-REVIEW` |
| `rejected_alternatives` | البدائل المرفوضة (نص/JSON) |
| القيم التشغيلية المرجعية | `implementation_status` (STS-*)، `verification_status` (VER-*)، `effectiveness` (EFF-*)، `exception_status` (EXC-*) — **افتراضية مرجعية فقط** |

## الجداول الفرعية للمرجع
| الجدول | الغرض | القيود المضبوطة |
|---|---|---|
| `artifact_tags` | وسوم ثانوية مطبّعة (PK مركّب) | `tag_type` ∈ Technology, Framework, Concept, Context, Threat, Data, Party |
| `artifact_relationships` | رسم علاقات العناصر (Source→Target) | `relation_type` ∈ 12 كود REL-*؛ REL-CNF يتطلب `resolution_status`+`resolution_note` |
| `framework_mappings` | ربط بالأطر | `mapping_strength` ∈ DIRECT/INDIRECT/PARTIAL/INFORMATIVE؛ غير DIRECT يتطلب `rationale` |
| `artifact_applicability_scope` | نطاق التطبيق المطبّع | `scope_type` ∈ 8 أنواع (ORGANIZATION_SIZE…EXCLUSION) |
| `artifact_self_assessments` | تقييم مرجعي (USACM) | `status` ∈ NOT_ASSESSED/IN_PROGRESS/COMPLETED/NEEDS_REVIEW؛ score 0-100 |
| `technical_dependencies` | اعتماديات تقنية | dependency_type/status مضبوطان |
| `verification_tools` | أدوات التحقق | tool_type ∈ SIEM/EDR/IAM/VULNERABILITY/CSPM/MANUAL |
| `stakeholders` | أصحاب المصلحة | responsibility ∈ OWNER/REVIEWER/APPROVER/CONSULTED/INFORMED |
| `remediation_actions` | إجراءات المعالجة | priority ∈ PRI-* |
| `external_references` | مراجع خارجية | type ∈ ARTICLE/BLOG/TOOL/VIDEO/STUDY/BENCHMARK |

## طبقة الإدخال
| الجدول | حقول رئيسية |
|---|---|
| `source_catalogs` | `id`, `name`, `source_type` (FRAMEWORK/STANDARD/THREAT_INTEL/GUIDELINE/POLICY_TEMPLATE/…), `version`, `issuing_authority`, `publication_date` |
| `raw_artifacts` | يخزّن غلاف `Raw_Catalogs` كما هو في `raw_json` + حقول مفهرسة: `title_draft`, `description_draft`, `context_paragraph`, `keywords_json`, `source_section`, تلميحات التصنيف المسبق، و`promoted_artifact_id` (نسب إلى الكتالوج) |

## طبقة القوالب
| الجدول | حقول رئيسية / قيود |
|---|---|
| `templates` | `id`, `name`, `version`, `scope_note` |
| `template_items` | `template_id`, `artifact_id`, `inclusion_status` ∈ MANDATORY/RECOMMENDED/OPTIONAL/CONDITIONAL, `inclusion_reason`, `applicability_condition`, `priority_override`, `review_frequency_override` — القالب لا ينسخ العناصر بل يشير إليها |

## الطبقة التشغيلية (الحالة الحقيقية لكل مؤسسة)
| الجدول | الغرض | حقول/قيود رئيسية |
|---|---|---|
| `enterprise_profiles` | سياق تشغيلي (مؤسسة/فرع/نظام/سحابة/تدقيق/مشروع) | `profile_kind`, `organization_size`, `industry`, `target_maturity_level`, `source_template_id` |
| `profile_artifacts` | حالة العنصر داخل الملف — **الحقيقة التشغيلية** | الحالات الأربع المستقلة (`implementation_status`, `verification_status`, `effectiveness`, `exception_status`) + `priority_override` + `current_maturity_level` + `assigned_owner` + `due_date` + `notes`؛ `UNIQUE(profile_id, artifact_id)` |
| `profile_assessments` | سجل تقييمات تاريخي | `assessor_name`, `score` (0-100)، ولقطة الحالات وقت التقييم |
| `profile_evidence` | أدلة الإثبات | `evidence_type` ∈ DOCUMENT/SCREENSHOT/LOG/REPORT/CONFIG/ATTESTATION/LINK/OTHER؛ يرتبط اختيارياً بتقييم |
| `profile_exceptions` | استثناءات معتمدة | `exception_status` (EXC غير NONE)، `justification` إلزامي، `approved_by`, `expiry_date` |

*قاعدة ذهبية: لا يجوز أبداً دمج حقول `profile_artifacts` التشغيلية داخل `security_artifacts`، ولا دمج الحالات الأربع في حالة واحدة.*

---

# ملحق: الترحيل 002 — الأصول والمؤشرات والتضمين

المصدر: [`migrations/002_assets_indicators_embeddings.sql`](../migrations/002_assets_indicators_embeddings.sql) (إضافي فوق 001). 16 جدولاً في ثلاث وحدات.

## وحدة (أ): ذكاء الأصول (تشغيلي لكل ملف)
| الجدول | الغرض | قيود رئيسية |
|---|---|---|
| `ref_asset_types` | تصنيف أنواع الأصول القابل للتهيئة | `category` ∈ أنواع أصول USACM |
| `enterprise_assets` | جرد الأصول الفعلية للمؤسسة | `asset_type`/`criticality` مضبوطان؛ ربط اختياري بـ`security_artifacts` (ART-AST) |
| `asset_controls` | الأصل ↔ ضابط يحميه | `coverage_status` ∈ COVERED/PARTIAL/PLANNED/GAP |
| `asset_vulnerabilities` | الأصل ↔ ثغرة | `cvss_score` 0-10؛ `status` مضبوط |
| `asset_threats` | الأصل ↔ تهديد | `relevance` مضبوط |

## وحدة (ب): مؤشرات التهديد (استخبارات مرصودة)
| الجدول | الغرض | قيود رئيسية |
|---|---|---|
| `threat_intelligence_sources` | مصادر الاستخبارات | `reliability` مضبوط |
| `detection_tools` | أدوات الكشف | `tool_type` ∈ SIEM/EDR/XDR/NDR/SOAR/… |
| `threat_indicators` | المؤشرات (IoC/IoA/TTP) | `indicator_class` (7 طبقات)، `ioc_type`، `severity_level`، `status`، `confidence_score` 0-1، ربط MITRE، وربط SDT مع شرط الانتماء |
| `indicator_vulnerabilities` | المؤشر ↔ ثغرة | `cvss_score` 0-10 |
| `indicator_controls` | المؤشر ↔ ضابط (كشفي/وقائي) | `control_role`، `coverage_pct` 0-100 |
| `indicator_tools` | المؤشر ↔ أداة كشف | `coverage_pct` 0-100 |
| `indicator_recommended_actions` | إجراءات الاستجابة الموصى بها | `priority` PRI-*، `status` مضبوط |

## وحدة (ج): التضمين الدلالي وكشف التكرار
راجع [`EMBEDDING_POLICY.md`](EMBEDDING_POLICY.md).
| الجدول | الغرض | قيود رئيسية |
|---|---|---|
| `artifact_embeddings` | متجه المعنى لكل عنصر لكل نموذج | `embedding` BLOB float32؛ يُفرض `length(embedding)=dim*4`؛ PK(artifact_id, model_name, model_version) |
| `equivalence_groups` | عناقيد المفاهيم المتكافئة عبر الأطر (canonical concept) | `canonical_artifact_id` اختياري؛ `concept_domain` مضبوط |
| `equivalence_group_members` | أعضاء العنقود | `member_role` ∈ CANONICAL/MEMBER؛ `similarity` |
| `duplicate_candidates` | مرشّحات التكرار للمراجعة البشرية | `a<b` (لا مرايا)، `detection_method`/`status`/`resolution` مضبوطة؛ **لا حذف — بشرية فقط** |

---

# ملحق: الترحيل 003 — البيانات المرجعية (كل الأقسام والتصنيفات)

المصدر: [`migrations/003_reference_data.sql`](../migrations/003_reference_data.sql) (مُولّد من [`scripts/build_reference_data.py`](../scripts/build_reference_data.py) — لا يُحرَّر يدوياً). يوفّر **كل قائمة تصنيف وقسم** ورد في USACM v2.2.1 (§3 الأنواع، §4 القوائم المضبوطة الـ24، §8 قيم الجداول الفرعية) و SDT v2.2.1 (§5) كـ**جدول lookup مفهرس منفصل لكل قائمة** ثنائي اللغة — لتغذية القوائم المنسدلة والفلاتر والتسميات في الواجهة، ومطابِق تماماً لقيود `CHECK` في المخطط (يتحقق منها [`scripts/validate_reference_data.py`](../scripts/validate_reference_data.py)).

## جداول الـ lookup (37 جدولاً — `lk_<اسم_القائمة>`)
بنية موحّدة لكل جدول: `code TEXT PRIMARY KEY`، `name_en`، `name_ar`، `sort_order` (مع فهرس على `sort_order`).

| النمط | أمثلة |
|---|---|
| قوائم USACM/المخطط (35) | `lk_artifact_type`, `lk_abstraction_level`, `lk_obligation_level`, `lk_priority`, `lk_relationship_type`, `lk_tag_type`, `lk_ai_review_status`, `lk_publication_status`, `lk_asset_type`, `lk_maturity_level`, `lk_catalog_source_type`, … |
| SDT | `lk_sdt_domain` (8)؛ `lk_sdt_subdomain` (40) بعمود `domain_code` **FK → `lk_sdt_domain(code)`** و`CHECK(substr(code,1,5)=domain_code)` |

مثال: `SELECT code, name_ar FROM lk_priority ORDER BY sort_order;` يعيد قائمة الأولويات جاهزة للعرض العربي.

> ملاحظة: القيم مطابِقة لقيود `CHECK` في المخطط (المُلزِمة)؛ هذه الجداول للعرض والفلترة والتسمية. يمكن لاحقاً تحويل القيود إلى مفاتيح خارجية على جداول الـ lookup إن رُغب بمصدر واحد للتحقق والعرض معاً.

## التغطية (35 قائمة + تصنيف SDT = 268 صفاً)
- **أنواع العناصر** (§3): 22.
- **القوائم المضبوطة** (§4.1–4.24): مستوى التجريد، مصدر الإلزام ومستواه، الاستثناء، التفصيل، طبيعة/وظيفة الضابط، قابلية الاختبار، حالات التنفيذ/التحقق/الفعالية، الأولوية، العلاقات، مراجعة AI، نوع المتطلب، قوة الربط، نوع الوسم، تواتر المراجعة، حالة النشر، نوع المصدر، نوع الأصل، النضج، فئة التكلفة، حالة الاستيراد.
- **قيم الجداول الفرعية** (§8): نطاق التطبيق، الاعتماديات، أدوات/طرق التحقق، مسؤوليات أصحاب المصلحة، المراجع الخارجية، حالة التقييم الذاتي، حالة الحل.
- **قائمة مستوى المخطط**: `CATALOG_SOURCE_TYPE` لعمود `source_catalogs.source_type` (FRAMEWORK/STANDARD/THREAT_INTEL/…).
- **SDT**: `SDT_DOMAIN` (8) + `SDT_SUBDOMAIN` (40، مع `parent_code`).

## ملفات JSON المرجعية (مُولّدة)
- [`reference/usacm_controlled_lists.json`](../reference/usacm_controlled_lists.json) — كل قوائم USACM المضبوطة (يَستبدل المجموعة الجزئية القديمة `usacm_codes.json`).
- [`reference/sdt_taxonomy.json`](../reference/sdt_taxonomy.json) — تصنيف SDT ثنائي اللغة (8 مجالات + 40 فرعياً).

---

# ملحق: الترحيلان 004+005 — طبقة الجودة والتنسيق والعروض

المصدر: [`migrations/004_curation_layer.sql`](../migrations/004_curation_layer.sql) و[`migrations/005_views.sql`](../migrations/005_views.sql). تُنفّذ مسار [`SECUREGUIDE_AI_AGENT_BRIEF.md`](../SECUREGUIDE_AI_AGENT_BRIEF.md): خام → staging → صياغة إنجليزية canonical → تصنيف USACM/SDT → ترشيح تشابه/دمج → مراجعة → اعتماد. **لا تُخزَّن حالة تشغيلية عالمية هنا؛ الكتالوج يبقى مرجعياً.**

## جداول التنسيق (Curation)
| الجدول | الغرض | حقول/قيود رئيسية |
|---|---|---|
| `schema_migrations` | تتبّع نسخ الهجرات المُطبّقة | `version` PK، مبذور بـ 001–005 |
| `curation_batches` | معالجة دفعية قابلة للإعادة + نقطة snapshot | `status` ∈ OPEN/PROCESSING/COMPLETED/ROLLED_BACK |
| `staging_artifacts` | المسودّة العاملة بين الخام والمعتمد | صياغة إنجليزية + تصنيف مقترَح (`proposed_*` مقيّد بقيم USACM/SDT مع انتماء المجال الفرعي) + `classification_confidence`/`rationale` + `curation_status` ∈ DRAFT/CLASSIFIED/DEDUP_REVIEW/READY/APPROVED/REJECTED/NEEDS_REVIEW + `quality_score` (0-100، **جودة لا مخاطرة**) + `merge_action` (6 قرارات) + `promoted_artifact_id` (نسب). الوسوم/الربط المقترحة JSON مؤقت (تُطبَّع عند الترقية). |
| `consolidation_decisions` | القرار المرجعي للتوحيد (6 قيم) | `decision` ∈ CANONICALIZE/EQUIVALENCE_GROUP/CROSSWALK_ONLY/RELATE_ONLY/KEEP_SEPARATE/DEPRECATE_DERIVED + `canonical_artifact_id` + `rationale` |
| `consolidation_members` | أعضاء القرار | `role` ∈ CANONICAL/MEMBER/SOURCE |
| `curation_lessons` | دروس مستفادة خفيفة (CONSOLIDATION §9) | `lesson_type` مضبوط |

> **مفردات الدمج:** `consolidation_decisions.decision` (6 قيم) هو المرجع القاطع لقرار التوحيد؛ أما `duplicate_candidates` (في 002) فهو **كشف مرشّحين فقط** (PENDING/CONFIRMED/REJECTED) — الترشيح ثم القرار.

## العروض للقراءة (Views)
| العرض | الغرض |
|---|---|
| `v_review_queue` | طابور المراجعة البشرية (staging منخفض الثقة/معلّم + كتالوج يحتاج مراجعة) |
| `v_duplicate_candidates` | مرشّحات التكرار المعلّقة مع العنوانين، الأقوى أولاً |
| `v_catalog_curation` | تقدّم التنسيق (أعداد حسب الحالة والمجال + متوسط الثقة/الجودة) |
| `v_artifact_detail` | تفاصيل العنصر + وسوم مجمّعة + عدد الروابط/الـ mappings |
| `v_profile_dashboard` | ملخّص تشغيلي لكل ملف مؤسسي |
| `v_gap_analysis` | فجوات الملف (غير مطبّق كلياً وبلا استثناء) |
