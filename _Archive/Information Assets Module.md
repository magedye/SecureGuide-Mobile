# 🏛️ المقترح الشامل: قسم الأصول المعلوماتية (Information Assets Module)
## الإصدار 1.0 - إضافة معيارية لـ USACM v2.2.0

---

## 📋 أولاً: الإطار المفاهيمي والحاجة

### 1.1 لماذا نحتاج قسم الأصول؟

في النماذج السابقة (USACM v2.2.0)، كان `ART-AST` (Information Asset) مجرد **كيان معزول** يصف الأصل بشكل عام. لكن في الواقع العملي:

| المشكلة | الأثر |
|---------|-------|
| لا يوجد كتالوج مرجعي لأنواع الأصول | كل مؤسسة تصف الأصول بطريقة مختلفة |
| لا يوجد ربط بين الأصل والضوابط | لا يمكن قياس "تغطية الضوابط" |
| لا يوجد ربط بين الأصل والأدوات | لا يمكن قياس "تغطية المراقبة" |
| لا يوجد ربط بين الأصل والمخاطر | لا يمكن حساب "الخطر المتبقي" |
| لا يوجد جرد مؤسسي موحد | كل فريق له قائمة أصول خاصة |

### 1.2 الرؤية الجديدة

> **"الأصل المعلوماتي هو المحور الذي تدور حوله جميع الكيانات الأمنية الأخرى."**

```
                    ┌─────────────────┐
                    │  Information    │
                    │     Asset       │
                    │   (ART-AST)     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐        ┌─────────┐         ┌─────────┐
   │ Threats │        │Controls │         │  Tools  │
   │ (THR)   │        │ (CTR)   │         │  (CFG)  │
   └────┬────┘        └────┬────┘         └────┬────┘
        │                  │                   │
        ▼                  ▼                   ▼
   ┌─────────┐        ┌─────────┐         ┌─────────┐
   │Vulnerab.│        │Evidence │         │ Metrics │
   │ (VUL)   │        │ (EVD)   │         │ (MET)   │
   └─────────┘        └─────────┘         └─────────┘
```

---

## 🗂️ ثانياً: البنية المعمارية (4 طبقات)

```
┌─────────────────────────────────────────────────────────────────┐
│  الطبقة 1: Asset Taxonomy Reference (المرجع المعياري)          │
│  ─────────────────────────────────────────────────────────────  │
│  ● أنواع الأصول (20 نوع من ملف CSV)                            │
│  ● المصنّعون (Vendors)                                          │
│  ● الموديلات/الأنظمة (Models/Systems)                          │
│  ● ثابتة لا تتغير بتغير المؤسسة                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  الطبقة 2: Enterprise Asset Inventory (الجرد المؤسسي)          │
│  ─────────────────────────────────────────────────────────────  │
│  ● الأصول الفعلية في المؤسسة                                   │
│  ● مرتبطة بالطبقة 1 (نوع الأصل)                                │
│  ● خاصة بالمؤسسة (تتغير بتغير البنية)                          │
│  ● تحتوي على: الموقع، المالك، الأهمية، الحالة                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  الطبقة 3: Asset-Artifact Relationships (العلاقات)             │
│  ─────────────────────────────────────────────────────────────  │
│  ● الأصل ←→ الضابط (أي ضابط يحمي أي أصل؟)                     │
│  ● الأصل ←→ الثغرة (أي ثغرة في أي أصل؟)                       │
│  ● الأصل ←→ التهديد (أي تهديد يستهدف أي أصل؟)                 │
│  ● الأصل ←→ الأداة (أي أداة تراقب أي أصل؟)                    │
│  ● الأصل ←→ الدليل (أي دليل يثبت حماية الأصل؟)                │
│  ● الأصل ←→ المؤشر (أي مؤشر يقيس حماية الأصل؟)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  الطبقة 4: Asset Intelligence (الاستخبارات والتحليلات)         │
│  ─────────────────────────────────────────────────────────────  │
│  ● Asset Coverage Score (نسبة تغطية الضوابط)                   │
│  ● Asset Risk Score (درجة الخطر المتبقي)                       │
│  ● Asset Monitoring Score (نسبة تغطية المراقبة)                │
│  ● Asset Compliance Score (نسبة الامتثال)                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ ثالثاً: البنية التقنية (SQLite Schema)

### 3.1 الطبقة الأولى: Asset Taxonomy Reference

```sql
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
```

### 3.2 الطبقة الثانية: Enterprise Asset Inventory

```sql
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
```

### 3.3 الطبقة الثالثة: Asset-Artifact Relationships

```sql
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
```

### 3.4 الطبقة الرابعة: Asset Intelligence (Views)

```sql
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
```

---

## 🔗 رابعاً: التكامل مع USACM v2.2.0 و SDT v2.2.0

### 4.1 تحديث جدول `security_artifacts`

إضافة حقل `protected_asset_id` للربط المباشر:

```sql
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
```

### 4.2 إضافة أنواع علاقات جديدة

```sql
-- إضافة إلى ref_relationship_types
INSERT INTO ref_relationship_types (code, name_en, name_ar, description) VALUES
('REL-PRO', 'Protects', 'يحمي', 'Control protects an asset'),
('REL-MON', 'Monitors', 'يراقب', 'Tool monitors an asset'),
('REL-AFF', 'Affects', 'يؤثر على', 'Threat/Vulnerability affects an asset');
```

### 4.3 الربط مع SDT v2.2.0

| المجال | الصلة بالأصول |
|--------|---------------|
| **SD-02.01** (Asset Inventory) | الجدول `enterprise_assets` هو التطبيق المباشر |
| **SD-02.02** (Software & License) | الأصول من نوع APPLICATION, DATABASE, OS |
| **SD-04.02** (Systems & Endpoints) | الأصول من نوع SERVER_HW, OS, VIRTUAL |
| **SD-04.04** (Cloud) | الأصول من نوع VIRTUAL, STORAGE في Cloud |
| **SD-06.01** (Logging) | جدول `asset_monitoring_tools` مع SIEM |
| **SD-06.03** (Vulnerability) | جدول `asset_vulnerabilities` |
| **SD-06.05** (Threat Intel) | جدول `asset_threats` مع MITRE |

### 4.4 أمثلة على ART-AST محدّث

```json
{
  "id": "AST-DB-PROD-001",
  "type": "ART-AST",
  "title_en": "Production Customer Database",
  "title_ar": "قاعدة بيانات العملاء الإنتاجية",
  "primary_domain": "SD-02",
  "sub_domain": "SD-02.01",
  "asset_type": "SOFTWARE",
  "asset_criticality": "CRITICAL",
  
  // ===== ربط بجدول الأصول =====
  "enterprise_asset_id": "AST-DB-PROD-001",
  "asset_details": {
    "asset_type_code": "DATABASE",
    "vendor_code": "ORCL",
    "model_code": "Oracle Database 19c",
    "version": "19.15",
    "environment": "PRODUCTION",
    "location": "DC1",
    "network_zone": "INTERNAL",
    "data_classification": "RESTRICTED",
    "business_owner": "Head of Customer Service",
    "technical_owner": "DBA Team Lead"
  },
  
  // ===== الإحصائيات المحسوبة =====
  "intelligence": {
    "control_coverage": 85.5,
    "risk_score": 6.8,
    "monitoring_coverage": 92.0,
    "open_vulnerabilities": 3,
    "critical_vulnerabilities": 1,
    "overall_compliance_score": 88.2
  },
  
  // ===== العلاقات =====
  "relationships": [
    {"type": "REL-PRO", "target_id": "CTR-ENC-001", "description": "Encryption protects database"},
    {"type": "REL-PRO", "target_id": "CTR-BKP-001", "description": "Backup protects database"},
    {"type": "REL-MON", "target_id": "CFG-SIEM-001", "description": "SIEM monitors database"},
    {"type": "REL-AFF", "target_id": "THR-RANSOM-001", "description": "Ransomware threatens database"}
  ]
}
```

---

## 🖼️ خامساً: الشاشات الجديدة

### 5.1 شاشة "جرد الأصول" (Asset Inventory)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏛️ جرد الأصول المعلوماتية                              [+ أصل جديد] │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📊 الملخص                                                     │ │
│  │  ┌──────────┬──────────┬──────────┬──────────┬─────────────────┐ │ │
│  │  │  127 أصل │ 🔴 12    │ 🟠 35    │ 🟢 80    │ 📊 78% تغطية  │ │ │
│  │  │  نشط     │ حرج      │ عالي     │ متوسط/منخفض│ الضوابط       │ │ │
│  │  └──────────┴──────────┴──────────┴──────────┴─────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  🔍 البحث...  [فلتر: النوع ▼] [الخطورة ▼] [البيئة ▼]         │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📋 الأصول (127)                                                │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  🔴 AST-DB-PROD-001: قاعدة بيانات العملاء                │ │ │
│  │  │  النوع: Database · المصنّع: Oracle · الإصدار: 19c         │ │ │
│  │  │  الخطورة: 🔴 حرج · البيئة: Production · الموقع: DC1       │ │ │
│  │  │  ───────────────────────────────────────────────────────── │ │ │
│  │  │  ● تغطية الضوابط: 85%  ● المراقبة: 92%  ● الثغرات: 3    │ │ │
│  │  │  ● درجة الخطر: 6.8/10  ● الامتثال: 88%                   │ │ │
│  │  │  [التفاصيل]  [الضوابط]  [الثغرات]  [الأدوات]             │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  🟠 AST-SRV-WEB-005: خادم الويب الرئيسي                  │ │ │
│  │  │  النوع: Server Hardware · Dell R750 · Windows 2022         │ │ │
│  │  │  الخطورة: 🟠 عالي · البيئة: Production · الموقع: DC2      │ │ │
│  │  │  ───────────────────────────────────────────────────────── │ │ │
│  │  │  ● تغطية الضوابط: 70%  ● المراقبة: 85%  ● الثغرات: 5    │ │ │
│  │  │  ● درجة الخطر: 5.2/10  ● الامتثال: 75%                   │ │ │
│  │  │  [التفاصيل]  [الضوابط]  [الثغرات]  [الأدوات]             │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 شاشة "تفاصيل الأصل" (Asset Detail)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🏛️ تفاصيل الأصل: AST-DB-PROD-001                          [تعديل]  │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📋 المعلومات الأساسية                                        │ │
│  │  الاسم: قاعدة بيانات العملاء الإنتاجية                         │ │
│  │  النوع: Database · Oracle 19c · DC1 · Production              │ │
│  │  الخطورة: 🔴 حرج · تصنيف البيانات: RESTRICTED                  │ │
│  │  المالك: DBA Team Lead · مالك الأعمال: Head of Customer Service│ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📊 لوحة الاستخبارات (Intelligence Dashboard)                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  ┌──────────┬──────────┬──────────┬──────────┐             │ │ │
│  │  │  │ تغطية    │ مراقبة   │ درجة     │ امتثال   │             │ │ │
│  │  │  │ الضوابط  │ SIEM/EDR │ الخطر    │ شامل     │             │ │ │
│  │  │  │ 85%      │ 92%      │ 6.8/10   │ 88%      │             │ │ │
│  │  │  │ ■■■■■■■■□□│ ■■■■■■■■■□│ ■■■■■■□□□□│ ■■■■■■■■□□│             │ │ │
│  │  │  └──────────┴──────────┴──────────┴──────────┘             │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  🛡️ الضوابط الحامية (12 ضابطاً)                                │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  ✅ CTR-ENC-001: تشفير البيانات أثناء النقل والتخزين     │ │ │
│  │  │     الحالة: مطبق بالكامل · الفعالية: عالية · آخر اختبار: 2026-07-01│ │ │
│  │  │  ✅ CTR-BKP-001: النسخ الاحتياطي اليومي                  │ │ │
│  │  │     الحالة: مطبق بالكامل · الفعالية: جيدة · آخر اختبار: 2026-07-09│ │ │
│  │  │  ⚠️ CTR-ACC-001: مراجعة صلاحيات الوصول                   │ │ │
│  │  │     الحالة: مطبق جزئياً · الفعالية: متوسطة · يحتاج تحسين │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  🐛 الثغرات المفتوحة (3 ثغرات)                                  │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  🔴 CVE-2026-1234: Critical SQL Injection · CVSS 9.8       │ │ │
│  │  │     الاكتشاف: 2026-07-05 · المعالجة: مطلوبة عاجلاً         │ │ │
│  │  │  🟠 CVE-2026-5678: High Privilege Escalation · CVSS 7.5    │ │ │
│  │  │     الاكتشاف: 2026-07-08 · المعالجة: خلال 15 يوم          │ │ │
│  │  │  🟡 CVE-2026-9012: Medium Information Disclosure · CVSS 5.0│ │ │
│  │  │     الاكتشاف: 2026-07-09 · المعالجة: خلال 30 يوم          │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  🔍 أدوات المراقبة (4 أدوات)                                    │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  ✅ Splunk (SIEM) · نشط · آخر بيانات: قبل 5 دقائق        │ │ │
│  │  │  ✅ CrowdStrike (EDR) · نشط · آخر بيانات: قبل 2 دقيقة    │ │ │
│  │  │  ✅ Oracle Audit Vault · نشط · آخر بيانات: قبل 10 دقائق  │ │ │
│  │  │  ✅ Qualys (VULN) · نشط · آخر فحص: 2026-07-09            │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  [إضافة ضابط]  [تسجيل ثغرة]  [إضافة أداة]  [تصدير التقرير]         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 سادساً: حالات الاستخدام (Use Cases)

### 6.1 تحليل الفجوات (Gap Analysis)

```sql
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
```

### 6.2 تقييم المخاطر (Risk Assessment)

```sql
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
```

### 6.3 تغطية المراقبة (Monitoring Coverage)

```sql
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
```

### 6.4 تقارير الامتثال (Compliance Reports)

```sql
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
```

---

## 🏆 سابعاً: الخلاصة التنفيذية

### 7.1 ملخص الإضافات

| العنصر | العدد | الوصف |
|--------|-------|-------|
| **جداول مرجعية** | 3 | ref_asset_types, ref_asset_vendors, ref_asset_models |
| **جداول الجرد** | 1 | enterprise_assets |
| **جداول العلاقات** | 6 | asset_controls, asset_vulnerabilities, asset_threats, asset_monitoring_tools, asset_evidence, asset_metrics |
| **Views ذكية** | 4 | v_asset_control_coverage, v_asset_risk_score, v_asset_monitoring_coverage, v_asset_dashboard |
| **شاشات جديدة** | 2 | Asset Inventory, Asset Detail |
| **أنواع علاقات جديدة** | 2 | REL-PRO (Protects), REL-MON (Monitors) |

### 7.2 الفوائد الاستراتيجية

| الفائدة | الأثر |
|---------|-------|
| **محور مركزي للأمن** | جميع الكيانات تدور حول الأصل |
| **قياس موضوعي** | تغطية الضوابط، المراقبة، الامتثال |
| **تقارير تنفيذية** | لوحة قيادة شاملة للأصول |
| **تحليل الفجوات** | تحديد الأصول غير المحمية |
| **إدارة المخاطر** | حساب درجة الخطر لكل أصل |
| **التدقيق** | ربط الأدلة بالأصول المباشرة |

### 7.3 القرار النهائي

✅ **اعتماد قسم الأصول المعلوماتية كإضافة معيارية لـ USACM v2.2.0**

**الخطوات التالية:**
1. تنفيذ مخطط SQLite (الطبقات 1-4)
2. استيراد البيانات الأولية من ملف CSV
3. تطوير شاشتي Asset Inventory و Asset Detail
4. ربط الصفحات الأخرى بالأصول (الضوابط، الثغرات، الأدوات)
5. بناء لوحة القيادة التنفيذية للأصول

---

**الشعار النهائي:**
> **"الأصل المعلوماتي هو المحور، والضوابط والأدوات والمخاطر هي المدارات التي تدور حوله."**

🎯 **جاهز للانتقال إلى مرحلة التنفيذ!**