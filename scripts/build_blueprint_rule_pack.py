"""Build the deterministic MVP blueprint rule schema and rule pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "reference"


def action(code: str, key: str, title: str, description: str, phase: str = "IMPLEMENT") -> dict[str, Any]:
    return {"actionCode": code, "semanticKey": key, "title": title, "description": description, "category": "IMPLEMENTATION", "phase": phase, "taskable": True}


def output(code: str, key: str, title: str, description: str) -> dict[str, Any]:
    return {"outputCode": code, "semanticKey": key, "title": title, "description": description}


def evidence(code: str, key: str, title: str, evidence_type: str, description: str, mandatory: bool = False) -> dict[str, Any]:
    return {"evidenceCode": code, "semanticKey": key, "title": title, "evidenceType": evidence_type, "description": description, "mandatory": mandatory}


BASES = {
    "ART-POL": ("POLICY_LIFECYCLE", "سياسة", [action("ACT-POL-DRAFT", "policy.draft", "صياغة السياسة", "تحديد الغرض والنطاق والأدوار والأحكام"), action("ACT-POL-APPROVE", "governance.approval", "اعتماد السياسة", "مراجعة السياسة واعتمادها من الصلاحية المناسبة", "GOVERN")], output("OUT-POL", "policy.document", "وثيقة سياسة معتمدة", "نسخة مضبوطة وقابلة للتتبع"), evidence("EVD-POL-APPROVAL", "approval.record", "سجل الاعتماد", "ATTESTATION", "إثبات المراجعة والاعتماد")),
    "ART-STD": ("STANDARD_BASELINE", "معيار", [action("ACT-STD-DEFINE", "standard.define", "تعريف خط الأساس", "تحديد القواعد والقيم القابلة للقياس"), action("ACT-STD-EXCEPTION", "exception.process", "تحديد مسار الاستثناء", "تعريف الموافقة والمدة والمعالجة للاستثناءات", "GOVERN")], output("OUT-STD", "standard.baseline", "خط أساس معياري", "معيار مضبوط وقابل للاختبار"), evidence("EVD-STD-TEST", "standard.test.result", "نتائج اختبار المعيار", "REPORT", "نتائج موثقة للتحقق من الالتزام")),
    "ART-PRC": ("PROCEDURE_EXECUTION", "إجراء", [action("ACT-PRC-STEPS", "procedure.steps", "تفصيل خطوات الإجراء", "تحديد التسلسل والمسؤوليات والمدخلات والمخرجات"), action("ACT-PRC-EXERCISE", "procedure.exercise", "اختبار قابلية التنفيذ", "تنفيذ تجربة موثقة والتحقق من نقاط التسليم", "VERIFY")], output("OUT-PRC", "procedure.runbook", "دليل إجراء تشغيلي", "خطوات قابلة للتنفيذ وإعادة الإنتاج"), evidence("EVD-PRC-RUN", "execution.record", "سجل تنفيذ", "LOG", "سجل زمني لتنفيذ الإجراء")),
    "ART-CTR": ("CONTROL_IMPLEMENTATION", "ضابط", [action("ACT-CTR-DESIGN", "control.design", "تصميم الضابط", "تحديد النطاق والمالك وآلية العمل"), action("ACT-CTR-OPERATE", "control.operate", "تشغيل الضابط", "تطبيق الضابط ومراقبة انتظام التشغيل")], output("OUT-CTR", "control.implementation", "تنفيذ ضابط موثق", "وصف تنفيذي وحدود ومسؤوليات"), evidence("EVD-CTR-TEST", "control.test.result", "نتيجة اختبار الضابط", "REPORT", "اختبار تصميم وتشغيل الضابط")),
    "ART-REQ": ("REQUIREMENT_SATISFACTION", "متطلب", [action("ACT-REQ-INTERPRET", "requirement.interpret", "تفسير المتطلب", "تحديد النطاق ومعيار القبول والالتزامات"), action("ACT-REQ-TRACE", "requirement.trace", "ربط وسائل الاستيفاء", "تتبع المتطلب إلى السياسات والضوابط والأدلة", "GOVERN")], output("OUT-REQ", "requirement.traceability", "مصفوفة استيفاء", "ربط المتطلب بوسائل الاستيفاء"), evidence("EVD-REQ-MAP", "requirement.mapping", "سجل التتبع", "DOCUMENT", "مصفوفة ربط مع المبررات")),
    "ART-EVD": ("EVIDENCE_MANAGEMENT", "دليل", [action("ACT-EVD-SPEC", "evidence.specify", "تعريف مواصفات الدليل", "تحديد المصدر والمالك والفترة ومعايير القبول"), action("ACT-EVD-PRESERVE", "evidence.preserve", "حفظ سلامة الدليل", "حماية الدليل وتسجيل المصدر والتوقيت والتغييرات")], output("OUT-EVD", "evidence.package", "حزمة أدلة", "أدلة مفهرسة ومؤرخة وقابلة للمراجعة"), evidence("EVD-EVD-INTEGRITY", "evidence.integrity", "سجل سلامة الدليل", "ATTESTATION", "إثبات المنشأ والسلامة")),
    "ART-MET": ("METRIC_LIFECYCLE", "مقياس", [action("ACT-MET-DEFINE", "metric.define", "تعريف المقياس", "تحديد الصيغة والمدخلات والحدود والمالك"), action("ACT-MET-REVIEW", "metric.review", "مراجعة نتائج المقياس", "تحليل الاتجاه واتخاذ إجراء عند تجاوز الحدود", "VERIFY")], output("OUT-MET", "metric.definition", "تعريف مقياس قابل للحساب", "صيغة ومصدر بيانات ودورية وحدود"), evidence("EVD-MET-RESULT", "metric.result", "سجل نتائج المقياس", "REPORT", "نتائج دورية قابلة لإعادة الحساب")),
    "ART-RSK": ("RISK_TREATMENT", "مخاطر", [action("ACT-RSK-ASSESS", "risk.assess", "تقييم المخاطر", "توثيق السيناريو والاحتمال والأثر والمدخلات"), action("ACT-RSK-TREAT", "risk.treat", "اختيار معالجة المخاطر", "تحديد المعالجة والمالك والموعد والمخاطر المتبقية")], output("OUT-RSK", "risk.treatment.plan", "خطة معالجة مخاطر", "قرار معالجة قابل للتتبع"), evidence("EVD-RSK-DECISION", "risk.decision", "سجل قرار المخاطر", "ATTESTATION", "موافقة موثقة على المعالجة والمخاطر المتبقية")),
}


def rule(rule_id: str, stage: str, priority: int, when: dict[str, list[str]], then: dict[str, Any], rationale: str, confidence: float = .9) -> dict[str, Any]:
    return {"ruleId": rule_id, "ruleVersion": "1.0.0", "stage": stage, "priority": priority, "when": when, "then": then, "rationale": rationale, "baseConfidence": confidence}


def build_rules() -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for index, (artifact_type, (plan, label, actions, expected, evd)) in enumerate(BASES.items(), 1):
        rules.append(rule(f"BR-ART-{artifact_type[4:]}", "ARTIFACT_TYPE", index, {"artifactTypes": [artifact_type]}, {"actionPlanType": plan, "titleTemplate": f"خطة {label} معيارية", "actions": actions, "expectedOutputs": [expected], "evidence": [evd], "effortProfiles": [{"semanticKey": f"effort.{artifact_type.lower()}", "effortTypes": ["ANALYSIS", "IMPLEMENTATION", "REVIEW"], "effortLevel": "MEDIUM", "skillRequirements": ["DOMAIN_KNOWLEDGE"], "estimatedComplexity": "MEDIUM", "implementationMode": "INTERNAL"}], "supportingAssets": [{"semanticKey": f"template.{artifact_type.lower()}", "assetType": "CHECKLIST", "title": "قائمة تحقق تنفيذية", "usage": "تهيئة ومراجعة التنفيذ", "availability": "SUGGESTED"}], "suggestedSolutions": [{"semanticKey": f"solution.{artifact_type.lower()}", "solutionType": "PROCESS", "title": "مسار عمل معياري", "description": "مسار محايد تقنيًا لتنظيم التنفيذ والمراجعة", "recommendationLevel": "OPTIONAL", "vendorNeutral": True, "requiresHumanValidation": True, "prerequisites": [], "risks": ["يلزم تكييفه مع سياق المؤسسة"]}]}, f"نوع العنصر {artifact_type} يحدد الهيكل الأساسي للخطة"))

    nature_labels = {"NAT-ORG": ("organizational", "تحديد جهة حوكمة ومالك مسؤول"), "NAT-HUM": ("human", "إدراج التدريب والكفاءة وفصل المهام"), "NAT-PHY": ("physical", "تحديد الموقع والحماية المادية"), "NAT-TEC": ("technical", "تحديد الإعداد التقني والتحقق الآلي أو اليدوي")}
    for index, (code, (key, desc)) in enumerate(nature_labels.items(), 1):
        rules.append(rule(f"BR-NAT-{code[4:]}", "CONTROL_NATURE", index, {"controlNatures": [code]}, {"actions": [action(f"ACT-NAT-{code[4:]}", f"nature.{key}", desc, desc)], "evidence": [evidence(f"EVD-NAT-{code[4:]}", f"nature.{key}.record", f"إثبات تنفيذ {desc}", "DOCUMENT", desc)]}, f"طبيعة التنفيذ {code} تخصص طريقة العمل والأدلة", .88))

    function_labels = {"FUN-PRE": ("prevent", "التحقق من منع الحالة قبل وقوعها"), "FUN-DET": ("detect", "اختبار الاكتشاف والتنبيه ضمن زمن محدد"), "FUN-COR": ("correct", "توثيق التصحيح والتحقق من إزالة السبب"), "FUN-REC": ("recover", "اختبار الاستعادة وقياس أهدافها"), "FUN-DRR": ("deter", "إظهار الردع وتوثيق الإقرار أو التحذير"), "FUN-COM": ("compensate", "توثيق مبرر الضابط التعويضي ومكافأته")}
    for index, (code, (key, desc)) in enumerate(function_labels.items(), 1):
        rules.append(rule(f"BR-FUN-{code[4:]}", "CONTROL_FUNCTION", index, {"controlFunctions": [code]}, {"actions": [action(f"ACT-FUN-{code[4:]}", f"function.{key}", desc, desc, "VERIFY")]}, f"وظيفة الضابط {code} تخصص غرض التحقق", .88))

    domain_labels = {"SD-01": "الحوكمة والمخاطر والامتثال", "SD-02": "الأصول والبيانات والخصوصية", "SD-03": "الهوية والوصول والصلاحيات", "SD-04": "البنية والشبكات والسحابة", "SD-05": "التطبيقات والتطوير والتغيير", "SD-06": "الكشف والمراقبة والثغرات", "SD-07": "الاستجابة والتعافي والمرونة", "SD-08": "الأفراد والأطراف الثالثة والأمن المادي"}
    for index, (code, label) in enumerate(domain_labels.items(), 1):
        rules.append(rule(f"BR-DOM-{code[3:]}", "SECURITY_DOMAIN", index, {"primaryDomains": [code]}, {"actions": [action(f"ACT-DOM-{code[3:]}", f"domain.{code.lower()}.context", f"تكييف الخطة لسياق {label}", "تحديد الأصول والأطراف والحدود ذات الصلة بالمجال")], "evidence": [evidence(f"EVD-DOM-{code[3:]}", f"domain.{code.lower()}.scope", "سجل نطاق المجال", "DOCUMENT", "تحديد نطاق المجال والعناصر المشمولة")]}, f"المجال {code} يضيف سياقًا دون تغيير نوع الخطة", .86))

    obligations = {"OBL-MND": ("mandatory", True, "فرض اعتماد رسمي وتتبع كامل"), "OBL-CON": ("conditional", False, "توثيق شرط الانطباق ونتيجته"), "OBL-REC": ("recommended", False, "توثيق قرار التطبيق أو مبرر عدم الأولوية"), "OBL-OPT": ("optional", False, "تسجيل قرار اختياري خفيف")}
    for index, (code, (key, mandatory, desc)) in enumerate(obligations.items(), 1):
        rules.append(rule(f"BR-OBL-{code[4:]}", "OBLIGATION_LEVEL", index, {"obligationLevels": [code]}, {"actions": [action(f"ACT-OBL-{code[4:]}", f"obligation.{key}", desc, desc, "GOVERN")], "evidence": [evidence(f"EVD-OBL-{code[4:]}", f"obligation.{key}.decision", "سجل قرار الإلزام", "ATTESTATION", desc, mandatory)]}, f"مستوى الإلزام {code} يحدد صرامة التوثيق", .92))
    return rules


def schema() -> dict[str, Any]:
    text = {"type": "string", "minLength": 1}
    string_array = {"type": "array", "items": text}
    def object_array(required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
        return {"type": "array", "items": {"type": "object", "additionalProperties": False, "required": required, "properties": properties}}
    common = {"semanticKey": text, "title": text, "description": text}
    action_schema = object_array(
        ["actionCode", "semanticKey", "title", "description", "category", "phase", "taskable"],
        {**common, "actionCode": text, "category": text, "phase": text, "taskable": {"type": "boolean"}, "inheritSourceCitation": {"type": "boolean"}},
    )
    output_schema = object_array(
        ["outputCode", "semanticKey", "title", "description"],
        {**common, "outputCode": text},
    )
    evidence_schema = object_array(
        ["evidenceCode", "semanticKey", "title", "evidenceType", "description", "mandatory"],
        {**common, "evidenceCode": text, "evidenceType": {"enum": ["DOCUMENT", "SCREENSHOT", "LOG", "REPORT", "CONFIG", "ATTESTATION", "LINK", "OTHER"]}, "mandatory": {"type": "boolean"}, "inheritSourceCitation": {"type": "boolean"}},
    )
    effort_schema = object_array(
        ["semanticKey", "effortTypes", "effortLevel", "skillRequirements", "estimatedComplexity", "implementationMode"],
        {"semanticKey": text, "effortTypes": string_array, "effortLevel": {"enum": ["LOW", "MEDIUM", "HIGH"]}, "skillRequirements": string_array, "estimatedComplexity": {"enum": ["LOW", "MEDIUM", "HIGH"]}, "implementationMode": {"enum": ["INTERNAL", "EXTERNAL", "HYBRID"]}},
    )
    asset_schema = object_array(
        ["semanticKey", "assetType", "title", "usage", "availability"],
        {"semanticKey": text, "assetType": text, "title": text, "usage": text, "availability": text, "templateRef": text},
    )
    solution_schema = object_array(
        ["semanticKey", "solutionType", "title", "description", "recommendationLevel", "vendorNeutral", "requiresHumanValidation", "prerequisites", "risks"],
        {**common, "solutionType": text, "recommendationLevel": {"enum": ["RECOMMENDED", "OPTIONAL", "CONDITIONAL"]}, "vendorNeutral": {"const": True}, "requiresHumanValidation": {"type": "boolean"}, "prerequisites": string_array, "risks": string_array},
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://secureguide.local/schema/blueprint-rule-pack-v1",
        "title": "SecureGuide Blueprint Rule Pack",
        "type": "object",
        "additionalProperties": False,
        "required": ["ruleSetId", "ruleSetVersion", "engineCompatibility", "status", "rules"],
        "properties": {
            "ruleSetId": text, "ruleSetVersion": text, "engineCompatibility": text,
            "status": {"const": "ACTIVE"},
            "rules": {"type": "array", "minItems": 1, "items": {
                "type": "object", "additionalProperties": False,
                "required": ["ruleId", "ruleVersion", "stage", "priority", "when", "then", "rationale", "baseConfidence"],
                "properties": {
                    "ruleId": text, "ruleVersion": text,
                    "stage": {"enum": ["ARTIFACT_TYPE", "CONTROL_NATURE", "CONTROL_FUNCTION", "SECURITY_DOMAIN", "OBLIGATION_LEVEL"]},
                    "priority": {"type": "integer"},
                    "when": {"type": "object", "additionalProperties": False, "minProperties": 1, "properties": {
                        "artifactTypes": string_array, "controlNatures": string_array,
                        "controlFunctions": string_array, "primaryDomains": string_array,
                        "obligationLevels": string_array,
                    }},
                    "then": {"type": "object", "additionalProperties": False, "properties": {
                        "actionPlanType": text, "titleTemplate": text,
                        "actions": action_schema, "expectedOutputs": output_schema,
                        "evidence": evidence_schema, "effortProfiles": effort_schema,
                        "supportingAssets": asset_schema, "suggestedSolutions": solution_schema,
                    }},
                    "rationale": text,
                    "baseConfidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            }},
        },
    }


def build() -> None:
    REFERENCE.mkdir(parents=True, exist_ok=True)
    payload = {"ruleSetId": "secureguide-blueprint-mvp", "ruleSetVersion": "1.0.0", "engineCompatibility": "1.0.0", "status": "ACTIVE", "rules": build_rules()}
    for path, value in ((REFERENCE / "blueprint_rule_schema_v1.json", schema()), (REFERENCE / "blueprint_rules_mvp_v1.json", payload)):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
