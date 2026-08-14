# سياسة الترقية (Promotion Policy / Contract)

> العقد الحاكم لنقل العناصر من `staging_artifacts` إلى الكتالوج المرجعي `security_artifacts`.
> تنفّذها [`scripts/promote.py`](../scripts/promote.py) وتتحقق منها [`scripts/validate_promotion.py`](../scripts/validate_promotion.py).
>
> عقد الحد الأدنى المعياري هو [`config/catalog_minimum_fields.yaml`](../config/catalog_minimum_fields.yaml). نتيجة `MINIMUM_CATALOG_VALIDATION` مستقلة عن نتيجة `STRICT_USACM_CONFORMANCE` وعن حالة المراجعة البشرية.

## القاعدة الذهبية
> **إما أن تُكتب جميع مكونات العنصر (السجل + mappings + tags + relationships) بنجاح داخل transaction واحدة، أو لا يُكتب شيء.**
لا يوجد كتابة جزئية. أي فشل في أي جزء يُرجِع الدفعة كاملة (ROLLBACK) ولا يترك أثراً في الكتالوج.

## 1. شروط الانتقال من staging إلى catalog
لا يدخل عنصر الكتالوج إلا إذا استوفى **كل** ما يلي (يفحصها `minimum_promotion_blockers`):
- `ready_for_promotion = 1`، وألا تكون `curation_status=REJECTED`.
- حالة المراجعة والثقة لا تمنعان الحد الأدنى وحدهما، لكن يجب تسجيلهما بمساءلة كاملة، ويمنعان النشر التلقائي عند انخفاض الثقة.
- لا `promotion_blockers` مفتوحة.
- فكرة أمنية **ذرّية واحدة** (لا يتجاوز التعريف المختصر فعلين إلزاميين).
- صياغة إنجليزية مكتملة (`title_en` + `definition_short_en`).
- `type` من USACM، `abstraction_level` صالح، `primary_domain`/`sub_domain` من SDT مع **انتماء** (`substr(sub,1,5)=primary`).
- `type` و`primary_domain` و`sub_domain` لا تقبل أي fallback، وعضوية الكود في جدول lookup لا تعني أنه صالح للنشر.
- `*-UNKNOWN` يتطلب مراجعة بشرية، و`*-MULTI` يتطلب التقسيم أو التطبيع؛ كلاهما يمنع الترقية.
- الحقول الإلزامية حسب النوع موجودة وصالحة (القسم 3).
- `lineage` مكتمل: `proposed_mappings_json` غير فارغ، كل مصدر له `raw_id` و`source_document` و`mapping_strength` صالح؛ وأي ربط غير `DIRECT` له `rationale`.

## 2. النتائج المستقلة
| `MINIMUM_CATALOG_VALIDATION` | `STRICT_USACM_CONFORMANCE` |
|---|---|
| يقبل المكتمل بنيوياً حتى مع `NOT_REVIEWED` أو ثقة منخفضة ظاهرة | يتطلب مراجعة/اعتماداً موثقاً وثقة متوافقة |
| يرفض `REJECTED` والبنية أو النسب أو النوع غير المكتمل | لا يغيّر نتيجة الحد الأدنى إلا إذا كشف مخالفة بنيوية مشتركة |
| يسمح بإثراء ناقص | يقيس المطابقة الصارمة دون إعادة تعريف USACM |

**منع الترقية الجزئية:** لا يُرقّى عنصر مركّب (مثل AI-04) — يجب تقسيمه أولاً إلى عناصر staging مستقلة، ثم تُرقّى المستقلة فقط.

## 3. الحقول الإلزامية لكل نوع USACM (قبل الترقية)
| النوع | حقول إلزامية إضافية |
|---|---|
| `ART-REQ` | `requirement_type` (RQT-*) |
| `ART-CTR` / `ART-CTE` | `control_nature` (NAT-*) + `control_function` (FUN-*) + `testability` (TST-*) |
| `ART-AST` | `asset_type` + `asset_criticality` |
| `ART-POL`/`ART-STD`/`ART-PRC` | `effective_date` فقط إن كان `publication_status=PUBLISHED` (الترقية تضع `APPROVED`، فلا يلزم) |
تُملأ هذه في المراجعة النهائية داخل أعمدة `proposed_*` على staging (هجرة 006).

## 4. توليد المعرّف النهائي
حتمي وقابل لإعادة الإنتاج: `SG-<TYPE>-<SUFFIX>` حيث `TYPE` = رمز USACM بلا بادئة، و`SUFFIX` من معرّف staging.
مثال: `STG-CANON-AI-02` (ART-CTR) → **`SG-CTR-AI-02`**. المعرّف ثابت للعنصر نفسه ⇒ يدعم idempotency ويكشف التعارض.

## 5. حفظ النسب (lineage)
- تُطبَّع مصادر `proposed_mappings_json` إلى صفوف `framework_mappings`.
- يُسجّل النسب النهائي مباشرة في `artifact_source_lineage`، ويكون لكل canonical صف صالح واحد على الأقل.
- يظل `staging_artifacts.promoted_artifact_id` رابط توافق فقط، وليس حد النسب النهائي.
- لكل خام إقرار واحد في `raw_artifact_dispositions`، ولا يُحذف `raw_artifacts` بسبب الدمج.

## 6. mappings والعلاقات والوسوم
- **mappings:** من `proposed_mappings_json` (كما أعلاه).
- **tags:** من `proposed_tags_json` → `artifact_tags` (`INSERT OR IGNORE`).
- **relationships:** من `proposed_relationships_json` → `artifact_relationships`.
كلها تُكتب داخل نفس الـtransaction.

## 7. مجموعات التكافؤ (equivalence groups)
يُحفظ `canonical_group_id` في الخطة. عند الترقية يبقى الربط عبر `equivalence_group_members` (تُضاف لاحقاً عند ترقية أعضاء المجموعة)؛ العنصر canonical في المجموعة يُرقّى، والأعضاء المؤجّلون يُربطون لاحقاً دون حذف.

## 8. إعادة التشغيل (Idempotency)
- عند `apply` يُعاد تقييم وجود المعرّف النهائي **وقت التنفيذ**:
  - موجود ومصدره نفس staging (`promoted_artifact_id` مطابق) ⇒ **SKIP** (لا تكرار).
  - موجود من مصدر مختلف ⇒ **CONFLICT** (يوقف، القسم 10).
  - غير موجود ⇒ **INSERT**.
- إعادة `apply` لنفس الخطة لا تنشئ تكراراً.

## 9. سياسة rollback
- يعكس **فقط** ما أنشأته الدفعة المحددة (صفوف `promotion_batch_items` بـ`action=INSERT`).
- يحذف child rows التي أنشأها (mappings/tags/relationships للعنصر) ثم سجل `security_artifacts`، ويعيد `promoted_artifact_id` إلى `NULL`.
- **لا** يحذف عناصر كانت موجودة قبل الدفعة، ولا يمسّ raw أو staging (عدا إعادة الرابط).
- **يُرفض** إذا أصبحت العناصر مرتبطة ببيانات لاحقة (`profile_artifacts`/`artifact_relationships`/`template_items`) ما لم يُستخدم `--force` موثّق.

## 10. التعارض عند وجود عنصر مُرقّى سابقاً
- إن كان المعرّف النهائي موجوداً من **نفس** staging ⇒ SKIP (آمن).
- إن كان موجوداً من مصدر **مختلف** ⇒ يُسجَّل CONFLICT في الخطة ويُوقف الـapply حتى يُحسم يدوياً (لا استبدال صامت).

## 11. منع الترقية على خطة قديمة (Optimistic Locking)
- تلتقط الخطة `content_hash` (بصمة المحتوى القابل للترقية) لكل عنصر staging.
- عند `apply` يُعاد حساب البصمة؛ إن اختلفت (تغيّر staging بعد الخطة) ⇒ **رفض الدفعة كاملة** دون كتابة، وتسجيل `REJECT` في التدقيق.

## 12. سجل التدقيق المطلوب
- `promotion_batches` (id, plan_hash, status, applied_at, rolled_back_at).
- `promotion_batch_items` (staging_id, final_artifact_id, source_staging_hash, action, عدد mappings/tags/relationships).
- `promotion_audit_log` (event ∈ PLAN/APPLY/APPLY_SKIP/ROLLBACK/REJECT/ERROR + detail + timestamp).
كل عملية plan/apply/rollback/رفض تُسجَّل.

## سير الأوامر
```bash
python scripts/promote.py validate --db <db>
python scripts/promote.py plan     --db <db> --batch <ID>      # ينتج خطة JSON + checksum
# مراجعة الخطة يدوياً
python scripts/promote.py apply    --db <db> --plan <plan.json>
python scripts/promote.py rollback --db <db> --batch <ID> [--force]
```
> **لا يُطبَّق على قاعدة العمل الرئيسية إلا بعد نجاح جميع الاختبارات على قاعدة اختبار.**
