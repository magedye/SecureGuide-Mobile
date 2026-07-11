# BASELINE_MANIFEST — SecureGuide Curation Baseline

> بيان الحالة المعتمدة للمشروع عند تثبيت أول baseline في Git، بعد Pilotَي Asset Inventory و Privileged Access.

| الحقل | القيمة |
|---|---|
| تاريخ الـBaseline | 2026-07-11 |
| الوسم | `baseline-curation-v1` |
| الفرع | `main` |
| USACM | v2.2.1 |
| SDT | v2.2.1 |

## الهجرات (migrations/) — 5
1. `001_initial_schema.sql` — النواة (intake + master catalog + 10 child tables + templates + profiles).
2. `002_assets_indicators_embeddings.sql` — الأصول + مؤشرات التهديد + التضمين/كشف التكرار.
3. `003_reference_data.sql` — 37 جدول lookup مفهرس ثنائي اللغة (مُولّد من `build_reference_data.py`).
4. `004_curation_layer.sql` — staging + batches + consolidation decisions + lessons + schema_migrations.
5. `005_views.sql` — 6 عروض للتنسيق والمنتج.

## أدوات التحقق (scripts/) — 8 حزم
`validate_schema` · `validate_schema_002` · `validate_reference_data` · `validate_curation` · `validate_pilot` · `validate_pilot_pam` · `validate_screen` · `validate_golden`.

## البيانات الخام
- ملفات كتالوج JSON: **21** (`SecureGuide_Mobile_Docs/Raw_Catalogs/`).
- العدد الفعلي للعناصر الخام: **2,798** (محسوب مستقلاً = مجموع JSON = raw في DB).
- الاستيراد **idempotent** (تشغيل ثانٍ = 0 إدراج).

## حالة الكتالوج
- **`security_artifacts` = 0** — لم يُرقَّ أي عنصر بعد (الترقية `promote.py` غير مبنية عمداً).
- كل مخرجات التوحيد في **staging فقط**.

## نتائج آخر تشغيل للاختبارات (Gate قبل الـCommit)
كل الحزم الثماني **PASS**. قاعدة جديدة من الصفر: الهجرات بالترتيب (integrity=ok)، استيراد مرتين (2798 ثم 0/0/2798)، `security_artifacts=0`.

## تقارير الـPilots والمراجعة (في الجذر)
- `AUDIT_REPORT.md`
- `ASSET_INVENTORY_PILOT_REPORT.md`
- `ASSET_INVENTORY_REVIEW_REPORT.md`
- `PRIVILEGED_ACCESS_PILOT_REPORT.md`
- `METHODOLOGY_READINESS_REPORT.md`
- `PROJECT_NOTES.md` · `SECUREGUIDE_AI_AGENT_BRIEF.md`

## قرارات التوحيد المعتمدة (consolidation/)
- `asset_inventory/AI-01…AI-10.json` (+ `index.json`, `unclassified.json`, `review.json`).
- `privileged_access/PA-01…PA-07.json` (+ `index.json`, `unclassified.json`).
- `screening/*.json` (مخرجات فرز — قابلة لإعادة التوليد عبر `screen.py`، محفوظة كدليل على مسار الـPilot).

## Golden Dataset
`tests/fixtures/golden/asset_inventory/` — 10 حالات + index، يتحقق منها `validate_golden.py`.

## القيود المعروفة
1. **الترقية إلى الكتالوج** (`promote.py`) غير مبنية — الحقول الناقصة (control fields, requirement_type, effective_date) تُستوفى عند الترقية.
2. **انتقاء المرشحين** (`screen.py`) عالي الدقة/متوسط الاستدعاء — يحتاج تمريرة قراءة وكيل على `POSSIBLY/NEEDS_REVIEW` قبل التوسّع.
3. **حديّات تحتاج مراجعة بشرية:** AI-03 (REJECTED)، AI-09 (WITH_CHANGES/NEEDS_REVIEW)، PA-03..PA-07 (ثقة ≤0.80).
4. **فجوات تغطية بيانات** (لا منهجية): مفاهيم PAM كـ vault/session/break-glass غير ظاهرة في الكتالوجات الحالية.
5. **الأرشيف** `_Archive/` مرجع تاريخي فقط — لا يُعتمد عليه.
6. تحذيرات Git `LF→CRLF` عند التسجيل (تطبيع أسطر على ويندوز) — غير مؤثّرة على المحتوى.

## الملفات المستبعدة من Git وأسبابها (`.gitignore`)
| النمط | السبب |
|---|---|
| `*.db`, `*.sqlite*` | قواعد بيانات تشغيلية/اختبار قابلة لإعادة التوليد عبر `ingest_raw.py` (منها `pilot.db`, `audit.db`, `secureguide.db`, `*_test.db`) — لا تُسجَّل |
| `__pycache__/`, `*.py[cod]`, `.pytest_cache/` | مخرجات بايت مؤقتة |
| `.venv/`, `venv/`, `env/` | بيئات افتراضية |
| `.idea/`, `.vscode/`, `.DS_Store`, `Thumbs.db` | ملفات IDE/نظام |
| `*.tmp`, `*.bak`, `*.log`, `*.orig`, `*~` | مؤقتات ونسخ احتياطية |

## فحوص السلامة قبل التسجيل
- **لا أسرار** (فحص مفاتيح/رموز/كلمات مرور) — نظيف.
- **لا `.db` في الـstaging** — مؤكَّد.
- **كل الملفات النصية المهمة UTF-8** — مؤكَّد.
- عدد الملفات المسجّلة: **181**.
