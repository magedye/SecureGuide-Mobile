# 🛡️ دمج قائمة الوظائف الأمنية الموحدة في SecureGuide Mobile
## النسخة المُحسَّنة والمنسقة مع USACM v2.2.0 و SDT v2.2.0 و FCAPS+I

---

## 📋 أولاً: التحليل النقدي للمقترح الأصلي

### 1.1 نقاط القوة
- ✅ تغطية شاملة لـ 43 وظيفة أمنية وتشغيلية
- ✅ تصنيف واضح حسب المجال (EDR, SIEM, IAM, إلخ)
- ✅ ربط الوظائف بالضوابط الأمنية
- ✅ اقتراح شاشات واجهة واضحة

### 1.2 نقاط الضعف التي تحتاج تصحيح

| المشكلة | الأثر | الحل |
|---------|-------|------|
| **اقتراح إضافة `ART-TOOL`** | يتعارض مع USACM v2.2.0 المعتمد | الاعتماد على `verification_tools` الموجود |
| **الخلط بين الوظائف والأدوات** | تكرار في البيانات | فصل المفاهيم في جداول منفصلة |
| **عدم الربط بـ FCAPS+I** | فقدان البعد التشغيلي | إضافة حقل `fcapsi_pillar` |
| **عدم الربط بـ SDT v2.2.0** | فقدان التصنيف الموضوعي | ربط المجالات الفرعية |
| **التكرار مع `verification_tools`** | ازدواجية في البيانات | دمج الجداول |

---

## 🎯 ثانياً: الرؤية المُحسَّنة

### 2.1 الفصل بين ثلاثة مفاهيم

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Security Functions (الوظائف الأمنية)                       │
│     ● قدرات مجردة مثل "Antivirus", "Threat Hunting"           │
│     ● مستقلة عن الأدوات والموردين                              │
│     ● مرتبطة بـ FCAPS+I و SDT                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. Security Tools (الأدوات الأمنية)                           │
│     ● منتجات فعلية مثل "Splunk", "CrowdStrike"                │
│     ● تحتوي على وظائف متعددة                                  │
│     ● مرتبطة بـ verification_tools في USACM                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. Security Controls (الضوابط الأمنية)                        │
│     ● ART-CTR في USACM                                         │
│     ● تُنفَّذ عبر الأدوات                                       │
│     ● تغطي وظائف محددة                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 قاعدة الذهب المعمارية

> **"الوظيفة هي 'ماذا' (What)، الأداة هي 'كيف' (How)، والضابط هو 'لماذا' (Why)."**

---

## 🗄️ ثالثاً: البنية التقنية المُحسَّنة

### 3.1 جدول `security_functions` (الوظائف الأمنية)

```sql
CREATE TABLE IF NOT EXISTS security_functions (
    id TEXT PRIMARY KEY,                    -- FUNC-ANTIVIRUS, FUNC-THREAT-HUNTING
    function_code TEXT NOT NULL UNIQUE,     -- ANTIVIRUS, EDR, SIEM, SOAR
    function_name_en TEXT NOT NULL,
    function_name_ar TEXT NOT NULL,
    description_en TEXT,
    description_ar TEXT,
    
    -- ===== التصنيف =====
    fcapsi_pillar TEXT NOT NULL,            -- FAULT, CONFIGURATION, ACCOUNTING, PERFORMANCE, SECURITY, INTELLIGENCE
    primary_domain TEXT NOT NULL,           -- SD-01 إلى SD-08
    sub_domain TEXT NOT NULL,               -- SD-01.01 إلى SD-08.05
    
    -- ===== التصنيف التقني =====
    function_category TEXT NOT NULL,        -- PREVENTION, DETECTION, RESPONSE, MANAGEMENT, GOVERNANCE
    function_level TEXT NOT NULL,           -- ENDPOINT, NETWORK, CLOUD, IDENTITY, DATA, APPLICATION
    
    -- ===== الأهمية =====
    priority TEXT NOT NULL DEFAULT 'PRI-MEDIUM',
    priority_weight INTEGER NOT NULL DEFAULT 4,
    
    -- ===== التغطية =====
    typical_tools_count INTEGER DEFAULT 0,  -- عدد الأدوات النموذجية
    typical_controls_count INTEGER DEFAULT 0,
    
    -- ===== البيانات الوصفية =====
    mitre_techniques TEXT,                  -- JSON array من MITRE ATT&CK
    cis_controls TEXT,                      -- JSON array من CIS Controls
    nist_csf_functions TEXT,                -- JSON array من NIST CSF
    
    -- ===== حالة النظام =====
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    
    -- ===== القيود =====
    CHECK (fcapsi_pillar IN ('FAULT','CONFIGURATION','ACCOUNTING','PERFORMANCE','SECURITY','INTELLIGENCE')),
    CHECK (primary_domain IN ('SD-01','SD-02','SD-03','SD-04','SD-05','SD-06','SD-07','SD-08')),
    CHECK (substr(sub_domain,1,5) = primary_domain),
    CHECK (function_category IN ('PREVENTION','DETECTION','RESPONSE','MANAGEMENT','GOVERNANCE')),
    CHECK (function_level IN ('ENDPOINT','NETWORK','CLOUD','IDENTITY','DATA','APPLICATION','INFRASTRUCTURE')),
    CHECK (priority IN ('PRI-CRITICAL','PRI-HIGH','PRI-MEDIUM','PRI-LOW')),
    CHECK (priority_weight BETWEEN 1 AND 10)
);

-- بيانات أولية (أمثلة)
INSERT INTO security_functions VALUES
('FUNC-ANTIVIRUS', 'ANTIVIRUS', 'Antivirus & Anti-Malware', 'مكافحة الفيروسات والبرمجيات الخبيثة',
 'Real-time protection against viruses, ransomware, and exploits',
 'حماية لحظية ضد الفيروسات وبرامج الفدية والاستغلال',
 'SECURITY', 'SD-04', 'SD-04.02', 'PREVENTION', 'ENDPOINT', 'PRI-CRITICAL', 10, 5, 8,
 '["T1587.001","T1588.001"]', '["7","10"]', '["PR.DS"]'),

('FUNC-EDR', 'EDR', 'Endpoint Detection & Response', 'كشف والاستجابة لنقاط النهاية',
 'Behavioral analysis and threat detection on endpoints',
 'تحليل سلوكي وكشف التهديدات على نقاط النهاية',
 'SECURITY', 'SD-04', 'SD-04.02', 'DETECTION', 'ENDPOINT', 'PRI-CRITICAL', 10, 4, 6,
 '["T1059","T1003"]', '["10"]', '["DE.CM"]'),

('FUNC-SIEM', 'SIEM', 'Security Information & Event Management', 'إدارة معلومات وأحداث الأمن',
 'Log aggregation, correlation, and alerting',
 'جمع السجلات والارتباط والتنبيه',
 'FAULT', 'SD-06', 'SD-06.01', 'DETECTION', 'INFRASTRUCTURE', 'PRI-CRITICAL', 10, 6, 8,
 '["All"]', '["8"]', '["DE.CM","DE.AE"]'),

('FUNC-MFA', 'MFA', 'Multi-Factor Authentication', 'المصادقة متعددة العوامل',
 'Additional authentication factor beyond password',
 'عامل مصادقة إضافي بجانب كلمة المرور',
 'SECURITY', 'SD-03', 'SD-03.02', 'PREVENTION', 'IDENTITY', 'PRI-CRITICAL', 10, 8, 12,
 '["T1110","T1078"]', '["6"]', '["PR.AA"]');

-- فهارس
CREATE INDEX IF NOT EXISTS idx_functions_pillar ON security_functions(fcapsi_pillar);
CREATE INDEX IF NOT EXISTS idx_functions_domain ON security_functions(primary_domain, sub_domain);
CREATE INDEX IF NOT EXISTS idx_functions_category ON security_functions(function_category);
CREATE INDEX IF NOT EXISTS idx_functions_level ON security_functions(function_level);
```

### 3.2 جدول `security_tools` (الأدوات الأمنية)

```sql
CREATE TABLE IF NOT EXISTS security_tools (
    id TEXT PRIMARY KEY,                    -- TOOL-SPLUNK-001, TOOL-CROWDSTRIKE-001
    tool_code TEXT NOT NULL UNIQUE,         -- SPLUNK, CROWDSTRIKE, OKTA
    tool_name_en TEXT NOT NULL,
    tool_name_ar TEXT NOT NULL,
    description_en TEXT,
    description_ar TEXT,
    
    -- ===== التصنيف =====
    tool_category TEXT NOT NULL,            -- EPP, EDR, SIEM, SOAR, IAM, DLP, UTM, CSPM, UEM, GRC
    vendor TEXT NOT NULL,
    version TEXT,
    
    -- ===== نموذج النشر =====
    deployment_model TEXT NOT NULL,         -- CLOUD, ON-PREMISE, HYBRID, SAAS
    
    -- ===== الترخيص والدعم =====
    license_type TEXT,                      -- COMMERCIAL, OPEN_SOURCE, FREEMIium
    support_status TEXT DEFAULT 'ACTIVE',   -- ACTIVE, DEPRECATED, EOL
    support_expiry_date TEXT,
    
    -- ===== التوثيق =====
    documentation_url TEXT,
    official_website TEXT,
    
    -- ===== التكامل =====
    api_available INTEGER DEFAULT 0,
    siem_integration INTEGER DEFAULT 0,
    soar_integration INTEGER DEFAULT 0,
    
    -- ===== البيانات الوصفية =====
    primary_domain TEXT NOT NULL,
    sub_domain TEXT NOT NULL,
    typical_functions_count INTEGER DEFAULT 0,
    
    -- ===== حالة النظام =====
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    
    -- ===== القيود =====
    FOREIGN KEY (primary_domain) REFERENCES security_functions(primary_domain),
    CHECK (tool_category IN ('EPP','EDR','SIEM','SOAR','IAM','DLP','UTM','CSPM','UEM','GRC','PAM','MDM','OTHER')),
    CHECK (deployment_model IN ('CLOUD','ON-PREMISE','HYBRID','SAAS')),
    CHECK (license_type IS NULL OR license_type IN ('COMMERCIAL','OPEN_SOURCE','FREEMIUM')),
    CHECK (support_status IN ('ACTIVE','DEPRECATED','EOL'))
);

-- بيانات أولية (أمثلة)
INSERT INTO security_tools VALUES
('TOOL-SPLUNK-001', 'SPLUNK', 'Splunk Enterprise Security', 'سبلنك إنتربرايز سيكيوريتي',
 'SIEM platform for security monitoring and threat detection',
 'منصة SIEM للمراقبة الأمنية وكشف التهديدات',
 'SIEM', 'Splunk', '9.1', 'HYBRID', 'COMMERCIAL', 'ACTIVE', NULL,
 'https://docs.splunk.com', 'https://splunk.com', 1, 1, 1, 'SD-06', 'SD-06.01', 8),

('TOOL-CROWDSTRIKE-001', 'CROWDSTRIKE', 'CrowdStrike Falcon', 'كراود سترايك فالكون',
 'Cloud-native EDR platform with threat intelligence',
 'منصة EDR سحابية مع استخبارات التهديدات',
 'EDR', 'CrowdStrike', '7.0', 'CLOUD', 'COMMERCIAL', 'ACTIVE', NULL,
 'https://crowdstrike.com', 'https://crowdstrike.com', 1, 1, 1, 'SD-04', 'SD-04.02', 6),

('TOOL-OKTA-001', 'OKTA', 'Okta Identity Cloud', 'أوكता هوية سحابية',
 'Identity and access management platform',
 'منصة إدارة الهوية والوصول',
 'IAM', 'Okta', '2024', 'SAAS', 'COMMERCIAL', 'ACTIVE', NULL,
 'https://okta.com', 'https://okta.com', 1, 1, 1, 'SD-03', 'SD-03.02', 5);

-- فهارس
CREATE INDEX IF NOT EXISTS idx_tools_category ON security_tools(tool_category);
CREATE INDEX IF NOT EXISTS idx_tools_vendor ON security_tools(vendor);
CREATE INDEX IF NOT EXISTS idx_tools_deployment ON security_tools(deployment_model);
CREATE INDEX IF NOT EXISTS idx_tools_domain ON security_tools(primary_domain, sub_domain);
```

### 3.3 جدول `tool_function_coverage` (تغطية الوظائف بالأدوات)

```sql
CREATE TABLE IF NOT EXISTS tool_function_coverage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id TEXT NOT NULL,
    function_id TEXT NOT NULL,
    
    -- ===== مستوى التغطية =====
    coverage_level TEXT NOT NULL,           -- FULL, PARTIAL, NONE
    coverage_percentage REAL DEFAULT 100,   -- 0-100
    
    -- ===== التفاصيل =====
    capability_description TEXT,
    implementation_notes TEXT,
    
    -- ===== الترخيص =====
    requires_addon INTEGER DEFAULT 0,       -- هل يتطلب إضافة؟
    addon_name TEXT,
    license_tier TEXT,                      -- BASIC, STANDARD, PREMIUM, ENTERPRISE
    
    -- ===== البيانات الوصفية =====
    last_verified TEXT,
    verified_by TEXT,
    
    -- ===== القيود =====
    FOREIGN KEY (tool_id) REFERENCES security_tools(id) ON DELETE CASCADE,
    FOREIGN KEY (function_id) REFERENCES security_functions(id) ON DELETE CASCADE,
    UNIQUE(tool_id, function_id),
    CHECK (coverage_level IN ('FULL','PARTIAL','NONE')),
    CHECK (coverage_percentage BETWEEN 0 AND 100),
    CHECK (license_tier IS NULL OR license_tier IN ('BASIC','STANDARD','PREMIUM','ENTERPRISE'))
);

-- بيانات أولية (أمثلة)
INSERT INTO tool_function_coverage VALUES
(1, 'TOOL-SPLUNK-001', 'FUNC-SIEM', 'FULL', 100, 'Native SIEM capabilities', NULL, 0, NULL, 'ENTERPRISE', '2026-07-10', 'System'),
(2, 'TOOL-SPLUNK-001', 'FUNC-SOAR', 'FULL', 95, 'SOAR playbooks included', NULL, 0, NULL, 'ENTERPRISE', '2026-07-10', 'System'),
(3, 'TOOL-CROWDSTRIKE-001', 'FUNC-EDR', 'FULL', 100, 'Core EDR functionality', NULL, 0, NULL, 'STANDARD', '2026-07-10', 'System'),
(4, 'TOOL-CROWDSTRIKE-001', 'FUNC-THREAT-HUNTING', 'FULL', 90, 'Falcon Discover add-on', 1, 'Falcon Discover', 'PREMIUM', '2026-07-10', 'System');

-- فهارس
CREATE INDEX IF NOT EXISTS idx_coverage_tool ON tool_function_coverage(tool_id);
CREATE INDEX IF NOT EXISTS idx_coverage_function ON tool_function_coverage(function_id);
CREATE INDEX IF NOT EXISTS idx_coverage_level ON tool_function_coverage(coverage_level);
```

### 3.4 جدول `control_function_mapping` (ربط الضوابط بالوظائف)

```sql
CREATE TABLE IF NOT EXISTS control_function_mapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    control_artifact_id TEXT NOT NULL,      -- ربط بـ ART-CTR
    function_id TEXT NOT NULL,
    
    -- ===== مستوى المساهمة =====
    contribution_level TEXT NOT NULL,       -- PRIMARY, SECONDARY, SUPPORTIVE
    contribution_percentage REAL DEFAULT 100,
    
    -- ===== التفاصيل =====
    implementation_notes TEXT,
    
    -- ===== القيود =====
    FOREIGN KEY (control_artifact_id) REFERENCES security_artifacts(id) ON DELETE CASCADE,
    FOREIGN KEY (function_id) REFERENCES security_functions(id) ON DELETE CASCADE,
    UNIQUE(control_artifact_id, function_id),
    CHECK (contribution_level IN ('PRIMARY','SECONDARY','SUPPORTIVE')),
    CHECK (contribution_percentage BETWEEN 0 AND 100)
);

-- فهارس
CREATE INDEX IF NOT EXISTS idx_mapping_control ON control_function_mapping(control_artifact_id);
CREATE INDEX IF NOT EXISTS idx_mapping_function ON control_function_mapping(function_id);
```

### 3.5 تحديث جدول `verification_tools` (الربط مع ART-TOOL)

```sql
-- إضافة عمود الربط مع security_tools
ALTER TABLE verification_tools ADD COLUMN security_tool_id TEXT;
ALTER TABLE verification_tools ADD FOREIGN KEY (security_tool_id) REFERENCES security_tools(id);

-- إضافة عمود الربط مع security_functions
ALTER TABLE verification_tools ADD COLUMN function_id TEXT;
ALTER TABLE verification_tools ADD FOREIGN KEY (function_id) REFERENCES security_functions(id);
```

---

## 📊 رابعاً: البيانات الأولية (43 وظيفة)

### 4.1 Endpoint Prevention & EDR (10 وظائف)

| Code | Function | FCAPS+I | SDT Domain | Priority |
|------|----------|---------|------------|----------|
| ANTIVIRUS | Antivirus & Anti-Malware | SECURITY | SD-04.02 | CRITICAL |
| HOST-FW | Host Firewall | SECURITY | SD-04.02 | HIGH |
| DEVICE-CTRL | Device Control | SECURITY | SD-04.02 | HIGH |
| DLP | Data Loss Prevention | SECURITY | SD-02.04 | HIGH |
| BEHAVIORAL | Advanced Behavioral Analysis | SECURITY | SD-04.02 | HIGH |
| EDR | Endpoint Detection & Response | SECURITY | SD-04.02 | CRITICAL |
| ENCRYPTION | Disk Encryption (BitLocker) | SECURITY | SD-02.04 | HIGH |
| APP-CTRL | Application Control | SECURITY | SD-04.02 | MEDIUM |
| MDM | Mobile Device Management | CONFIGURATION | SD-04.02 | MEDIUM |
| PATCH-AGENT | Patch Management Agent | CONFIGURATION | SD-06.03 | HIGH |

### 4.2 Threat Hunting & Response (6 وظائف)

| Code | Function | FCAPS+I | SDT Domain | Priority |
|------|----------|---------|------------|----------|
| THREAT-HUNT | Threat Hunting | INTELLIGENCE | SD-06.05 | HIGH |
| SOAR | Security Orchestration & Response | FAULT | SD-07.01 | HIGH |
| FORENSICS | Digital Forensics | FAULT | SD-07.02 | MEDIUM |
| YARA | YARA Rules Execution | INTELLIGENCE | SD-06.05 | MEDIUM |
| SIGMA | SIGMA Rules Conversion | INTELLIGENCE | SD-06.05 | MEDIUM |
| IOC-SCAN | IOC Scanning | INTELLIGENCE | SD-06.05 | HIGH |

### 4.3 SIEM & Monitoring (6 وظائف)

| Code | Function | FCAPS+I | SDT Domain | Priority |
|------|----------|---------|------------|----------|
| SIEM | Security Information & Event Management | FAULT | SD-06.01 | CRITICAL |
| LOG-AGG | Log Aggregation | FAULT | SD-06.01 | HIGH |
| CORRELATION | Event Correlation | FAULT | SD-06.01 | HIGH |
| ALERTING | Alert Management | FAULT | SD-06.02 | HIGH |
| DASHBOARD | Security Dashboards | INTELLIGENCE | SD-01.05 | MEDIUM |
| UEBA | User & Entity Behavior Analytics | INTELLIGENCE | SD-06.02 | MEDIUM |

### 4.4 System Management (6 وظائف)

| Code | Function | FCAPS+I | SDT Domain | Priority |
|------|----------|---------|------------|----------|
| SW-DEPLOY | Software Deployment | CONFIGURATION | SD-05.04 | MEDIUM |
| SCRIPT-EXEC | Script Execution | CONFIGURATION | SD-05.04 | MEDIUM |
| REMOTE-CTRL | Remote Control | CONFIGURATION | SD-04.02 | MEDIUM |
| ASSET-MGMT | Asset Management | ACCOUNTING | SD-02.01 | HIGH |
| COMPLIANCE | Compliance & Configuration | CONFIGURATION | SD-04.03 | HIGH |
| INVENTORY | Hardware/Software Inventory | ACCOUNTING | SD-02.01 | HIGH |

### 4.5 Identity & Access (5 وظائف)

| Code | Function | FCAPS+I | SDT Domain | Priority |
|------|----------|---------|------------|----------|
| MFA | Multi-Factor Authentication | SECURITY | SD-03.02 | CRITICAL |
| SSO | Single Sign-On | SECURITY | SD-03.02 | HIGH |
| PAM | Privileged Access Management | SECURITY | SD-03.04 | CRITICAL |
| IAM-LIFECYCLE | Identity Lifecycle Management | SECURITY | SD-03.01 | HIGH |
| ACCESS-REVIEW | Access Recertification | SECURITY | SD-03.03 | HIGH |

### 4.6 Network & Infrastructure (5 وظائف)

| Code | Function | FCAPS+I | SDT Domain | Priority |
|------|----------|---------|------------|----------|
| FIREWALL | Network Firewall | SECURITY | SD-04.01 | CRITICAL |
| IDS-IPS | Intrusion Detection/Prevention | SECURITY | SD-04.01 | HIGH |
| VPN | Virtual Private Network | SECURITY | SD-03.05 | HIGH |
| DNS-SEC | DNS Security | SECURITY | SD-04.01 | MEDIUM |
| WEB-FILTER | Web Filtering | SECURITY | SD-04.05 | MEDIUM |

### 4.7 Cloud & Virtualization (3 وظائف)

| Code | Function | FCAPS+I | SDT Domain | Priority |
|------|----------|---------|------------|----------|
| CSPM | Cloud Security Posture Management | SECURITY | SD-04.04 | HIGH |
| CWPP | Cloud Workload Protection | SECURITY | SD-04.04 | HIGH |
| CONTAINER-SEC | Container Security | SECURITY | SD-04.04 | MEDIUM |

### 4.8 GRC & Compliance (2 وظائف)

| Code | Function | FCAPS+I | SDT Domain | Priority |
|------|----------|---------|------------|----------|
| RISK-ANALYSIS | Risk Analysis & Assessment | INTELLIGENCE | SD-01.03 | HIGH |
| COMPLIANCE-MAP | Compliance Mapping | ACCOUNTING | SD-01.04 | MEDIUM |

---

## 🖼️ خامساً: الشاشات المُحسَّنة

### 5.1 صفحة تفاصيل الضابط - تبويب "الوظائف والأدوات"

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🔐 MFA للحسابات الإدارية                                              │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📋 الوظائف الأمنية المرتبطة                                    │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  ● MFA (المصادقة متعددة العوامل)                          │ │ │
│  │  │    → المساهمة: PRIMARY (100%)                               │ │ │
│  │  │    → FCAPS+I: SECURITY · SDT: SD-03.02                     │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  🛠️ الأدوات الموصى بها (8 أدوات)                               │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  ✅ Microsoft Entra ID (Azure AD)                           │ │ │
│  │  │     → التغطية: MFA (100%), SSO (95%), IAM (90%)            │ │ │
│  │  │     → الحالة: ✅ مفعل · التكامل: متكامل                    │ │ │
│  │  ├─────────────────────────────────────────────────────────────┤ │ │
│  │  │  ✅ Okta Identity Cloud                                     │ │ │
│  │  │     → التغطية: MFA (100%), SSO (100%), PAM (85%)           │ │ │
│  │  │     → الحالة: ✅ مفعل · التكامل: متكامل                    │ │ │
│  │  ├─────────────────────────────────────────────────────────────┤ │ │
│  │  │  ⏳ Duo Security                                            │ │ │
│  │  │     → التغطية: MFA (100%)                                   │ │ │
│  │  │     → الحالة: ⏳ قيد التقييم                                │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │  [عرض جميع الأدوات]  [مقارنة الأدوات]                          │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 صفحة "كتالوج الوظائف الأمنية" (جديدة)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🎯 كتالوج الوظائف الأمنية (43 وظيفة)                                 │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  [🔍 البحث...]  [FCAPS+I: الكل ▼]  [SDT: الكل ▼]              │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  🛡️ SECURITY (18 وظيفة)                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  ● ANTIVIRUS · مكافحة الفيروسات                            │ │ │
│  │  │    SD-04.02 · ENDPOINT · 🔴 CRITICAL · 5 أدوات            │ │ │
│  │  │  ● EDR · كشف والاستجابة                                   │ │ │
│  │  │    SD-04.02 · ENDPOINT · 🔴 CRITICAL · 4 أدوات            │ │ │
│  │  │  ● MFA · المصادقة متعددة العوامل                          │ │ │
│  │  │    SD-03.02 · IDENTITY · 🔴 CRITICAL · 8 أدوات            │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  🔧 FAULT (8 وظائف)                                             │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  ● SIEM · إدارة معلومات الأمن                              │ │ │
│  │  │    SD-06.01 · INFRASTRUCTURE · 🔴 CRITICAL · 6 أدوات      │ │ │
│  │  │  ● SOAR · الأتمتة والاستجابة                              │ │ │
│  │  │    SD-07.01 · INFRASTRUCTURE · 🟠 HIGH · 5 أدوات          │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  ⚙️ CONFIGURATION (6 وظائف)                                     │ │
│  │  📊 ACCOUNTING (4 وظائف)                                        │ │
│  │  📈 PERFORMANCE (3 وظائف)                                       │ │
│  │  🧠 INTELLIGENCE (4 وظائف)                                      │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.3 صفحة "كتالوج الأدوات الأمنية" (جديدة)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🛠️ كتالوج الأدوات الأمنية (18 أداة)                                  │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  [🔍 البحث...]  [التصنيف: الكل ▼]  [النشر: الكل ▼]            │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📊 SIEM Tools (6 أدوات)                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  ✅ Splunk Enterprise Security                             │ │ │
│  │  │     · SIEM · Hybrid · Commercial                           │ │ │
│  │  │     · الوظائف: SIEM, SOAR, LOG-AGG, CORRELATION (8)       │ │ │
│  │  │     · SDT: SD-06.01 · FCAPS+I: FAULT                       │ │ │
│  │  ├─────────────────────────────────────────────────────────────┤ │ │
│  │  │  ✅ Microsoft Sentinel                                     │ │ │
│  │  │     · SIEM · Cloud · Commercial                            │ │ │
│  │  │     · الوظائف: SIEM, SOAR, UEBA (6)                       │ │ │
│  │  │     · SDT: SD-06.01 · FCAPS+I: FAULT                       │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  🛡️ EDR Tools (4 أدوات)                                         │ │
│  │  ☁️ IAM Tools (3 أدوات)                                         │ │
│  │  🔒 DLP Tools (2 أدوات)                                         │ │
│  │  🌐 UTM Tools (3 أدوات)                                         │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.4 صفحة "مقارنة الأدوات" (جديدة)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📊 مقارنة الأدوات                                                    │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  اختر أدوات للمقارنة:                                            │ │
│  │  [✓] Splunk  [✓] Sentinel  [✓] QRadar  [ ] ELK                 │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📋 مقارنة الوظائف                                               │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  الوظيفة          │ Splunk │ Sentinel │ QRadar             │ │ │
│  │  ├─────────────────────────────────────────────────────────────┤ │ │
│  │  │  SIEM             │ ✅ 100% │ ✅ 100%  │ ✅ 100%           │ │ │
│  │  │  SOAR             │ ✅ 95%  │ ✅ 90%   │ 🟨 70%            │ │ │
│  │  │  LOG-AGG          │ ✅ 100% │ ✅ 100%  │ ✅ 100%           │ │ │
│  │  │  CORRELATION      │ ✅ 95%  │ ✅ 90%   │ ✅ 95%            │ │ │
│  │  │  UEBA             │ 🟨 70%  │ ✅ 85%   │ ✅ 90%            │ │ │
│  │  │  THREAT-INTEL     │ ✅ 90%  │ ✅ 95%   │ 🟨 75%            │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  📊 التغطية الإجمالية                                           │ │
│  │  ● Splunk: 92%  ·  Sentinel: 94%  ·  QRadar: 88%              │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 سادساً: ملخص التغييرات المطلوبة

### 6.1 التحديثات في USACM v2.2.0

| التغيير | النوع | الأولوية |
|---------|-------|----------|
| **عدم إضافة ART-TOOL** | قرار معماري | ✅ معتمد |
| تحديث `verification_tools` بربط `security_tool_id` | تحديث جدول | عالية |
| إضافة حقل `function_id` في `verification_tools` | تحديث جدول | عالية |

### 6.2 الجداول الجديدة

| الجدول | الوصف | الأولوية |
|--------|-------|----------|
| `security_functions` | 43 وظيفة أمنية | 🔴 حرجة |
| `security_tools` | 18 أداة أمنية | 🔴 حرجة |
| `tool_function_coverage` | تغطية الوظائف بالأدوات | 🔴 حرجة |
| `control_function_mapping` | ربط الضوابط بالوظائف | 🟠 عالية |

### 6.3 الشاشات الجديدة

| الشاشة | الوصف | الأولوية |
|--------|-------|----------|
| كتالوج الوظائف الأمنية | عرض 43 وظيفة | 🟠 عالية |
| كتالوج الأدوات الأمنية | عرض 18 أداة | 🟠 عالية |
| مقارنة الأدوات | مقارنة بين الأدوات | 🟡 متوسطة |
| تبويب "الوظائف والأدوات" في تفاصيل الضابط | ربط الضابط بالوظائف | 🔴 حرجة |

---

## 🏆 سابعاً: الخلاصة التنفيذية

### 7.1 الفوائد المعمارية

| الفائدة | الأثر |
|---------|-------|
| **الاتساق مع USACM v2.2.0** | عدم إضافة أنواع كيانات جديدة |
| **الاتساق مع SDT v2.2.0** | ربط الوظائف بالمجالات الفرعية |
| **الاتساق مع FCAPS+I** | ربط الوظائف بالركائز الست |
| **فصل المفاهيم** | وظائف ≠ أدوات ≠ ضوابط |
| **قابلية التوسع** | إضافة وظائف وأدوات جديدة بسهولة |
| **التحليل المتقدم** | مقارنة الأدوات، تحليل الفجوات |

### 7.2 القرار النهائي

✅ **اعتماد هذا المقترح المُحسَّن كمرجع نهائي لدمج الوظائف الأمنية**

### 7.3 الخطوات التالية

1. **الأسبوع 1**: تنفيذ جداول `security_functions` و `security_tools`
2. **الأسبوع 2**: تنفيذ جداول `tool_function_coverage` و `control_function_mapping`
3. **الأسبوع 3**: استيراد البيانات الأولية (43 وظيفة + 18 أداة)
4. **الأسبوع 4**: تطوير الشاشات الجديدة
5. **الأسبوع 5**: الاختبار والتحسين

---

**الشعار النهائي:**
> **"الوظيفة هي 'ماذا'، الأداة هي 'كيف'، والضابط هو 'لماذا' - مع الاتساق الكامل لـ USACM و SDT و FCAPS+I."**

🎯 **جاهز للانتقال إلى مرحلة التنفيذ!**
