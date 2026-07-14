# مسار اعتماد Blueprint وتحويله إلى مهام

## القرار المعماري

يبقى `GeneratedBlueprint` اقتراحًا مؤقتًا غير سلطوي. لا يدخل SQLite إلا عندما ينشئ مؤلف بشري مسودة تشغيلية داخل ملف مؤسسي. المسودة والنسخ اللاحقة لا تغير `security_artifacts`، وكل سجل يحمل `profile_id`, `profile_artifact_id`, و`artifact_id` المتطابقة.

الترحيل المنفذ: [`../migrations/023_blueprint_approval_tasks.sql`](../migrations/023_blueprint_approval_tasks.sql).

## الجداول

| الجدول | المسؤولية |
|---|---|
| `approved_blueprints` | رأس الخطة وإصدارها وحالتها ونسب المحرك وحزمة القواعد وبصمة الحمولة. الاسم يمثل وجهة دورة الحياة؛ الصف يبدأ دائمًا `DRAFT`. |
| `approved_blueprint_rules` | لقطة مطبعة للقواعد المطبقة وإصداراتها. |
| `approved_blueprint_actions` | الإجراءات المعتمدة المرشحة للتحويل إلى مهام. |
| `approved_blueprint_action_rules` | نسب كل إجراء إلى قواعده دون مصفوفة JSON. |
| `approved_blueprint_outputs` و`approved_blueprint_output_rules` | المخرجات المتوقعة ونسبها. |
| `approved_blueprint_evidence` و`approved_blueprint_evidence_rules` | متطلبات الأدلة ونسبها؛ ليست أدلة تنفيذ فعلية. |
| `blueprint_review_events` | سجل ملحق فقط للإنشاء والإرسال والإرجاع والاعتماد والاستبدال والإلغاء وإنشاء المهام. |
| `approved_blueprint_review_findings` | لقطة مطبعة لأسباب المراجعة وأحداث التطبيع وتعارضات التوليد التي عالجها المعتمد. |
| `approved_blueprint_pattern_enrichments` | إثراءات المسودة من مكتبة الأنماط التشغيلية: هوية النمط ونسب المكتبة وبصمتها، والنص المنسوخ بعد تعديل المؤلف، وإقرار السلامة، وسبب الاختيار. (الترحيل `024`) |
| `blueprint_pattern_enrichment_events` | سجل ملحق فقط لإضافة الإثراء وتراجعه (`ADDED`/`REMOVED`) يبقى بعد حذف الإثراء. |
| `profile_tasks` | المهام الفعلية الخاصة بالملف، مرتبطة بإجراء معتمد واحد. |
| `profile_task_events` | سجل تغير حالة المهمة. |

لا تخزن `sourceRuleIds` كمصفوفة JSON؛ جداول الربط هي المرجع. وتبقى الأدلة الفعلية التي تجمعها المؤسسة في `profile_evidence`.

## آلة حالات الخطة

```text
DRAFT ──AUTHOR──> UNDER_REVIEW ──APPROVER──> APPROVED ──APPROVER──> SUPERSEDED
  │                    │
  └──AUTHOR──> CANCELLED
                       ├──REVIEWER──> DRAFT
                       └──REVIEWER──> CANCELLED
```

- الإدراج المباشر بحالة غير `DRAFT` ممنوع.
- الإرسال يتطلب إجراءات وأدلة ونسب قواعد مطبعة لكل منها.
- محتوى اللقطة يصبح غير قابل للتعديل بعد الإرسال.
- الاعتماد لا يتم إلا من `UNDER_REVIEW` وبواسطة دور `APPROVER`.
- إذا حمل التوليد علامة مراجعة، تصبح `review_resolution_note` إلزامية.
- توجد خطة واحدة قيد التأليف/المراجعة، وخطة واحدة معتمدة، لكل `profile_artifact`.
- اعتماد إصدار جديد يستبدل الإصدار المعتمد السابق داخل المعاملة نفسها.
- `SUPERSEDED` و`CANCELLED` حالتان نهائيتان.

الأدوار هنا أدوار سير عمل مسجلة للتدقيق وليست نظام مصادقة. عند إضافة إدارة المستخدمين، يجب على طبقة المصادقة إثبات أن الفاعل يملك الدور قبل استدعاء الخدمة.

## إثراء المسودة من الأنماط التشغيلية

يستطيع المؤلف إثراء مسودة خطة بنمط تشغيلي غير سلطوي من مكتبة الأنماط دون أن يتحول النمط إلى مهمة:

- الإثراء متاح فقط والخطة `DRAFT`؛ ومشغلات SQLite تمنع الإدراج والتعديل والحذف بعد مغادرة `DRAFT`.
- تُحفظ على اللقطة هوية النمط ورقم صفه، ونسب المكتبة وإصدارها وبصمة `sha256`، والنص المنسوخ **بعد** تعديل المؤلف (لا مرجعاً حياً)، ومن اختار ومتى ولماذا.
- نمط `safetyReviewRequired` يتطلب إقرار سلامة صريحاً وإلا يُرفض الإثراء؛ ويُحفظ نص التحذير.
- `UNIQUE(blueprint_id,source_pattern_id)` يمنع تكرار إثراء النمط نفسه على الخطة.
- الإثراء قابل للتراجع أثناء المسودة، مع سجل أحداث ملحق فقط يبقي `ADDED` ثم `REMOVED`.
- عند الإرسال يتجمّد الإثراء مع باقي اللقطة ويرافق الخطة المعتمدة كنسب.

بوابة الحوكمة `v_blueprint_enrichment_governance_issues` ترجع صفراً في القاعدة السليمة، وتكشف إثراءً بلا إقرار سلامة أو بنسب مكتبة ناقص أو بتعارض مجال/فرع.

## إنشاء المهام

- لا تنشأ مهمة إلا من `approved_blueprint_actions.taskable=1` وخطة حالتها `APPROVED`.
- مشغل SQLite يتحقق من تطابق الملف والخطة والإجراء.
- `UNIQUE(blueprint_action_id)` يجعل إعادة الأمر آمنة؛ الإعادة ترجع المهمة الموجودة بدل نسخها.
- استبدال الخطة لا يحذف مهام الإصدار السابق ولا يغيرها بصمت؛ تبقى قابلة للتتبع ويقرر المستخدم إكمالها أو إلغاءها.
- حالات المهمة: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `CANCELLED`. الحالتان الأخيرتان نهائيتان.

## التقارير

التقرير الرسمي لا يعرض `GeneratedBlueprint` ولا المسودات. يعرض فقط الصفوف ذات الحالة `APPROVED` والمهام الخاصة بالملف، مع أعداد المهام المفتوحة. الخطط المستبدلة تبقى في سجل التدقيق ولا تظهر كخطة حالية معتمدة.

## أوامر CLI

```powershell
python -m secureguide --db catalog_work.db blueprint-draft ARTIFACT-ID --profile PROFILE-ID --by author
python -m secureguide --db catalog_work.db blueprint-enrich BLUEPRINT-ID --pattern OPP-001 --profile PROFILE-ID --by author --reason "سبب الاختيار" --text "نص معدّل" --ack-safety
python -m secureguide --db catalog_work.db blueprint-enrich-remove BLUEPRINT-ID --enrichment ENR-ID --profile PROFILE-ID --by author --reason "سبب التراجع"
python -m secureguide --db catalog_work.db blueprint-submit BLUEPRINT-ID --profile PROFILE-ID --by author
python -m secureguide --db catalog_work.db blueprint-return BLUEPRINT-ID --profile PROFILE-ID --by reviewer --note "Required changes"
python -m secureguide --db catalog_work.db blueprint-approve BLUEPRINT-ID --profile PROFILE-ID --by approver
python -m secureguide --db catalog_work.db blueprint-tasks BLUEPRINT-ID --profile PROFILE-ID --by approver
python -m secureguide --db catalog_work.db task-list --profile PROFILE-ID
python -m secureguide --db catalog_work.db task-update TASK-ID --profile PROFILE-ID --by operator --status IN_PROGRESS
```

## الاسترداد

قبل تطبيق 023 على قاعدة قائمة، تنشأ نسخة احتياطية متسقة باستخدام SQLite backup API. الترحيل إضافي ولا يعدل الكتالوج، لكن الرجوع البنيوي الآمن يكون باستعادة النسخة السابقة، لا بحذف الجداول جزئيًا.
