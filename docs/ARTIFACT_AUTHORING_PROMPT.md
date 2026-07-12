# معيار وطلب صياغة العناصر والضوابط الأمنية (Artifact Authoring Standard & Prompt)

> يوفّر هذا المستند: **(أ)** وصفاً لما هو العنصر المصاغ جيداً، **(ب)** معياراً قاطعاً للحقول والقيم، **(ج)** طلباً (Prompt) جاهزاً لوكيل ذكاء اصطناعي يُنتج مخرجات JSON مطابقة لجدول `staging_artifacts` وقابلة للترقية.
> يستند إلى: `AUTHORING_POLICY.md` · `CLASSIFICATION_POLICY.md` · `CONSOLIDATION_POLICY.md` · `PROMOTION_POLICY.md` · USACM v2.2.1 · SDT v2.2.1.

---

## أ. الوصف (ما هو العنصر المصاغ جيداً)
عنصر SecureGuide المصاغ جيداً = **فكرة أمنية ذرّية واحدة**، مُعاد صياغتها بالإنجليزية (لا نسخ للنص الأصلي)، مصنّفة قطعياً بـ USACM (نوع + مستوى) و SDT (مجال + مجال فرعي واحد)، بحقول محتوى منظّمة، ونسب واضح للمصدر، وثقة وتبرير. يجب أن يكون: **محدّداً، قابلاً للتصنيف، قابلاً للتقييم/التحقق، قابلاً للربط**، وخالياً من الكلمات الفضفاضة، ولا يخلط "ما يجب تحقيقه" بـ"كيف يُنفَّذ" (إلا لـ ART-CFG/ART-PRC).

---

## ب. المعيار (الحقول والقيم القاطعة)

### ب.1 حقول المحتوى (English-first)
| الحقل | إلزامي؟ | الطول | الوصف |
|---|---|---|---|
| `title_en` | **نعم** | 4–10 كلمات | عنوان اسمي مباشر (لا جملة/فعل غامض) |
| `definition_short_en` | **نعم** | 20–35 كلمة | «This artifact defines [ما المطلوب] within [النطاق] to achieve [النتيجة الأمنية].» |
| `definition_full_en` | نعم (موصى) | 80–180 كلمة | يجيب: ما هو؟ لماذا؟ أين ينطبق؟ الحد الأدنى؟ كيف نتحقق؟ |
| `objective_en` | نعم (موصى) | جملة واحدة | نتيجة أمنية واحدة |
| `canonical_statement` | اختياري | جملة–جملتان | نص موحّد رسمي إن وُجد |
| `applicability_note`, `implementation_guidance`, `verification_method_note`, `evidence_required`, `common_misinterpretations` | اختياري | مختصر | سياق تطبيقي |
| `*_ar` (عربي) | مؤجّل/اختياري | — | لا يمنع الاعتماد إن فارغ |
> **لا تنشر النص الأصلي الكامل** للمصدر. `source_quote` مقتطف قصير عند الحاجة القانونية فقط؛ النسب يكون عبر الحقول المهيكلة.

### ب.2 حقول التصنيف (قيم مضبوطة — لا تخترع قيماً)
| الحقل | القيم المسموحة |
|---|---|
| `proposed_type` | 22: ART-REQ, ART-OBJ, ART-PRI, ART-POL, ART-STD, ART-CTR, ART-CTE, ART-PRO, ART-PRC, ART-PRG, ART-PLN, ART-TSK, ART-CFG, ART-RUL, ART-EVD, ART-MET, ART-EXC, ART-RSK, ART-AST, ART-THR, ART-VUL, ART-OWN |
| `proposed_abstraction_level` | ABS-GOV, ABS-RIS, ABS-POL, ABS-CTR, ABS-PRO, ABS-TEC, ABS-EVM |
| `proposed_primary_domain` | SD-01 … SD-08 |
| `proposed_sub_domain` | 40 قيمة `SD-XX.YY` — **ويجب أن تبدأ بكود المجال الرئيسي** (`substr(sub,1,5)=primary`) |
| `proposed_obligation_level` | OBL-MND, OBL-CON, OBL-REC, OBL-OPT |

**SDT — المجالات الثمانية:** SD-01 حوكمة/مخاطر/امتثال · SD-02 أصول/بيانات/خصوصية · SD-03 هوية/وصول/امتياز · SD-04 بنية/شبكة/سحابة · SD-05 تطبيقات/تطوير/تغيير · SD-06 كشف/مراقبة/ثغرات · SD-07 استجابة/تعافٍ/صمود · SD-08 أشخاص/أطراف ثالثة/مادي.

**قواعد ترجيح المجال:** Cloud IAM→SD-03 · إعداد منصة سحابية→SD-04 · اختبار تطبيقات→SD-05 · اختراق واسع/red team→SD-06 · least privilege عام→SD-03.03 · MFA عام→SD-03.02 · جرد الأصول→SD-02.01 · جرد البرمجيات→SD-02.02 · تصنيف الأصول→SD-02.03.

### ب.3 الحقول الإلزامية حسب النوع
| النوع | حقول إضافية إلزامية |
|---|---|
| `ART-REQ` | `proposed_requirement_type` ∈ RQT-GOV, RQT-REG, RQT-LEG, RQT-CON, RQT-STD, RQT-INT, RQT-RSK |
| `ART-CTR` / `ART-CTE` | `proposed_control_nature` ∈ NAT-ORG/HUM/PHY/TEC · `proposed_control_function` ∈ FUN-PRE/DET/COR/REC/DRR/COM · `proposed_testability` ∈ TST-AUTO/MAN/DOC/INT/NA |
| `ART-AST` | `proposed_asset_type` (HARDWARE…INTELLECTUAL_PROPERTY) · `proposed_asset_criticality` (CRITICAL/HIGH/MEDIUM/LOW) |

### ب.4 المساءلة والنسب
| الحقل | القاعدة |
|---|---|
| `classification_confidence` | 0.0–1.0. إن ≤ **0.70** ⇒ `requires_human_review=1`. |
| `classification_rationale` | إلزامي إن وُجدت ثقة — يشرح سبب النوع/المجال. |
| `rejected_alternatives` | JSON للبدائل المرفوضة عند الغموض. |
| `requires_human_review` | 0/1. |
| `proposed_tags_json` | مصفوفة `{tag_type, tag_value}`؛ tag_type ∈ Technology/Framework/Concept/Context/Threat/Data/Party. سياق ثانوي لا بديل عن المجال. |
| `proposed_mappings_json` | مصفوفة `{raw_id, source_document, source_version, source_section, mapping_strength, rationale}`؛ strength ∈ DIRECT/INDIRECT/PARTIAL/INFORMATIVE؛ **أي غير DIRECT يتطلب rationale**. |
| `merge_action` | (عند التوحيد) ∈ CANONICALIZE/EQUIVALENCE_GROUP/CROSSWALK_ONLY/RELATE_ONLY/KEEP_SEPARATE/DEPRECATE_DERIVED. |

### ب.5 قواعد الذرّية والجودة (شروط القبول)
1. فكرة إلزامية واحدة (لا تتجاوز صياغة `definition_short_en` فعلين إلزاميين). لو تعدّدت الأفكار ⇒ اقترح تقسيماً.
2. النوع والمستوى والمجال مستقلة — لا تُشتق آلياً بلا مبرر.
3. مجال واحد ومجال فرعي واحد ينتمي إليه.
4. لا خلط متطلب/إجراء/إعداد/دليل في عنصر واحد.
5. خالٍ من: مناسب، جيد، كافٍ، قوي، حديث… إلا بمعيار معرّف.
6. `sub_domain` يبدأ بكود `primary_domain`.

---

## ج. الطلب الجاهز (Authoring Prompt)

### ج.1 System Prompt (الصقه كما هو)
```
You are SecureGuide's Security Artifact Author. You transform a RAW security
statement into ONE atomic, well-formed SecureGuide artifact, English-first,
strictly following USACM v2.2.1 and SDT v2.2.1.

HARD RULES:
- Output ONE JSON object only. No prose, no markdown, no original full text.
- REWRITE in your own English words; never copy the source verbatim.
- Exactly ONE USACM type, ONE SDT primary_domain, ONE sub_domain that starts
  with the primary_domain code. Never invent enum values outside the allowed lists.
- If the raw statement contains more than one independent mandatory idea, DO NOT
  merge them: set "needs_split": true and describe the atomic pieces in
  "split_suggestion"; still classify the primary idea.
- Fill type-specific required fields: ART-REQ→requirement_type;
  ART-CTR/ART-CTE→control_nature+control_function+testability;
  ART-AST→asset_type+asset_criticality.
- classification_confidence in [0,1]; if <= 0.70 set requires_human_review=1
  and ai_review_status="AIR-HUMAN-REVIEW"; else "AIR-AUTO-ACCEPTED".
- Always give a non-empty classification_rationale and >=1 source mapping in
  proposed_mappings; any mapping_strength other than DIRECT needs a rationale.
- Tags are secondary context only, never a substitute for the domain.

ALLOWED VALUES:
type: ART-REQ,ART-OBJ,ART-PRI,ART-POL,ART-STD,ART-CTR,ART-CTE,ART-PRO,ART-PRC,ART-PRG,ART-PLN,ART-TSK,ART-CFG,ART-RUL,ART-EVD,ART-MET,ART-EXC,ART-RSK,ART-AST,ART-THR,ART-VUL,ART-OWN
abstraction_level: ABS-GOV,ABS-RIS,ABS-POL,ABS-CTR,ABS-PRO,ABS-TEC,ABS-EVM
primary_domain: SD-01..SD-08 ; sub_domain: SD-XX.YY (must belong to primary)
obligation_level: OBL-MND,OBL-CON,OBL-REC,OBL-OPT
requirement_type: RQT-GOV,RQT-REG,RQT-LEG,RQT-CON,RQT-STD,RQT-INT,RQT-RSK
control_nature: NAT-ORG,NAT-HUM,NAT-PHY,NAT-TEC
control_function: FUN-PRE,FUN-DET,FUN-COR,FUN-REC,FUN-DRR,FUN-COM
testability: TST-AUTO,TST-MAN,TST-DOC,TST-INT,TST-NA
asset_type: HARDWARE,SOFTWARE,DATA,SERVICE,FACILITY,PERSONNEL,NETWORK,CLOUD_INSTANCE,DOCUMENT,INTELLECTUAL_PROPERTY
asset_criticality: CRITICAL,HIGH,MEDIUM,LOW
mapping_strength: DIRECT,INDIRECT,PARTIAL,INFORMATIVE
tag_type: Technology,Framework,Concept,Context,Threat,Data,Party
ai_review_status: AIR-AUTO-ACCEPTED,AIR-HUMAN-REVIEW,AIR-HUMAN-APPROVED,AIR-HUMAN-REJECTED

SDT domains: SD-01 Governance,Risk&Compliance | SD-02 Assets,Data&Privacy |
SD-03 Identity,Access&Privilege | SD-04 Infrastructure,Network&Cloud |
SD-05 Applications,Development&Change | SD-06 Detection,Monitoring&Vulnerability |
SD-07 Response,Recovery&Resilience | SD-08 People,ThirdParties&Physical
TIE-BREAKERS: cloud IAM->SD-03 ; cloud platform config->SD-04 ; app/API testing->SD-05 ;
broad pentest/red-team->SD-06 ; general least-privilege->SD-03.03 ; general MFA->SD-03.02.

OUTPUT JSON SCHEMA (keys exactly):
{
  "title_en": str, "definition_short_en": str, "definition_full_en": str,
  "objective_en": str, "canonical_statement": str|null,
  "proposed_type": str, "proposed_abstraction_level": str,
  "proposed_primary_domain": str, "proposed_sub_domain": str,
  "proposed_obligation_level": str,
  "proposed_requirement_type": str|null,
  "proposed_control_nature": str|null, "proposed_control_function": str|null,
  "proposed_testability": str|null,
  "proposed_asset_type": str|null, "proposed_asset_criticality": str|null,
  "classification_confidence": number, "classification_rationale": str,
  "rejected_alternatives": [str], "requires_human_review": 0|1,
  "ai_review_status": str,
  "proposed_tags": [{"tag_type": str, "tag_value": str}],
  "proposed_mappings": [{"raw_id": str, "source_document": str, "source_version": str,
                         "source_section": str, "mapping_strength": str, "rationale": str|null}],
  "needs_split": bool, "split_suggestion": [str]
}
```

### ج.2 User Prompt (املأ الحقول من `raw_artifacts`)
```
RAW ITEM:
- raw_id: {raw_artifacts.id}
- source_document: {source_document}
- source_version: {source_version}
- source_section: {source_section}
- source_type: {source_type}
- title_draft: {title_draft}
- text: {raw_text_en}
- context: {context_paragraph}
- keywords: {keywords_json}
- hints (if present): usacm_type={usacm_type_assigned}, sdt={sdt_subdomain_assigned}

Produce the single JSON artifact per the schema and rules.
```

---

## د. مثال محلول (Input → Output)

**Input (raw):** `cis_controls_v8::0000` · CIS Controls v8 · §1.1 · "Establish and maintain an accurate, detailed, and up-to-date inventory of all enterprise assets…"

**Output:**
```json
{
  "title_en": "Enterprise Asset Inventory",
  "definition_short_en": "This artifact defines the requirement to establish and maintain an accurate, current inventory of all enterprise information and technology assets that store, process, or transmit organizational data.",
  "definition_full_en": "This artifact requires the organization to build and maintain a complete, accurate inventory of information and technology assets — including end-user devices, servers, network devices, and IoT — with enough detail to identify and govern each asset. It applies across all in-scope environments. The minimum expected outcome is a documented, regularly reconciled asset register. Verification is by inspecting the register and reconciling it against automated discovery.",
  "objective_en": "Ensure every in-scope asset is known so it can be secured, monitored, and governed.",
  "canonical_statement": null,
  "proposed_type": "ART-REQ",
  "proposed_abstraction_level": "ABS-CTR",
  "proposed_primary_domain": "SD-02",
  "proposed_sub_domain": "SD-02.01",
  "proposed_obligation_level": "OBL-MND",
  "proposed_requirement_type": "RQT-STD",
  "proposed_control_nature": null,
  "proposed_control_function": null,
  "proposed_testability": null,
  "proposed_asset_type": null,
  "proposed_asset_criticality": null,
  "classification_confidence": 0.9,
  "classification_rationale": "Core asset-inventory requirement; single SDT sub-domain SD-02.01 (Asset Inventory & Management); framework-standard requirement type.",
  "rejected_alternatives": ["ART-CTR (rejected: phrased as a required outcome, not a specific safeguard mechanism)"],
  "requires_human_review": 0,
  "ai_review_status": "AIR-AUTO-ACCEPTED",
  "proposed_tags": [{"tag_type": "Framework", "tag_value": "CIS"}, {"tag_type": "Concept", "tag_value": "Asset Management"}],
  "proposed_mappings": [{"raw_id": "cis_controls_v8::0000", "source_document": "CIS Controls v8", "source_version": "Unknown", "source_section": "1.1", "mapping_strength": "DIRECT", "rationale": null}],
  "needs_split": false,
  "split_suggestion": []
}
```

---

## هـ. قائمة القبول (تُطابق فحص `promotion_blockers`)
قبل قبول المخرجات في staging ثم الترقية، تحقّق أن:
- [ ] `title_en` و`definition_short_en` غير فارغين.
- [ ] `proposed_type` من الـ22 · `proposed_abstraction_level` صالح.
- [ ] `proposed_primary_domain` من SD-01..08 · `proposed_sub_domain` من الـ40 ويبدأ بكود المجال.
- [ ] الحقول الإلزامية حسب النوع مملوءة وصالحة (RQT-*/NAT-*/FUN-*/TST-*/asset_*).
- [ ] `classification_confidence` في [0,1]؛ إن ≤0.70 فـ `requires_human_review=1` و`ai_review_status=AIR-HUMAN-REVIEW`.
- [ ] `classification_rationale` غير فارغ.
- [ ] `proposed_mappings` فيه مصدر واحد على الأقل بـ`raw_id`+`source_document`+`mapping_strength` صالح؛ وأي غير DIRECT له rationale.
- [ ] فكرة ذرّية (`needs_split=false`).
- [ ] الوسوم لم تُستخدم بديلاً عن المجال.

> المخرجات تُكتب إلى `staging_artifacts` (الحقول `proposed_*`, `*_en`, `classification_*`, `proposed_tags_json`, `proposed_mappings_json`)، ثم تمرّ بالمراجعة النهائية والترقية وفق `PROMOTION_POLICY.md`.
