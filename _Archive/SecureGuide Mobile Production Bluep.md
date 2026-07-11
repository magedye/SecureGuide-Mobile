# 📘 SecureGuide Mobile Production Blueprint v3.0
## النسخة النهائية المُحدّثة - Enterprise Reference Platform

---

## 🎯 أولاً: ملخص التحديثات الجوهرية

بعد مراجعة الوثيقة السابقة ومطابقتها مع جميع المخرجات المستحدثة (USACM v2.2.0, SDT v2.2.0, Enterprise Reference Platform, Indicators Page, Architecture v3.0)، تم إجراء **12 تحديثاً جوهرياً**:

| # | التحديث | السبب |
|---|---------|-------|
| 1 | **تحول الرؤية** من "ملف شخصي" إلى "منصة مرجعية مؤسسية" | الفصل بين البيانات المرجعية والتشغيلية |
| 2 | **إعادة هيكلة المحركات** من 10 إلى **8 محركات** | دمج ذكي (Validation → Classification, Sync+Audit → Data Integrity) |
| 3 | **إضافة Event Bus** للتواصل بين المحركات | فصل الاهتمامات |
| 4 | **إضافة Service Layer** كوسيط | فصل الواجهة عن المحركات |
| 5 | **تحديث الشاشات** لتشمل 8 شاشات | إضافة Profile Manager, Indicators, Review Queue |
| 6 | **تحديث الجداول** لتشمل 17 جدولاً | إضافة profile_assessments, profile_shares, جداول المؤشرات, operational tables |
| 7 | **تحديث الـ Prompts** لتعكس USACM v2.2.0 | إضافة Tie-Breakers, Typical Risks, Mapping Strength |
| 8 | **إضافة Layout Engine** | تخطيط ديناميكي للواجهات |
| 9 | **إضافة Comparison Engine** | مقارنة الملفات المؤسسية |
| 10 | **إضافة Typical Risks by Domain** | دعم تحليل الفجوات |
| 11 | **إضافة Profile Switcher** | تبديل الملف النشط |
| 12 | **إضافة Human Review Queue** | حوكمة الذكاء الاصطناعي |

---

## 🏗️ ثانياً: البنية المعمارية النهائية (5 طبقات + 8 محركات)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🎨 Presentation Layer (UI)                                            │
│  ● Dynamic Components + Layout Engine + State Management + RTL/AR     │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│  🔌 Service Layer (API Gateway)                                        │
│  ● ArtifactService, ProfileService, IndicatorService, IntakeService   │
│  ● SyncService, Event Bus (Pub/Sub)                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│  🧠 Engine Layer (8 Engines)                                           │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  Core (5): Classification, Priority, Progress, Recommendation, │  │
│  │          Filter                                                 │  │
│  │  Specialized (3): Indicator, Context, Data Integrity           │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│  🗄️ Data Access Layer (DAL)                                            │
│  ● Repository Pattern + Query Builder + Transaction Manager           │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│  💾 Storage Layer (SQLite - Offline-First)                             │
│  ● Core Tables + Profile Tables + Indicator Tables + Operational      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 🧠 المحركات الثمانية (8 Engines)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🧠 المحركات الأساسية (Core Engines - 5)                             │
│  1. Classification Engine  →  USACM + SDT + Intake + Validation      │
│  2. Priority Engine        →  Priority & Risk-based Calculation      │
│  3. Progress Engine        →  CMMC/ISO Maturity Calculation          │
│  4. Recommendation Engine  →  Quick Wins Matrix + Roadmap            │
│  5. Filter Engine          →  Saved + Smart Filters                  │
├─────────────────────────────────────────────────────────────────────────┤
│  🧩 المحركات المتخصصة (Specialized Engines - 3)                      │
│  6. Indicator Engine       →  Compromise Indicators & MITRE          │
│  7. Context Engine         →  Profiles, Templates, Comparison        │
│  8. Data Integrity Engine  →  Sync + Audit + Versioning              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 ثالثاً: التدفق الإنتاجي المحدث (Intake Pipeline)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ARTIFACT INTAKE PIPELINE (v3.0)                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  📄 Source Documents → 🤖 Extraction → 🏷️ Classification             │
│         ↓                                                              │
│  ✅ Validation → ✏️ Completion → 👤 Human Review                     │
│         ↓                                                              │
│  📚 Master Catalog → 📁 Enterprise Profile → 📱 Mobile App           │
│                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### الطبقات الخمس المُحدّثة

| الطبقة | الوظيفة | التحديث في v3.0 |
|--------|---------|----------------|
| **1. Extraction** | استخراج الكيانات من 7 مصادر | إضافة Document Chunking + Deduplication |
| **2. Classification** | تطبيق USACM + SDT | إضافة Tie-Breakers + Typical Risks |
| **3. Completion** | استكمال الحقول الناقصة | إضافة Context-Aware Suggestions |
| **4. Review & Governance** | حوكمة الذكاء الاصطناعي | إضافة Confidence Thresholds + RACI |
| **5. Catalog + Profile** | الكتالوج + الملف المؤسسي | ⭐ **جديد**: الفصل بين Master Catalog و Enterprise Profile |

---

## 🗄️ رابعاً: بنية البيانات النهائية (17 جدولاً في 4 مجموعات)

### 4.1 المجموعة الأولى: Core Tables (USACM v2.2.0)

```sql
-- 1. security_artifacts (البيانات المرجعية فقط)
CREATE TABLE security_artifacts (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,                    -- ART-*
    title_en TEXT NOT NULL,
    title_ar TEXT,
    description_en TEXT,
    description_ar TEXT,
    primary_domain TEXT NOT NULL,          -- SD-*
    sub_domain TEXT NOT NULL,              -- SD-*.**
    abstraction_level TEXT NOT NULL,       -- ABS-*
    source TEXT NOT NULL,                  -- SRC-*
    source_type TEXT NOT NULL,             -- DOCUMENT, SYSTEM, etc.
    obligation_level TEXT NOT NULL,        -- OBL-*
    requirement_type TEXT,                 -- RQT-* (for ART-REQ)
    granularity_level TEXT NOT NULL,       -- GRN-*
    control_nature TEXT,                   -- NAT-*
    control_function TEXT,                 -- FUN-*
    testability TEXT,                      -- TST-*
    priority TEXT NOT NULL DEFAULT 'PRI-MEDIUM',
    priority_weight INTEGER NOT NULL DEFAULT 4,
    scope TEXT,
    source_document TEXT NOT NULL,
    source_section TEXT,
    classification_confidence REAL,
    classification_rationale TEXT,
    ai_review_status TEXT DEFAULT 'AIR-HUMAN-REVIEW',
    requires_human_review INTEGER DEFAULT 1,
    import_status TEXT,
    import_source TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    version INTEGER DEFAULT 1,
    is_custom INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    CHECK (type IN ('ART-REQ','ART-OBJ','ART-PRI','ART-POL','ART-STD','ART-CTR','ART-CTE','ART-PRO','ART-PRC','ART-PRG','ART-PLN','ART-TSK','ART-CFG','ART-RUL','ART-EVD','ART-MET','ART-EXC','ART-RSK','ART-AST','ART-THR','ART-VUL','ART-OWN')),
    CHECK (substr(sub_domain,1,5) = primary_domain),
    CHECK (priority_weight BETWEEN 1 AND 10)
);

-- 2. artifact_tags
CREATE TABLE artifact_tags (
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    tag_type TEXT NOT NULL,
    tag_value TEXT NOT NULL,
    PRIMARY KEY (artifact_id, tag_type, tag_value),
    CHECK (tag_type IN ('Technology','Framework','Concept','Context','Threat','Data','Party'))
);

-- 3. artifact_relationships
CREATE TABLE artifact_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    relation_type TEXT NOT NULL,
    description TEXT,
    resolution_status TEXT,
    resolution_note TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE (source_id, target_id, relation_type),
    CHECK (relation_type IN ('REL-DER','REL-SAT','REL-SUP','REL-SPL','REL-IMP','REL-VER','REL-MEA','REL-MIT','REL-AFF','REL-EXC','REL-DEP','REL-CNF'))
);

-- 4. framework_mappings
CREATE TABLE framework_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    framework TEXT NOT NULL,
    version TEXT NOT NULL,
    reference TEXT NOT NULL,
    mapping_strength TEXT DEFAULT 'DIRECT',
    rationale TEXT,
    UNIQUE (artifact_id, framework, version, reference),
    CHECK (mapping_strength IN ('DIRECT','INDIRECT','PARTIAL','INFORMATIVE'))
);

-- 5. technical_dependencies
CREATE TABLE technical_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL,
    dependency_name TEXT NOT NULL,
    dependency_status TEXT NOT NULL,
    CHECK (dependency_type IN ('SYSTEM','PLATFORM','VENDOR','SKILL','BUDGET'))
);

-- 6. verification_tools
CREATE TABLE verification_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL,
    verification_method TEXT NOT NULL,
    CHECK (tool_type IN ('SIEM','EDR','IAM','VULNERABILITY','CSPM','MANUAL'))
);

-- 7. stakeholders (مرجعي)
CREATE TABLE stakeholders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    responsibility TEXT NOT NULL,
    CHECK (responsibility IN ('OWNER','REVIEWER','APPROVER','CONSULTED','INFORMED'))
);

-- 8. remediation_actions
CREATE TABLE remediation_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    priority TEXT NOT NULL,
    effort_estimate INTEGER,
    responsible_role TEXT NOT NULL
);
```

### 4.2 المجموعة الثانية: Profile Tables (Enterprise Reference Platform) ⭐

```sql
-- 9. enterprise_profiles (ملفات التعريف المؤسسية)
CREATE TABLE enterprise_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    owner_team TEXT,
    owner_person TEXT,
    is_active INTEGER DEFAULT 0,           -- ملف نشط واحد فقط
    is_template INTEGER DEFAULT 0,
    template_category TEXT,                -- ESSENTIALS, CLOUD, PCI, RANSOMWARE
    total_artifacts INTEGER DEFAULT 0,
    target_maturity_level TEXT,
    source_version TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    CHECK (target_maturity_level IN ('INITIAL','REPEATABLE','DEFINED','MANAGED','OPTIMIZED'))
);

-- 10. profile_artifacts (البيانات التشغيلية - القلب الجديد) ⭐
CREATE TABLE profile_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    artifact_id TEXT NOT NULL,
    custom_priority TEXT,                  -- يمكن تعديلها عن المرجعية
    custom_priority_weight INTEGER,
    implementation_status TEXT DEFAULT 'STS-NOT-APPLIED',
    verification_status TEXT DEFAULT 'VER-NOT-VERIFIED',
    effectiveness TEXT DEFAULT 'EFF-UNKNOWN',
    exception_status TEXT DEFAULT 'EXC-NONE',
    review_frequency TEXT,
    last_review_date TEXT,
    next_review_date TEXT,
    exception_approval_date TEXT,
    exception_expiry_date TEXT,
    exception_justification TEXT,
    owner_role TEXT,                       -- المالك في هذا الملف
    owner_person TEXT,
    custom_notes TEXT,
    self_assessment_status TEXT DEFAULT 'NOT_ASSESSED',
    self_assessment_score INTEGER,
    self_assessment_date TEXT,
    cost_category TEXT,
    cost_estimate REAL,
    effort_estimate INTEGER,
    added_date TEXT DEFAULT (datetime('now')),
    added_by TEXT,
    is_critical INTEGER DEFAULT 0,
    FOREIGN KEY (profile_id) REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES security_artifacts(id) ON DELETE CASCADE,
    UNIQUE(profile_id, artifact_id),
    CHECK (implementation_status IN ('STS-NOT-APPLIED','STS-PARTIAL','STS-FULL','STS-PLANNED','STS-NEEDS-IMPROVEMENT')),
    CHECK (self_assessment_score IS NULL OR (self_assessment_score BETWEEN 0 AND 100))
);

-- 11. profile_assessments (سجل تاريخ التقييمات) ⭐
CREATE TABLE profile_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    artifact_id TEXT NOT NULL,
    assessment_date TEXT DEFAULT (datetime('now')),
    implementation_status TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    effectiveness TEXT NOT NULL,
    exception_status TEXT NOT NULL,
    notes TEXT,
    assessed_by TEXT,
    assessment_method TEXT,                -- MANUAL, AUTOMATED, AUDIT
    FOREIGN KEY (profile_id) REFERENCES enterprise_profiles(id) ON DELETE CASCADE
);

-- 12. profile_stakeholders (تشغيلي - خاص بالملف)
CREATE TABLE profile_stakeholders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    artifact_id TEXT NOT NULL,
    responsibility TEXT NOT NULL,
    person_name TEXT,
    team_name TEXT,
    FOREIGN KEY (profile_id) REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    CHECK (responsibility IN ('OWNER','REVIEWER','APPROVER','CONSULTED','INFORMED'))
);

-- 13. profile_shares (المشاركة)
CREATE TABLE profile_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    shared_with_type TEXT NOT NULL,        -- USER, TEAM, ORGANIZATION
    shared_with_id TEXT NOT NULL,
    share_type TEXT NOT NULL,              -- VIEW, EDIT, ADMIN
    share_date TEXT DEFAULT (datetime('now')),
    expiry_date TEXT,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (profile_id) REFERENCES enterprise_profiles(id) ON DELETE CASCADE
);
```

### 4.3 المجموعة الثالثة: Indicator Tables (Compromise Indicators) ⭐

```sql
-- 14. threat_indicators
CREATE TABLE threat_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    indicator_type TEXT NOT NULL,
    indicator_value TEXT NOT NULL,
    severity_level TEXT NOT NULL,
    mitre_technique_id TEXT,
    mitre_tactic TEXT,
    confidence_score REAL,
    status TEXT DEFAULT 'ACTIVE',
    first_seen TEXT,
    last_seen TEXT,
    threat_family TEXT,
    ioc_type TEXT,
    CHECK (severity_level IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    CHECK (status IN ('ACTIVE','INACTIVE','INVESTIGATING'))
);

-- 15. indicator_controls
CREATE TABLE indicator_controls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id INTEGER NOT NULL REFERENCES threat_indicators(id) ON DELETE CASCADE,
    control_artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    control_type TEXT NOT NULL,            -- DETECTIVE, PREVENTIVE, CORRECTIVE
    coverage_percentage REAL DEFAULT 0,
    effectiveness_score REAL DEFAULT 0,
    implementation_status TEXT NOT NULL,
    UNIQUE(indicator_id, control_artifact_id)
);

-- 16. detection_tools
CREATE TABLE detection_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL,
    vendor TEXT,
    integration_status TEXT DEFAULT 'NOT_INTEGRATED',
    is_active INTEGER DEFAULT 1
);

-- 17. indicator_recommended_actions
CREATE TABLE indicator_recommended_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id INTEGER NOT NULL REFERENCES threat_indicators(id) ON DELETE CASCADE,
    action_order INTEGER,
    action_title TEXT NOT NULL,
    priority TEXT NOT NULL,
    effort_estimate TEXT,
    expected_risk_reduction REAL DEFAULT 0,
    related_artifact_id TEXT,
    is_completed INTEGER DEFAULT 0
);
```

### 4.4 المجموعة الرابعة: Operational Tables

```sql
-- 18. audit_log
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    user_id TEXT,
    action TEXT NOT NULL,                  -- CREATE, UPDATE, DELETE, STATUS_CHANGE
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    changes TEXT                           -- JSON diff
);

-- 19. sync_queue
CREATE TABLE sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    payload TEXT,
    status TEXT DEFAULT 'PENDING',
    retry_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 20. artifact_versions
CREATE TABLE artifact_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL,
    version_number INTEGER NOT NULL,
    artifact_data TEXT,                    -- JSON snapshot
    changed_by TEXT,
    changed_at TEXT DEFAULT (datetime('now'))
);
```

---

## 🖼️ خامساً: الشاشات الثمانية (8 Screens)

| # | الشاشة | الوظيفة | المحركات المستخدمة |
|---|--------|---------|-------------------|
| 1 | **Home** | لوحة القيادة المخصصة حسب الملف النشط | Progress, Recommendation, Priority, Context |
| 2 | **Profile Manager** | إدارة ملفات التعريف + القوالب + المقارنة | Context |
| 3 | **Master Catalog** | الكتالوج المرجعي الشامل | Filter, Classification |
| 4 | **Indicators** | مؤشرات الاختراق + MITRE ATT&CK | Indicator, Priority |
| 5 | **Review Queue** | طابور المراجعة البشرية للذكاء الاصطناعي | Classification, Audit |
| 6 | **Artifact Detail** | تفاصيل الكيان في سياق الملف النشط | All Engines |
| 7 | **Security Info** | مركز المعرفة المرجعي | - |
| 8 | **Settings** | الإعدادات + التزامن + الذكاء الاصطناعي | Context, Data Integrity |

---

## 🤖 سادساً: الـ Prompts الإنتاجية المُحدّثة

### 6.1 Extraction Prompt (v3.0)

```text
You are a cybersecurity artifact extraction and classification engine 
compliant with USACM v2.2.0 and SDT v2.2.0.

Your task is to analyze the provided security text and extract all 
distinct security artifacts.

CRITICAL RULES:
1. Each artifact must have EXACTLY ONE primary_domain and ONE sub_domain
2. Apply Tie-Breaker Rules from SDT v2.2.0 when conflicts arise:
   - Governance vs other → SD-01
   - Data vs application → SD-02 vs SD-05
   - IAM vs infrastructure/cloud → SD-03 vs SD-04
   - Application testing vs general testing → SD-05.02 vs SD-06.04
   - Encryption vs database → SD-02.04 vs SD-05.05
   - Endpoint vs configuration → SD-04.02 vs SD-04.03
   - Supplier access vs third-party risk → SD-03.05 vs SD-08.03
   - Backup vs DR → SD-07.03 vs SD-07.04
   - Logging vs evidence → SD-06.01 vs domain of verified control
   - Awareness vs acceptable use → SD-08.01 vs SD-08.05
   - Legacy ambiguous → route to human review

3. Consider Typical Risks by Domain from SDT v2.2.0 for context

4. Confidence Thresholds:
   - ≥ 0.90: AIR-AUTO-ACCEPTED
   - 0.75-0.89: AIR-AUTO-ACCEPTED with review_notes
   - 0.60-0.74: AIR-HUMAN-REVIEW
   - < 0.60: Reject and require manual classification

5. Conditional Requirements:
   - ART-REQ → requirement_type (RQT-*) mandatory
   - ART-CTR/CTE → control_nature, control_function, testability mandatory
   - ART-EXC → exception_approval_date, exception_expiry_date mandatory
   - ART-AST → asset_type, asset_criticality mandatory
   - ART-RSK → remediation_actions required
   - Non-DIRECT mapping_strength → rationale required

6. Priority Weight Mapping:
   - PRI-CRITICAL = 10
   - PRI-HIGH = 7
   - PRI-MEDIUM = 4
   - PRI-LOW = 1

Return valid JSON matching USACM v2.2.0 schema.
```

### 6.2 Completion Prompt (v3.0)

```text
You are a cybersecurity artifact completion assistant for USACM v2.2.0.

Given a partially extracted artifact, enrich it using:
1. Direct evidence from the source text
2. Reasonable inference from context
3. Controlled suggestions from SDT v2.2.0 taxonomy

DO NOT overwrite valid fields. Leave null if undetermined.

Validate:
- Type-specific requirements (USACM-VAL-003, 004, 019, 020)
- Domain/sub-domain consistency (USACM-VAL-002)
- Priority/weight consistency (USACM-VAL-018)
- AI review status (USACM-VAL-009, 010)
- Framework mapping rationale (USACM-VAL-014)
- Tags taxonomy (SDT-TAG-*)
- Publication lifecycle (USACM-VAL-022)
- Review lifecycle (USACM-VAL-021)

Return JSON with: artifact, changes_applied, suggested_changes, 
missing_fields, validation_findings, requires_human_review.
```

### 6.3 Human Review Prompt (v3.0)

```text
You are a human-review preparation assistant for USACM v2.2.0.

Prepare a concise review package including:
1. Classification summary with confidence score
2. Why AI selected type, domain, sub-domain (rationale)
3. Tie-breaker applied (if any) and rejected alternatives
4. Missing or weak fields
5. Validation failures (from 22 USACM-VAL rules)
6. Risk of accepting as-is
7. Recommended decision

Decision options:
- APPROVE
- APPROVE_WITH_CHANGES
- REQUEST_MORE_INFORMATION
- RECLASSIFY
- REJECT

Return JSON with: review_summary, classification_decision, 
tie_breaker_analysis, issues, recommended_changes, 
risk_of_acceptance, recommended_decision.
```

---

## 📊 سابعاً: مقارنة النسخة السابقة vs v3.0

| الجانب | v2.2.1 السابقة | v3.0 المُحدّثة |
|--------|----------------|----------------|
| **الرؤية** | Personal Knowledge Reference | ⭐ **Enterprise Reference Platform** |
| **البيانات** | مختلطة (مرجعية + تشغيلية) | ⭐ **منفصلة** (Master Catalog + Profiles) |
| **عدد المحركات** | 10 | ⭐ **8** (دمج ذكي) |
| **Event Bus** | ❌ | ⭐ **✅** |
| **Service Layer** | ❌ | ⭐ **✅** |
| **Layout Engine** | ❌ | ⭐ **✅** |
| **عدد الشاشات** | 6 | ⭐ **8** (إضافة Profile Manager, Indicators, Review Queue) |
| **عدد الجداول** | 13 | ⭐ **20** (إضافة profile_assessments, profile_shares, indicator_*, operational) |
| **Profile Switcher** | ❌ | ⭐ **✅** |
| **Comparison Engine** | ❌ | ⭐ **✅** |
| **Typical Risks** | ❌ | ⭐ **✅** (من SDT v2.2.0) |
| **Tie-Breakers في Prompts** | ❌ | ⭐ **✅** (11 قاعدة) |
| **Mapping Strength** | ❌ | ⭐ **✅** (DIRECT, INDIRECT, PARTIAL, INFORMATIVE) |
| **Audit Trail** | جزئي | ⭐ **كامل** (audit_log + artifact_versions) |
| **Sync Queue** | ❌ | ⭐ **✅** |
| **Human Review Queue** | ❌ | ⭐ **✅** (شاشة مستقلة) |

---

## 🚀 ثامناً: خطة التنفيذ المُحدّثة (4 مراحل - 20 أسبوع)

| المرحلة | المدة | المخرجات | المعيار |
|---------|-------|----------|---------|
| **Phase 0: Foundation** | 3 أسابيع | SQLite Schema + Seed Data + Validation Engine | 100 كيان مُصنَّف بنجاح |
| **Phase 1: Core Engines** | 5 أسابيع | Classification + Priority + Progress + Recommendation + Filter | لوحة قيادة تعمل |
| **Phase 2: Enterprise Platform** | 4 أسابيع | Profile Manager + Master Catalog + Profile Switcher + Comparison | تعدد الملفات يعمل |
| **Phase 3: Advanced Features** | 4 أسابيع | Indicators + Review Queue + Intake Pipeline + Sync + Audit | استخراج تلقائي + مؤشرات |
| **Phase 4: Production** | 4 أسابيع | Performance + Security + UAT + Documentation | جاهز لـ 100 جهاز |

---

## 🏆 تاسعاً: الخلاصة التنفيذية

### الحالة النهائية

| الجانب | الحالة |
|--------|--------|
| **الرؤية** | ✅ Enterprise Reference Platform |
| **البنية المعمارية** | ✅ 5 طبقات + 8 محركات + Event Bus |
| **قاعدة البيانات** | ✅ 20 جدولاً في 4 مجموعات |
| **الشاشات** | ✅ 8 شاشات رئيسية |
| **الـ Prompts** | ✅ 3 Prompts محدّثة مع Tie-Breakers |
| **الفصل المعماري** | ✅ البيانات المرجعية (Master Catalog) ≠ التشغيلية (Profiles) |
| **الحوكمة** | ✅ Human Review Queue + Audit Trail |
| **المؤشرات** | ✅ Indicators Page + MITRE ATT&CK |
| **خطة التنفيذ** | ✅ 4 مراحل / 20 أسبوع |

### 🎯 القرار النهائي

✅ **اعتماد SecureGuide Mobile Production Blueprint v3.0 كمرجع نهائي**

### 📋 الخطوة التالية المباشرة

البدء في إعداد **المكون رقم 1: Product Requirements Document (PRD)** الذي سيحتوي على:

1. **Vision & Scope** - الرؤية المؤسسية
2. **Personas** - 4 شخصيات مستخدم (CISO, GRC Manager, Security Architect, Auditor)
3. **Core Features** - MVP vs Full Release
4. **Success Metrics** - معايير النجاح القابلة للقياس
5. **Constraints & Assumptions** - القيود والافتراضات
6. **Release Plan** - خطة الإطلاق المرحلية

---

**الشعار النهائي:**
> **"منصة مرجعية مؤسسية، بنية مرنة، محركات معزولة، ملفات قابلة للتبديل، تنفيذ متدرج."**

🎯 **جاهز للانتقال إلى مرحلة PRD فور تأكيدك!**