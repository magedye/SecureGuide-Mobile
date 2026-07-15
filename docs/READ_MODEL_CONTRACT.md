# عقد القراءة (Read-Model / DTO) — `read-model-v1`

عقدٌ مستقر لأشكال القراءة التي تعتمد عليها واجهة Flutter (والـAPI المحلي لاحقًا)،
مبنيّ فوق [`SecureGuideService`](../secureguide/services.py) في طبقة نقية:
[`secureguide/read_models.py`](../secureguide/read_models.py).

هذه الطبقة تُبنى **قبل أي شاشة** لتعزل الواجهة عن التمثيل الداخلي وتطبّق مبدأ
«لا قواعد أعمال في العرض». وهي امتدادٌ لنفس فصل العرض الذي يجسّده مُصيّر HTML في
[`secureguide/reporting.py`](../secureguide/reporting.py): دالة نقية تحوّل مخرجات
الخدمة إلى عرضٍ دون إعادة احتساب أي قاعدة.

## لماذا عقدٌ منفصل

الخدمة تُرجع `dict` خامًا يعكس التخزين الداخلي، وهو تمثيل **غير متسق** أصلًا:

- صفوف القراءة المستمرة `snake_case` (`workflow_status`, `artifact_id`,
  `implementation_status`) عبر `SELECT *` من الجداول/العروض — أي إضافة عمود تتسرّب
  مباشرة إلى الواجهة.
- بينما محرّك الـBlueprint (`generate_blueprint`) يُصدر `camelCase`
  (`blueprintId`, `ruleSetHash`, `appliedRules`).

العقد يخفي هذا التباين خلف سطحٍ واحد ثابت. **الشاشات تربط بهذا السطح فقط، ولا تنفّذ
SQL ولا قواعد الاستثناء/الاحتساب/الاعتماد.**

## المبادئ

| المبدأ | التطبيق |
|---|---|
| اصطلاح واحد على السلك | `camelCase` (اصطلاح Dart/JSON، ويوحّد مع مخرجات المحرّك). |
| إصدار صريح | كل حمولة عليا تحمل `contractVersion: "read-model-v1"`. |
| اختيار حقول صريح | كل DTO يقرأ حقولًا مُسمّاة عبر `dict.get`، فإضافة عمود لا تُسرَّب ولا تكسر. |
| تطبيع تمثيل فقط | تحويل أعلام SQLite العددية (0/1) إلى `bool` حقيقي، وإعادة التسمية — **دون** إعادة تصنيف أو احتساب. |
| لا احتساب | القيم (النتيجة، الأعداد، الفجوات) تمرّ كما هي من الخدمة؛ يختبرها `test_dashboard_passes_service_values_through_unchanged`. |

## الأسطح (`ReadModel`)

كل دالة تُرجع `dict` قابلًا للتسلسل إلى JSON، مغلّفًا بـ`contractVersion`.
العيّنة الرسمية لكل سطح محفوظة (مُنقّاة من المعرّفات والطوابع الزمنية المتغيّرة) في
[`tests/fixtures/read_models/`](../tests/fixtures/read_models).

| الدالة | الشاشة | جسم الحمولة | العيّنة |
|---|---|---|---|
| `profiles()` | منتقي الملف | `profiles[]` | [`profiles.json`](../tests/fixtures/read_models/profiles.json) |
| `active_profile()` | شريط التطبيق | `profile` أو `null` | [`active_profile.json`](../tests/fixtures/read_models/active_profile.json) |
| `dashboard(profile_id)` | الرئيسية | `profile,counts,score,gaps[],recommendations[],reviewQueue[]` | [`dashboard.json`](../tests/fixtures/read_models/dashboard.json) |
| `catalog(...)` | عارض الكتالوج | `locale,query,limit,offset,count,items[]` | [`catalog.json`](../tests/fixtures/read_models/catalog.json) |
| `blueprints(profile_id,...)` | قائمة الخطط | `blueprints[]` (بعناوين وعدّادات) | [`blueprints.json`](../tests/fixtures/read_models/blueprints.json) |
| `blueprint(blueprint_id,...)` | تفصيل الخطة | `blueprint` (اللقطة الكاملة + المجموعات المتداخلة) | [`blueprint_detail.json`](../tests/fixtures/read_models/blueprint_detail.json) |
| `tasks(profile_id,status)` | المهام | `tasks[]` | [`tasks.json`](../tests/fixtures/read_models/tasks.json) |
| `report(profile_id)` | التقرير الرسمي | مظروف بالخطط المعتمدة فقط | [`report.json`](../tests/fixtures/read_models/report.json) |

### ملاحظات على التصميم

- **العدّادات والعناوين للقائمة، لا للتفصيل.** سطح `blueprints` يحمل
  `artifactTitleEn/Ar` و`actionCount/evidenceCount/taskCount` من العرض
  `v_profile_blueprints`. أما `blueprint(...)` فيحمل اللقطة الكاملة والمجموعات
  المتداخلة (`actions`, `evidence`, `expectedOutputs`, `appliedRules`,
  `patternEnrichments`, `reviewFindings`)؛ والعدد هو طول المصفوفة.
- **`isSelected`** في الكتالوج علمٌ عرضي بسيط = وجود `profileArtifactId` الذي حلّته
  الخدمة (ليس قاعدة أعمال).
- **`isActive`** في ملف اللوحة/التقرير قد يكون `null` لأن صف الملف لا يؤكّد النشاط؛
  استخدم `profiles()`/`active_profile()` لحالة النشاط.
- **إثراءات الأنماط** (`patternEnrichments`) تبقى «اقتراحات معيارية بناءً على
  التصنيف» غير سلطوية، محفوظة كنسب على اللقطة — لا تتحوّل إلى مهام.

## عقد الكتابة والـsidecar

القراءة والكتابة تصلان النواة عبر **sidecar محلي** (بايثون كما هو) على `127.0.0.1`
([`secureguide/sidecar.py`](../secureguide/sidecar.py))، والقواعد تبقى في الخدمة:

- **قراءة (GET):** `/read/profiles` · `/read/active-profile` · `/read/dashboard` ·
  `/read/catalog` · `/read/blueprints[/{id}]` · `/read/tasks` · `/read/report` ·
  `/health`. كل نقطة تُرجع سطحها كما في الجدول أعلاه.
- **كتابة (POST):** أجسام camelCase، وتُرجع المورد المتأثّر كـDTO قراءة داخل نفس
  المظروف المُصدَّر الإصدار. المتوفّر الآن:
  - `POST /write/profiles` — `{name, profileKind?, …, activate?}` → `{profile}`.
  - `POST /write/active-profile` — `{profileId}` → `{profile}`.
- أخطاء المجال تُترجَم لأكواد HTTP: 400 (تحقّق/قيمة)، 404 (غير موجود)، 403 (تفويض).
- طبقة الكتابة [`secureguide/write_models.py`](../secureguide/write_models.py) (`WriteModel`)
  متناظرة مع `ReadModel`: إعادة تسمية مفاتيح وتغليف فقط، دون قواعد أعمال.

تشغيل: `python -m scripts.build_release_db` ثم `python -m secureguide.sidecar`،
والتطبيق يخاطبه عبر `SecureGuideClient` (تنفيذ `HttpSecureGuideClient`).

## جانب Dart

يعكس فريق Flutter هذه الأشكال أصنافَ بيانات مقابلة (`fromJson`/`toJson`) بالمفاتيح
`camelCase` نفسها. العيّنات الذهبية هي مرجع الأشكال والاختبار: أيّ صنف Dart يجب أن
يُفكّك عيّنته المقابلة دون فقد مفتاح. تُعامَل هذه الطبقة كـ**السطح الوحيد** الذي
تربط به الشاشات.

## الإصدار والتغيير

- `contractVersion` يبقى `read-model-v1` طالما التغييرات إضافية (حقل/سطح جديد).
- أي تغيير كاسر (حذف/إعادة تسمية/تغيير نوع حقل) يرفع الإصدار (`read-model-v2`).
- بعد أي تغيير مقصود، أعد توليد العيّنات:

```powershell
python -m scripts.dump_read_model_contract
```

المولّد [`scripts/dump_read_model_contract.py`](../scripts/dump_read_model_contract.py)
هو المصدر الوحيد للعيّنات: يبذر قاعدة مؤقتة، يشغّل مسار حوكمة حتميًا، يصيّر كل سطح،
ثم **يُنقّي** المعرّفات المولّدة والطوابع الزمنية إلى بدائل (`<id>` / `<ts>`)
و**يطبّع** ترتيب المجموعات (بعض العروض تكسر تعادل الصفوف بمعرّف عشوائي). يستورد
[`tests/test_read_models.py`](../tests/test_read_models.py) الدوال نفسها ويعيد
التصيير، فلا يمكن للعيّنات والاختبار أن يفترقا. الاختبارات تتحقق أيضًا من: مطابقة
العيّنات، وجود `contractVersion`، أن كل المفاتيح `camelCase`، ومرور قيم الخدمة دون
احتساب.
