# التصور المنقح: منصة مرجعية مؤسسية قابلة للتخصيص (Enterprise Reference Platform)

## 🎯 أولاً: تقييم الرؤية الجديدة

الرؤية الجديدة **ممتازة وتمثل نقلة نوعية**، لكنها تحتاج إلى **تنقيح معماري حاسم** لضمان الاتساق مع USACM v2.2.0 وتجنب تكرار البيانات.

### ✅ نقاط القوة المعتمدة
| النقطة | القيمة |
|--------|--------|
| الفصل بين المرجعية الشاملة والتخصيص | يحل مشكلة حقيقية في المؤسسات |
| تعدد الملفات (Profiles) | يسمح بإدارة سياقات مختلفة |
| القوالب الجاهزة | تسرع البدء بشكل كبير |
| المشاركة بين الفرق | تعزز التعاون المؤسسي |

### ⚠️ النقاط التي تحتاج تنقيح معماري

**المشكلة الجوهرية**: أين تُخزّن **البيانات التشغيلية** (حالة التطبيق، المالك، التواريخ، التقييم)؟

| الخيار | المشكلة |
|--------|---------|
| **الخيار أ**: تخزينها في `security_artifacts` | ❌ إذا غيّر المستخدم الملف النشط، ستظهر نفس الحالة لجميع الملفات! |
| **الخيار ب**: تخزينها في `profile_artifacts` | ✅ الحل الصحيح: كل ملف له حالته التشغيلية الخاصة |

**الحل المعتمد**: **فصل البيانات المرجعية عن البيانات التشغيلية**

---

## 🏗️ ثانياً: البنية المعمارية المنقحة

### 2.1. الطبقات الثلاث للتطبيق

```
┌─────────────────────────────────────────────────────────────────┐
│  الطبقة 1: الكتالوج المرجعي الشامل (Master Catalog)            │
│  ─────────────────────────────────────────────────────────────  │
│  ● جميع الكيانات الأمنية من المعايير العالمية                  │
│  ● البيانات المرجعية فقط (الوصف، التصنيف، العلاقات، المصادر)  │
│  ● ثابتة لا تتغير بتغير المؤسسة                                │
│  ● تُحدَّث فقط عند إصدار نسخ جديدة من المعايير                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  الطبقة 2: ملفات التعريف المؤسسية (Enterprise Profiles)        │
│  ─────────────────────────────────────────────────────────────  │
│  ● اختيارات من الكتالوج الشامل + كيانات مخصصة                 │
│  ● البيانات التشغيلية (الحالة، المالك، التواريخ، التقييم)     │
│  ● قابلة للتعدد والتبديل                                       │
│  ● خاصة بالمؤسسة أو الفريق                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  الطبقة 3: التقييمات والسجل التاريخي (Assessments & Audit)     │
│  ─────────────────────────────────────────────────────────────  │
│  ● سجل تغييرات الحالة لكل عنصر في كل ملف                       │
│  ● يدعم التدقيق وتتبع التقدم عبر الزمن                         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2. قاعدة الذهب المعمارية

> **"الكتالوج المرجعي يحتوي على 'ماذا' (What)، والملفات المؤسسية تحتوي على 'كيف' (How) و'متى' (When) و'من' (Who)."**

---

## 🗄️ ثالثاً: البنية التقنية المنقحة (SQLite Schema)

### 3.1. جدول `security_artifacts` (البيانات المرجعية فقط)

**التغيير الجوهري**: إزالة الحقول التشغيلية التي تنتقل إلى `profile_artifacts`.

```sql
CREATE TABLE IF NOT EXISTS security_artifacts (
    -- ===== الهوية والتصنيف =====
    id TEXT PRIMARY KEY,
    source_artifact_id TEXT,                    -- للكيانات المستوردة
    temp_id TEXT,                               -- للكيانات المؤقتة
    type TEXT NOT NULL,                         -- ART-*
    title_en TEXT NOT NULL,
    title_ar TEXT,
    description_en TEXT,
    description_ar TEXT,
    
    -- ===== التصنيف حسب USACM/SDT =====
    primary_domain TEXT NOT NULL,               -- SD-*
    sub_domain TEXT NOT NULL,                   -- SD-*.**
    abstraction_level TEXT NOT NULL,            -- ABS-*
    source TEXT NOT NULL,                       -- SRC-*
    source_type TEXT NOT NULL,                  -- DOCUMENT, SYSTEM, etc.
    source_location TEXT,
    obligation_level TEXT NOT NULL,             -- OBL-*
    requirement_type TEXT,                      -- RQT-* (for ART-REQ)
    granularity_level TEXT NOT NULL,            -- GRN-*
    
    -- ===== حقول الضابط (المرجعية) =====
    control_nature TEXT,                        -- NAT-*
    control_function TEXT,                      -- FUN-*
    testability TEXT,                           -- TST-*
    
    -- ===== الأولوية المرجعية (يمكن تعديلها في الملف) =====
    priority TEXT NOT NULL DEFAULT 'PRI-MEDIUM',
    priority_weight INTEGER NOT NULL DEFAULT 4,
    
    -- ===== نطاق التطبيق المرجعي =====
    scope TEXT,
    
    -- ===== بيانات الذكاء الاصطناعي =====
    classification_confidence REAL,
    classification_rationale TEXT,
    ai_review_status TEXT NOT NULL DEFAULT 'AIR-HUMAN-REVIEW',
    requires_human_review INTEGER NOT NULL DEFAULT 1,
    
    -- ===== بيانات الاستيراد =====
    import_status TEXT,
    import_source TEXT,
    import_date TEXT,
    import_version TEXT,
    
    -- ===== المصادر والعلاقات =====
    source_document TEXT NOT NULL,
    source_section TEXT,
    extraction_date TEXT,
    
    -- ===== بيانات النظام =====
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    version INTEGER NOT NULL DEFAULT 1,
    is_custom INTEGER NOT NULL DEFAULT 0,       -- 1 = كيان مخصص (ليس من المعايير)
    is_active INTEGER NOT NULL DEFAULT 1,
    is_template_item INTEGER NOT NULL DEFAULT 0, -- 1 = جزء من قالب جاهز
    
    -- ===== القيود =====
    CHECK (type IN ('ART-REQ','ART-OBJ','ART-PRI','ART-POL','ART-STD','ART-CTR','ART-CTE','ART-PRO','ART-PRC','ART-PRG','ART-PLN','ART-TSK','ART-CFG','ART-RUL','ART-EVD','ART-MET','ART-EXC','ART-RSK','ART-AST','ART-THR','ART-VUL','ART-OWN')),
    CHECK (primary_domain IN ('SD-01','SD-02','SD-03','SD-04','SD-05','SD-06','SD-07','SD-08')),
    CHECK (substr(sub_domain,1,5) = primary_domain),
    CHECK (priority IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW')),
    CHECK (priority_weight BETWEEN 1 AND 10),
    CHECK ((priority = 'PRI-CRITICAL' AND priority_weight = 10) OR 
           (priority = 'PRI-HIGH' AND priority_weight = 7) OR 
           (priority = 'PRI-MEDIUM' AND priority_weight = 4) OR 
           (priority = 'PRI-LOW' AND priority_weight = 1))
);
```

### 3.2. جدول `enterprise_profiles` (ملفات التعريف)

```sql
CREATE TABLE IF NOT EXISTS enterprise_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    owner_team TEXT,                            -- الفريق المالك
    owner_person TEXT,                          -- الشخص المالك
    
    -- ===== حالة الملف =====
    is_active BOOLEAN DEFAULT 0,                -- هل هو الملف النشط حالياً؟
    is_template BOOLEAN DEFAULT 0,              -- هل هو قالب جاهز؟
    template_category TEXT,                     -- ESSENTIALS, CLOUD, PCI, RANSOMWARE, etc.
    
    -- ===== إحصائيات (محسوبة) =====
    total_artifacts INTEGER DEFAULT 0,
    implemented_count INTEGER DEFAULT 0,
    verified_count INTEGER DEFAULT 0,
    
    -- ===== النضج المستهدف =====
    target_maturity_level TEXT,                 -- INITIAL, REPEATABLE, DEFINED, MANAGED, OPTIMIZED
    
    -- ===== البيانات الوصفية =====
    source_version TEXT,                        -- إصدار الكتالوج عند الإنشاء
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    last_assessment_date TEXT,
    
    -- ===== القيود =====
    CHECK (target_maturity_level IS NULL OR target_maturity_level IN ('INITIAL','REPEATABLE','DEFINED','MANAGED','OPTIMIZED'))
);

-- ضمان ملف نشط واحد فقط في كل وقت
CREATE UNIQUE INDEX idx_active_profile ON enterprise_profiles(is_active) WHERE is_active = 1;
```

### 3.3. جدول `profile_artifacts` (البيانات التشغيلية الخاصة بالملف) ⭐ **الأهم**

هذا الجدول هو **قلب الرؤية الجديدة**. يحتوي على البيانات التشغيلية لكل عنصر في كل ملف.

```sql
CREATE TABLE IF NOT EXISTS profile_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    artifact_id TEXT NOT NULL,
    
    -- ===== الأولوية المخصصة (يمكن تعديلها عن المرجعية) =====
    custom_priority TEXT,                       -- PRI-* (إذا كانت مختلفة عن المرجعية)
    custom_priority_weight INTEGER,
    
    -- ===== البيانات التشغيلية (خاصة بالملف) =====
    implementation_status TEXT NOT NULL DEFAULT 'STS-NOT-APPLIED',
    verification_status TEXT NOT NULL DEFAULT 'VER-NOT-VERIFIED',
    effectiveness TEXT NOT NULL DEFAULT 'EFF-UNKNOWN',
    exception_status TEXT NOT NULL DEFAULT 'EXC-NONE',
    
    -- ===== التواريخ والدورة الحياة =====
    review_frequency TEXT,                      -- DAILY, WEEKLY, MONTHLY, etc.
    last_review_date TEXT,
    next_review_date TEXT,
    
    -- ===== الاستثناءات =====
    exception_approval_date TEXT,
    exception_expiry_date TEXT,
    exception_justification TEXT,
    
    -- ===== الملكية والتخصيص =====
    owner_role TEXT,                            -- المالك في هذا الملف
    owner_person TEXT,                          -- الشخص المحدد
    custom_notes TEXT,                          -- ملاحظات خاصة بالملف
    
    -- ===== التقييم الذاتي =====
    self_assessment_status TEXT DEFAULT 'NOT_ASSESSED',
    self_assessment_score INTEGER,              -- 0-100
    self_assessment_date TEXT,
    self_assessment_by TEXT,
    self_assessment_comments TEXT,
    
    -- ===== التكلفة والجهد =====
    cost_category TEXT,                         -- LOW, MEDIUM, HIGH, VERY_HIGH
    cost_estimate REAL,
    effort_estimate INTEGER,                    -- أيام
    
    -- ===== البيانات الوصفية =====
    added_date TEXT DEFAULT (datetime('now')),
    added_by TEXT,
    is_critical BOOLEAN DEFAULT 0,
    
    -- ===== القيود والعلاقات =====
    FOREIGN KEY (profile_id) REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES security_artifacts(id) ON DELETE CASCADE,
    UNIQUE(profile_id, artifact_id),
    
    CHECK (implementation_status IN ('STS-NOT-APPLIED','STS-PARTIAL','STS-FULL','STS-PLANNED','STS-NEEDS-IMPROVEMENT')),
    CHECK (verification_status IN ('VER-NOT-VERIFIED','VER-PASS','VER-FAIL')),
    CHECK (effectiveness IN ('EFF-LOW','EFF-MED','EFF-HIGH','EFF-UNKNOWN')),
    CHECK (exception_status IN ('EXC-NONE','EXC-NAP','EXC-RISK-ACCEPTED','EXC-DEFERRED','EXC-UNAVAILABLE')),
    CHECK (self_assessment_status IN ('NOT_ASSESSED','IN_PROGRESS','COMPLETED','NEEDS_REVIEW')),
    CHECK (self_assessment_score IS NULL OR (self_assessment_score >= 0 AND self_assessment_score <= 100))
);

-- فهارس للأداء
CREATE INDEX IF NOT EXISTS idx_profile_artifacts_profile ON profile_artifacts(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_artifacts_artifact ON profile_artifacts(artifact_id);
CREATE INDEX IF NOT EXISTS idx_profile_artifacts_status ON profile_artifacts(implementation_status);
CREATE INDEX IF NOT EXISTS idx_profile_artifacts_priority ON profile_artifacts(custom_priority);
CREATE INDEX IF NOT EXISTS idx_profile_artifacts_next_review ON profile_artifacts(next_review_date);
```

### 3.4. جدول `profile_assessments` (سجل تاريخ التقييمات)

```sql
CREATE TABLE IF NOT EXISTS profile_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    artifact_id TEXT NOT NULL,
    
    -- ===== حالة التقييم =====
    assessment_date TEXT NOT NULL DEFAULT (datetime('now')),
    implementation_status TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    effectiveness TEXT NOT NULL,
    exception_status TEXT NOT NULL,
    
    -- ===== معلومات التقييم =====
    notes TEXT,
    assessed_by TEXT,
    assessment_method TEXT,                     -- MANUAL, AUTOMATED, AUDIT
    
    -- ===== العلاقات =====
    FOREIGN KEY (profile_id) REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES security_artifacts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_assessments_profile ON profile_assessments(profile_id);
CREATE INDEX IF NOT EXISTS idx_assessments_date ON profile_assessments(assessment_date);
```

### 3.5. جداول العلاقات المرجعية (كما هي في USACM v2.2.0)

```sql
-- ===== الوسوم =====
CREATE TABLE IF NOT EXISTS artifact_tags (
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    tag_type TEXT NOT NULL,
    tag_value TEXT NOT NULL,
    PRIMARY KEY (artifact_id, tag_type, tag_value),
    CHECK (tag_type IN ('Technology','Framework','Concept','Context','Threat','Data','Party'))
);

-- ===== العلاقات بين الكيانات =====
CREATE TABLE IF NOT EXISTS artifact_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    target_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE RESTRICT,
    relation_type TEXT NOT NULL,
    description TEXT,
    resolution_note TEXT,
    resolution_status TEXT,
    resolution_date TEXT,
    resolved_by TEXT,
    owner_role TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (source_id, target_id, relation_type),
    CHECK (relation_type IN ('REL-DER','REL-SAT','REL-SUP','REL-SPL','REL-IMP','REL-VER','REL-MEA','REL-MIT','REL-AFF','REL-EXC','REL-DEP','REL-CNF')),
    CHECK (resolution_status IS NULL OR resolution_status IN ('PENDING','RESOLVED','ACCEPTED','REJECTED')),
    CHECK (relation_type <> 'REL-CNF' OR (resolution_status IS NOT NULL AND resolution_note IS NOT NULL))
);

-- ===== ربط الأطر العالمية =====
CREATE TABLE IF NOT EXISTS framework_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    framework TEXT NOT NULL,
    version TEXT NOT NULL,
    reference TEXT NOT NULL,
    category TEXT,
    mapping_strength TEXT NOT NULL DEFAULT 'DIRECT',
    rationale TEXT,
    UNIQUE (artifact_id, framework, version, reference),
    CHECK (mapping_strength IN ('DIRECT','INDIRECT','PARTIAL','INFORMATIVE')),
    CHECK (mapping_strength = 'DIRECT' OR rationale IS NOT NULL)
);

-- ===== الأدوات والتقنيات والاعتماديات (مرجعية) =====
CREATE TABLE IF NOT EXISTS verification_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL,
    verification_method TEXT NOT NULL,
    CHECK (tool_type IN ('SIEM','EDR','IAM','VULNERABILITY','CSPM','MANUAL')),
    CHECK (verification_method IN ('API','LOG','REPORT','INTERVIEW','OBSERVATION'))
);

CREATE TABLE IF NOT EXISTS technical_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL,
    dependency_name TEXT NOT NULL,
    dependency_status TEXT NOT NULL,
    CHECK (dependency_type IN ('SYSTEM','PLATFORM','VENDOR','SKILL','BUDGET')),
    CHECK (dependency_status IN ('AVAILABLE','NOT_AVAILABLE','PARTIAL','PLANNED'))
);

-- ===== أصحاب المصلحة (تشغيلي - خاص بالملف) =====
CREATE TABLE IF NOT EXISTS profile_stakeholders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    artifact_id TEXT NOT NULL,
    role TEXT NOT NULL,
    responsibility TEXT NOT NULL,
    person_name TEXT,
    team_name TEXT,
    FOREIGN KEY (profile_id) REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES security_artifacts(id) ON DELETE CASCADE,
    CHECK (responsibility IN ('OWNER','REVIEWER','APPROVER','CONSULTED','INFORMED'))
);

-- ===== الإجراءات الموصى بها (مرجعية) =====
CREATE TABLE IF NOT EXISTS remediation_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL REFERENCES security_artifacts(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    priority TEXT NOT NULL,
    effort_estimate INTEGER,
    responsible_role TEXT NOT NULL,
    CHECK (priority IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW'))
);

-- ===== مشاركة الملفات =====
CREATE TABLE IF NOT EXISTS profile_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    shared_with_type TEXT NOT NULL,             -- USER, TEAM, ORGANIZATION
    shared_with_id TEXT NOT NULL,
    share_type TEXT NOT NULL,                   -- VIEW, EDIT, ADMIN
    share_date TEXT DEFAULT (datetime('now')),
    expiry_date TEXT,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (profile_id) REFERENCES enterprise_profiles(id) ON DELETE CASCADE,
    CHECK (shared_with_type IN ('USER','TEAM','ORGANIZATION')),
    CHECK (share_type IN ('VIEW','EDIT','ADMIN'))
);
```

---

## 🖼️ رابعاً: الشاشات المنقحة

### 4.1. الصفحة الرئيسية (Home) - المخصصة حسب الملف النشط

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🛡️ SecureGuide Enterprise                                          │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📋 الملف النشط: خط الأساس المؤسسي (V1.0)          [تبديل ▼]  │ │
│  │  👤 المالك: فريق الأمن  ·  📊 45 عنصراً  ·  🔄 2026-07-10     │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📊 مستوى النضج (حسب الملف النشط)                              │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  الحالي: ■■■■■■□□□□ DEFINED 65%  ·  المستهدف: MANAGED 80%│ │ │
│  │  │  ● التطبيق: 65% (29/45)  ● التحقق: 45% (20/45)           │ │ │
│  │  │  ● الفعالية: 55% (25/45)  ● الفجوات: 8 حرجة              │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  🎯 الإجراء التالي (Quick Win)                                  │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  📌 MFA للحسابات الإدارية (من الملف النشط)                │ │ │
│  │  │  ● الأولوية: 🔴 حرجة (مخصصة)  ·  الحالة: ⏳ غير مطبق     │ │ │
│  │  │  ● المالك: IAM Manager  ·  الجهد: 20 يوم  ·  الأثر: 70%  │ │ │
│  │  │  [ابدأ التنفيذ]  [التفاصيل]  [تخطي]                       │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📋 الفجوات الحرجة (8)  ·  🚨 مؤشرات الاختراق (12)            │ │
│  │  ● MFA للحسابات الإدارية 🔴  ● مراجعة الصلاحيات 🔴             │ │
│  │  ● تشفير قواعد البيانات 🟠  ● تدريب التوعية 🟡                 │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  [إدارة الملفات]  [عرض الكتالوج الشامل]  [تصدير التقرير]            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2. صفحة إدارة الملفات (Profile Manager)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📁 إدارة الملفات (Profiles)                                        │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  [+ ملف جديد]  [استيراد قالب]  [مشاركة]  [مقارنة ملفات]       │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📋 الملفات الحالية                                           │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  🟢 خط الأساس المؤسسي     [نشط] 45 عنصراً                │ │ │
│  │  │  ● المالك: فريق الأمن  ·  النضج: 65%  ·  الفجوات: 8      │ │ │
│  │  │  [فتح]  [تعديل]  [نسخ]  [تصدير]  [مقارنة]                │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  ⚪ أمن السحابة             [غير نشط] 60 عنصراً            │ │ │
│  │  │  ● المالك: فريق السحابة  ·  النضج: 40%  ·  الفجوات: 15   │ │ │
│  │  │  [فتح]  [تعديل]  [نسخ]  [تصدير]  [مقارنة]                │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  ⚪ الامتثال المالي (PCI)   [غير نشط] 80 عنصراً           │ │ │
│  │  │  ● المالك: فريق الامتثال  ·  النضج: 25%  ·  الفجوات: 30  │ │ │
│  │  │  [فتح]  [تعديل]  [نسخ]  [تصدير]  [مقارنة]                │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📦 القوالب الجاهزة                                           │ │
│  │  ● خط الأساس (Essentials) · 45  ● أمن السحابة · 60            │ │
│  │  ● الامتثال المالي · 80  ● مقاومة الفدية · 35                 │ │
│  │  ● حماية الهوية · 30  ● أمن التطبيقات · 50                    │ │
│  │  [استيراد قالب]                                               │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3. صفحة مقارنة الملفات (File Comparison) ⭐ **جديدة**

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📊 مقارنة الملفات                                                  │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  الملف أ: [خط الأساس المؤسسي ▼]  ·  الملف ب: [أمن السحابة ▼]  │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📊 الملخص                                                     │ │
│  │  ● مشترك: 25 عنصراً  ● فريد في أ: 20  ● فريد في ب: 35        │ │
│  │  ● تعارض في الأولوية: 3 عناصر                                 │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📋 العناصر المشتركة مع الاختلافات                             │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  🔐 MFA للحسابات الإدارية                                 │ │ │
│  │  │  ● في أ: 🔴 حرجة  ·  غير مطبق  ·  المالك: IAM Manager   │ │ │
│  │  │  ● في ب: 🟠 عالية  ·  مطبق جزئياً  ·  المالك: Cloud Team │ │ │
│  │  │  [دمج]  [تجاهل]                                           │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  [دمج الملفات]  [تصدير التقرير]                                     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.4. صفحة تفاصيل العنصر في سياق الملف

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🔐 MFA للحسابات الإدارية                    [في الملف: خط الأساس]  │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📋 البيانات المرجعية (من الكتالوج الشامل)                     │ │
│  │  ● النوع: ART-CTR  ·  المجال: SD-03.02  ·  المصدر: NIST CSF   │ │ │
│  │  ● الوصف: يجب تفعيل MFA لجميع الحسابات الإدارية               │ │ │
│  │  ● الضوابط المرتبطة: 5  ·  المخاطر المعالجة: 2                │ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  ⚙️ البيانات التشغيلية (خاصة بالملف النشط)                     │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  الأولوية: 🔴 حرجة (مخصصة)  ·  الحالة: ⏳ غير مطبق        │ │ │
│  │  │  المالك: IAM Manager  ·  الجهد: 20 يوم  ·  التكلفة: HIGH  │ │ │
│  │  │  آخر مراجعة: 2026-07-10  ·  القادمة: 2026-10-10           │ │ │
│  │  │  التقييم الذاتي: 65/100  ·  الملاحظات: "يحتاج تفعيل"      │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📊 التاريخ (في هذا الملف)                                     │ │
│  │  ● 2026-07-10: تم التحديث بواسطة محمد أحمد                    │ │ │
│  │  ● 2026-06-15: تم الإضافة إلى الملف                           │ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  [تحديث الحالة]  [تعديل الأولوية]  [عرض في ملفات أخرى]             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 خامساً: التدفق التشغيلي (Operational Flow)

### 5.1. سيناريو البدء السريع

```
1. المستخدم يفتح التطبيق لأول مرة
   ↓
2. يختار قالباً جاهزاً (مثلاً: "خط الأساس المؤسسي")
   ↓
3. يتم إنشاء ملف جديد من القالب (45 عنصراً)
   ↓
4. يحدد الملف كـ "نشط"
   ↓
5. الصفحة الرئيسية تعرض مؤشرات الأداء بناءً على هذا الملف
   ↓
6. المستخدم يبدأ بتحديث حالة كل عنصر (غير مطبق → مطبق جزئياً → مطبق)
   ↓
7. يتم حفظ كل تغيير في profile_assessments (سجل تاريخي)
   ↓
8. مؤشرات الأداء تُحدَّث تلقائياً
```

### 5.2. سيناريو تعدد الملفات

```
المؤسسة لديها 3 ملفات نشطة في أوقات مختلفة:
├─ خط الأساس المؤسسي (نشط دائماً) - 45 عنصراً
├─ الامتثال المالي (نشط قبل التدقيق) - 80 عنصراً
└─ أمن السحابة (نشط أثناء الهجرة) - 60 عنصراً

كل ملف له:
● حالته التشغيلية الخاصة
● أولوياته المخصصة
● مالكيه المحددين
● مؤشرات أداء مستقلة
```

---

## 📊 سادساً: الاستعلامات التحليلية

### 6.1. حساب مؤشرات الأداء للملف النشط

```sql
-- حساب نسبة التطبيق والتحقق للملف النشط
SELECT 
    p.name AS profile_name,
    COUNT(pa.id) AS total_artifacts,
    SUM(CASE WHEN pa.implementation_status = 'STS-FULL' THEN 1 ELSE 0 END) AS fully_implemented,
    SUM(CASE WHEN pa.implementation_status = 'STS-PARTIAL' THEN 1 ELSE 0 END) AS partially_implemented,
    ROUND(
        (SUM(CASE WHEN pa.implementation_status IN ('STS-FULL', 'STS-PARTIAL') THEN 1 ELSE 0 END) * 100.0) 
        / COUNT(pa.id), 2
    ) AS implementation_percentage,
    SUM(CASE WHEN pa.verification_status = 'VER-PASS' THEN 1 ELSE 0 END) AS verified,
    ROUND(
        (SUM(CASE WHEN pa.verification_status = 'VER-PASS' THEN 1 ELSE 0 END) * 100.0) 
        / COUNT(pa.id), 2
    ) AS verification_percentage
FROM enterprise_profiles p
JOIN profile_artifacts pa ON p.id = pa.profile_id
WHERE p.is_active = 1
GROUP BY p.id;
```

### 6.2. استخراج الفجوات الحرجة للملف النشط

```sql
-- الفجوات الحرجة في الملف النشط
SELECT 
    sa.id,
    sa.title_en,
    sa.title_ar,
    sa.primary_domain,
    sa.sub_domain,
    COALESCE(pa.custom_priority, sa.priority) AS effective_priority,
    pa.implementation_status,
    pa.owner_role,
    pa.effort_estimate
FROM profile_artifacts pa
JOIN security_artifacts sa ON pa.artifact_id = sa.id
JOIN enterprise_profiles p ON pa.profile_id = p.id
WHERE p.is_active = 1
  AND COALESCE(pa.custom_priority, sa.priority) IN ('PRI-CRITICAL', 'PRI-HIGH')
  AND pa.implementation_status IN ('STS-NOT-APPLIED', 'STS-PARTIAL', 'STS-NEEDS-IMPROVEMENT')
ORDER BY 
    CASE COALESCE(pa.custom_priority, sa.priority)
        WHEN 'PRI-CRITICAL' THEN 1
        WHEN 'PRI-HIGH' THEN 2
        ELSE 3
    END,
    pa.effort_estimate ASC;
```

### 6.3. مقارنة ملفين

```sql
-- مقارنة عنصرين في ملفين مختلفين
SELECT 
    sa.title_en,
    p1.name AS profile_1,
    pa1.implementation_status AS status_1,
    pa1.owner_role AS owner_1,
    p2.name AS profile_2,
    pa2.implementation_status AS status_2,
    pa2.owner_role AS owner_2
FROM security_artifacts sa
JOIN profile_artifacts pa1 ON sa.id = pa1.artifact_id
JOIN enterprise_profiles p1 ON pa1.profile_id = p1.id
LEFT JOIN profile_artifacts pa2 ON sa.id = pa2.artifact_id AND pa2.profile_id = 2
LEFT JOIN enterprise_profiles p2 ON pa2.profile_id = p2.id
WHERE p1.id = 1
  AND (pa2.id IS NOT NULL OR pa2.id IS NULL);
```

---

## 🏆 سابعاً: الخلاصة التنفيذية

### 7.1. ملخص التغييرات الجوهرية

| الجانب | الرؤية السابقة | الرؤية المنقحة |
|--------|---------------|----------------|
| **البيانات التشغيلية** | في `security_artifacts` | ⭐ في `profile_artifacts` |
| **البيانات المرجعية** | مختلطة مع التشغيلية | ⭐ منفصلة في `security_artifacts` |
| **تعدد الملفات** | غير مدعوم | ⭐ مدعوم بالكامل |
| **السجل التاريخي** | غير موجود | ⭐ `profile_assessments` |
| **المقارنة** | غير ممكنة | ⭐ مقارنة بين الملفات |
| **القوالب** | غير موجودة | ⭐ قوالب جاهزة |

### 7.2. الفوائد المعمارية

1. **فصل الاهتمامات (Separation of Concerns)**: المرجعية vs التشغيلية
2. **المرونة**: كل ملف له سياقه الخاص
3. **التدقيق**: سجل تاريخي كامل لكل تغيير
4. **القابلية للتوسع**: إضافة ملفات جديدة دون التأثير على الكتالوج
5. **المشاركة**: مشاركة الملفات بين الفرق مع تحكم في الصلاحيات

### 7.3. القرار النهائي

✅ **اعتماد الرؤية المنقحة** كأساس للتطبيق.

**الخطوات التالية:**
1. تنفيذ مخطط SQLite المنقح (مع فصل البيانات المرجعية عن التشغيلية)
2. تطوير `Profile Management Module` (إنشاء، تعديل، نسخ، حذف)
3. تطوير `Profile Switcher` (تبديل الملف النشط)
4. تطوير `Template Importer` (استيراد القوالب الجاهزة)
5. تطوير `Comparison Engine` (مقارنة الملفات)
6. تطوير `Assessment History Tracker` (سجل التقييمات)

**الشعار النهائي:**
> **"منصة مرجعية شاملة، ملفات مؤسسية قابلة للتخصيص، تقييمات دقيقة حسب السياق."**