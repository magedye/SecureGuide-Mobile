# مكتبة الأنماط التشغيلية

## الحالة والغرض

توفر `reference/operational_patterns_v1.json` أمثلة تشغيلية قابلة للبحث للاستفادة منها عند تصميم التنفيذ والأدلة. تحتوي النسخة `1.0.0` على 59 نمطاً مستخلصاً دون فقد من القائمة التشغيلية التي قدمها المستخدم، مع الاحتفاظ برقم الصف وبصمة المصدر.

التسمية الواجبة في الواجهة هي: **«اقتراحات معيارية بناءً على التصنيف»**.

هذه المكتبة:

- غير سلطوية (`authoritative=false`) وليست مصدراً أصلياً للمتطلبات.
- لا تضيف سجلات إلى `security_artifacts` ولا تغيّر النص الأصلي أو التصنيف المعتمد.
- لا تدخل تلقائياً في `GeneratedBlueprint` أو `ApprovedBlueprint`.
- لا تنشئ مهام ولا أدلة فعلية ولا قيماً تشغيلية داخل أي ملف مؤسسي.
- تبقى كل تصنيفاتها الأولية في `AIR-HUMAN-REVIEW` حتى اعتمادها بشرياً في سياق استخدام واضح.

## لماذا لم تُستورد كضوابط

الصف الواحد في القائمة قد يمثل ضابطاً أو معياراً أو عملية أو إجراءً أو إعداداً أو برنامجاً، وقد يجمع أكثر من مفهوم. استيراده كضابط واحد كان سيخالف USACM ويخلط المرجع بالتشغيل. لذلك حُفظت القائمة في طبقة مستقلة للبحث والإثراء، وصُنّف الغرض الغالب لكل نمط مع علم صريح عند الحاجة إلى التفكيك.

## البنية والحوكمة

| الحقل | الدلالة |
|---|---|
| `patternId` / `sourcePatternId` | هوية ثابتة قابلة للنسب، مثل `OPP-001` |
| `sourceRow` / `sourceTextAr` | تتبع الصف والنص المقدمين دون الادعاء بأنهما مرجع معياري |
| `recommendedArtifactType` | اقتراح أولي من أكواد USACM `ART-*` |
| `primaryDomain` / `subDomain` | تصنيف واحد متسق مع SDT |
| `controlNature` / `controlFunction` | يوجدان فقط للنوعين `ART-CTR` و`ART-CTE` |
| `testability` | قيمة USACM أولية مطلوبة عند اقتراح نوع ضابط |
| `requirementType` | قيمة USACM أولية مطلوبة فقط عند اقتراح `ART-REQ` |
| `implementationActions` | خطوات مثال؛ ليست أوامر تنفيذ ولا متطلبات أصلية |
| `evidenceExamples` | أمثلة لما قد يثبت التنفيذ؛ ليست `profile_evidence` فعلية |
| `ownerRoles` | أدوار مقترحة حرة؛ ليست تعيينات مستخدمين أو مسؤوليات ملف مؤسسي |
| `priority` | أولوية استرشادية؛ لا تستبدل أولوية العنصر أو تجاوز الملف المؤسسي |
| `classificationConfidence` / `classificationRationaleAr` | تفسير وثقة التصنيف الأولي |
| `requiresSplit` | يمنع ترقية البند المركب كما هو إلى عنصر مرجعي واحد |
| `safetyReviewRequired` / `safetyNoteAr` | يفرض ظهور تحذير قبل أي استعمال تنفيذي حساس |

`deliveryArchetype` و`effortSize` و`complexity` مفردات داخل هذه المكتبة وليست قيماً مضافة إلى قوائم USACM أو أعمدة الكتالوج.

## نتيجة التحويل

- 59 نمطاً محفوظاً بالترتيب من 1 إلى 59.
- 12 نمطاً مركباً بعلامة `requiresSplit=true`.
- 14 نمطاً حساساً للتغيير أو الحوادث بعلامة `safetyReviewRequired=true`.
- 19 ضابطاً، و11 عملية، و8 إعدادات تقنية، و7 معايير، و7 إجراءات، و3 متطلبات، وبرنامجان، وخطة، وسياسة.
- البنود المركبة لها ثقة أولية `0.68`، والبقية `0.82`؛ جميعها تحتاج مراجعة بشرية بصرف النظر عن الثقة.

## الاستخدام البرمجي

البحث قراءة فقط ولا يفتح SQLite:

```powershell
python -m secureguide --db catalog_work.db pattern-search --query "PAM"
python -m secureguide --db catalog_work.db pattern-search --domain SD-04 --sub-domain SD-04.03
python -m secureguide --db catalog_work.db pattern-search --safety-review --limit 100
```

تدعم الخدمة المرشحات `artifact_type` و`primary_domain` و`sub_domain` و`safety_review_required`. ترفض الخدمة القيم غير المضبوطة، وعدم تطابق المجال والفرع، وحدود النتائج خارج 1–200.

## الإثراء داخل Blueprint (منفّذ)

نُفّذ مسار إثراء المسودة من الأنماط في الترحيل [`024`](../migrations/024_blueprint_pattern_enrichment.sql). إذا اختار المؤلف نمطاً لإثراء **مسودة** خطة، تكون العملية صريحة وقابلة للتراجع وتحفظ على لقطة الخطة:

- `source_pattern_id` وصف المصدر `pattern_source_row`.
- `library_id` وإصدار المكتبة وبصمتها `library_sha256`.
- `selected_by` و`selected_at` و`selection_reason`.
- `copied_title_ar` و`copied_text_ar`: النص المنسوخ بعد تعديلات المؤلف، لا مرجعاً حياً يتغير بصمت.
- عند نمط `safetyReviewRequired=true` يجب إقرار صريح (`safety_acknowledged`) ويُحفظ `safety_note_ar`؛ وإلا تُرفض العملية.

الضمانات:

- الإثراء متاح فقط والخطة `DRAFT`؛ ومشغلات SQLite تمنع الإدراج والتعديل والحذف بعد مغادرة `DRAFT`.
- قابل للتراجع أثناء المسودة عبر `blueprint-enrich-remove`، مع سجل `blueprint_pattern_enrichment_events` ملحق فقط يحفظ `ADDED` ثم `REMOVED` (لا يُحذف بحذف الإثراء).
- يتجمّد الإثراء مع باقي اللقطة عند الإرسال ويرافق الخطة المعتمدة كنسب.
- `UNIQUE(blueprint_id,source_pattern_id)` يمنع تكرار إثراء النمط نفسه.

لا يجوز تحويل النمط مباشرة إلى مهمة. المسار يبقى: اختيار بشري → إثراء المسودة → مراجعة → اعتماد → تحويل الإجراء المعتمد إلى مهمة بطريقة idempotent.

```powershell
python -m secureguide --db catalog_work.db blueprint-enrich BLUEPRINT-ID --pattern OPP-001 --profile PROFILE-ID --by author --reason "سبب الاختيار" --text "نص معدّل" [--ack-safety]
python -m secureguide --db catalog_work.db blueprint-enrich-remove BLUEPRINT-ID --enrichment ENR-ID --profile PROFILE-ID --by author --reason "سبب التراجع"
```

## التحقق وإعادة البناء

```powershell
python scripts/build_operational_pattern_library.py <source-tsv-or-text>
python scripts/validate_operational_patterns.py
python -m unittest tests.test_operational_patterns -v
```

يتحقق الحارس من JSON Schema، وعدم تكرار مفاتيح JSON، وقيم USACM، وانتماء جميع فروع SDT الأربعين، والنسب، والثقة، وأعلام التفكيك والسلامة. لا يحتاج هذا الإصدار إلى ترحيل قاعدة بيانات لأنه مرجع قراءة فقط.
