# SecureGuide Dynamic Action & Evidence Blueprint Engine

## وثيقة التوثيق والتحديد والتنفيذ

**الإصدار:** 1.0

**التاريخ:** 2026-07-14
**النطاق:** تصميم وتنفيذ محرك توليد الإجراءات، الأدلة، الجهد، الأصول المساعدة، والحلول المقترحة لعناصر SecureGuide المصنفة وفق USACM و SDT.

## حالة المراجعة والتنفيذ

اعتمدت هذه الوثيقة بعد التصحيحات التنفيذية الآتية، وهي مقدمة على أي مثال أقدم داخلها:

- أكواد USACM/SDT الفعلية وحدها هي القيم الداخلية. `NAT-GOV` و`FUN-PRV` اسما إدخال يُطبّعان إلى `NAT-ORG` و`FUN-PRE`. أما `NAT-OPS` و`NAT-LEG` و`FUN-DIR` و`FUN-COMP` فغامضة، لا تُخزّن ولا تُستنتج قسرًا، وتؤدي إلى مراجعة بشرية.
- إزالة التكرار تتم بمفتاح `semanticKey` مع دمج `sourceRuleIds` و`sourceRuleVersions`، وليس بمعرف العرض `id`.
- اعتماد الخطة لا يرفع `confidence`؛ الثقة مقياس تقني لجودة المدخلات والقواعد والتطابق فقط.
- نُفّذ MVP في طبقة Python المشتركة الحالية كي يبقى منطق الأعمال خارج Flutter. تستهلك Flutter ناتج الخدمة لاحقًا ولا تعيد تنفيذ القواعد.
- `GeneratedBlueprint` مؤقت وغير سلطوي ولا يُحفظ في SQLite ولا يدخل التقرير الرسمي. نُفذ مسار اللقطة البشرية والاعتماد والمهام في الترحيل 023؛ ولا تدخل الخطة التقرير حتى تصبح `APPROVED`.

التنفيذ الحالي:

- مخطط قواعد: `reference/blueprint_rule_schema_v1.json`.
- حزمة 30 قاعدة مرتبة: `reference/blueprint_rules_mvp_v1.json`.
- التحميل والتحقق: `secureguide/blueprints/rules.py`.
- التوليد والثقة وإزالة التكرار: `secureguide/blueprints/engine.py`.
- خدمة قراءة فقط: `SecureGuideService.generate_blueprint()`.
- أمر تجريبي: `python -m secureguide.cli --db catalog_work.db blueprint-generate <artifact-id>`.
- اختبارات الحوكمة والحالات العملية: `tests/test_blueprint_engine.py`.

---

## 1. الملخص التنفيذي

يهدف هذا المستند إلى توثيق فكرة **Dynamic Action & Evidence Blueprint Engine** من البداية إلى النهاية داخل مشروع SecureGuide.

المحرك المقترح هو محرك **Rule-Based Deterministic Engine**، وليس محرك ذكاء اصطناعي توليدي. وظيفته تحويل التصنيف الأمني للعنصر إلى خطة تشغيلية مقترحة تشمل:

- نوع خطة التنفيذ.
- الإجراءات التنفيذية المقترحة.
- المخرجات المتوقعة.
- أدلة الإثبات المطلوبة.
- نوعية الجهد المطلوب.
- الأدوات والقوالب المساعدة.
- الحلول المقترحة.
- القواعد التي أدت إلى كل توصية.
- مستوى الثقة في التوليد.

هذه المخرجات لا تمثل المتطلب الأصلي ولا تصبح جزءًا رسميًا من الامتثال إلا بعد اعتماد المستخدم لها. لذلك يتم التعامل معها كطبقة تشغيلية مساعدة:

**Operational Enablement Layer**

---

## 2. المشكلة التي يعالجها المحرك

الكتالوج الأمني التقليدي يحتوي على ضوابط ومتطلبات وسياسات، لكنه غالبًا لا يجيب عن أسئلة التنفيذ العملية:

- ماذا أفعل لتطبيق هذا العنصر؟
- ما نوع الخطة المطلوبة؟
- ما الأدلة التي سيطلبها المدقق؟
- ما مستوى الجهد المتوقع؟
- ما القوالب أو الأدوات التي تساعدني؟
- هل أحتاج حلًا تقنيًا أم إجراءً تشغيليًا أم مراجعة قانونية؟

ترك هذه الحقول فارغة أو عامة يقلل قيمة التطبيق. وفي المقابل، تخزين إجراءات ثابتة داخل الكتالوج الأساسي يسبب مشكلة أخرى: تلويث المصدر الأصلي بتوصيات تشغيلية قد تختلف حسب المؤسسة والسياق.

الحل هو توليد هذه المعلومات ديناميكيًا من التصنيف، ثم عرضها كمقترحات قابلة للاعتماد أو التعديل.

---

## 3. المبادئ الحاكمة

### 3.1 الفصل بين الحقيقة والتوصية

يجب الفصل بين:

| الطبقة | المعنى |
|---|---|
| Source Artifact | النص الأصلي والمصدر الرسمي |
| Classification | تصنيف العنصر وفق USACM و SDT |
| Generated Blueprint | خطة مقترحة مولدة من القواعد |
| Approved Blueprint | خطة اعتمدها المستخدم |
| Tasks | مهام تشغيلية فعلية قابلة للإسناد والمتابعة |

### 3.2 عدم الادعاء بأن التوصية متطلب أصلي

لا يجوز عرض الإجراء أو الدليل المولد على أنه مطلوب صراحة من المصدر، إلا إذا كان له اقتباس أو مرجع مباشر.

### 3.3 قابلية التدقيق

كل إجراء أو دليل أو حل مقترح يجب أن يحمل:

- `sourceRuleIds`
- `rationale`
- `engineVersion`
- `ruleVersion`
- `blueprintVersion`

وعند وجود استناد مباشر لمصدر خارجي:

- `sourceArtifactId`
- `sourceCitation`

### 3.4 الاعتماد البشري

الخطة المولدة لا تؤثر على حالة الامتثال. تصبح قابلة للاستخدام الرسمي فقط عند اعتمادها أو تحويلها إلى مهام.

---

## 4. القرار المعماري الأساسي

الترتيب الصحيح لتوليد الخطة:

| البعد | الدور |
|---|---|
| `artifactType` | يحدد نوع الخطة والمخرجات الأساسية |
| `controlNature` | يحدد طريقة التنفيذ |
| `controlFunction` | يحدد الغرض الأمني |
| `securityDomain` | يضيف سياق المجال |
| `obligationLevel` | يحدد مستوى الصرامة والتوثيق |

القاعدة الذهبية:

> يولد النظام نوع الإجراء ومخرجاته الأساسية بناءً على `artifactType`، ثم يخصص خطوات التنفيذ والأدلة والجهد والأصول والحلول بناءً على `controlNature`, `controlFunction`, `securityDomain`, و `obligationLevel`.

---

## 5. نطاق المحرك

### 5.1 داخل النطاق

- توليد خطة تنفيذ مقترحة.
- توليد أدلة إثبات مقترحة.
- توليد مخرجات متوقعة.
- تحديد نوعية الجهد المطلوب.
- اقتراح قوالب وأدوات مساعدة.
- اقتراح حلول عامة ومحايدة.
- حساب مستوى الثقة.
- عرض أسباب التوليد.
- اعتماد الخطة وتحويلها إلى مهام.

### 5.2 خارج النطاق في الإصدار الأول

- توصية منتجات أو موردين محددين.
- تنفيذ تلقائي للضوابط.
- إرسال مهام إلى أنظمة خارجية.
- الاعتماد النهائي للامتثال بدون مراجعة بشرية.
- استنتاج قانوني ملزم.

---

## 6. الأبعاد التصنيفية المستخدمة

### 6.1 `artifactType`

| القيمة | نوع الخطة الأساسية |
|---|---|
| `ART-POL` | Policy Development Plan |
| `ART-STD` | Standard Development Plan |
| `ART-PRC` | Procedure Development Plan |
| `ART-CTR` | Control Implementation Plan |
| `ART-REQ` | Requirement Fulfillment Plan |
| `ART-EVD` | Evidence Collection Plan |
| `ART-MET` | Metric Definition Plan |
| `ART-RSK` | Risk Treatment Plan |
| `ART-ROL` | Role & Responsibility Plan |
| `ART-THR` | Threat Analysis Plan |

### 6.2 `controlNature`

| القيمة | التأثير |
|---|---|
| `NAT-GOV` | حوكمة، اعتماد، لجان، RACI |
| `NAT-TEC` | إعدادات تقنية، تكوين، اختبار فني |
| `NAT-OPS` | تشغيل يومي، إجراءات دورية، مراقبة |
| `NAT-PHY` | ضوابط فيزيائية، فحص موقعي |
| `NAT-LEG` | مراجعة قانونية، عقود، التزامات |
| `NAT-HUM` | تدريب، توعية، سلوك مستخدمين |
| `NAT-TPR` | طرف ثالث، موردون، اتفاقيات |

### 6.3 `controlFunction`

| القيمة | التأثير |
|---|---|
| `FUN-PRV` | منع واستباق |
| `FUN-DET` | كشف ورصد وتنبيه |
| `FUN-COR` | تصحيح واستجابة |
| `FUN-DIR` | توجيه وتعليمات |
| `FUN-DETERR` | ردع ومساءلة |
| `FUN-COMP` | تعويض وضوابط بديلة |
| `FUN-REC` | تعافي واستعادة |

### 6.4 `obligationLevel`

| القيمة | التأثير |
|---|---|
| `MANDATORY` | يتطلب أدلة رسمية واعتماد واضح |
| `RECOMMENDED` | أدلة تشغيلية كافية غالبًا |
| `OPTIONAL` | يطبق عند الحاجة |
| `CONDITIONAL` | يتطلب توثيق شرط التطبيق |
| `PROHIBITED` | يتطلب أدلة منع أو تعطيل أو إزالة |

---

## 7. مخرجات المحرك

ينتج المحرك كائنًا من نوع `GeneratedBlueprint` يحتوي على:

- `actionPlanType`
- `actions`
- `expectedOutputs`
- `evidence`
- `effortProfiles`
- `supportingAssets`
- `suggestedSolutions`
- `appliedRules`
- `confidence`
- `generatedAt`
- `engineVersion`
- `ruleVersion`
- `blueprintVersion`

---

## 8. نموذج البيانات المقترح

```dart
class GeneratedBlueprint {
  final String blueprintId;
  final String artifactId;
  final String artifactType;
  final String actionPlanType;
  final String title;
  final List<BlueprintAction> actions;
  final List<String> expectedOutputs;
  final List<BlueprintEvidence> evidence;
  final List<EffortProfile> effortProfiles;
  final List<SupportingAsset> supportingAssets;
  final List<SuggestedSolution> suggestedSolutions;
  final List<AppliedRule> appliedRules;
  final double confidence;
  final String confidenceRationale;
  final String engineVersion;
  final String ruleVersion;
  final String blueprintVersion;
  final DateTime generatedAt;
  final bool isGenerated;
}

class BlueprintAction {
  final String id;
  final String title;
  final String description;
  final String category;
  final int order;
  final List<String> sourceRuleIds;
  final String? sourceArtifactId;
  final String? sourceCitation;
  final String rationale;
}

class BlueprintEvidence {
  final String id;
  final String title;
  final String evidenceType;
  final String description;
  final List<String> sourceRuleIds;
  final String? sourceArtifactId;
  final String? sourceCitation;
  final bool mandatory;
}

class EffortProfile {
  final String effortType;
  final String effortLevel;
  final List<String> skillRequirements;
  final String estimatedComplexity;
  final String implementationMode;
  final List<String> sourceRuleIds;
}

class SupportingAsset {
  final String id;
  final String assetType;
  final String title;
  final String usage;
  final String availability;
  final String? templateRef;
  final List<String> sourceRuleIds;
}

class SuggestedSolution {
  final String id;
  final String solutionType;
  final String title;
  final String description;
  final bool vendorNeutral;
  final String recommendationLevel;
  final List<String> prerequisites;
  final List<String> risks;
  final bool requiresHumanValidation;
  final List<String> sourceRuleIds;
}

class AppliedRule {
  final String ruleId;
  final String ruleVersion;
  final String dimension;
  final String value;
  final String description;
}

class ApprovedBlueprint {
  final String approvedBlueprintId;
  final String artifactId;
  final String approvedBy;
  final DateTime approvedAt;
  final String engineVersion;
  final String ruleVersion;
  final String blueprintVersion;
  final List<BlueprintAction> approvedActions;
  final List<BlueprintEvidence> approvedEvidence;
  final List<EffortProfile> approvedEffortProfiles;
  final List<SupportingAsset> approvedSupportingAssets;
  final List<SuggestedSolution> approvedSuggestedSolutions;
  final List<UserOverride> userOverrides;
}

class UserOverride {
  final String targetId;
  final String targetType;
  final String overrideType;
  final String overrideReason;
  final String changedBy;
  final String? oldValue;
  final String? newValue;
  final DateTime timestamp;
}
```

---

## 9. قيم الجهد والأصول والحلول

### 9.1 `effortType`

- `DOCUMENTATION`
- `CONFIGURATION`
- `PROCESS_DESIGN`
- `TECHNICAL_IMPLEMENTATION`
- `LEGAL_REVIEW`
- `TRAINING`
- `ASSESSMENT`
- `MONITORING`
- `REMEDIATION`

### 9.2 `effortLevel`

- `LOW`
- `MEDIUM`
- `HIGH`
- `VERY_HIGH`

### 9.3 `implementationMode`

- `MANUAL`
- `SEMI_AUTOMATED`
- `AUTOMATED`

### 9.4 `supportingAsset.assetType`

- `TEMPLATE`
- `CHECKLIST`
- `PLAYBOOK`
- `CONFIG_GUIDE`
- `SCRIPT`
- `DASHBOARD`
- `RACI_MATRIX`
- `EVIDENCE_FORM`

### 9.5 `suggestedSolution.solutionType`

- `PROCESS_SOLUTION`
- `TECHNICAL_SOLUTION`
- `GOVERNANCE_SOLUTION`
- `AUTOMATION_SOLUTION`
- `THIRD_PARTY_SOLUTION`

---

## 10. Rule Schema

يجب أن تكون القواعد قابلة للتوسع، بدون مفاتيح JSON مكررة، وبدون شروط متداخلة معقدة.

```json
{
  "engineVersion": "1.0.0",
  "ruleVersion": "2026.07",
  "rules": {
    "artifactType": {
      "ART-POL": {
        "ruleId": "RULE-TYP-POL",
        "planType": "POLICY_DEVELOPMENT_PLAN",
        "title": "خطة إعداد واعتماد سياسة",
        "actions": [
          {
            "id": "ACT-POL-SCOPE",
            "order": 10,
            "category": "PREPARATION",
            "title": "تحديد نطاق السياسة",
            "description": "تحديد نطاق السياسة، الأهداف، الجهات المشمولة، والالتزامات الرئيسية."
          },
          {
            "id": "ACT-POL-DRAFT",
            "order": 20,
            "category": "DRAFTING",
            "title": "صياغة مسودة السياسة",
            "description": "إعداد مسودة سياسة قابلة للمراجعة والاعتماد."
          },
          {
            "id": "ACT-POL-APPROVE",
            "order": 40,
            "category": "APPROVAL",
            "title": "اعتماد السياسة",
            "description": "اعتماد السياسة من الجهة المخولة."
          }
        ],
        "expectedOutputs": [
          "وثيقة سياسة معتمدة",
          "سجل اعتماد",
          "سجل نشر وتعميم"
        ],
        "evidence": [
          {
            "id": "EVD-POL-DOC",
            "evidenceType": "POLICY_DOCUMENT",
            "title": "وثيقة السياسة المعتمدة",
            "mandatory": true
          }
        ],
        "effortProfiles": [
          {
            "effortType": "DOCUMENTATION",
            "effortLevel": "MEDIUM",
            "skillRequirements": ["GRC"],
            "estimatedComplexity": "MODERATE",
            "implementationMode": "MANUAL"
          }
        ],
        "supportingAssets": [
          {
            "id": "AST-POL-TEMPLATE",
            "assetType": "TEMPLATE",
            "title": "قالب سياسة",
            "usage": "يستخدم لتوحيد صياغة السياسات."
          }
        ]
      }
    },
    "controlNature": {},
    "controlFunction": {},
    "securityDomain": {},
    "obligationLevel": {}
  }
}
```

---

## 11. منطق عمل المحرك

```text
1. استلام SecurityArtifact أو ControlV3.
2. التحقق من وجود artifactType.
3. اختيار القالب الأساسي حسب artifactType.
4. تطبيق توسعات controlNature.
5. تطبيق توسعات controlFunction.
6. تطبيق توسعات securityDomain.
7. تطبيق obligationLevel.
8. دمج الإجراءات والأدلة والأصول والحلول.
9. إزالة التكرار بناءً على id.
10. دمج sourceRuleIds عند التكرار.
11. ترتيب الإجراءات حسب order ثم category.
12. حساب confidence.
13. إنتاج GeneratedBlueprint.
```

---

## 12. إزالة التكرار

آلية الدمج:

- يستخدم `id` كمفتاح رئيسي لإزالة التكرار.
- إذا تكرر الإجراء أو الدليل، لا يكرر في الخطة.
- يتم دمج `sourceRuleIds`.
- إذا اختلف الوصف بين قاعدتين، يحتفظ المحرك بالوصف الأعلى أولوية أو يضيف ملاحظة في `rationale`.

مثال:

```json
{
  "id": "ACT-REVIEW",
  "title": "مراجعة دورية",
  "sourceRuleIds": ["RULE-TYP-POL", "RULE-NAT-GOV", "RULE-OBL-MANDATORY"]
}
```

---

## 13. حساب مستوى الثقة

لا ترتبط الثقة بالاعتماد البشري. الثقة تقيس جودة التوليد فقط.

العوامل:

| العامل | التأثير |
|---|---|
| اكتمال الأبعاد | يزيد الثقة |
| خصوصية القواعد | يزيد الثقة |
| وجود تعارض | يقلل الثقة |
| قيمة `UNKNOWN` أو `NA` | تقلل الثقة |
| قاعدة عامة جدًا | تقلل الثقة |

التوصية:

```text
Base confidence = 0.60
+ artifactType matched = +0.15
+ controlNature matched = +0.08
+ controlFunction matched = +0.07
+ securityDomain matched = +0.05
+ obligationLevel matched = +0.05
- conflicts = -0.10 to -0.30
Maximum generated confidence = 0.95
```

الاعتماد البشري يسجل في:

```text
approvalStatus
```

ولا يعدل `confidence`.

---

## 14. تجربة المستخدم

### 14.1 شاشة التفاصيل

تضاف بطاقة بعنوان:

**اقتراحات معيارية بناءً على التصنيف**

محتويات البطاقة:

- نوع الخطة.
- مستوى الثقة.
- سبب التوليد.
- نوعية الجهد.
- الإجراءات المقترحة.
- المخرجات المتوقعة.
- أدلة الإثبات.
- الأدوات والقوالب المساعدة.
- الحلول المقترحة.
- القواعد المطبقة.

### 14.2 تمييز التوصيات عن النص الأصلي

يجب أن تكون البطاقة منفصلة بصريًا عن بطاقة النص الأصلي والتصنيف.

العبارة المقترحة:

> هذه اقتراحات معيارية ناتجة عن قواعد التصنيف، وليست نصًا أصليًا من المصدر.

### 14.3 أزرار الإجراء

- `اعتماد الخطة`
- `تحويل إلى مهام`
- `تعديل قبل الاعتماد`
- `تجاهل`
- `عرض سبب التوصية`

---

## 15. الاعتماد والتحويل إلى مهام

عند اعتماد الخطة:

1. يتم إنشاء `ApprovedBlueprint`.
2. يتم نسخ الإجراءات والأدلة والجهد والأصول والحلول المعتمدة.
3. يتم تسجيل:
   - `approvedBy`
   - `approvedAt`
   - `engineVersion`
   - `ruleVersion`
   - `blueprintVersion`
4. يتم تحويل الإجراءات إلى مهام.
5. أي تعديل لاحق يسجل في `UserOverride`.

---

## 16. متطلبات Audit Trail

يجب حفظ:

- من اعتمد الخطة.
- متى اعتمدها.
- نسخة المحرك.
- نسخة القواعد.
- نسخة الخطة.
- القواعد التي أدت إلى كل توصية.
- أي تعديل بشري.
- سبب التعديل.
- القيم قبل وبعد التعديل عند الإمكان.

---

## 17. الملفات المقترحة للتنفيذ

```text
lib/v3/logic/blueprint_generator.dart
lib/v3/models/generated_blueprint.dart
lib/v3/models/approved_blueprint.dart
lib/v3/models/blueprint_rule.dart
lib/v3/data/blueprint_rules.dart
lib/v3/ui/widgets/generated_blueprint_card.dart
lib/v3/ui/screens/control_detail_v3_screen.dart
test/v3/logic/blueprint_generator_test.dart
```

---

## 18. خطة التنفيذ

### المرحلة 1: MVP

الهدف: عرض خطة مقترحة للقراءة فقط.

المهام:

- بناء نماذج البيانات.
- بناء `ControlBlueprintGenerator`.
- إضافة قواعد Mock مبدئية.
- دعم `artifactType` و `controlNature`.
- عرض البطاقة داخل شاشة التفاصيل.
- إضافة Unit Tests.

### المرحلة 2: Enhanced Release

الهدف: اعتماد الخطة وتحويلها إلى مهام.

المهام:

- حفظ `ApprovedBlueprint`.
- دعم `UserOverride`.
- تحويل الإجراءات إلى مهام.
- دعم `supportingAssets`.
- دعم `suggestedSolutions`.
- إضافة Integration Tests.

### المرحلة 3: Enterprise Release

الهدف: دمج مؤسسي.

المهام:

- Backend Workflows.
- إسناد ملاك.
- صلاحيات وموافقات.
- تصدير تقارير الامتثال.
- مكتبة قوالب مؤسسية.
- تكامل مع أدوات GRC أو ITSM.

---

## 19. خطة الاختبار

### 19.1 Unit Tests

- اختبار قالب `ART-POL`.
- اختبار قالب `ART-CTR`.
- اختبار دمج `sourceRuleIds`.
- اختبار إزالة التكرار.
- اختبار حساب الثقة.
- اختبار التعامل مع `UNKNOWN`.

### 19.2 Integration Tests

- اعتماد خطة.
- حفظ `ApprovedBlueprint`.
- تحويل الإجراءات إلى مهام.
- حفظ تعديلات المستخدم.

### 19.3 UI Tests

- ظهور البطاقة.
- تمييز المقترحات عن النص الأصلي.
- عرض تفاصيل `sourceRuleIds`.
- اختبار زر الاعتماد والتحويل.

### 19.4 Regression Tests

- تحديث `ruleVersion`.
- ضمان عدم تغير مخرجات القواعد الأساسية بشكل غير مقصود.
- مقارنة مخرجات المحرك قبل وبعد التحديث.

---

## 20. أمثلة عملية

### 20.1 `ART-POL` + `NAT-GOV` + `FUN-DIR`

الخطة: إعداد واعتماد سياسة حوكمية توجيهية.

الإجراءات:

- تحديد نطاق السياسة.
- صياغة المسودة.
- مراجعة لجنة الحوكمة.
- اعتماد السياسة.
- نشر السياسة.
- إعداد مواد توعوية.

الأدلة:

- وثيقة سياسة معتمدة.
- محضر اجتماع لجنة الحوكمة.
- سجل نشر وتوعية.

الجهد:

- `DOCUMENTATION`
- `GRC`
- `MEDIUM`

الأصول:

- قالب سياسة.
- قائمة تحقق مراجعة سياسة.

### 20.2 `ART-CTR` + `NAT-TEC` + `FUN-PRV`

الخطة: تطبيق ضابط تقني وقائي.

الإجراءات:

- تحديد نطاق الضابط.
- تحليل المتطلبات التقنية.
- إعداد التكوينات.
- اختبار الفعالية.
- التفعيل في الإنتاج.
- مراقبة الاستمرارية.

الأدلة:

- لقطات إعدادات.
- سجل تغيير.
- تقرير اختبار فعالية.

الجهد:

- `TECHNICAL_IMPLEMENTATION`
- `SECURITY_ENGINEERING`
- `HIGH`

الأصول:

- دليل إعداد تقني.
- قائمة تحقق اختبار.

### 20.3 `ART-PRC` + `NAT-OPS` + `FUN-DET`

الخطة: إعداد إجراء تشغيلي اكتشافي.

الإجراءات:

- توثيق خطوات التشغيل.
- تحديد مصادر الرصد.
- تحديد عتبات التنبيه.
- تكليف فرق التشغيل.
- مراجعة السجلات دوريًا.
- تصعيد الحالات الشاذة.

الأدلة:

- وثيقة إجراء.
- سجلات مراقبة.
- تقارير تنبيه.

### 20.4 `ART-STD` + `NAT-TEC` + `FUN-COR`

الخطة: إعداد معيار تقني تصحيحي.

الإجراءات:

- تحديد الحد الأدنى للمواصفات.
- تحديد آليات التصحيح.
- اعتماد المعيار.
- تطبيقه على الأنظمة.
- اختبار التصحيح.

الأدلة:

- وثيقة معيار.
- نتائج اختبار.
- سجل معالجة.

### 20.5 `ART-REQ` + `NAT-LEG` + `FUN-COMP`

الخطة: استيفاء متطلب قانوني بضابط تعويضي.

الإجراءات:

- تحليل المتطلب.
- مراجعة قانونية.
- تحديد الضابط التعويضي.
- توثيق سبب التعويض.
- اعتماد الاستثناء أو البديل.

الأدلة:

- رأي قانوني.
- سجل استثناء.
- موافقة الإدارة.

### 20.6 `ART-EVD` + `NAT-OPS`

الخطة: جمع وأرشفة دليل تشغيلي.

الإجراءات:

- تحديد الدليل المطلوب.
- تحديد مصدر الدليل.
- جمع الدليل دوريًا.
- حفظه في مستودع آمن.
- مراجعة صلاحيته.

الأدلة:

- سجل أرشفة.
- نموذج جمع أدلة.

### 20.7 `ART-RSK` + `NAT-GOV`

الخطة: معالجة مخاطرة حوكمية.

الإجراءات:

- تسجيل المخاطرة.
- تقييم الاحتمالية والأثر.
- تحديد مالك المخاطرة.
- اختيار استراتيجية المعالجة.
- عرضها على لجنة المخاطر.
- متابعة خطة المعالجة.

الأدلة:

- سجل مخاطر.
- محضر لجنة المخاطر.
- خطة معالجة.

---

## 21. الأخطاء التي يجب تجنبها

- تسمية المحرك بأنه ذكاء اصطناعي.
- تخزين الخطة المولدة داخل الكتالوج الأساسي.
- اعتبار `sourceRuleIds` مصادر معيارية خارجية.
- استخدام `sourceRuleId` مفرد بدل مصفوفة.
- جعل الاعتماد البشري يغير `confidence`.
- توليد توصيات منتجات محددة في الإصدار الأول.
- إخفاء سبب التوصية عن المستخدم.
- تحويل المقترحات إلى مهام بدون اعتماد.

---

## 22. معايير قبول MVP

يعد MVP مقبولًا إذا تحقق الآتي:

- يولد المحرك خطة مختلفة بناءً على `artifactType`.
- يطبق تخصيصات `controlNature`.
- يدمج `sourceRuleIds` عند التكرار.
- يعرض مستوى الثقة.
- يعرض بطاقة منفصلة عن النص الأصلي.
- لا يحفظ التوصيات كحقيقة امتثال.
- تغطي الاختبارات الحالات الأساسية.

---

## 23. التوصية النهائية

تم تنفيذ المحرك تدريجيًا بدءًا من طبقة المجال المشتركة الحالية:

```text
secureguide/blueprints/engine.py
```

مع قواعد معيارية مستقلة عن الواجهة داخل:

```text
reference/blueprint_rules_mvp_v1.json
```

عند ربط Flutter، يُنشأ محوّل خدمة وواجهات عرض فقط؛ لا تُنسخ القواعد إلى Dart كي لا يظهر مصدران للحقيقة.

الهدف الأول ليس بناء مكتبة قواعد ضخمة، بل إثبات صحة التصميم:

- هل ينتج `artifactType` خطة صحيحة؟
- هل تضيف الأبعاد الثانوية تخصيصًا منطقيًا؟
- هل يستطيع المستخدم فهم سبب التوصية؟
- هل تبقى التوصيات منفصلة عن الكتالوج الأصلي؟

بعد إثبات ذلك، يتم توسيع القواعد وربطها بإدارة المهام والأدلة.

القرار التنفيذي:

> التصميم مناسب للإنتاج إذا تم الالتزام بالفصل بين المصدر والتوصية، وباعتماد بشري قبل تحويل أي توصية إلى خطة رسمية أو مهمة تشغيلية.
