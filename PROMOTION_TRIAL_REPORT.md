# PROMOTION_TRIAL_REPORT

> أول ترقية تجريبية على **قاعدة اختبار فقط** (`trial.db`)، للعناصر الأربعة المعتمدة نهائياً من Asset Inventory.
> التاريخ: 2026-07-11. لم تُطبَّق على قاعدة العمل الرئيسية. لم تُرقَّ أي عناصر PAM.

## العناصر المُرقّاة (batch-1)
| staging | المعرّف النهائي | النوع | Sub-domain |
|---|---|---|---|
| STG-CANON-AI-02 | `SG-CTR-AI-02` | ART-CTR | SD-02.01 |
| STG-CANON-AI-05 | `SG-CTR-AI-05` | ART-CTR | SD-02.01 |
| STG-CANON-AI-06 | `SG-REQ-AI-06` | ART-REQ | SD-02.02 |
| STG-CANON-AI-08 | `SG-POL-AI-08` | ART-POL | SD-08.05 |

## خطوات التجربة (كما نُفّذت)
| # | الخطوة | النتيجة |
|---|---|---|
| 1 | `validate` | كل العناصر الأربعة قابلة للترقية (0 blockers) |
| 2 | `plan AI-BATCH-1` | `{insert:4, skip:0, conflict:0}`، excluded=7 (المؤجّلة/المرفوضة/المقسّمة)، checksum=`26ffda04…` |
| 3 | مراجعة الخطة | راجع `docs/sample_promotion_plan.json` (النموذج) |
| 4 | `apply` | inserted=4 → `security_artifacts=4`، 6 framework_mappings |
| 5 | التحقق من الكتالوج | الأنواع/المجالات صحيحة، `ai_review_status=AIR-HUMAN-APPROVED`، `publication_status=APPROVED`، integrity=ok |
| 6 | إعادة `apply` (idempotency) | inserted=0، skipped=4 → لا تزال 4 (لا تكرار) |
| 7 | `rollback AI-BATCH-1` | `security_artifacts=0`، mappings=0، `promoted_artifact_id` أُعيد، raw=2798 |
| 8 | التحقق من العودة | الحالة السابقة مستعادة بالكامل، integrity=ok |
| 9 | `apply` نهائي (batch جديد) | `security_artifacts=4`، integrity=ok |

## الثوابت المحفوظة طوال التجربة
- `raw_artifacts = 2798` **دون تغيير** في كل الخطوات.
- `staging_artifacts` محفوظ (لا حذف)؛ يتغيّر فقط `promoted_artifact_id`.
- **لا كتابة جزئية**: كل apply داخل transaction واحدة (all-or-nothing).
- لم تُرقَّ **AI-03** (REJECTED) ولا أي عنصر `NEEDS_REVIEW`/`DEFERRED`.

## النسب (lineage) — مثال SG-CTR-AI-02
مربوط عبر `framework_mappings` بمصدرَي NIST CM-8(1) و CM-8(2) (DIRECT)، مع الحفاظ على `staging.promoted_artifact_id = SG-CTR-AI-02` و`raw_artifacts` سليمة.

## سجل التدقيق
`promotion_batches` (PLANNED→APPLIED→ROLLED_BACK→APPLIED)، `promotion_batch_items` (4 صفوف INSERT)، `promotion_audit_log` (PLAN/APPLY/APPLY_SKIP/ROLLBACK).

## الاختبارات
[`scripts/validate_promotion.py`](scripts/validate_promotion.py) — **20+ اختباراً كلها PASS** (رفض غير المعتمد/الناقص/غير الصالح، plan بلا كتابة، apply، تطبيع mappings/tags، idempotency، رفض الخطة القديمة، rollback، all-or-nothing، عدم ترقية AI-03/NEEDS_REVIEW، سلامة audit log، integrity بعد apply وrollback).

**لم تُطبَّق على قاعدة العمل الرئيسية. توقّفت بعد إثبات الترقية على قاعدة الاختبار.**
