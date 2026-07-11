# -*- coding: utf-8 -*-
"""
Single source of truth for every controlled classification list mentioned in
USACM v2.2.1 (§3 artifact types, §4 controlled code lists, §8 child-table enums)
and SDT v2.2.1 (§5 domains + sub-domains).

Emits:
  - reference/usacm_controlled_lists.json
  - reference/sdt_taxonomy.json
  - migrations/003_reference_data.sql  (ref_code_lists table + seed rows)

Run: python scripts/build_reference_data.py
"""
import io
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REF = os.path.join(ROOT, 'reference')
MIG = os.path.join(ROOT, 'migrations')

# Each list: list_code -> (section, [ (code, name_en, name_ar) ... ])
# name_ar is filled for UI-facing lists; None where the code itself is the label.
USACM = {
    # ---- §3 Artifact Types ----
    'ARTIFACT_TYPE': ('USACM-3', [
        ('ART-REQ', 'Requirement', 'متطلب'),
        ('ART-OBJ', 'Security Objective', 'هدف أمني'),
        ('ART-PRI', 'Security Principle', 'مبدأ أمني'),
        ('ART-POL', 'Security Policy', 'سياسة أمنية'),
        ('ART-STD', 'Security Standard', 'معيار أمني'),
        ('ART-CTR', 'Security Control', 'ضابط أمني'),
        ('ART-CTE', 'Control Enhancement', 'تحسين ضابط'),
        ('ART-PRO', 'Security Process', 'عملية أمنية'),
        ('ART-PRC', 'Security Procedure', 'إجراء أمني'),
        ('ART-PRG', 'Security Program', 'برنامج أمني'),
        ('ART-PLN', 'Security Plan', 'خطة أمنية'),
        ('ART-TSK', 'Task', 'مهمة'),
        ('ART-CFG', 'Technical Configuration', 'إعداد تقني'),
        ('ART-RUL', 'Technical Rule', 'قاعدة فنية'),
        ('ART-EVD', 'Evidence', 'دليل'),
        ('ART-MET', 'Metric/KPI', 'مقياس/مؤشر أداء'),
        ('ART-EXC', 'Security Exception', 'استثناء أمني'),
        ('ART-RSK', 'Security Risk', 'خطر أمني'),
        ('ART-AST', 'Information Asset', 'أصل معلوماتي'),
        ('ART-THR', 'Threat', 'تهديد'),
        ('ART-VUL', 'Vulnerability', 'ثغرة'),
        ('ART-OWN', 'Owner/Role', 'مالك/دور'),
    ]),
    # ---- §4 Controlled Code Lists ----
    'ABSTRACTION_LEVEL': ('USACM-4.1', [
        ('ABS-GOV', 'Governance', 'حوكمة'),
        ('ABS-RIS', 'Risk', 'مخاطر'),
        ('ABS-POL', 'Policy', 'سياسات'),
        ('ABS-CTR', 'Control', 'ضوابط'),
        ('ABS-PRO', 'Procedure', 'إجراءات'),
        ('ABS-TEC', 'Technical', 'تقني'),
        ('ABS-EVM', 'Evidence/Measurement', 'أدلة/قياس'),
    ]),
    'OBLIGATION_SOURCE': ('USACM-4.2', [
        ('SRC-REG', 'Regulatory', 'تنظيمي'),
        ('SRC-LEG', 'Legal', 'قانوني'),
        ('SRC-CON', 'Contractual', 'تعاقدي'),
        ('SRC-STD', 'Standard', 'معياري'),
        ('SRC-INT', 'Internal', 'داخلي'),
        ('SRC-BST', 'Best Practice', 'أفضل ممارسة'),
        ('SRC-RSK', 'Risk-based', 'مبني على المخاطر'),
    ]),
    'OBLIGATION_LEVEL': ('USACM-4.3', [
        ('OBL-MND', 'Mandatory', 'إلزامي'),
        ('OBL-CON', 'Conditional', 'مشروط'),
        ('OBL-REC', 'Recommended', 'موصى به'),
        ('OBL-OPT', 'Optional', 'اختياري'),
    ]),
    'EXCEPTION_STATUS': ('USACM-4.4', [
        ('EXC-NONE', 'None', 'لا يوجد'),
        ('EXC-NOT-APPLICABLE', 'Not Applicable', 'غير منطبق'),
        ('EXC-RISK-ACCEPTED', 'Risk Accepted', 'مقبول مع المخاطرة'),
        ('EXC-DEFERRED', 'Deferred', 'مؤجل'),
        ('EXC-UNAVAILABLE', 'Unavailable', 'غير متاح'),
    ]),
    'GRANULARITY_LEVEL': ('USACM-4.5', [
        ('GRN-HIGH', 'High-level', None),
        ('GRN-MEDIUM', 'Medium', None),
        ('GRN-DETAILED', 'Detailed', None),
        ('GRN-EXECUTABLE', 'Executable', None),
        ('GRN-TECHNICAL', 'Technical', None),
        ('GRN-EVIDENTIARY', 'Evidentiary', None),
        ('GRN-METRIC', 'Metric', None),
    ]),
    'CONTROL_NATURE': ('USACM-4.6', [
        ('NAT-ORG', 'Organizational', 'تنظيمي'),
        ('NAT-HUM', 'Human', 'بشري'),
        ('NAT-PHY', 'Physical', 'مادي'),
        ('NAT-TEC', 'Technical', 'تقني'),
    ]),
    'CONTROL_FUNCTION': ('USACM-4.7', [
        ('FUN-PRE', 'Preventive', 'وقائي'),
        ('FUN-DET', 'Detective', 'كشفي'),
        ('FUN-COR', 'Corrective', 'تصحيحي'),
        ('FUN-REC', 'Recovery', 'استرداد'),
        ('FUN-DRR', 'Deterrent', 'ردعي'),
        ('FUN-COM', 'Compensating', 'تعويضي'),
    ]),
    'TESTABILITY': ('USACM-4.8', [
        ('TST-AUTO', 'Automated', 'آلي'),
        ('TST-MAN', 'Manual', 'يدوي'),
        ('TST-DOC', 'Documentary', 'مستندي'),
        ('TST-INT', 'Interview', 'مقابلة'),
        ('TST-NA', 'Not Testable', 'غير قابل للفحص'),
    ]),
    'IMPLEMENTATION_STATUS': ('USACM-4.9', [
        ('STS-NOT-APPLIED', 'Not Applied', 'غير مطبّق'),
        ('STS-PARTIAL', 'Partial', 'مطبّق جزئياً'),
        ('STS-FULL', 'Full', 'مطبّق كلياً'),
        ('STS-PLANNED', 'Planned', 'مخطّط له'),
        ('STS-NEEDS-IMPROVEMENT', 'Needs Improvement', 'يحتاج تحسيناً'),
    ]),
    'VERIFICATION_STATUS': ('USACM-4.10', [
        ('VER-NOT-VERIFIED', 'Not Verified', 'لم يُتحقق'),
        ('VER-PASS', 'Pass', 'نجح'),
        ('VER-FAIL', 'Fail', 'فشل'),
    ]),
    'EFFECTIVENESS': ('USACM-4.11', [
        ('EFF-LOW', 'Low', 'ضعيفة'),
        ('EFF-MEDIUM', 'Medium', 'متوسطة'),
        ('EFF-HIGH', 'High', 'عالية'),
        ('EFF-UNKNOWN', 'Unknown', 'غير معروفة'),
    ]),
    'PRIORITY': ('USACM-4.12', [
        ('PRI-CRITICAL', 'Critical', 'حرجة'),
        ('PRI-HIGH', 'High', 'عالية'),
        ('PRI-MEDIUM', 'Medium', 'متوسطة'),
        ('PRI-LOW', 'Low', 'منخفضة'),
    ]),
    'RELATIONSHIP_TYPE': ('USACM-4.13', [
        ('REL-DER', 'Derives From', 'مشتق من'),
        ('REL-SAT', 'Satisfies', 'يحقق'),
        ('REL-SUP', 'Supports', 'يدعم'),
        ('REL-SPL', 'Specifies', 'يحدد'),
        ('REL-IMP', 'Implements', 'يطبّق'),
        ('REL-VER', 'Verifies', 'يتحقق من'),
        ('REL-MEA', 'Measures', 'يقيس'),
        ('REL-MIT', 'Mitigates', 'يخفف'),
        ('REL-AFF', 'Affects', 'يؤثر على'),
        ('REL-EXC', 'Exempts', 'يعفي'),
        ('REL-DEP', 'Depends On', 'يعتمد على'),
        ('REL-CNF', 'Conflicts With', 'يتعارض مع'),
    ]),
    'AI_REVIEW_STATUS': ('USACM-4.14', [
        ('AIR-AUTO-ACCEPTED', 'Auto Accepted', 'مقبول آلياً'),
        ('AIR-HUMAN-REVIEW', 'Human Review', 'مراجعة بشرية'),
        ('AIR-HUMAN-APPROVED', 'Human Approved', 'معتمد بشرياً'),
        ('AIR-HUMAN-REJECTED', 'Human Rejected', 'مرفوض بشرياً'),
    ]),
    'REQUIREMENT_TYPE': ('USACM-4.15', [
        ('RQT-GOV', 'Governance', 'حوكمة'),
        ('RQT-REG', 'Regulatory', 'تنظيمي'),
        ('RQT-LEG', 'Legal', 'قانوني'),
        ('RQT-CON', 'Contractual', 'تعاقدي'),
        ('RQT-STD', 'Standard', 'معياري'),
        ('RQT-INT', 'Internal', 'داخلي'),
        ('RQT-RSK', 'Risk-based', 'مبني على المخاطر'),
    ]),
    'MAPPING_STRENGTH': ('USACM-4.16', [
        ('DIRECT', 'Direct', 'مباشر'),
        ('INDIRECT', 'Indirect', 'غير مباشر'),
        ('PARTIAL', 'Partial', 'جزئي'),
        ('INFORMATIVE', 'Informative', 'إرشادي'),
    ]),
    'TAG_TYPE': ('USACM-4.17', [
        ('Technology', 'Technology', 'تقنية'),
        ('Framework', 'Framework', 'إطار'),
        ('Concept', 'Concept', 'مفهوم'),
        ('Context', 'Context', 'سياق'),
        ('Threat', 'Threat', 'تهديد'),
        ('Data', 'Data', 'بيانات'),
        ('Party', 'Party', 'طرف'),
    ]),
    'REVIEW_FREQUENCY': ('USACM-4.18', [
        ('DAILY', 'Daily', 'يومي'),
        ('WEEKLY', 'Weekly', 'أسبوعي'),
        ('MONTHLY', 'Monthly', 'شهري'),
        ('QUARTERLY', 'Quarterly', 'ربع سنوي'),
        ('SEMI-ANNUAL', 'Semi-Annual', 'نصف سنوي'),
        ('ANNUAL', 'Annual', 'سنوي'),
        ('BIENNIAL', 'Biennial', 'كل سنتين'),
        ('AD-HOC', 'Ad-hoc', 'عند الحاجة'),
        ('CONTINUOUS', 'Continuous', 'مستمر'),
    ]),
    'PUBLICATION_STATUS': ('USACM-4.19', [
        ('DRAFT', 'Draft', 'مسودة'),
        ('UNDER_REVIEW', 'Under Review', 'قيد المراجعة'),
        ('APPROVED', 'Approved', 'معتمد'),
        ('PUBLISHED', 'Published', 'منشور'),
        ('DEPRECATED', 'Deprecated', 'مهمَل'),
        ('WITHDRAWN', 'Withdrawn', 'مسحوب'),
    ]),
    'SOURCE_TYPE': ('USACM-4.20', [
        ('DOCUMENT', 'Document', 'مستند'),
        ('SYSTEM', 'System', 'نظام'),
        ('TOOL', 'Tool', 'أداة'),
        ('INTERVIEW', 'Interview', 'مقابلة'),
        ('OBSERVATION', 'Observation', 'ملاحظة'),
        ('STANDARD', 'Standard', 'معيار'),
        ('REGULATION', 'Regulation', 'لائحة'),
    ]),
    # Catalog-level source kind (source_catalogs.source_type) — reflects the
    # Raw_Catalogs source_type values; distinct from the USACM §4.20 SourceType.
    'CATALOG_SOURCE_TYPE': ('SCHEMA-001', [
        ('FRAMEWORK', 'Framework', 'إطار'),
        ('STANDARD', 'Standard', 'معيار'),
        ('THREAT_INTEL', 'Threat Intelligence', 'استخبارات تهديد'),
        ('GUIDELINE', 'Guideline', 'إرشادات'),
        ('POLICY_TEMPLATE', 'Policy Template', 'قالب سياسة'),
        ('REGULATION', 'Regulation', 'لائحة'),
        ('DOCUMENT', 'Document', 'مستند'),
        ('SYSTEM', 'System', 'نظام'),
        ('TOOL', 'Tool', 'أداة'),
    ]),
    'ASSET_TYPE': ('USACM-4.21', [
        ('HARDWARE', 'Hardware', 'أجهزة'),
        ('SOFTWARE', 'Software', 'برمجيات'),
        ('DATA', 'Data', 'بيانات'),
        ('SERVICE', 'Service', 'خدمة'),
        ('FACILITY', 'Facility', 'منشأة'),
        ('PERSONNEL', 'Personnel', 'أفراد'),
        ('NETWORK', 'Network', 'شبكة'),
        ('CLOUD_INSTANCE', 'Cloud Instance', 'نسخة سحابية'),
        ('DOCUMENT', 'Document', 'وثيقة'),
        ('INTELLECTUAL_PROPERTY', 'Intellectual Property', 'ملكية فكرية'),
    ]),
    'MATURITY_LEVEL': ('USACM-4.22', [
        ('INITIAL', 'Initial', 'مبدئي'),
        ('REPEATABLE', 'Repeatable', 'قابل للتكرار'),
        ('DEFINED', 'Defined', 'محدد'),
        ('MANAGED', 'Managed', 'مُدار'),
        ('OPTIMIZED', 'Optimized', 'مُحسَّن'),
    ]),
    'COST_CATEGORY': ('USACM-4.23', [
        ('LOW', 'Low', 'منخفضة'),
        ('MEDIUM', 'Medium', 'متوسطة'),
        ('HIGH', 'High', 'عالية'),
        ('VERY_HIGH', 'Very High', 'عالية جداً'),
    ]),
    'IMPORT_STATUS': ('USACM-4.24', [
        ('NEW', 'New', 'جديد'),
        ('IMPORTED', 'Imported', 'مستورد'),
        ('UPDATED', 'Updated', 'محدّث'),
        ('MERGED', 'Merged', 'مدموج'),
        ('CONFLICT', 'Conflict', 'متعارض'),
        ('REJECTED', 'Rejected', 'مرفوض'),
    ]),
    # ---- §8 child-table enums ----
    'APPLICABILITY_SCOPE_TYPE': ('USACM-8', [
        ('ORGANIZATION_SIZE', 'Organization Size', 'حجم المؤسسة'),
        ('INDUSTRY', 'Industry', 'القطاع'),
        ('GEOGRAPHIC_REGION', 'Geographic Region', 'المنطقة الجغرافية'),
        ('BUSINESS_UNIT', 'Business Unit', 'وحدة العمل'),
        ('ENTITY_TYPE', 'Entity Type', 'نوع الكيان'),
        ('REGULATORY_SCOPE', 'Regulatory Scope', 'النطاق التنظيمي'),
        ('REGULATORY_JURISDICTION', 'Regulatory Jurisdiction', 'الاختصاص التنظيمي'),
        ('EXCLUSION', 'Exclusion', 'استثناء'),
    ]),
    'DEPENDENCY_TYPE': ('USACM-8', [
        ('SYSTEM', 'System', None), ('PLATFORM', 'Platform', None),
        ('VENDOR', 'Vendor', None), ('SKILL', 'Skill', None), ('BUDGET', 'Budget', None),
    ]),
    'DEPENDENCY_STATUS': ('USACM-8', [
        ('AVAILABLE', 'Available', None), ('NOT_AVAILABLE', 'Not Available', None),
        ('PARTIAL', 'Partial', None), ('PLANNED', 'Planned', None),
    ]),
    'VERIFICATION_TOOL_TYPE': ('USACM-8', [
        ('SIEM', 'SIEM', None), ('EDR', 'EDR', None), ('IAM', 'IAM', None),
        ('VULNERABILITY', 'Vulnerability', None), ('CSPM', 'CSPM', None), ('MANUAL', 'Manual', None),
    ]),
    'VERIFICATION_METHOD': ('USACM-8', [
        ('API', 'API', None), ('LOG', 'Log', None), ('REPORT', 'Report', None),
        ('INTERVIEW', 'Interview', None), ('OBSERVATION', 'Observation', None),
    ]),
    'STAKEHOLDER_RESPONSIBILITY': ('USACM-8', [
        ('OWNER', 'Owner', 'مالك'), ('REVIEWER', 'Reviewer', 'مراجع'),
        ('APPROVER', 'Approver', 'معتمِد'), ('CONSULTED', 'Consulted', 'مستشار'),
        ('INFORMED', 'Informed', 'مُبلَّغ'),
    ]),
    'EXTERNAL_REFERENCE_TYPE': ('USACM-8', [
        ('ARTICLE', 'Article', None), ('BLOG', 'Blog', None), ('TOOL', 'Tool', None),
        ('VIDEO', 'Video', None), ('STUDY', 'Study', None), ('BENCHMARK', 'Benchmark', None),
    ]),
    'SELF_ASSESSMENT_STATUS': ('USACM-8', [
        ('NOT_ASSESSED', 'Not Assessed', None), ('IN_PROGRESS', 'In Progress', None),
        ('COMPLETED', 'Completed', None), ('NEEDS_REVIEW', 'Needs Review', None),
    ]),
    'RESOLUTION_STATUS': ('USACM-8', [
        ('PENDING', 'Pending', None), ('RESOLVED', 'Resolved', None),
        ('ACCEPTED', 'Accepted', None), ('REJECTED', 'Rejected', None),
    ]),
}

# SDT v2.2.1 §5 : 8 domains, 40 sub-domains (en from spec, ar translated)
SDT = [
    ('SD-01', 'Governance, Risk & Compliance', 'الحوكمة والمخاطر والامتثال', [
        ('SD-01.01', 'Cybersecurity Strategy & Governance', 'استراتيجية وحوكمة الأمن السيبراني'),
        ('SD-01.02', 'Policies, Standards & Exceptions', 'السياسات والمعايير والاستثناءات'),
        ('SD-01.03', 'Security Risk Management', 'إدارة المخاطر الأمنية'),
        ('SD-01.04', 'Compliance, Audit & Assurance', 'الامتثال والتدقيق والضمان'),
        ('SD-01.05', 'Security Program Management & Metrics', 'إدارة البرنامج الأمني والمقاييس'),
    ]),
    ('SD-02', 'Assets, Data & Privacy', 'الأصول والبيانات والخصوصية', [
        ('SD-02.01', 'Asset Inventory & Management', 'جرد وإدارة الأصول'),
        ('SD-02.02', 'Software & License Management', 'إدارة البرمجيات والتراخيص'),
        ('SD-02.03', 'Data Classification & Ownership', 'تصنيف وملكية البيانات'),
        ('SD-02.04', 'Data Protection & Encryption', 'حماية البيانات والتشفير'),
        ('SD-02.05', 'Privacy, Retention & Disposal', 'الخصوصية والاحتفاظ والإتلاف'),
    ]),
    ('SD-03', 'Identity, Access & Privilege', 'الهوية والوصول والامتياز', [
        ('SD-03.01', 'Identity Lifecycle Management', 'إدارة دورة حياة الهوية'),
        ('SD-03.02', 'Authentication & Credential Management', 'المصادقة وإدارة بيانات الاعتماد'),
        ('SD-03.03', 'Authorization & Access Management', 'التخويل وإدارة الوصول'),
        ('SD-03.04', 'Privileged Access Management', 'إدارة الوصول المتميز'),
        ('SD-03.05', 'Remote & External Access', 'الوصول عن بُعد والخارجي'),
    ]),
    ('SD-04', 'Infrastructure, Network & Cloud', 'البنية التحتية والشبكة والسحابة', [
        ('SD-04.01', 'Network & Communications Security', 'أمن الشبكات والاتصالات'),
        ('SD-04.02', 'Systems, Servers & Endpoint Security', 'أمن الأنظمة والخوادم والأجهزة الطرفية'),
        ('SD-04.03', 'Configuration & Security Hardening', 'الإعداد والتحصين الأمني'),
        ('SD-04.04', 'Cloud & Virtual Platform Security', 'أمن المنصات السحابية والافتراضية'),
        ('SD-04.05', 'Email, Web & Digital Communications', 'البريد والويب والاتصالات الرقمية'),
    ]),
    ('SD-05', 'Applications, Development & Change', 'التطبيقات والتطوير والتغيير', [
        ('SD-05.01', 'Application Security Governance & SDLC', 'حوكمة أمن التطبيقات ودورة حياة التطوير'),
        ('SD-05.02', 'Application & API Security Testing', 'اختبار أمن التطبيقات وواجهات API'),
        ('SD-05.03', 'Code, Components & Software Supply Chain', 'الشيفرة والمكونات وسلسلة توريد البرمجيات'),
        ('SD-05.04', 'Change & Release Management', 'إدارة التغيير والإصدار'),
        ('SD-05.05', 'Database & Critical Application Security', 'أمن قواعد البيانات والتطبيقات الحرجة'),
    ]),
    ('SD-06', 'Detection, Monitoring & Vulnerability', 'الكشف والمراقبة والثغرات', [
        ('SD-06.01', 'Logging & Security Monitoring', 'التسجيل والمراقبة الأمنية'),
        ('SD-06.02', 'Threat Detection & Alerts', 'كشف التهديدات والتنبيهات'),
        ('SD-06.03', 'Vulnerability & Patch Management', 'إدارة الثغرات والتحديثات'),
        ('SD-06.04', 'Security Testing & Assessments', 'الاختبار والتقييم الأمني'),
        ('SD-06.05', 'Threat Intelligence & IoCs', 'استخبارات التهديدات ومؤشرات الاختراق'),
    ]),
    ('SD-07', 'Response, Recovery & Resilience', 'الاستجابة والتعافي والصمود', [
        ('SD-07.01', 'Incident Management', 'إدارة الحوادث'),
        ('SD-07.02', 'Digital Forensics & Evidence', 'التحليل الجنائي الرقمي والأدلة'),
        ('SD-07.03', 'Backup & Restore', 'النسخ الاحتياطي والاستعادة'),
        ('SD-07.04', 'Business Continuity & Disaster Recovery', 'استمرارية الأعمال والتعافي من الكوارث'),
        ('SD-07.05', 'Crisis Management & Communication', 'إدارة الأزمات والتواصل'),
    ]),
    ('SD-08', 'People, Third Parties & Physical', 'الأشخاص والأطراف الثالثة والأمن المادي', [
        ('SD-08.01', 'Awareness, Training & Security Culture', 'التوعية والتدريب وثقافة الأمن'),
        ('SD-08.02', 'HR Security & Employee Lifecycle', 'أمن الموارد البشرية ودورة حياة الموظف'),
        ('SD-08.03', 'Supplier & Third-Party Management', 'إدارة الموردين والأطراف الثالثة'),
        ('SD-08.04', 'Physical & Environmental Security', 'الأمن المادي والبيئي'),
        ('SD-08.05', 'Acceptable Use & Professional Conduct', 'الاستخدام المقبول والسلوك المهني'),
    ]),
]


def sql_str(v):
    if v is None:
        return 'NULL'
    return "'" + v.replace("'", "''") + "'"


def build():
    # ---- JSON: USACM controlled lists ----
    usacm_json = {}
    for list_code, (section, rows) in USACM.items():
        usacm_json[list_code] = {
            'section': section,
            'values': [{'code': c, 'name_en': en, 'name_ar': ar} for (c, en, ar) in rows],
        }
    io.open(os.path.join(REF, 'usacm_controlled_lists.json'), 'w', encoding='utf-8').write(
        json.dumps(usacm_json, ensure_ascii=False, indent=2))

    # ---- JSON: SDT taxonomy (bilingual) ----
    sdt_json = [{
        'code': d, 'name_en': en, 'name_ar': ar,
        'sub_domains': [{'code': sc, 'name_en': sen, 'name_ar': sar} for (sc, sen, sar) in subs],
    } for (d, en, ar, subs) in SDT]
    io.open(os.path.join(REF, 'sdt_taxonomy.json'), 'w', encoding='utf-8').write(
        json.dumps(sdt_json, ensure_ascii=False, indent=2))

    # ---- SQL: 003 reference-data migration (one indexed lookup table per list) ----
    def tname(list_code):
        return 'lk_' + list_code.lower()

    out = []
    out.append("-- ============================================================================")
    out.append("-- SecureGuide — Migration 003: Reference Data (per-list lookup tables)")
    out.append("-- GENERATED by scripts/build_reference_data.py — do not edit by hand.")
    out.append("-- One indexed bilingual lookup table per controlled list mentioned in")
    out.append("-- USACM v2.2.1 (§3,§4,§8) and SDT v2.2.1 (§5). Contents mirror the schema")
    out.append("-- CHECK constraints exactly (see scripts/validate_reference_data.py).")
    out.append("-- ============================================================================")
    out.append("")
    out.append("PRAGMA foreign_keys = ON;")
    out.append("")

    def emit_table(list_code, section, rows):
        tn = tname(list_code)
        out.append(f"-- {list_code} ({section})")
        out.append(f"CREATE TABLE IF NOT EXISTS {tn} (")
        out.append("    code       TEXT PRIMARY KEY,")
        out.append("    name_en    TEXT,")
        out.append("    name_ar    TEXT,")
        out.append("    sort_order INTEGER NOT NULL DEFAULT 0")
        out.append(");")
        out.append(f"CREATE INDEX IF NOT EXISTS idx_{tn}_sort ON {tn}(sort_order);")
        for i, row in enumerate(rows):
            out.append(
                f"INSERT INTO {tn} (code, name_en, name_ar, sort_order) "
                f"VALUES ({sql_str(row[0])}, {sql_str(row[1])}, {sql_str(row[2])}, {i});")
        out.append("")

    for list_code, (section, rows) in USACM.items():
        emit_table(list_code, section, rows)

    # SDT domains
    dom_rows = [(d, en, ar) for (d, en, ar, subs) in SDT]
    emit_table('SDT_DOMAIN', 'SDT-5', dom_rows)

    # SDT sub-domains — dedicated table with FK to the domain lookup
    sub_rows = []
    for (d, en, ar, subs) in SDT:
        for (sc, sen, sar) in subs:
            sub_rows.append((sc, sen, sar, d))
    out.append("-- SDT_SUBDOMAIN (SDT-5.1) — FK domain_code -> lk_sdt_domain(code)")
    out.append("CREATE TABLE IF NOT EXISTS lk_sdt_subdomain (")
    out.append("    code        TEXT PRIMARY KEY,")
    out.append("    name_en     TEXT,")
    out.append("    name_ar     TEXT,")
    out.append("    domain_code TEXT NOT NULL REFERENCES lk_sdt_domain(code),")
    out.append("    sort_order  INTEGER NOT NULL DEFAULT 0,")
    out.append("    CHECK (substr(code,1,5) = domain_code)")
    out.append(");")
    out.append("CREATE INDEX IF NOT EXISTS idx_lk_sdt_subdomain_domain ON lk_sdt_subdomain(domain_code, sort_order);")
    for i, (sc, sen, sar, d) in enumerate(sub_rows):
        out.append(
            "INSERT INTO lk_sdt_subdomain (code, name_en, name_ar, domain_code, sort_order) "
            f"VALUES ({sql_str(sc)}, {sql_str(sen)}, {sql_str(sar)}, {sql_str(d)}, {i});")
    out.append("")

    io.open(os.path.join(MIG, '003_reference_data.sql'), 'w', encoding='utf-8', newline='\n').write("\n".join(out))

    # ---- console summary ----
    total = sum(len(rows) for _, rows in USACM.values()) + len(dom_rows) + len(sub_rows)
    print(f"Lookup tables: {len(USACM) + 2} (USACM/schema lists {len(USACM)} + SDT domain + SDT subdomain)")
    print(f"SDT: {len(dom_rows)} domains, {len(sub_rows)} sub-domains")
    print(f"Total reference rows: {total}")
    print("Wrote: reference/usacm_controlled_lists.json, reference/sdt_taxonomy.json, migrations/003_reference_data.sql")


if __name__ == '__main__':
    build()
