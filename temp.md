
قمت بمراجعة شاملة للتطبيق من ثلاث زوايا (الاكتمال، الصحة، الأثر) عبر فحص طبقة الخدمات Python، تطبيق Flutter، محرك التقييم، الترحيلات، وحزمة الاختبارات. إليك التقرير المدمج:

---

# تقرير مراجعة جاهزية الإنتاج — SecureGuide

## مشاكل حرجة (يجب إصلاحها)

لا توجد مشاكل حرجة. لا يوجد حقن SQL (جميع الاستعلامات تستخدم معاملات آمنة)، ولا أخطاء منطقية مدمرة في مسارات الكتابة الأساسية، وفصل بيانات المرجع عن البيانات التشغيلية مُطبّق بشكل صحيح.

---

## تحذيرات (ينبغي إصلاحها)

### 1. ثغرة CORS تسمح بهجمات CSRF على نقاط الكتابة
[sidecar.py#L140-L173](/d:/APP/secure-guide/New%20folder/secureguide/sidecar.py)

**المشكلة**: `_send()` يضع `Access-Control-Allow-Origin: *` على **كل** الاستجابات، و`do_OPTIONS` يوافق على أي طلب preflight. بما أن نقاط الكتابة (`/write/profiles`، `/write/assessments`، ...) بلا مصادقة، يمكن لأي موقع ويب يزوره المستخدم إرسال طلبات POST إلى `http://127.0.0.1:8765/write/...` وتنفيذ عمليات (إنشاء ملفات، تعديل تقييمات) نيابةً عنه.

**الإصلاح**: قصر CORS على مسارات القراءة فقط، أو إزالته كلياً (تطبيق Flutter يستخدم HTTP أصلياً ولا يحتاجه):
```python
def _send(self, status, payload, *, allow_cors=False):
    ...
    if allow_cors:
        self.send_header("Access-Control-Allow-Origin", "*")
```
ثم تمرير `allow_cors=True` من `do_GET` فقط.

### 2. ترتيب أولويات المهام معكوس — `PRI-LOW` يظهر قبل `PRI-MEDIUM`
[repositories.py#L812-L821](/d:/APP/secure-guide/New%20folder/secureguide/repositories.py)

**المشكلة**: `tasks()` يرتب حسب عمود `priority` النصي أبجدياً، فيصبح `PRI-LOW` (L) قبل `PRI-MEDIUM` (M)، وتظهر المهام بلا أولوية (NULL) في الأعلى. يؤثر مباشرة على قائمة المهام في التطبيق.

**الإصلاح**: استخدام تعبير CASE كما هو موجود بالفعل في `gaps()`:
```python
sql += (" ORDER BY due_date IS NULL,due_date,"
        "CASE priority WHEN 'PRI-CRITICAL' THEN 1 WHEN 'PRI-HIGH' THEN 2"
        " WHEN 'PRI-MEDIUM' THEN 3 WHEN 'PRI-LOW' THEN 4 ELSE 5 END,id")
```

### 3. حقول `priorityOverride` فارغة صامتاً في كل أسطح القوائم
[read_models.py#L241-L275](/d:/APP/secure-guide/New%20folder/secureguide/read_models.py)

**المشكلة**: `OperationalItem.to_wire()` يعرض `priorityOverride`/`reviewFrequencyOverride`، لكنهما يُملآن فقط من مسار التفاصيل الفردية (`operational_item` الذي يعمل JOIN). كل مسارات القوائم (لوحة المراجعة، التقرير) تأتي من `v_profile_operational_items` الذي لا يعرض الأعمدة الخام. أي شاشة مستقبلية تربط قائمة ستعرض "لا يوجد تجاوز" خطأً، وقد ترسل `clearPriorityOverride: true` **فتمحو تجاوز المستخدم دون إنذار**.

**الإصلاح**: إضافة العمودين الخامين إلى `v_profile_operational_items` في ترحيل جديد، ثم تبسيط `operational_item` ليقرأ من الـ view مباشرة.

### 4. الوسوم (Tags) قابلة للبحث لكن لا يُكتب أي منها أبداً
[scripts/promote.py#L248-L253](/d:/APP/secure-guide/New%20folder/scripts/promote.py)

**المشكلة**: البند 6 من MVP والقاعدة 5 في AGENTS.md يتطلبان حفظ وسوم معيارية، لكن خط الترقية يكتب `ntag = 0` دائماً (الوسوم "أُلغيت" وفق SADP §2.4). فلاتر `tag_type`/`tag_value` في البحث لا تطابق أي صف في قاعدة بيانات حقيقية — تعارض غير مُسوَّى بين المتطلبات والتنفيذ.

**الإصلاح**: إما ملء `artifact_tags` من `proposed_tags_json` أثناء الترقية، أو إزالة فلاتر الوسوم الميتة وتحديث الوثائق لتسجيل الإلغاء صراحةً.

### 5. نطاق Applicability Scope له مخطط وفلاتر لكن لا مسار كتابة
[secureguide/repositories.py#L162-L169](/d:/APP/secure-guide/New%20folder/secureguide/repositories.py)

**المشكلة**: الجدول موجود في الترحيل 001 والبحث يدعم فلاتر `applicability_scope_type/value`، لكن لا يوجد أي `INSERT INTO artifact_applicability_scope` خارج تثبيتات الاختبار. الميزة نصف مُسلَّمة: قابلة للفلترة لكن غير مُعبّأة أبداً.

**الإصلاح**: إضافة مرحلة نطاق Applicability إلى خط الترقية، أو إزالة الفلاتر وتوثيق التأجيل في MVP_SCOPE.md.

---

## اقتراحات (يُنصح بالنظر فيها)

### 6. قيمة `score` غير الرقمية تعيد 500 بدلاً من 400
[services.py#L1192](/d:/APP/secure-guide/New%20folder/secureguide/services.py)

`float(score)` يثير `ValueError` لمدخل مثل `"abc"`، فيُحوَّل إلى 500 InternalError بدلاً من 400. **الإصلاح**: محاولة التحويل داخل `try/except` وإثارة `ValidationError`.

### 7. الترحيلات تسجّل نسختها قبل اكتمال DDL
[database.py#L51](/d:/APP/secure-guide/New%20folder/secureguide/database.py)

كل ترحيل يُدخل صفه في `schema_migrations` كأول عبارة. إذا فشل DDL لاحقاً، يُتخطى الترحيل نهائياً ويبقى المخطط ناقصاً بلا استرداد تلقائي. **الإصلاح**: نقل الإدراج لنهاية الملف، أو تنفيذ كل ملف داخل معاملة صريحة وتسجيل النجاح بعده.

### 8. الـ Sidecar يعرض 4 عمليات كتابة فقط
[sidecar.py#L118-L134](/d:/APP/secure-guide/New%20folder/secureguide/sidecar.py)

`apply_template` و`add_evidence` ودورة حياة الاستثناءات مُنفَّذة بالكامل في طبقة الخدمات لكنها غير متاحة عبر HTTP — البندان 9 و10 من MVP يعملان فقط عبر CLI. **الإصلاح**: تمديد `WriteModel` و`resolve_write` بمسارات القوالب والأدلة والاستثناءات.

### 9. لا توجد وسيلة إنتاجية لإنشاء القوالب
[secureguide/cli.py#L158-L160](/d:/APP/secure-guide/New%20folder/secureguide/cli.py)

جانب التطبيق مكتمل، لكن كل `INSERT INTO templates` موجود في تثبيتات الاختبار فقط. قاعدة بيانات جديدة لا تحتوي أي قالب. **الإصلاح**: إضافة أمر CLI أو استيراد JSON لتعريفات القوالب.

### 10. استيراد `scripts.scoring` عبر حدود غير مُعبّأة
[secureguide/services.py#L13](/d:/APP/secure-guide/New%20folder/secureguide/services.py)

`from scripts import scoring` يعمل فقط لأن جذر المشروع على `sys.path`. تعبئة `secureguide` مستقلاً أو تغيير الاسم يكسر الخدمة. **الإصلاح**: نقل نواة التقييم إلى `secureguide/scoring.py` وترك `scripts/scoring.py` كغلاف CLI.

### 11. `EventBus.history` ينمو بلا حد في الـ Sidecar طويل العمر
[secureguide/services.py#L110](/d:/APP/secure-guide/New%20folder/secureguide/services.py)

كل `publish()` يضيف للتاريخ ولا شيء يقصّه. **الإصلاح**: `deque(maxlen=500)` أو إزالته حتى يحتاجه مشترك فعلي.

---

## ملخص التغييرات

- **البنية سليمة وقابلة للتدقيق**: فصل واضح بين الكتالوج المرجعي والحالة التشغيلية لكل ملف مؤسسي، مع 24 ترحيل SQL تفرض قيم USACM/SDT عبر قيود CHECK والمحفزات، وحفظ الواردات الخام في `raw_artifacts`.
- **خط الاستيراد كامل**: `ingest_raw → batch_process → promote` مع تصنيف آلي يوجَّه للمراجعة البشرية عند ثقة ≤ 0.70، وترقية معاملاتية قابلة للتراجع.
- **سير عمل الملف المؤسسي مكتمل في طبقة الخدمات/CLI**: إدارة الملفات، تطبيق القوالب مع تتبع المصدر، أربعة حقول حالة تشغيلية مستقلة، سجل تقييمات غير قابل للتعديل، أدلة، دورة حياة استثناءات، لوحة قيادة بالتقييم والفجوات، وتصدير JSON + HTML.
- **الفجوات الرئيسية في السطح المحمول والبيانات الثانوية**: الوسوم ونطاق Applicability قابلة للفلترة لكن غير مُعبّأة، والـ Sidecar يعرض عمليات كتابة التقييم فقط — القوالب والأدلة والاستثناءات حصرية على CLI.
- **الحكم**: المنطق الأساسي صحيح وآمن من حيث سلامة البيانات، لكن التطبيق **غير جاهز كلياً للإنتاج بعد** — يجب إصلاح التحذيرين الأمنيين (#1 CORS) وترتيب المهام (#2) على الأقل، وحسم تعارض الوسوم (#4) قبل الإطلاق.