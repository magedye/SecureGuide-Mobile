# المسار التشغيلي للملف المؤسسي

يطبق هذا المسار شريحة MVP كاملة فوق SQLite مع إبقاء تعريف العنصر في الكتالوج المرجعي وحالته داخل الملف المؤسسي.

## الطبقات المنفذة

| الطبقة | التنفيذ | المسؤولية |
|---|---|---|
| Presentation Adapter | `secureguide/cli.py` | أوامر قابلة للاستبدال لاحقاً بواجهة Flutter أو API محلي. |
| Service & State | `secureguide/services.py` | الملف النشط، المعاملات، قواعد القالب والتقييم والاستثناء، والأحداث. |
| Core Engine | `scripts/scoring.py` | احتساب `profile-score-v1` والتوصيات القابلة للتفسير. |
| Data Access | `secureguide/repositories.py` | استعلامات الكتالوج والملفات والقوالب؛ كل استعلام تشغيلي يحمل `profile_id`. |
| Storage | SQLite + migration 021 | قيود المفاتيح، مصادر الاختيار، سلامة الأدلة، وعروض القراءة. |

## ضمانات المسار

- `security_artifacts` لا يتغير عند اختيار عنصر أو تقييمه.
- `profile_artifacts` يخزن الحالة الحالية، و`profile_assessments` يخزن لقطة تاريخية غير قابلة للتعديل.
- يستطيع العنصر داخل الملف أن يأتي يدوياً ومن عدة قوالب عبر `profile_artifact_origins` دون نسخ تعريفه، ويرتبط كل مصدر قالب بسجل التطبيق والإصدار الدقيق في `profile_templates`.
- أولوية القالب وتواتره قيم افتراضية منفصلة عن تعديل المؤسسة الصريح.
- لا يمكن ربط دليل بتقييم يخص عنصراً تشغيلياً آخر، حتى لو كان العنصر المرجعي نفسه مستخدماً في ملف ثانٍ.
- حالة الاستثناء لا تُكتب مباشرة؛ تتغير فقط بعد اعتماد `profile_exceptions` وفق آلة الحالات.
- `EXC-NOT-APPLICABLE` و`EXC-UNAVAILABLE` يخرجان من المقام، بينما `EXC-DEFERRED` و`EXC-RISK-ACCEPTED` يبقيان فجوة مفتوحة.
- عمليات الكتابة تنفذ داخل `BEGIN IMMEDIATE` مع `PRAGMA foreign_keys=ON`، وتنشر الأحداث بعد نجاح الالتزام فقط.

## دورة الاستخدام

```text
profile-create → profile-activate
      ↓
catalog-search → profile-select / template-apply
      ↓
assess → evidence-add
      ↓
exception-create → exception-submit → exception-approve
      ↓
dashboard → report
```

## أمثلة

```powershell
python -m secureguide --db catalog_work.db migrate
python -m secureguide --db catalog_work.db profile-create --name "المقر الرئيسي" --id PRF-HQ --activate
python -m secureguide --db catalog_work.db catalog-search --query identity --domain SD-03
python -m secureguide --db catalog_work.db profile-select ARTIFACT-ID --by analyst
python -m secureguide --db catalog_work.db assess ARTIFACT-ID --assessor auditor --implementation-status STS-FULL --verification-status VER-PASS --effectiveness EFF-HIGH
python -m secureguide --db catalog_work.db dashboard
python -m secureguide --db catalog_work.db report --output profile-report.json
```

## نموذج القراءة للواجهة

- `v_active_profile_context`: الملف النشط المستمر محلياً.
- `v_profile_operational_items`: تعريف الكتالوج مع حالة ملف واحد وأولوية/تواتر فعليين وعدد الأدلة.
- `v_profile_dashboard`: أعداد التطبيق والتحقق والاستثناء والفجوات والمواعيد المتأخرة.
- `v_gap_analysis`: فجوات الملف وفق سياسة الاستثناء المعتمدة.
- `v_profile_evidence_integrity_issues`: بوابة كشف أي ربط قديم غير صحيح بين الدليل والتقييم.
- `v_profile_origin_governance_issues`: بوابة كشف نسب قالب ناقص أو غير مطابق للملف والعنصر والإصدار.

الواجهة المستقبلية يجب أن تستخدم `SecureGuideService` أو واجهة مكافئة، ولا تنفذ SQL أو قواعد الاستثناء والاحتساب داخل مكونات العرض.
