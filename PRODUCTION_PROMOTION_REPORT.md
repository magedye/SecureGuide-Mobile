# PRODUCTION_PROMOTION_REPORT

> أول دفعة ترقية إنتاجية محدودة: عناصر **Asset Inventory** المعتمدة الأربعة فقط، على قاعدة العمل `catalog.db`.
> التنفيذ: 2026-07-11 (UTC). لم تُرقَّ أي عناصر PAM ولا مؤجّلة/مرفوضة/مقسّمة.

## الهوية
| الحقل | القيمة |
|---|---|
| Batch ID | `AI-INV-PROD-20260711` |
| plan checksum | `e411524714f3dab4e4e85baffc39a3abaaff6c6442e7a14dd0b22420977cfe45` |
| مسار قاعدة العمل | `D:\APP\secure-guide\New folder\catalog.db` |
| مسار النسخة الاحتياطية | `D:\APP\secure-guide\New folder\catalog_backup_20260711T203543Z.db` |
| SHA-256 للنسخة الاحتياطية | `bc2274fbe12b2ac0da76a5ee8e8d9c7e4ecec03a62be549288cd6d3bbf64d894` |
| وقت التنفيذ / المنطقة الزمنية | 2026-07-11T20:35Z (UTC) |

> قاعدة العمل `catalog.db` أُنشئت حتميّاً من المصدر (migrations 001–006 → ingest → pilot_asset_inventory → final_review) بعد تعذّر تحديد قاعدة إنتاج من إعدادات المشروع (لا إعدادات؛ security_artifacts=0 في كل الملفات). قاعدة العمل والنسخة الاحتياطية **مستبعدتان من Git**.

## العناصر الأربعة ومعرفاتها النهائية
| staging | المعرّف النهائي | النوع | Sub-domain | mappings |
|---|---|---|---|---|
| STG-CANON-AI-02 | `SG-CTR-AI-02` | ART-CTR | SD-02.01 | 2 (CM-8(1)/(2) DIRECT) |
| STG-CANON-AI-05 | `SG-CTR-AI-05` | ART-CTR | SD-02.01 | 1 (CIS 1.2 DIRECT) |
| STG-CANON-AI-06 | `SG-REQ-AI-06` | ART-REQ | SD-02.02 | 1 (CIS 2.1 DIRECT) |
| STG-CANON-AI-08 | `SG-POL-AI-08` | ART-POL | SD-08.05 | 2 (ECC 2-1-3 DIRECT, 2-1-4 INDIRECT+rationale) |

## أعداد الصفوف (قبل → بعد)
| الجدول | قبل | بعد |
|---|---|---|
| security_artifacts | 0 | **4** |
| framework_mappings | 0 | **6** |
| artifact_tags | 0 | 0 |
| artifact_relationships | 0 | 0 |
| raw_artifacts | 2798 | **2798** (دون تغيير) |
| staging_artifacts | 11 | 11 (محفوظ) |
| promoted_artifact_id مضبوط | 0 | 4 |

## نتائج التحقق
- **integrity_check**: `ok` قبل التطبيق و`ok` بعده.
- **النسخة الاحتياطية**: صالحة (تفتح مستقلة، integrity=ok، أعداد الجداول الحرجة مطابقة).
- **raw artifacts**: المحتوى **مطابق للنسخة الاحتياطية** (aggregate hash) ⇒ لم يتغيّر.
- **§6 (16 فحصاً)**: كلها PASS — لا معرّفات مكررة، lineage مكتمل لكل عنصر، كل mapping صالح، غير DIRECT له rationale، انتماء sub_domain، `ai_review_status=AIR-HUMAN-APPROVED`، لا PAM/مؤجّل/مرفوض/مقسّم، `foreign_keys` مفعّل، حالة الدفعة **COMPLETED**.
- **idempotency**: إعادة تطبيق نفس الخطة → security_artifacts 4→4، mappings 6→6، لا دفعة مكررة (APPLY_SKIP×4).
- **عروض القراءة**: `v_artifact_detail` يعرض الأربعة بعدد mappings صحيح (2/1/1/2)؛ `v_review_queue` (كتالوج) = 0.
- **rollback**: أُعيد التحقق منه على قاعدة معزولة قبل الإنتاج (عكس كامل على مستوى الصفوف/المعرّفات، لا orphans) — راجع `ROLLBACK_REPORT.md`.

## حزم الاختبار التسع (على قواعد منفصلة، لا تمسّ catalog.db)
| # | الأمر | النتيجة |
|---|---|---|
| 1 | `python scripts/validate_schema.py` | PASS |
| 2 | `python scripts/validate_schema_002.py` | PASS |
| 3 | `python scripts/validate_reference_data.py` | PASS |
| 4 | `python scripts/validate_curation.py` | PASS |
| 5 | `python scripts/validate_pilot.py` | PASS |
| 6 | `python scripts/validate_pilot_pam.py` | PASS |
| 7 | `python scripts/validate_screen.py` | PASS |
| 8 | `python scripts/validate_golden.py` | PASS |
| 9 | `python scripts/validate_promotion.py` | PASS |

## التحذيرات
- تحذيرات Git `LF→CRLF` عند التسجيل (تطبيع أسطر على ويندوز) — غير مؤثّرة.
- إصلاح موثّق للأداة: حالة الدفعة النهائية أصبحت `COMPLETED` (كانت `APPLIED`) لمطابقة عقد المهمة — عُدّل `migrations/006` و`scripts/promote.py` وأُعيد اجتياز الحزم التسع.

## الملفات التي تغيّرت في Git (هذه المهمة)
`migrations/006_promotion_workflow.sql` (COMPLETED)، `scripts/promote.py` (COMPLETED)، `PRODUCTION_PROMOTION_PLAN.json` (خطة منقّحة بلا مسارات محلية)، `PRODUCTION_PROMOTION_PLAN_REVIEW.md`، `PRODUCTION_PROMOTION_REPORT.md`. **لم تُضَف** `catalog.db` ولا النسخ الاحتياطية.

## تعليمات الاستعادة من النسخة الاحتياطية
1. **أوقف أي عملية/اتصال** يستخدم `catalog.db` (لا كاتب نشط).
2. استعد النسخة بأمان: `copy "catalog_backup_20260711T203543Z.db" "catalog.db"` (بعد إيقاف الكتّاب)، أو افتح النسخة وأعد بناء العمل منها.
3. تحقّق: `sqlite3 catalog.db "PRAGMA integrity_check;"` يجب أن يعيد `ok`.
4. تحقّق من أعداد الجداول الحرجة: `raw_artifacts=2798`, `source_catalogs=21`, و`security_artifacts` = الحالة المستعادة (0 قبل الترقية).
5. طابِق SHA-256 للنسخة قبل الاعتماد: `bc2274fb…`.

**توقّف بعد تثبيت الدفعة الإنتاجية الأولى والتحقق منها. لم تبدأ PAM ولا أي عناصر إضافية.**
