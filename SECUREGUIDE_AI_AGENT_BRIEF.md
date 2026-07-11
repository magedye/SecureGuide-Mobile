# SecureGuide AI Agent Brief

> استخدم هذه الوثيقة كتعليمات مركزة لوكيل الذكاء الاصطناعي الذي سيعمل على مشروع SecureGuide. الهدف هو توحيد الفهم قبل أي معالجة أو كود أو تعديل بيانات.

## 1. الهدف العام

SecureGuide هو تطبيق offline-first لإدارة كتالوج معرفة أمني وتقييمات مبنية على ملفات profile. المطلوب الآن ليس بناء منصة استيراد عامة، بل معالجة المجموعة الخام الموجودة حالياً وتحويلها إلى كتالوج SecureGuide موحد، إنجليزي، قابل للتصنيف والبحث والتقييم.

المسار المركزي:

```text
Raw_Catalogs JSON
  -> raw_artifacts
  -> staging / curation
  -> English canonical draft
  -> USACM + SDT classification
  -> similarity and merge suggestions
  -> review / correction
  -> approved security_artifacts
  -> FTS5 search + indexes + profile views
```

## 2. المراجع الحاكمة

يجب الاعتماد أولاً على:

1. `SecureGuide_Mobile_Docs/USACM_v2.2.1_Unified_Security_Artifact_Classification_Model.md`
2. `SecureGuide_Mobile_Docs/SDT_v2.2.1_Security_Domain_Taxonomy.md`

ثم السياسات التالية:

1. `docs/CLASSIFICATION_POLICY.md`
2. `docs/AUTHORING_POLICY.md`
3. `docs/CONSOLIDATION_POLICY.md`
4. `docs/EMBEDDING_POLICY.md`
5. `docs/RELATIONSHIP_POLICY.md`
6. `docs/DATA_DICTIONARY.md`

USACM وSDT هما النواة الرسمية. أي إضافة جديدة يجب أن تكون SecureGuide extension مربوطة بأقرب قيمة رسمية، وليست بديلاً عشوائياً عن التصنيف الأساسي.

## 3. البيانات الحالية

المصادر موجودة في:

`SecureGuide_Mobile_Docs/Raw_Catalogs`

الحالة المعروفة:

- 21 ملف JSON.
- 2,798 عنصر خام.
- البنية العامة: `extraction_metadata` + `artifacts`.
- أكبر المصادر:
  - NIST SP 800-53 Rev.5: 1196 عنصر.
  - MITRE ATT&CK Enterprise: 858 عنصر.
  - OWASP ASVS 5.0.0: 345 عنصر.
  - ECC 2024: 108 عناصر.
  - NIST CSF 2.0: 106 عناصر.

هذه المجموعة كافية للـMVP. الاستيراد المستقبلي نادر، لذلك لا تبن import platform واسعاً في البداية.

## 4. قرارات التصميم الأساسية

1. **المعالجة أهم من الاستيراد**
   ركز على batch processing للمجموعة الحالية.

2. **English-first**
   الحقول الإنجليزية هي الحقول الأساسية للاعتماد. العربية تؤجل كترجمة/إثراء لاحق.

3. **إعادة الصياغة بدل النسخ**
   لا تنشر النصوص الأصلية الكاملة للضوابط. أنشئ صياغة SecureGuide أصلية مع حفظ النسب.

4. **النسب قبل الاقتباس**
   احفظ المصدر، الإصدار، القسم، raw ID، وmapping strength. لا تعتمد على `source_quote` كنص كامل.

5. **التوحيد والدمج جزء أساسي**
   عدة ضوابط من مصادر مختلفة يمكن أن تتحول إلى عنصر SecureGuide واحد إذا كانت تعبر عن نفس الفكرة الأمنية.

6. **التضمين للمعالجة، وFTS5 للمنتج**
   استخدم embeddings لاكتشاف التشابه والدمج. استخدم FTS5 لاحقاً للبحث السريع فوق الكتالوج المعتمد.

7. **المرونة قبل التعقيد المؤسسي**
   لا تبن workflows موافقات ثقيلة. اجعل التصحيح اليدوي سهلاً، والتحقق ذكياً وخفيفاً.

8. **لا risk scoring مبكر**
   لا تعرض درجات خطر أو نضج قبل توثيق الصيغة والمدخلات.

## 5. ما يجب فعله

### 5.1 معالجة العناصر الخام

- اقرأ ملفات `Raw_Catalogs`.
- خزّن الأصل في `raw_artifacts`.
- أنشئ staging/curation layer للمعالجة.
- لا تكتب مباشرة في `security_artifacts` قبل التحقق.

### 5.2 صياغة العنصر

لكل عنصر معتمد أو مسودة canonical:

- `title_en`
- `definition_short_en`
- `definition_full_en`
- `objective_en`
- `canonical_statement` عند الحاجة
- `classification_rationale`
- source lineage

اتبع `AUTHORING_POLICY.md`.

### 5.3 التصنيف

لكل عنصر:

- `type` من USACM.
- `abstraction_level`.
- `primary_domain` من SDT.
- `sub_domain` من SDT.
- `classification_confidence`.
- `classification_rationale`.
- `requires_human_review` عند انخفاض الثقة.

لا تصنف كل شيء كـ`ART-CTR`. استخدم `ART-CFG` للإعدادات التقنية، `ART-REQ` للمتطلبات، `ART-EVD` للأدلة، وهكذا.

### 5.4 التوحيد والدمج

اتبع `CONSOLIDATION_POLICY.md`.

قرارات الدمج الممكنة:

- `CANONICALIZE`
- `EQUIVALENCE_GROUP`
- `CROSSWALK_ONLY`
- `RELATE_ONLY`
- `KEEP_SEPARATE`
- `DEPRECATE_DERIVED`

لا تحذف السجلات الخام. الدمج يعني حفظ lineage وربط المصادر، لا فقدان الأصل.

### 5.5 Curation Workbook

اقترح أو نفذ تصدير Excel/CSV منظم للمراجعة الخارجية.

الـ workbook المثالي يحتوي sheets:

- `artifacts`
- `mappings`
- `tags`
- `relationships`
- `lookups`
- `proposed_values`

الاستيراد الراجع يجب أن يدخل staging أولاً، مع تقرير فروقات، validation، واعتماد انتقائي.

## 6. ضمان الجودة والاستقرار

استخدم طبقات ضبط خفيفة:

1. Stable core schema.
2. SQLite constraints: FK, CHECK, UNIQUE, NOT NULL.
3. Services بين الواجهة والقاعدة.
4. Views للعرض بدلاً من تكرار الاستعلامات.
5. Data integrity validation.
6. Golden dataset صغير.
7. Idempotent batch processing.
8. Snapshot قبل الاستيراد أو التعديلات الجماعية.
9. Quality score للعنصر، وليس risk score.
10. Validation dashboard.

Views مقترحة:

- `v_catalog_curation`
- `v_artifact_detail`
- `v_review_queue`
- `v_duplicate_candidates`
- `v_profile_dashboard`
- `v_gap_analysis`

## 7. ضمان صحة التصنيفات

اتبع الآتي:

1. استخدم قوائم USACM/SDT المعتمدة فقط للحقول الأساسية.
2. تحقق أن `sub_domain` يتبع `primary_domain`.
3. خزّن confidence وrationale لكل تصنيف آلي.
4. اعرض البدائل عند الغموض.
5. اسمح بتصحيح يدوي مباشر من القيم المعتمدة.
6. تعلم من التصحيحات المتكررة لتحسين prompts والقواعد.
7. لا تضف نوع USACM أو مجال SDT جديد مباشرة؛ استخدم extension أو tag أو alias.

## 8. ما يجب تأجيله

- import platform عام ومتعدد الصيغ.
- الترجمة العربية الشاملة.
- البحث العربي والتضمين متعدد اللغات.
- المزامنة والمشاركة والتعاون.
- roles/users/workflows مؤسسية ثقيلة.
- risk scoring أو maturity scoring قبل توثيق الصيغة.
- واجهة ضخمة قبل اختبار views والاستعلامات.
- تكاملات خارجية متقدمة.

## 9. مخرجات مقترحة للوكيل

عند العمل على المشروع، قدم مخرجات صغيرة ومتسلسلة:

1. تقرير فهم للمخطط والسياسات.
2. تصميم staging/curation tables أو models.
3. batch processor قابل للإعادة.
4. عينة معالجة من 20-50 عنصر.
5. تقرير تصنيف وتوحيد للعينة.
6. golden dataset أولي.
7. validation queries.
8. export/import Curation Workbook prototype.
9. views أساسية للـcuration والبحث.
10. خطة ترقية العناصر المعتمدة إلى `security_artifacts`.

## 10. قواعد المنع

لا تفعل الآتي:

- لا تخزن الحالة التشغيلية داخل `security_artifacts` كحقيقة عالمية.
- لا تعامل كل العناصر كضوابط.
- لا تخترع قيم enum خارج USACM/SDT.
- لا تجعل tags بديلاً عن domain/sub-domain.
- لا تكرر arrays داخل `security_artifacts` بدلاً من الجداول الفرعية.
- لا تنشر low-confidence classification.
- لا تدمج مصادر دون حفظ lineage.
- لا تحذف raw artifacts.
- لا تنشئ mappings بلا strength/rationale عند الحاجة.
- لا تعرض risk score بلا صيغة.

## 11. الخلاصة التنفيذية

أفضل اتجاه الآن هو بناء **Quality & Curation Layer** فوق البيانات الحالية:

- يعالج 2,798 عنصر خام.
- يصوغها إنجليزياً.
- يصنفها بـUSACM/SDT.
- يوحد المتشابه.
- يحفظ نسب المصادر.
- يسمح بتصحيح سهل.
- يصدّر workbook للمراجعة بالذكاء الاصطناعي.
- يستورد التحسينات بعد validation.
- ينشر فقط العناصر المعتمدة إلى الكتالوج.

نجاح SecureGuide في هذه المرحلة يعتمد على جودة الكتالوج ونظافة التصنيف أكثر من كثرة الميزات.
