"""Build a non-authoritative operational-pattern library from the supplied TSV."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "reference" / "operational_patterns_v1.json"
SCHEMA_OUTPUT = ROOT / "reference" / "operational_pattern_schema_v1.json"


# Explicit human-reviewed primary classification. Compound rows are flagged
# separately; this mapping never creates Master Catalog artifacts.
CLASSIFICATION = {
    1:("ART-CTR","SD-04","SD-04.01","NAT-TEC","FUN-PRE"), 2:("ART-CTR","SD-04","SD-04.01","NAT-TEC","FUN-PRE"),
    3:("ART-CTR","SD-04","SD-04.05","NAT-TEC","FUN-PRE"), 4:("ART-CTR","SD-03","SD-03.05","NAT-TEC","FUN-PRE"),
    5:("ART-CFG","SD-04","SD-04.03",None,None), 6:("ART-CTR","SD-04","SD-04.01","NAT-TEC","FUN-PRE"),
    7:("ART-CTR","SD-06","SD-06.02","NAT-TEC","FUN-DET"), 8:("ART-PRO","SD-06","SD-06.02",None,None),
    9:("ART-CTR","SD-06","SD-06.01","NAT-TEC","FUN-DET"), 10:("ART-CTR","SD-06","SD-06.02","NAT-TEC","FUN-DET"),
    11:("ART-REQ","SD-02","SD-02.04",None,None), 12:("ART-CTR","SD-03","SD-03.04","NAT-TEC","FUN-PRE"),
    13:("ART-CTR","SD-03","SD-03.02","NAT-TEC","FUN-PRE"), 14:("ART-PRO","SD-04","SD-04.02",None,None),
    15:("ART-CTR","SD-06","SD-06.02","NAT-TEC","FUN-DET"), 16:("ART-CTR","SD-02","SD-02.04","NAT-TEC","FUN-PRE"),
    17:("ART-CTR","SD-02","SD-02.04","NAT-TEC","FUN-PRE"), 18:("ART-REQ","SD-08","SD-08.05",None,None),
    19:("ART-CTR","SD-03","SD-03.04","NAT-TEC","FUN-PRE"), 20:("ART-STD","SD-04","SD-04.03",None,None),
    21:("ART-STD","SD-02","SD-02.04",None,None), 22:("ART-PRC","SD-07","SD-07.01",None,None),
    23:("ART-PRO","SD-03","SD-03.01",None,None), 24:("ART-STD","SD-03","SD-03.02",None,None),
    25:("ART-CFG","SD-03","SD-03.02",None,None), 26:("ART-CTR","SD-03","SD-03.02","NAT-TEC","FUN-PRE"),
    27:("ART-STD","SD-03","SD-03.04",None,None), 28:("ART-CTR","SD-03","SD-03.04","NAT-TEC","FUN-PRE"),
    29:("ART-PRO","SD-03","SD-03.01",None,None), 30:("ART-STD","SD-03","SD-03.03",None,None),
    31:("ART-PRC","SD-03","SD-03.04",None,None), 32:("ART-PRO","SD-03","SD-03.05",None,None),
    33:("ART-PRO","SD-04","SD-04.03",None,None), 34:("ART-STD","SD-06","SD-06.01",None,None),
    35:("ART-CFG","SD-04","SD-04.03",None,None), 36:("ART-CFG","SD-04","SD-04.03",None,None),
    37:("ART-CFG","SD-04","SD-04.03",None,None), 38:("ART-STD","SD-03","SD-03.05",None,None),
    39:("ART-CTR","SD-04","SD-04.02","NAT-TEC","FUN-PRE"), 40:("ART-CFG","SD-04","SD-04.03",None,None),
    41:("ART-CTR","SD-04","SD-04.01","NAT-TEC","FUN-PRE"), 42:("ART-PRO","SD-07","SD-07.04",None,None),
    43:("ART-PRO","SD-06","SD-06.03",None,None), 44:("ART-CTR","SD-04","SD-04.02","NAT-TEC","FUN-PRE"),
    45:("ART-PRG","SD-01","SD-01.04",None,None), 46:("ART-PRO","SD-08","SD-08.03",None,None),
    47:("ART-PRO","SD-01","SD-01.04",None,None), 48:("ART-PRG","SD-08","SD-08.01",None,None),
    49:("ART-REQ","SD-01","SD-01.01",None,None), 50:("ART-PRO","SD-07","SD-07.01",None,None),
    51:("ART-PLN","SD-01","SD-01.01",None,None), 52:("ART-POL","SD-01","SD-01.02",None,None),
    53:("ART-PRC","SD-07","SD-07.01",None,None), 54:("ART-PRC","SD-07","SD-07.01",None,None),
    55:("ART-CFG","SD-04","SD-04.03",None,None), 56:("ART-PRC","SD-07","SD-07.02",None,None),
    57:("ART-PRC","SD-07","SD-07.01",None,None), 58:("ART-PRC","SD-03","SD-03.02",None,None),
    59:("ART-CFG","SD-04","SD-04.03",None,None),
}

SPLIT_REQUIRED = {11,18,21,23,24,32,42,43,45,46,50,51}
CHANGE_SAFETY = {35,36,37,39,40,41,55,59}
INCIDENT_SAFETY = {22,53,54,56,57,58}
REQUIREMENT_TYPES = {11: "RQT-INT", 18: "RQT-INT", 49: "RQT-GOV"}

ARTIFACT_TYPE_LABELS = {
    "ART-CTR": "ضابط أمني", "ART-PRO": "عملية أمنية", "ART-CFG": "إعداد تقني",
    "ART-STD": "معيار أمني", "ART-PRC": "إجراء أمني", "ART-REQ": "متطلب أمني",
    "ART-PRG": "برنامج أمني", "ART-PLN": "خطة أمنية", "ART-POL": "سياسة أمنية",
}
DOMAIN_LABELS = {
    "SD-01": "الحوكمة والمخاطر والامتثال",
    "SD-02": "الأصول والبيانات والخصوصية",
    "SD-03": "الهوية والوصول والامتياز",
    "SD-04": "البنية التحتية والشبكات والسحابة",
    "SD-05": "التطبيقات والتطوير والتغيير",
    "SD-06": "الكشف والمراقبة والثغرات",
    "SD-07": "الاستجابة والتعافي والمرونة",
    "SD-08": "الأفراد والأطراف الخارجية والأمن المادي",
}


def split_ar(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[،;؛]", value) if item.strip()]


def priority(value: str) -> str:
    if "حرجة" in value:
        return "PRI-CRITICAL"
    if "مرتفعة" in value:
        return "PRI-HIGH"
    return "PRI-MEDIUM"


def effort(value: str) -> tuple[str, str]:
    parts = [part.strip() for part in value.split("/")]
    size_text = parts[0] if parts else ""
    complexity_text = parts[1] if len(parts) > 1 else ""
    if "كبير جداً" in size_text:
        size = "VERY_LARGE"
    elif "متوسط–كبير" in size_text or "متوسط-كبير" in size_text:
        size = "MEDIUM_LARGE"
    elif "صغير–متوسط" in size_text or "صغير-متوسط" in size_text:
        size = "SMALL_MEDIUM"
    elif "كبير" in size_text:
        size = "LARGE"
    elif "صغير" in size_text:
        size = "SMALL"
    else:
        size = "MEDIUM"
    complexity = "HIGH" if "مرتفع" in complexity_text else "MEDIUM"
    return size, complexity


def delivery_archetype(value: str) -> str:
    if "عاجل" in value or "فوري" in value or "حادث" in value:
        return "URGENT_RESPONSE"
    if "خدمة مدارة" in value:
        return "MANAGED_SERVICE"
    if "برنامج" in value:
        return "PROGRAM"
    if "مبادرة" in value:
        return "INITIATIVE"
    if "عملية" in value and "مشروع" not in value:
        return "CONTINUOUS_OPERATION"
    if "مشروع" in value:
        return "PROJECT"
    if "تغيير" in value or "مهمة" in value or "إجراء" in value:
        return "CONTROLLED_CHANGE"
    return "OPERATIONAL_ACTIVITY"


def review_frequencies(value: str) -> list[str]:
    result: list[str] = []
    remaining = value
    for token, code in (("ربع سنوي", "QUARTERLY"), ("نصف سنوي", "SEMI-ANNUAL")):
        if token in remaining:
            result.append(code)
            remaining = remaining.replace(token, "")
    for token, code in (
        ("يومي", "DAILY"), ("أسبوع", "WEEKLY"), ("شهري", "MONTHLY"),
        ("سنوي", "ANNUAL"), ("مستمر", "CONTINUOUS"),
    ):
        if token in remaining:
            result.append(code)
    return result


def schema() -> dict[str, Any]:
    text = {"type": "string", "minLength": 1}
    artifact_types = sorted(ARTIFACT_TYPE_LABELS)
    domains = sorted(DOMAIN_LABELS)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://secureguide.local/schema/operational-pattern-library-v1",
        "type": "object", "additionalProperties": False,
        "required": ["libraryId","version","authoritative","usageLabelAr","source","patterns"],
        "properties": {
            "libraryId": text, "version": text, "authoritative": {"const": False},
            "usageLabelAr": {"const": "اقتراحات معيارية بناءً على التصنيف"},
            "source": {
                "type": "object", "additionalProperties": False,
                "required": ["sourceType", "sourceBatchId", "sourceSha256",
                             "isOriginalRequirementSource", "usageConstraint"],
                "properties": {
                    "sourceType": {"const": "USER_SUPPLIED_OPERATIONAL_GUIDANCE"},
                    "sourceBatchId": text,
                    "sourceSha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "isOriginalRequirementSource": {"const": False},
                    "usageConstraint": text,
                },
            },
            "patterns": {"type": "array", "minItems": 1, "items": {
                "type": "object",
                "required": ["patternId","sourceRow","sectionAr","sourceTextAr","titleAr",
                             "originalClassificationAr", "originalDeliveryModelAr",
                             "recommendedArtifactType","primaryDomain","subDomain","deliveryArchetype",
                             "controlNature", "controlFunction", "priority", "effortSize", "complexity",
                             "ownerRoles","implementationActions","evidenceExamples", "reviewFrequencies",
                             "acceptanceCriteriaAr","requiresSplit","safetyReviewRequired",
                             "safetyNoteAr",
                             "classificationConfidence", "classificationRationaleAr",
                             "requiresHumanReview", "aiReviewStatus", "sourcePatternId",
                             "testability", "requirementType"],
                "properties": {
                    "patternId": {"type": "string", "pattern": "^OPP-[0-9]{3}$"},
                    "sourceRow": {"type": "integer", "minimum": 1}, "sectionAr": text,
                    "sourceTextAr": text, "titleAr": text, "originalClassificationAr": text,
                    "originalDeliveryModelAr": text,
                    "recommendedArtifactType": {"enum": artifact_types},
                    "primaryDomain": {"enum": domains},
                    "subDomain": {"type": "string", "pattern": "^SD-0[1-8]\\.0[1-5]$"},
                    "controlNature": {"enum": ["NAT-ORG","NAT-HUM","NAT-PHY","NAT-TEC",None]},
                    "controlFunction": {"enum": ["FUN-PRE","FUN-DET","FUN-COR","FUN-REC","FUN-DRR","FUN-COM",None]},
                    "testability": {"enum": ["TST-AUTO","TST-MAN","TST-DOC","TST-INT","TST-NA",None]},
                    "requirementType": {"enum": ["RQT-GOV","RQT-REG","RQT-LEG","RQT-CON","RQT-STD","RQT-INT","RQT-RSK",None]},
                    "deliveryArchetype": {"enum": ["URGENT_RESPONSE","MANAGED_SERVICE","PROGRAM",
                        "INITIATIVE","CONTINUOUS_OPERATION","PROJECT","CONTROLLED_CHANGE","OPERATIONAL_ACTIVITY"]},
                    "effortSize": {"enum": ["SMALL","SMALL_MEDIUM","MEDIUM","MEDIUM_LARGE","LARGE","VERY_LARGE"]},
                    "complexity": {"enum": ["MEDIUM","HIGH"]},
                    "priority": {"enum": ["PRI-CRITICAL","PRI-HIGH","PRI-MEDIUM"]},
                    "ownerRoles": {"type":"array","minItems":1,"uniqueItems":True,"items":text},
                    "implementationActions": {"type":"array","minItems":1,"uniqueItems":True,"items":text},
                    "evidenceExamples": {"type":"array","minItems":1,"uniqueItems":True,"items":text},
                    "acceptanceCriteriaAr": text,
                    "reviewFrequencies": {"type":"array","uniqueItems":True,"items": {
                        "enum": ["DAILY","WEEKLY","MONTHLY","QUARTERLY","SEMI-ANNUAL","ANNUAL","CONTINUOUS"]}},
                    "requiresSplit": {"type":"boolean"},
                    "safetyReviewRequired": {"type":"boolean"},
                    "safetyNoteAr": {"type":["string","null"]},
                    "classificationConfidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "classificationRationaleAr": text,
                    "requiresHumanReview": {"const": True},
                    "aiReviewStatus": {"const": "AIR-HUMAN-REVIEW"},
                    "sourcePatternId": {"type": "string", "pattern": "^OPP-[0-9]{3}$"},
                },
                "allOf": [
                    {
                        "if": {"properties": {"recommendedArtifactType": {"enum": ["ART-CTR", "ART-CTE"]}}},
                        "then": {"properties": {
                            "controlNature": {"type": "string"},
                            "controlFunction": {"type": "string"},
                            "testability": {"type": "string"},
                        }},
                        "else": {"properties": {
                            "controlNature": {"type": "null"},
                            "controlFunction": {"type": "null"},
                            "testability": {"type": "null"},
                        }},
                    },
                    {
                        "if": {"properties": {"recommendedArtifactType": {"const": "ART-REQ"}}},
                        "then": {"properties": {"requirementType": {"type": "string"}}},
                        "else": {"properties": {"requirementType": {"type": "null"}}},
                    },
                    {
                        "if": {"properties": {"safetyReviewRequired": {"const": True}}},
                        "then": {"properties": {"safetyNoteAr": text}},
                        "else": {"properties": {"safetyNoteAr": {"type": "null"}}},
                    },
                ],
                "additionalProperties": False,
            }},
        },
    }


def build(source_path: Path) -> dict[str, Any]:
    source_bytes = source_path.read_bytes()
    raw = source_bytes.decode("utf-8-sig")
    rows: list[dict[str, Any]] = []
    section = ""
    for line in raw.splitlines():
        cells = [cell.strip() for cell in line.split("\t")]
        first = cells[0] if cells else ""
        if re.match(r"^\d+\.\s", first):
            section = re.sub(r"^\d+\.\s*", "", first)
            continue
        if not first.isdigit():
            continue
        row_id = int(first)
        if len(cells) != 11 or row_id not in CLASSIFICATION:
            raise ValueError(f"invalid source row {row_id}")
        artifact_type, domain, subdomain, nature, function = CLASSIFICATION[row_id]
        size, complexity = effort(cells[5])
        safety_note = None
        if row_id in CHANGE_SAFETY:
            safety_note = "يتطلب تحليل أثر وPilot وخطة رجوع وموافقة تغيير قبل التطبيق الواسع."
        elif row_id in INCIDENT_SAFETY:
            safety_note = "يجب حفظ الأدلة وتنسيق الاستجابة قبل الحذف أو الاستبدال، وإعادة البناء عند تعذر ضمان السلامة."
        title = re.split(r"[:：]", cells[1], maxsplit=1)[0].strip()
        pattern_id = f"OPP-{row_id:03d}"
        confidence = 0.68 if row_id in SPLIT_REQUIRED else 0.82
        rationale = (
            f"تصنيف أولي كـ{ARTIFACT_TYPE_LABELS[artifact_type]} ضمن مجال "
            f"{DOMAIN_LABELS[domain]} استناداً إلى الغرض الغالب في النص؛ "
            "يلزم اعتماده بشرياً قبل تحويله إلى عنصر مرجعي أو خطة تشغيلية."
        )
        rows.append({
            "patternId": pattern_id,
            "sourceRow": row_id,
            "sectionAr": section,
            "sourceTextAr": cells[1],
            "titleAr": title,
            "originalClassificationAr": cells[2],
            "originalDeliveryModelAr": cells[3],
            "recommendedArtifactType": artifact_type,
            "primaryDomain": domain,
            "subDomain": subdomain,
            "controlNature": nature,
            "controlFunction": function,
            "testability": "TST-MAN" if artifact_type in {"ART-CTR", "ART-CTE"} else None,
            "requirementType": REQUIREMENT_TYPES.get(row_id),
            "deliveryArchetype": delivery_archetype(cells[3]),
            "effortSize": size,
            "complexity": complexity,
            "priority": priority(cells[6]),
            "ownerRoles": split_ar(cells[7]),
            "implementationActions": split_ar(cells[8]),
            "evidenceExamples": split_ar(cells[9]),
            "acceptanceCriteriaAr": cells[10],
            "reviewFrequencies": review_frequencies(cells[10]),
            "requiresSplit": row_id in SPLIT_REQUIRED,
            "safetyReviewRequired": row_id in CHANGE_SAFETY | INCIDENT_SAFETY,
            "safetyNoteAr": safety_note,
            "classificationConfidence": confidence,
            "classificationRationaleAr": rationale,
            "requiresHumanReview": True,
            "aiReviewStatus": "AIR-HUMAN-REVIEW",
            "sourcePatternId": pattern_id,
        })
    if [row["sourceRow"] for row in rows] != list(range(1, 60)):
        raise ValueError("expected source rows 1..59 exactly")
    return {
        "libraryId": "secureguide-operational-patterns",
        "version": "1.0.0",
        "authoritative": False,
        "usageLabelAr": "اقتراحات معيارية بناءً على التصنيف",
        "source": {
            "sourceType": "USER_SUPPLIED_OPERATIONAL_GUIDANCE",
            "sourceBatchId": "e5d58e5a-6a5d-43ff-a25b-91e8540ce981",
            "sourceSha256": hashlib.sha256(source_bytes).hexdigest(),
            "isOriginalRequirementSource": False,
            "usageConstraint": "Do not present patterns as original source requirements or auto-approve them.",
        },
        "patterns": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="user-supplied TSV/text export")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    payload = build(args.source)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SCHEMA_OUTPUT.write_text(json.dumps(schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {len(payload['patterns'])} patterns -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
