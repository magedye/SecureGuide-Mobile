# ROLLBACK_REPORT

> إثبات عكس دفعة ترقية (`AI-BATCH-1`) على قاعدة الاختبار `trial.db`، والعودة الكاملة إلى الحالة السابقة.
> التاريخ: 2026-07-11.

## قبل الـrollback
- `security_artifacts` = 4 (`SG-CTR-AI-02`, `SG-CTR-AI-05`, `SG-REQ-AI-06`, `SG-POL-AI-08`).
- `framework_mappings` = 6.
- `staging.promoted_artifact_id` مضبوط للأربعة.

## الأمر
```bash
python scripts/promote.py rollback --db trial.db --batch AI-BATCH-1
```

## ما فعله الـrollback (داخل transaction واحدة)
- حذف **فقط** ما أنشأته الدفعة (`promotion_batch_items.action='INSERT'`):
  - child rows: `framework_mappings` (6) + أي tags/relationships للعناصر.
  - سجلات `security_artifacts` الأربعة.
- أعاد `staging_artifacts.promoted_artifact_id` إلى `NULL` للأربعة.
- ضبط `promotion_batches.status = ROLLED_BACK` + `rolled_back_at`.
- سجّل حدث `ROLLBACK` في `promotion_audit_log`.

## بعد الـrollback
| القياس | القيمة |
|---|---|
| `security_artifacts` | **0** |
| `framework_mappings` | **0** |
| `staging.promoted set` | **0** |
| `raw_artifacts` | **2798** (دون تغيير) |
| `staging_artifacts` | محفوظ (لا حذف) |
| `PRAGMA integrity_check` | **ok** |
| حالة الدفعة | `ROLLED_BACK` |

## ضمانات السلامة (وفق `docs/PROMOTION_POLICY.md` §9)
- **لا** يحذف الـrollback عناصر كانت موجودة قبل الدفعة (يقتصر على صفوف الدفعة).
- **لا** يمسّ `raw_artifacts` ولا يحذف `staging_artifacts`.
- **يُرفض** الـrollback إذا أصبحت العناصر المُرقّاة مرتبطة ببيانات لاحقة (`profile_artifacts`/`artifact_relationships`/`template_items`) ما لم يُمرَّر `--force` موثّق (مُختبَر منطقياً في `promote.py`).

## بعد الـrollback: إعادة apply نظيفة
أُنشئت خطة/دفعة جديدة (`AI-BATCH-FINAL`) و`apply` أعاد الترقية إلى 4 عناصر بنجاح، integrity=ok — إثبات أن الـrollback أعاد حالة قابلة لإعادة الترقية.
