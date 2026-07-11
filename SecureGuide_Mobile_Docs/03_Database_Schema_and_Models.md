# Database Schema and Models
**Project:** SecureGuide Mobile (Enterprise Reference Platform)
**Version:** 3.0

> **المصدر المرجعي القاطع للمخطط هو `migrations/001_initial_schema.sql`** (المتوافق مع USACM v2.2.1 §8 و SDT v2.2.1، والموثّق في `docs/DATA_DICTIONARY.md`). عند أي اختلاف بين الأمثلة أدناه وملف الترحيل، **يفوز ملف الترحيل**. يوثّق ملف الترحيل حالياً نطاق "نواة التصنيف": الإدخال + الكتالوج المرجعي + جداوله الفرعية العشرة + القوالب + الطبقة التشغيلية. أما وحدتا **الأصول المؤسسية ومؤشرات التهديد** الموصوفتان في هذه الوثيقة فهما **لِما بعد الـMVP** ولم تُضافا بعدُ إلى ملف الترحيل (تماشياً مع نطاق MVP في AGENTS.md). ملاحظة تسمية: عمود العلاقة المعياري هو `relation_type`، والحالات التشغيلية الحقيقية تعيش في `profile_artifacts` لا في `security_artifacts`.

## 1. Core Principles
- **Offline-First SQLite:** All data is stored locally.
- **Strict Normalization:** USACM CHECK constraints enforce data integrity at the database level.
- **Reference vs. Operational Data Separation:** Global frameworks are immutable (Master Catalog); profile-specific data is operational (Enterprise Profiles).

## 2. Advanced Schema Definitions

The database is divided into four main logical modules, adapted from the advanced architectural studies.

### 2.1. Master Catalog Module (Reference Data)
Contains the immutable data imported from standard frameworks (NIST, ISO, etc.). Operational fields have been strictly removed to ensure the catalog remains a pure reference.

`sql
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
`

`sql

### 2.2. Enterprise Profiles Module (Operational Data)
Manages institutional contexts and their implementation states. This is the core of the separation logic, where a profile tracks its own `implementation_status` for the referenced artifacts.

`sql
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
`

`sql
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
    CHECK (effectiveness IN ('EFF-LOW','EFF-MEDIUM','EFF-HIGH','EFF-UNKNOWN')),
    CHECK (exception_status IN ('EXC-NONE','EXC-NOT-APPLICABLE','EXC-RISK-ACCEPTED','EXC-DEFERRED','EXC-UNAVAILABLE')),
    CHECK (self_assessment_status IN ('NOT_ASSESSED','IN_PROGRESS','COMPLETED','NEEDS_REVIEW')),
    CHECK (self_assessment_score IS NULL OR (self_assessment_score >= 0 AND self_assessment_score <= 100))
);

-- فهارس للأداء
CREATE INDEX IF NOT EXISTS idx_profile_artifacts_profile ON profile_artifacts(profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_artifacts_artifact ON profile_artifacts(artifact_id);
CREATE INDEX IF NOT EXISTS idx_profile_artifacts_status ON profile_artifacts(implementation_status);
CREATE INDEX IF NOT EXISTS idx_profile_artifacts_priority ON profile_artifacts(custom_priority);
CREATE INDEX IF NOT EXISTS idx_profile_artifacts_next_review ON profile_artifacts(next_review_date);
`

`sql
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
`

`sql
-- ===== الوسوم =====
`

### 2.3. Information Assets Module (4-Tier Architecture)
Maps the enterprise's physical, logical, and human assets, linking them dynamically to controls, vulnerabilities, and monitoring tools to generate real-time coverage and risk scores.

`sql
-- ============================================================================
-- 1.1 أنواع الأصول المرجعية (من ملف CSV)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ref_asset_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,              -- SERVER_HW, DATABASE, FIREWALL, etc.
    category TEXT NOT NULL,                 -- HARDWARE, SOFTWARE, NETWORK, SERVICE
    name_en TEXT NOT NULL,
    name_ar TEXT NOT NULL,
    description_en TEXT,
    description_ar TEXT,
    default_criticality TEXT DEFAULT 'MEDIUM',
    typical_threats TEXT,                   -- JSON array
    typical_controls TEXT,                  -- JSON array
    typical_tools TEXT,                     -- JSON array
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    CHECK (category IN ('HARDWARE','SOFTWARE','NETWORK','SERVICE','DATA','FACILITY','PERSONNEL')),
    CHECK (default_criticality IN ('CRITICAL','HIGH','MEDIUM','LOW'))
);

-- بيانات أولية من ملف CSV
INSERT INTO ref_asset_types (code, category, name_en, name_ar, description_en) VALUES
('AD', 'SOFTWARE', 'Active Directory', 'خدمات الدليل النشط', 'Microsoft Active Directory Domain Services'),
('APPLICATION', 'SOFTWARE', 'Application', 'تطبيق', 'Enterprise or custom application'),
('BACKUP', 'SOFTWARE', 'Backup System', 'نظام النسخ الاحتياطي', 'Backup and replication system'),
('BILLING', 'SOFTWARE', 'Billing System', 'نظام الفوترة', 'Billing and automation platform'),
('DATABASE', 'SOFTWARE', 'Database', 'قاعدة بيانات', 'Relational or NoSQL database'),
('DNS', 'NETWORK', 'DNS Server', 'خادم DNS', 'Domain Name System server'),
('EMAIL_SEC', 'SOFTWARE', 'Email Security', 'أمن البريد', 'Email Security Gateway'),
('EMAIL_SYS', 'SOFTWARE', 'Email System', 'نظام البريد', 'Mail server system'),
('FIREWALL', 'NETWORK', 'Firewall', 'جدار ناري', 'Network firewall (NGFW)'),
('LOAD_BAL', 'NETWORK', 'Load Balancer', 'موزع الأحمال', 'Application or network load balancer'),
('OS', 'SOFTWARE', 'Operating System', 'نظام تشغيل', 'Server or endpoint operating system'),
('PROXY', 'NETWORK', 'Proxy Server', 'خادم وسيط', 'Proxy or API gateway'),
('ROUTER', 'NETWORK', 'Router', 'موجّه', 'Network router'),
('SERVER_HW', 'HARDWARE', 'Server Hardware', 'خوادم مادية', 'Physical server hardware'),
('STORAGE', 'HARDWARE', 'Storage System', 'نظام تخزين', 'SAN/NAS storage system'),
('SWITCH', 'NETWORK', 'Switch', 'محوّل شبكي', 'Network switch'),
('SYSTEM', 'SOFTWARE', 'System', 'نظام', 'Enterprise system or platform'),
('TERMINAL', 'SOFTWARE', 'Terminal Server', 'خادم طرفي', 'Remote Desktop Services'),
('VIRTUAL', 'SOFTWARE', 'Virtualization', 'أنظمة افتراضية', 'Hypervisor or virtualization platform'),
('WEB_HOST', 'SERVICE', 'Web Hosting', 'استضافة ويب', 'Web hosting control panel');

-- ============================================================================
-- 1.2 المصنّعون (Vendors)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ref_asset_vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,              -- MSFT, CISCO, FRTNT, etc.
    name_en TEXT NOT NULL,
    name_ar TEXT,
    website TEXT,
    support_contact TEXT,
    is_active INTEGER DEFAULT 1
);

-- بيانات أولية
INSERT INTO ref_asset_vendors (code, name_en, name_ar) VALUES
('MSFT', 'Microsoft', 'مايكروسوفت'),
('CISCO', 'Cisco', 'سيسكو'),
('FRTNT', 'Fortinet', 'فورتينيت'),
('ORCL', 'Oracle', 'أوراكل'),
('IBM', 'IBM', 'آي بي إم'),
('HPE', 'HP Enterprise', 'إتش بي إي'),
('DELL', 'Dell', 'ديل'),
('VMW', 'VMware', 'في إم وير'),
('JNPR', 'Juniper', 'جونيبر'),
('HWI', 'Huawei', 'هواوي'),
('KASP', 'Kaspersky', 'كاسبرسكي'),
('VEAM', 'Veeam', 'فيفام');

-- ============================================================================
-- 1.3 الموديلات/الأنظمة (Models/Systems)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ref_asset_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_type_code TEXT NOT NULL,
    vendor_code TEXT NOT NULL,
    model_name TEXT NOT NULL,
    version TEXT,
    description TEXT,
    end_of_life_date TEXT,
    is_supported INTEGER DEFAULT 1,
    FOREIGN KEY (asset_type_code) REFERENCES ref_asset_types(code),
    FOREIGN KEY (vendor_code) REFERENCES ref_asset_vendors(code),
    UNIQUE(asset_type_code, vendor_code, model_name)
);

-- بيانات أولية (أمثلة من CSV)
INSERT INTO ref_asset_models (asset_type_code, vendor_code, model_name, description) VALUES
('FIREWALL', 'CISCO', 'ASA 5500-X', 'Cisco ASA Firewall'),
('FIREWALL', 'CISCO', 'Firepower 2100', 'Cisco Firepower NGFW'),
('FIREWALL', 'FRTNT', 'FortiGate 60F', 'Fortinet FortiGate'),
('FIREWALL', 'FRTNT', 'FortiGate 100F', 'Fortinet FortiGate'),
('DATABASE', 'ORCL', 'Oracle Database 19c', 'Oracle RDBMS'),
('DATABASE', 'ORCL', 'Oracle Database 21c', 'Oracle RDBMS'),
('DATABASE', 'MSFT', 'SQL Server 2019', 'Microsoft SQL Server'),
('DATABASE', 'MSFT', 'SQL Server 2022', 'Microsoft SQL Server'),
('DATABASE', 'IBM', 'DB2', 'IBM DB2'),
('SERVER_HW', 'DELL', 'PowerEdge R750', 'Dell PowerEdge Server'),
('SERVER_HW', 'DELL', 'PowerEdge R760', 'Dell PowerEdge Server'),
('SERVER_HW', 'HPE', 'ProLiant DL360 Gen10', 'HP ProLiant Server'),
('SERVER_HW', 'HPE', 'ProLiant DL380 Gen11', 'HP ProLiant Server'),
('VIRTUAL', 'VMW', 'vSphere 8.0', 'VMware vSphere'),
('VIRTUAL', 'VMW', 'ESXi 8.0', 'VMware ESXi Hypervisor'),
('BACKUP', 'VEAM', 'Veeam Backup & Replication', 'Veeam Backup Suite');
`

`sql
-- ============================================================================
-- 2.1 جرد الأصول المؤسسي (الأصول الفعلية)
-- ============================================================================
CREATE TABLE IF NOT EXISTS enterprise_assets (
    id TEXT PRIMARY KEY,                    -- AST-SRV-001, AST-DB-001
    asset_name TEXT NOT NULL,
    asset_name_ar TEXT,
    asset_type_code TEXT NOT NULL,          -- ربط بـ ref_asset_types
    vendor_code TEXT,                       -- ربط بـ ref_asset_vendors
    model_code TEXT,                        -- ربط بـ ref_asset_models
    version TEXT,
    
    -- ===== التصنيف والأهمية =====
    criticality TEXT NOT NULL DEFAULT 'MEDIUM',
    data_classification TEXT,               -- PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED
    business_function TEXT,                 -- الوظيفة bisnis
    business_owner TEXT,                    -- مالك الأعمال
    technical_owner TEXT,                   -- المالك التقني
    
    -- ===== الموقع والبيئة =====
    location TEXT,                          -- DC1, DC2, Cloud-AWS, Cloud-Azure
    environment TEXT,                       -- PRODUCTION, DR, UAT, DEV, TEST
    network_zone TEXT,                      -- DMZ, INTERNAL, EXTERNAL, MANAGEMENT
    
    -- ===== الحالة التشغيلية =====
    status TEXT NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE, DECOMMISSIONED, MAINTENANCE, RETIRED
    install_date TEXT,
    warranty_expiry TEXT,
    support_contract_expiry TEXT,
    last_patch_date TEXT,
    last_assessment_date TEXT,
    
    -- ===== الاتصال والشبكة =====
    ip_address TEXT,
    hostname TEXT,
    fqdn TEXT,
    mac_address TEXT,
    
    -- ===== البيانات الوصفية =====
    description TEXT,
    tags TEXT,                              -- JSON array
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    is_active INTEGER DEFAULT 1,
    
    -- ===== القيود =====
    FOREIGN KEY (asset_type_code) REFERENCES ref_asset_types(code),
    FOREIGN KEY (vendor_code) REFERENCES ref_asset_vendors(code),
    CHECK (criticality IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    CHECK (data_classification IN ('PUBLIC','INTERNAL','CONFIDENTIAL','RESTRICTED')),
    CHECK (environment IN ('PRODUCTION','DR','UAT','DEV','TEST')),
    CHECK (status IN ('ACTIVE','DECOMMISSIONED','MAINTENANCE','RETIRED'))
);

-- فهارس للأداء
CREATE INDEX IF NOT EXISTS idx_assets_type ON enterprise_assets(asset_type_code);
CREATE INDEX IF NOT EXISTS idx_assets_criticality ON enterprise_assets(criticality);
CREATE INDEX IF NOT EXISTS idx_assets_status ON enterprise_assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_environment ON enterprise_assets(environment);
CREATE INDEX IF NOT EXISTS idx_assets_location ON enterprise_assets(location);
`

`sql
-- ============================================================================
-- 3.1 الأصل ←→ الضابط (أي ضابط يحمي أي أصل؟)
-- ============================================================================
CREATE TABLE IF NOT EXISTS asset_controls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,              -- ART-CTR, ART-CTE, ART-CFG, ART-RUL
    coverage_percentage REAL DEFAULT 100,   -- نسبة تغطية الضابط للأصل
    implementation_status TEXT NOT NULL DEFAULT 'STS-FULL',
    effectiveness_score REAL,               -- 0-1
    last_tested TEXT,
    notes TEXT,
    FOREIGN KEY (asset_id) REFERENCES enterprise_assets(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES security_artifacts(id) ON DELETE CASCADE,
    UNIQUE(asset_id, artifact_id),
    CHECK (coverage_percentage BETWEEN 0 AND 100)
);

CREATE INDEX IF NOT EXISTS idx_asset_controls_asset ON asset_controls(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_controls_artifact ON asset_controls(artifact_id);

-- ============================================================================
-- 3.2 الأصل ←→ الثغرة (أي ثغرة في أي أصل؟)
-- ============================================================================
CREATE TABLE IF NOT EXISTS asset_vulnerabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,              -- ART-VUL
    cve_id TEXT,                            -- CVE-2024-XXXX
    cvss_score REAL,                        -- 0-10
    severity TEXT NOT NULL,                 -- CRITICAL, HIGH, MEDIUM, LOW
    exploit_available INTEGER DEFAULT 0,
    discovery_date TEXT,
    remediation_date TEXT,
    mitigation_status TEXT DEFAULT 'OPEN',  -- OPEN, MITIGATED, ACCEPTED, FALSE_POSITIVE
    FOREIGN KEY (asset_id) REFERENCES enterprise_assets(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES security_artifacts(id) ON DELETE CASCADE,
    UNIQUE(asset_id, artifact_id),
    CHECK (severity IN ('CRITICAL','HIGH','MEDIUM','LOW')),
    CHECK (cvss_score BETWEEN 0 AND 10),
    CHECK (mitigation_status IN ('OPEN','MITIGATED','ACCEPTED','FALSE_POSITIVE'))
);

CREATE INDEX IF NOT EXISTS idx_asset_vuln_asset ON asset_vulnerabilities(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_vuln_severity ON asset_vulnerabilities(severity);

-- ============================================================================
-- 3.3 الأصل ←→ التهديد (أي تهديد يستهدف أي أصل؟)
-- ============================================================================
CREATE TABLE IF NOT EXISTS asset_threats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,              -- ART-THR
    likelihood TEXT NOT NULL,               -- HIGH, MEDIUM, LOW
    impact TEXT NOT NULL,                   -- HIGH, MEDIUM, LOW
    mitre_technique_id TEXT,                -- T1110, T1078
    mitre_tactic TEXT,                      -- Initial Access, Execution
    first_seen TEXT,
    last_seen TEXT,
    FOREIGN KEY (asset_id) REFERENCES enterprise_assets(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES security_artifacts(id) ON DELETE CASCADE,
    UNIQUE(asset_id, artifact_id),
    CHECK (likelihood IN ('HIGH','MEDIUM','LOW')),
    CHECK (impact IN ('HIGH','MEDIUM','LOW'))
);

CREATE INDEX IF NOT EXISTS idx_asset_threats_asset ON asset_threats(asset_id);

-- ============================================================================
-- 3.4 الأصل ←→ الأداة (أي أداة تراقب/تحمي أي أصل؟)
-- ============================================================================
CREATE TABLE IF NOT EXISTS asset_monitoring_tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,                -- Splunk, Sentinel, CrowdStrike
    tool_type TEXT NOT NULL,                -- SIEM, EDR, IAM, VULN, CSPM, DLP
    monitoring_coverage REAL DEFAULT 100,   -- نسبة التغطية
    integration_status TEXT DEFAULT 'ACTIVE', -- ACTIVE, PARTIAL, INACTIVE
    last_data_received TEXT,
    FOREIGN KEY (asset_id) REFERENCES enterprise_assets(id) ON DELETE CASCADE,
    UNIQUE(asset_id, tool_name),
    CHECK (tool_type IN ('SIEM','EDR','IAM','VULN','CSPM','DLP','NDR','PAM','OTHER')),
    CHECK (monitoring_coverage BETWEEN 0 AND 100),
    CHECK (integration_status IN ('ACTIVE','PARTIAL','INACTIVE'))
);

CREATE INDEX IF NOT EXISTS idx_asset_tools_asset ON asset_monitoring_tools(asset_id);
CREATE INDEX IF NOT EXISTS idx_asset_tools_type ON asset_monitoring_tools(tool_type);

-- ============================================================================
-- 3.5 الأصل ←→ الدليل (أي دليل يثبت حماية الأصل؟)
-- ============================================================================
CREATE TABLE IF NOT EXISTS asset_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,              -- ART-EVD
    evidence_type TEXT NOT NULL,            -- REPORT, LOG, CONFIG, SCREENSHOT, CERTIFICATE
    collection_date TEXT,
    expiry_date TEXT,
    file_path TEXT,
    is_valid INTEGER DEFAULT 1,
    FOREIGN KEY (asset_id) REFERENCES enterprise_assets(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES security_artifacts(id) ON DELETE CASCADE,
    CHECK (evidence_type IN ('REPORT','LOG','CONFIG','SCREENSHOT','CERTIFICATE','OTHER'))
);

-- ============================================================================
-- 3.6 الأصل ←→ المؤشر (أي مؤشر يقيس حماية الأصل؟)
-- ============================================================================
CREATE TABLE IF NOT EXISTS asset_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,              -- ART-MET
    metric_value REAL,
    measurement_date TEXT,
    target_value REAL,
    is_compliant INTEGER,
    FOREIGN KEY (asset_id) REFERENCES enterprise_assets(id) ON DELETE CASCADE,
    FOREIGN KEY (artifact_id) REFERENCES security_artifacts(id) ON DELETE CASCADE
);
`

`sql
-- ============================================================================
-- 4.1 عرض: درجة تغطية الضوابط لكل أصل
-- ============================================================================
CREATE VIEW IF NOT EXISTS v_asset_control_coverage AS
SELECT 
    a.id AS asset_id,
    a.asset_name,
    a.criticality,
    a.asset_type_code,
    COUNT(DISTINCT ac.artifact_id) AS total_controls,
    SUM(CASE WHEN ac.implementation_status = 'STS-FULL' THEN 1 ELSE 0 END) AS fully_implemented,
    SUM(CASE WHEN ac.implementation_status = 'STS-PARTIAL' THEN 1 ELSE 0 END) AS partially_implemented,
    ROUND(
        CASE 
            WHEN COUNT(DISTINCT ac.artifact_id) = 0 THEN 0
            ELSE (
                (SUM(CASE WHEN ac.implementation_status = 'STS-FULL' THEN 1.0 ELSE 0 END) +
                 SUM(CASE WHEN ac.implementation_status = 'STS-PARTIAL' THEN 0.5 ELSE 0 END))
                * 100.0 / COUNT(DISTINCT ac.artifact_id)
            )
        END, 2
    ) AS coverage_percentage
FROM enterprise_assets a
LEFT JOIN asset_controls ac ON a.id = ac.asset_id
WHERE a.is_active = 1
GROUP BY a.id;

-- ============================================================================
-- 4.2 عرض: درجة الخطر لكل أصل
-- ============================================================================
CREATE VIEW IF NOT EXISTS v_asset_risk_score AS
SELECT 
    a.id AS asset_id,
    a.asset_name,
    a.criticality AS asset_criticality,
    COUNT(DISTINCT av.artifact_id) AS total_vulnerabilities,
    SUM(CASE WHEN av.severity = 'CRITICAL' THEN 1 ELSE 0 END) AS critical_vulns,
    SUM(CASE WHEN av.severity = 'HIGH' THEN 1 ELSE 0 END) AS high_vulns,
    COUNT(DISTINCT at2.artifact_id) AS total_threats,
    ROUND(
        (
            (CASE a.criticality 
                WHEN 'CRITICAL' THEN 4 
                WHEN 'HIGH' THEN 3 
                WHEN 'MEDIUM' THEN 2 
                ELSE 1 
            END) *
            (SUM(CASE WHEN av.severity = 'CRITICAL' THEN 10 
                      WHEN av.severity = 'HIGH' THEN 7 
                      WHEN av.severity = 'MEDIUM' THEN 4 
                      ELSE 1 END) + 1)
        ) / 10.0, 2
    ) AS risk_score
FROM enterprise_assets a
LEFT JOIN asset_vulnerabilities av ON a.id = av.asset_id AND av.mitigation_status = 'OPEN'
LEFT JOIN asset_threats at2 ON a.id = at2.asset_id
WHERE a.is_active = 1
GROUP BY a.id;

-- ============================================================================
-- 4.3 عرض: درجة المراقبة لكل أصل
-- ============================================================================
CREATE VIEW IF NOT EXISTS v_asset_monitoring_coverage AS
SELECT 
    a.id AS asset_id,
    a.asset_name,
    a.criticality,
    COUNT(DISTINCT amt.tool_name) AS total_tools,
    SUM(CASE WHEN amt.integration_status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_tools,
    SUM(CASE WHEN amt.tool_type = 'SIEM' THEN 1 ELSE 0 END) AS siem_coverage,
    SUM(CASE WHEN amt.tool_type = 'EDR' THEN 1 ELSE 0 END) AS edr_coverage,
    ROUND(
        CASE 
            WHEN COUNT(DISTINCT amt.tool_name) = 0 THEN 0
            ELSE SUM(CASE WHEN amt.integration_status = 'ACTIVE' THEN amt.monitoring_coverage ELSE 0 END)
                 * 100.0 / (COUNT(DISTINCT amt.tool_name) * 100)
        END, 2
    ) AS monitoring_percentage
FROM enterprise_assets a
LEFT JOIN asset_monitoring_tools amt ON a.id = amt.asset_id
WHERE a.is_active = 1
GROUP BY a.id;

-- ============================================================================
-- 4.4 عرض: لوحة القيادة الشاملة للأصول
-- ============================================================================
CREATE VIEW IF NOT EXISTS v_asset_dashboard AS
SELECT 
    a.id AS asset_id,
    a.asset_name,
    a.asset_name_ar,
    t.name_en AS asset_type,
    t.name_ar AS asset_type_ar,
    v.name_en AS vendor,
    a.criticality,
    a.environment,
    a.location,
    a.status,
    COALESCE(acc.coverage_percentage, 0) AS control_coverage,
    COALESCE(ars.risk_score, 0) AS risk_score,
    COALESCE(amc.monitoring_percentage, 0) AS monitoring_coverage,
    COALESCE(ars.total_vulnerabilities, 0) AS open_vulnerabilities,
    COALESCE(ars.critical_vulns, 0) AS critical_vulnerabilities,
    -- درجة الامتثال الشاملة
    ROUND(
        (COALESCE(acc.coverage_percentage, 0) * 0.4 + 
         COALESCE(amc.monitoring_percentage, 0) * 0.3 + 
         (100 - COALESCE(ars.risk_score, 0) * 10) * 0.3), 2
    ) AS overall_compliance_score
FROM enterprise_assets a
LEFT JOIN ref_asset_types t ON a.asset_type_code = t.code
LEFT JOIN ref_asset_vendors v ON a.vendor_code = v.code
LEFT JOIN v_asset_control_coverage acc ON a.id = acc.asset_id
LEFT JOIN v_asset_risk_score ars ON a.id = ars.asset_id
LEFT JOIN v_asset_monitoring_coverage amc ON a.id = amc.asset_id
WHERE a.is_active = 1;
`

`sql
ALTER TABLE security_artifacts ADD COLUMN protected_asset_id TEXT;
ALTER TABLE security_artifacts ADD COLUMN affected_asset_id TEXT;

-- قيود
CREATE TRIGGER IF NOT EXISTS trg_artifact_asset_link
BEFORE INSERT ON security_artifacts
WHEN NEW.protected_asset_id IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'Asset not found')
    WHERE NEW.protected_asset_id NOT IN (SELECT id FROM enterprise_assets);
END;
`

`sql
-- إضافة إلى ref_relationship_types
INSERT INTO ref_relationship_types (code, name_en, name_ar, description) VALUES
('REL-PRO', 'Protects', 'يحمي', 'Control protects an asset'),
('REL-MON', 'Monitors', 'يراقب', 'Tool monitors an asset'),
('REL-AFF', 'Affects', 'يؤثر على', 'Threat/Vulnerability affects an asset');
`

`sql
-- الأصول الحرجة غير المغطاة بضوابط كافية (< 70%)
SELECT 
    asset_name,
    criticality,
    control_coverage,
    risk_score
FROM v_asset_dashboard
WHERE criticality IN ('CRITICAL', 'HIGH')
  AND control_coverage < 70
ORDER BY risk_score DESC;
`

`sql
-- الأصول الأعلى خطراً
SELECT 
    asset_name,
    criticality,
    risk_score,
    open_vulnerabilities,
    critical_vulnerabilities
FROM v_asset_dashboard
WHERE risk_score > 7
ORDER BY risk_score DESC;
`

`sql
-- الأصول الحرجة بدون مراقبة SIEM/EDR
SELECT 
    a.asset_name,
    a.criticality,
    COALESCE(amc.siem_coverage, 0) AS siem,
    COALESCE(amc.edr_coverage, 0) AS edr
FROM enterprise_assets a
LEFT JOIN v_asset_monitoring_coverage amc ON a.id = amc.asset_id
WHERE a.criticality = 'CRITICAL'
  AND (COALESCE(amc.siem_coverage, 0) = 0 OR COALESCE(amc.edr_coverage, 0) = 0);
`

`sql
-- تقرير الامتثال حسب نوع الأصل
SELECT 
    t.name_en AS asset_type,
    COUNT(*) AS total_assets,
    ROUND(AVG(ad.control_coverage), 2) AS avg_control_coverage,
    ROUND(AVG(ad.monitoring_coverage), 2) AS avg_monitoring_coverage,
    ROUND(AVG(ad.overall_compliance_score), 2) AS avg_compliance
FROM enterprise_assets a
JOIN ref_asset_types t ON a.asset_type_code = t.code
JOIN v_asset_dashboard ad ON a.id = ad.asset_id
WHERE a.is_active = 1
GROUP BY t.name_en
ORDER BY avg_compliance ASC;
`


### 2.4. Core Relationship Tables (USACM Standards)
`sql
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
`

`sql
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
`

`sql
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
`

`sql
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
`
`

## 3. Key USACM Constraints
The SQLite schema implements strict `CHECK` constraints based on USACM v2.2.1 and SDT v2.2.1:
- `type` MUST be one of the 22 USACM codes: `ART-REQ`, `ART-OBJ`, `ART-PRI`, `ART-POL`, `ART-STD`, `ART-CTR`, `ART-CTE`, `ART-PRO`, `ART-PRC`, `ART-PRG`, `ART-PLN`, `ART-TSK`, `ART-CFG`, `ART-RUL`, `ART-EVD`, `ART-MET`, `ART-EXC`, `ART-RSK`, `ART-AST`, `ART-THR`, `ART-VUL`, `ART-OWN`.
- `primary_domain` MUST be between `SD-01` and `SD-08`.
- `implementation_status` MUST be mapped to the profile, not the root artifact, ensuring contextual isolation.

These constraints ensure that the application layer (the 8 Engines) always receives perfectly formatted data, eliminating defensive programming overhead in the UI.

