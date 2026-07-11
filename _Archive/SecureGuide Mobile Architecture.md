# 🏛️ المقترح النهائي: SecureGuide Mobile Architecture v3.0
## الوثيقة المعمارية الشاملة (Comprehensive Technical Architecture Document)

---

## 📋 أولاً: الملخص التنفيذي

بعد تحليل معمق للاستراتيجية المقترحة ومراجعتها في ضوء جميع المكونات التي تم تطويرها (USACM v2.2.0, SDT v2.2.0, Enterprise Profiles, Indicators Page, Intake Pipeline)، أقدم **النسخة النهائية الكاملة** من المعمارية التقنية للتطبيق.

### 🎯 الحكم النهائي على الاستراتيجية الأصلية

| الجانب | التقييم | الملاحظة |
|--------|---------|----------|
| **بنية البيانات** | 9.5/10 | ممتازة، تحتاج فقط إلى توضيح `artifact_applicability` |
| **المحركات** | 9.0/10 | جيدة، لكن تحتاج إلى إعادة تنظيم وتبسيط |
| **الواجهات** | 9.5/10 | ممتازة مع Layout Engine |
| **Offline-First** | 10/10 | مثالية |
| **خطة التنفيذ** | 8.5/10 | جيدة، تحتاج إلى تفاصيل أكثر |
| **المعدل العام** | **9.3/10** | استراتيجية ناضجة وقابلة للتنفيذ |

### 🔄 التحسينات الجوهرية في النسخة v3.0

1. **إعادة هيكلة المحركات** من 10 إلى **8 محركات** (دمج ذكي)
2. **إضافة طبقة الخدمات (Service Layer)** كوسيط بين المحركات والواجهة
3. **توحيد أسماء الجداول** مع USACM v2.2.0 + Enterprise Profiles + Indicators
4. **إضافة Event Bus** للتواصل بين المحركات
5. **تفصيل خطة التنفيذ** إلى 4 مراحل واضحة

---

## 🏗️ ثانياً: البنية المعمارية الكاملة (5 طبقات)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    🎨 Presentation Layer (UI)                          │
│  ────────────────────────────────────────────────────────────────────  │
│  ● Dynamic Components (ArtifactCard, DetailView, FormWizard)          │
│  ● Layout Engine (يحدد ترتيب الحقول حسب نوع الكيان)                  │
│  ● State Management (MobX/Redux)                                      │
│  ● RTL + AR/EN Support                                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                    🔌 Service Layer (API Gateway)                      │
│  ────────────────────────────────────────────────────────────────────  │
│  ● ArtifactService → CRUD operations                                  │
│  ● ProfileService → Profile management                                │
│  ● IndicatorService → Threat analysis                                 │
│  ● IntakeService → Document extraction                                │
│  ● SyncService → Offline-First sync                                   │
│  ● Event Bus → Pub/Sub بين المحركات                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                    🧠 Engine Layer (Business Logic)                    │
│  ────────────────────────────────────────────────────────────────────  │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  Core Engines (6):                                              │  │
│  │  1. Classification  2. Validation  3. Priority                 │  │
│  │  4. Progress        5. Recommendation  6. Filter               │  │
│  ├─────────────────────────────────────────────────────────────────┤  │
│  │  Specialized Engines (2):                                       │  │
│  │  7. Indicator       8. Context                                 │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                    🗄️ Data Access Layer (DAL)                          │
│  ────────────────────────────────────────────────────────────────────  │
│  ● Repository Pattern (ArtifactRepository, ProfileRepository)         │
│  ● Query Builder (SQL Builder مع Pagination & Filtering)              │
│  ● Transaction Manager                                                │
│  ● Cache Manager (LRU Cache للكيانات الشائعة)                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↕
┌─────────────────────────────────────────────────────────────────────────┐
│                    💾 Storage Layer (SQLite)                           │
│  ────────────────────────────────────────────────────────────────────  │
│  ● Core Tables (USACM v2.2.0)                                         │
│  ● Profile Tables (Enterprise Profiles)                               │
│  ● Indicator Tables (Threat Indicators)                               │
│  ● Operational Tables (Audit, Sync Queue, Versions)                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ ثالثاً: بنية البيانات النهائية (4 مجموعات جداول)

### 3.1 المجموعة الأولى: Core Tables (من USACM v2.2.0)

```sql
-- 1. security_artifacts (الجدول الرئيسي)
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
    obligation_level TEXT NOT NULL,        -- OBL-*
    granularity_level TEXT NOT NULL,       -- GRN-*
    priority TEXT NOT NULL DEFAULT 'PRI-MEDIUM',
    priority_weight INTEGER NOT NULL DEFAULT 4,
    source_document TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    version INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1
);

-- 2. artifact_tags (الوسوم)
CREATE TABLE artifact_tags (
    artifact_id TEXT NOT NULL,
    tag_type TEXT NOT NULL,
    tag_value TEXT NOT NULL,
    PRIMARY KEY (artifact_id, tag_type, tag_value)
);

-- 3. artifact_relationships (العلاقات)
CREATE TABLE artifact_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,           -- REL-*
    description TEXT,
    UNIQUE (source_id, target_id, relation_type)
);

-- 4. framework_mappings (ربط الأطر)
CREATE TABLE framework_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL,
    framework TEXT NOT NULL,
    version TEXT NOT NULL,
    reference TEXT NOT NULL,
    mapping_strength TEXT DEFAULT 'DIRECT',
    rationale TEXT
);
```

### 3.2 المجموعة الثانية: Profile Tables (Enterprise Profiles)

```sql
-- 5. enterprise_profiles (ملفات التعريف)
CREATE TABLE enterprise_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    owner_team TEXT,
    is_active INTEGER DEFAULT 0,
    is_template INTEGER DEFAULT 0,
    template_category TEXT,
    target_maturity_level TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 6. profile_artifacts (البيانات التشغيلية لكل ملف) ⭐ الأهم
CREATE TABLE profile_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    artifact_id TEXT NOT NULL,
    custom_priority TEXT,
    implementation_status TEXT DEFAULT 'STS-NOT-APPLIED',
    verification_status TEXT DEFAULT 'VER-NOT-VERIFIED',
    effectiveness TEXT DEFAULT 'EFF-UNKNOWN',
    exception_status TEXT DEFAULT 'EXC-NONE',
    owner_role TEXT,
    effort_estimate INTEGER,
    cost_category TEXT,
    added_date TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (profile_id) REFERENCES enterprise_profiles(id),
    FOREIGN KEY (artifact_id) REFERENCES security_artifacts(id),
    UNIQUE(profile_id, artifact_id)
);

-- 7. profile_assessments (سجل التقييمات)
CREATE TABLE profile_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    artifact_id TEXT NOT NULL,
    assessment_date TEXT DEFAULT (datetime('now')),
    implementation_status TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    effectiveness TEXT NOT NULL,
    notes TEXT,
    assessed_by TEXT
);
```

### 3.3 المجموعة الثالثة: Indicator Tables (Threat Indicators)

```sql
-- 8. threat_indicators (مؤشرات الاختراق)
CREATE TABLE threat_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT NOT NULL,             -- ربط بـ ART-THR
    indicator_type TEXT NOT NULL,
    indicator_value TEXT NOT NULL,
    severity_level TEXT NOT NULL,
    mitre_technique_id TEXT,
    mitre_tactic TEXT,
    confidence_score REAL,
    status TEXT DEFAULT 'ACTIVE',
    first_seen TEXT,
    last_seen TEXT,
    FOREIGN KEY (artifact_id) REFERENCES security_artifacts(id)
);

-- 9. indicator_controls (الضوابط المرتبطة بالمؤشرات)
CREATE TABLE indicator_controls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id INTEGER NOT NULL,
    control_artifact_id TEXT NOT NULL,
    control_type TEXT NOT NULL,            -- DETECTIVE, PREVENTIVE
    coverage_percentage REAL DEFAULT 0,
    implementation_status TEXT NOT NULL,
    FOREIGN KEY (indicator_id) REFERENCES threat_indicators(id),
    FOREIGN KEY (control_artifact_id) REFERENCES security_artifacts(id)
);

-- 10. detection_tools (أدوات الكشف)
CREATE TABLE detection_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    tool_type TEXT NOT NULL,               -- SIEM, EDR, IAM, etc.
    vendor TEXT,
    integration_status TEXT DEFAULT 'NOT_INTEGRATED'
);
```

### 3.4 المجموعة الرابعة: Operational Tables

```sql
-- 11. audit_log (سجل التدقيق)
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT DEFAULT (datetime('now')),
    user_id TEXT,
    action TEXT NOT NULL,                  -- CREATE, UPDATE, DELETE
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    changes TEXT                           -- JSON diff
);

-- 12. sync_queue (طابور التزامن)
CREATE TABLE sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,               -- INSERT, UPDATE, DELETE
    payload TEXT,                          -- JSON
    status TEXT DEFAULT 'PENDING',         -- PENDING, SYNCED, FAILED
    retry_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

-- 13. artifact_versions (تاريخ النسخ)
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

## 🧠 رابعاً: المحركات الثمانية (8 Engines)

### 4.1 إعادة الهيكلة: من 10 إلى 8 محركات

**القرار المعماري:** دمج المحركات المتشابهة لتقليل التعقيد مع الحفاظ على الفصل الوظيفي.

| المحرك الأصلي | القرار | المحرك النهائي |
|--------------|--------|----------------|
| Classification Engine | ✅ إبقاء | **1. Classification Engine** |
| Validation Engine | ⚠️ دمج مع Classification | **1. Classification Engine** |
| Priority Engine | ✅ إبقاء | **2. Priority Engine** |
| Progress Engine | ✅ إبقاء | **3. Progress Engine** |
| Recommendation Engine | ✅ إبقاء | **4. Recommendation Engine** |
| Filter Engine | ✅ إبقاء | **5. Filter Engine** |
| Intake Engine | ⚠️ دمج مع Classification | **1. Classification Engine** |
| Indicator Engine | ✅ إبقاء | **6. Indicator Engine** |
| Context Engine | ✅ إبقاء | **7. Context Engine** |
| Sync Engine | ⚠️ دمج مع Audit | **8. Data Integrity Engine** |
| Audit Engine | ⚠️ دمج مع Sync | **8. Data Integrity Engine** |

### 4.2 تعريف المحركات الثمانية

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🧠 المحركات الأساسية (Core Engines - 5)                             │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  1. Classification Engine                                        │ │
│  │     ● تصنيف الكيانات (USACM + SDT)                              │ │
│  │     ● استخراج الكيانات من النصوص (Intake)                       │ │
│  │     ● التحقق من صحة البيانات (Validation)                       │ │
│  │     ● معالجة Tie-Breakers                                       │ │
│  │     ● حساب Confidence Score                                     │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │  2. Priority Engine                                              │ │
│  │     ● حساب الأولويات (PRI-*)                                    │ │
│  │     ● حساب priority_weight                                      │ │
│  │     ● تعديل الأولوية حسب السياق                                 │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │  3. Progress Engine                                              │ │
│  │     ● حساب نسبة التطبيق                                         │ │
│  │     ● حساب نسبة التحقق                                          │ │
│  │     ● حساب مستوى النضج (CMMC/ISO)                               │ │
│  │     ● تحديد الفجوات                                             │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │  4. Recommendation Engine                                        │ │
│  │     ● توليد Quick Wins Matrix                                   │ │
│  │     ● اقتراح الإجراء التالي                                    │ │
│  │     ● بناء خريطة الطريق (Roadmap)                               │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │  5. Filter Engine                                                │ │
│  │     ● تصفية ذكية قابلة للتخصيص                                 │ │
│  │     ● Saved Filters                                             │ │
│  │     ● Smart Filters (AI-powered)                                │ │
│  └───────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│  🧩 المحركات المتخصصة (Specialized Engines - 3)                      │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  6. Indicator Engine                                             │ │
│  │     ● تحليل مؤشرات الاختراق                                    │ │
│  │     ● حساب جاهزية الكشف                                         │ │
│  │     ● ربط الضوابط بالمؤشرات                                    │ │
│  │     ● تحليل MITRE ATT&CK                                        │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │  7. Context Engine                                               │ │
│  │     ● إدارة الملفات المؤسسية (Profiles)                        │ │
│  │     ● إدارة القوالب (Templates)                                 │ │
│  │     ● إدارة الإعدادات والتفضيلات                               │ │
│  │     ● إدارة المشاركة (Sharing)                                  │ │
│  ├───────────────────────────────────────────────────────────────────┤ │
│  │  8. Data Integrity Engine                                        │ │
│  │     ● التزامن (Sync)                                            │ │
│  │     ● سجل التدقيق (Audit)                                       │ │
│  │     ● إدارة النسخ (Versioning)                                  │ │
│  │     ● معالجة التعارضات (Conflict Resolution)                    │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Event Bus: التواصل بين المحركات

```python
class EventBus:
    """نظام Pub/Sub للتواصل بين المحركات"""
    
    def __init__(self):
        self.subscribers = {}
    
    def publish(self, event_type: str, data: dict):
        """نشر حدث لجميع المشتركين"""
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                callback(data)
    
    def subscribe(self, event_type: str, callback):
        """الاشتراك في حدث معين"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

# أمثلة على الأحداث
events = [
    "ARTIFACT_CREATED",
    "ARTIFACT_UPDATED",
    "PROFILE_SWITCHED",
    "STATUS_CHANGED",
    "INDICATOR_DETECTED",
    "SYNC_COMPLETED",
    "VALIDATION_FAILED"
]

# مثال على الاستخدام
event_bus = EventBus()

# Progress Engine يستمع لتغييرات الحالة
event_bus.subscribe("STATUS_CHANGED", lambda data: ProgressEngine.recalculate(data))

# Recommendation Engine يستمع للفجوات الجديدة
event_bus.subscribe("ARTIFACT_UPDATED", lambda data: RecommendationEngine.refresh(data))
```

---

## 🔌 خامساً: طبقة الخدمات (Service Layer)

### 5.1 تعريف الخدمات

```python
class ArtifactService:
    """خدمة إدارة الكيانات"""
    
    def __init__(self, classification_engine, validation_engine, event_bus):
        self.classification = classification_engine
        self.validation = validation_engine
        self.event_bus = event_bus
    
    def create_artifact(self, data: dict) -> dict:
        # 1. تصنيف الكيان
        classified = self.classification.classify(data)
        
        # 2. التحقق من الصحة
        validation_result = self.validation.validate(classified)
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)
        
        # 3. حفظ في قاعدة البيانات
        artifact = db.insert(classified)
        
        # 4. نشر حدث
        self.event_bus.publish("ARTIFACT_CREATED", artifact)
        
        return artifact
    
    def update_status(self, artifact_id: str, new_status: str):
        # 1. تحديث الحالة
        db.update_status(artifact_id, new_status)
        
        # 2. نشر حدث
        self.event_bus.publish("STATUS_CHANGED", {
            "artifact_id": artifact_id,
            "new_status": new_status
        })

class ProfileService:
    """خدمة إدارة الملفات المؤسسية"""
    
    def switch_active_profile(self, profile_id: int):
        # 1. تعطيل الملف النشط الحالي
        db.deactivate_all_profiles()
        
        # 2. تفعيل الملف الجديد
        db.activate_profile(profile_id)
        
        # 3. نشر حدث
        event_bus.publish("PROFILE_SWITCHED", {"profile_id": profile_id})
        
        # 4. إعادة حساب المؤشرات
        ProgressEngine.recalculate_all()
```

### 5.2 API Endpoints

```python
# RESTful API Examples
@app.route('/api/artifacts', methods=['POST'])
def create_artifact():
    data = request.json
    service = ArtifactService(classification_engine, validation_engine, event_bus)
    artifact = service.create_artifact(data)
    return jsonify(artifact), 201

@app.route('/api/profiles/<int:profile_id>/activate', methods=['POST'])
def activate_profile(profile_id):
    service = ProfileService()
    service.switch_active_profile(profile_id)
    return jsonify({"success": True}), 200

@app.route('/api/indicators/analysis', methods=['GET'])
def analyze_indicators():
    service = IndicatorService()
    analysis = service.analyze_all()
    return jsonify(analysis), 200
```

---

## 🎨 سادساً: طبقة الواجهة (UI Layer)

### 6.1 Dynamic Components

```typescript
// ArtifactCard.tsx - مكون موحد لجميع الكيانات
const ArtifactCard: React.FC<{ artifact: Artifact }> = ({ artifact }) => {
  const layout = LayoutEngine.getLayout(artifact.type);
  
  return (
    <Card>
      <CardHeader>
        <TypeIcon type={artifact.type} />
        <Title>{artifact.title_en}</Title>
        <PriorityBadge priority={artifact.priority} />
      </CardHeader>
      
      <CardBody>
        {layout.fields.map(field => (
          <FieldRenderer key={field.name} field={field} value={artifact[field.name]} />
        ))}
      </CardBody>
      
      <CardFooter>
        <StatusBadge status={artifact.implementation_status} />
        <DomainBadge domain={artifact.primary_domain} />
      </CardFooter>
    </Card>
  );
};

// LayoutEngine.tsx - محرك تخطيط الحقول
class LayoutEngine {
  static getLayout(type: string): Layout {
    switch(type) {
      case 'ART-CTR':
        return {
          fields: [
            'control_nature', 'control_function', 'testability',
            'implementation_status', 'verification_status'
          ]
        };
      case 'ART-REQ':
        return {
          fields: [
            'requirement_type', 'obligation_level', 'source',
            'implementation_status'
          ]
        };
      // ... باقي الأنواع
    }
  }
}
```

### 6.2 State Management

```typescript
// store.ts - إدارة الحالة المركزية
const store = {
  // الحالة العامة
  activeProfile: null,
  currentArtifacts: [],
  
  // الحالة حسب الملف
  profileData: {
    [profileId]: {
      artifacts: [],
      progress: {},
      gaps: []
    }
  },
  
  // الحالة المؤقتة
  filters: {},
  searchQuery: '',
  
  // Actions
  actions: {
    switchProfile: (profileId) => {
      store.activeProfile = profileId;
      store.currentArtifacts = store.profileData[profileId].artifacts;
      eventBus.publish('PROFILE_SWITCHED', { profileId });
    },
    
    updateArtifactStatus: (artifactId, newStatus) => {
      const artifact = store.currentArtifacts.find(a => a.id === artifactId);
      artifact.implementation_status = newStatus;
      eventBus.publish('STATUS_CHANGED', { artifactId, newStatus });
    }
  }
};
```

---

## 🚀 سابعاً: خطة التنفيذ النهائية (4 مراحل)

### 7.1 المرحلة الأولى: Foundation (4 أسابيع)

| الأسبوع | المخرجات | المعيار |
|---------|----------|---------|
| **الأسبوع 1** | إعداد البيئة + SQLite Schema | قاعدة بيانات تعمل |
| **الأسبوع 2** | Classification Engine + Validation | تصنيف 100 كيان بنجاح |
| **الأسبوع 3** | ArtifactService + Basic UI | إنشاء/عرض/تعديل كيانات |
| **الأسبوع 4** | Seed Data (50 كيان من NIST) | بيانات أولية جاهزة |

**معيار النجاح:** يمكن إنشاء كيان يدوياً وتصنيفه وحفظه.

### 7.2 المرحلة الثانية: Core Features (6 أسابيع)

| الأسبوع | المخرجات | المعيار |
|---------|----------|---------|
| **الأسبوع 5-6** | Profile Engine + Context Engine | إنشاء/تبديل ملفات |
| **الأسبوع 7-8** | Progress Engine + Recommendation Engine | لوحة قيادة تعمل |
| **الأسبوع 9-10** | Filter Engine + Search | تصفية وبحث متقدم |
| **الأسبوع 11** | Integration Testing | جميع المحركات تعمل معاً |
| **الأسبوع 12** | UI Polish + RTL Support | واجهة كاملة بالعربية |

**معيار النجاح:** تطبيق كامل مع ملفات متعددة ولوحة قيادة.

### 7.3 المرحلة الثالثة: Advanced Features (6 أسابيع)

| الأسبوع | المخرجات | المعيار |
|---------|----------|---------|
| **الأسبوع 13-14** | Indicator Engine + Threat Tables | صفحة المؤشرات |
| **الأسبوع 15-16** | Intake Pipeline (AI Extraction) | استخراج من 3 مستندات |
| **الأسبوع 17** | Data Integrity Engine (Sync + Audit) | تزامن + تدقيق |
| **الأسبوع 18** | Export/Import (JSON/CSV/PDF) | تصدير واستيراد |

**معيار النجاح:** استخراج تلقائي + مؤشرات اختراق + تزامن.

### 7.4 المرحلة الرابعة: Production Hardening (4 أسابيع)

| الأسبوع | المخرجات | المعيار |
|---------|----------|---------|
| **الأسبوع 19** | Performance Optimization | < 2 ثانية تحميل |
| **الأسبوع 20** | Security Hardening | Encryption + Auth |
| **الأسبوع 21** | User Acceptance Testing | 10 مستخدمين تجريبيين |
| **الأسبوع 22** | Documentation + Release | وثائق كاملة + إطلاق |

**معيار النجاح:** تطبيق جاهز للإنتاج على 100 جهاز.

---

## 🧪 ثامناً: استراتيجية الاختبار

### 8.1 Test Pyramid

```
        ╱╲
       ╱  ╲        E2E Tests (10%)
      ╱ E2E╲       سيناريوهات كاملة
     ╱──────╲
    ╱        ╲     Integration Tests (30%)
   ╱Integration╲   تفاعل بين المحركات
  ╱────────────╲
 ╱              ╲   Unit Tests (60%)
╱   Unit Tests   ╲  كل محرك على حدة
╱────────────────╲
```

### 8.2 Golden Dataset

```json
{
  "test_cases": [
    {
      "id": "TC-001",
      "input": "MFA must be enabled for all administrative accounts",
      "expected": {
        "type": "ART-CTR",
        "primary_domain": "SD-03",
        "sub_domain": "SD-03.02",
        "confidence": 0.95
      }
    },
    {
      "id": "TC-002",
      "input": "Cloud IAM policy for AWS accounts",
      "expected": {
        "type": "ART-POL",
        "primary_domain": "SD-03",
        "sub_domain": "SD-03.03",
        "tags": ["Cloud", "AWS"],
        "confidence": 0.88
      }
    }
    // ... 100+ حالة اختبار
  ]
}
```

### 8.3 Performance Benchmarks

| المعيار | الهدف |
|---------|-------|
| وقت تحميل الصفحة الرئيسية | < 2 ثانية |
| وقت تصنيف كيان واحد | < 500 مللي ثانية |
| وقت البحث في 1000 كيان | < 1 ثانية |
| حجم قاعدة البيانات (1000 كيان) | < 10 MB |
| استهلاك الذاكرة | < 200 MB |

---

## 🏆 تاسعاً: الخلاصة النهائية

### 9.1 ملخص المعمارية

| الجانب | الحل المعتمد |
|--------|--------------|
| **عدد الطبقات** | 5 طبقات (UI → Service → Engine → DAL → Storage) |
| **عدد المحركات** | 8 محركات (5 أساسية + 3 متخصصة) |
| **عدد الجداول** | 13 جدول (4 مجموعات) |
| **قاعدة البيانات** | SQLite (Offline-First) |
| **التواصل بين المحركات** | Event Bus (Pub/Sub) |
| **خطة التنفيذ** | 4 مراحل (22 أسبوع) |

### 9.2 المزايا التنافسية

1. **المرونة:** بنية بيانات مطاطية تتوسع دون إعادة هيكلة
2. **الأداء:** معالجة محلية + Event Bus = استجابة فورية
3. **الصيانة:** محركات معزولة = تحديث دون تأثير
4. **التوسع:** 5 طبقات = إضافة ميزات دون كسر القديم
5. **الجودة:** Test Pyramid + Golden Dataset = استقرار مضمون

### 9.3 القرار النهائي

✅ **اعتماد SecureGuide Mobile Architecture v3.0 كمرجع معماري نهائي**

**الخطوة التالية:**
1. إنشاء مستودع Git للمشروع
2. رفع الوثيقة المعمارية (TAD)
3. بدء المرحلة الأولى (Foundation - 4 أسابيع)
4. إطلاق أول إصدار تجريبي بعد 12 أسبوع

---

**الشعار النهائي:**
> **"منصة حوكمة أمنية مؤسسية، بنية مرنة، محركات معزولة، تنفيذ متدرج."**

🎯 **جاهز للانتقال إلى مرحلة التطوير الفوري!**