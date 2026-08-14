// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Arabic (`ar`).
class AppLocalizationsAr extends AppLocalizations {
  AppLocalizationsAr([String locale = 'ar']) : super(locale);

  @override
  String get appTitle => 'سكيور جايد';

  @override
  String get dashboard => 'لوحة القيادة';

  @override
  String get catalog => 'الفهرس';

  @override
  String get profiles => 'الملفات الشخصية';

  @override
  String get searchHint => 'ابحث في العناصر...';

  @override
  String get noArtifactsFound => 'لم يتم العثور على عناصر';

  @override
  String get implementationStatus => 'حالة التنفيذ';

  @override
  String get verificationStatus => 'حالة التحقق';

  @override
  String get switchToEnglish => 'Switch to English';

  @override
  String get switchToArabic => 'التبديل إلى العربية';

  @override
  String localeChangeError(Object error) {
    return 'تعذّر حفظ تفضيل اللغة: $error';
  }

  @override
  String localDataOpenError(Object error) {
    return 'تعذّر فتح بيانات SecureGuide المحلية.\n\n$error';
  }

  @override
  String get noProfiles => 'لا توجد ملفات مؤسسية بعد.';

  @override
  String get createProfileTooltip => 'ملف مؤسسي جديد';

  @override
  String get tasks => 'المهام';

  @override
  String get templates => 'القوالب';

  @override
  String get exceptionLog => 'سجل الاستثناءات';

  @override
  String get profileSettings => 'إعدادات الملف';

  @override
  String get chooseProfile => 'اختيار الملف';

  @override
  String get createProfileTitle => 'ملف مؤسسي جديد';

  @override
  String get profileName => 'اسم الملف';

  @override
  String get cancel => 'إلغاء';

  @override
  String get create => 'إنشاء';

  @override
  String profileCreateError(Object error) {
    return 'تعذّر إنشاء الملف: $error';
  }

  @override
  String profileActivateError(Object error) {
    return 'تعذّر تفعيل الملف: $error';
  }

  @override
  String get filter => 'تصفية';

  @override
  String get catalogFiltersTitle => 'تصفية الكتالوج';

  @override
  String get artifactTypeFilter => 'نوع العنصر';

  @override
  String get primaryDomainFilter => 'النطاق الأساسي';

  @override
  String get subDomainFilter => 'النطاق الفرعي';

  @override
  String get priorityFilter => 'الأولوية';

  @override
  String get testabilityFilter => 'قابلية الاختبار';

  @override
  String get clearFilters => 'مسح';

  @override
  String get applyFilters => 'تطبيق';

  @override
  String catalogLoadError(Object error) {
    return 'تعذّر تحميل الكتالوج: $error';
  }

  @override
  String get noMatchingArtifacts => 'لا توجد عناصر مطابقة.';

  @override
  String get openAssessment => 'فتح التقييم';

  @override
  String get addToProfile => 'إضافة إلى الملف';

  @override
  String addToProfileError(Object error) {
    return 'تعذّرت إضافة العنصر: $error';
  }

  @override
  String dashboardLoadError(Object error) {
    return 'تعذّر تحميل اللوحة: $error';
  }

  @override
  String get exportReport => 'تصدير التقرير';

  @override
  String get totalScore => 'النتيجة الكلية';

  @override
  String get items => 'العناصر';

  @override
  String get fullyImplemented => 'مطبَّقة كليًا';

  @override
  String get openGaps => 'الفجوات المفتوحة';

  @override
  String get overdue => 'متأخرة';

  @override
  String get recommendations => 'التوصيات';

  @override
  String get noOpenGaps => 'لا توجد فجوات مفتوحة.';

  @override
  String get noRecommendations => 'لا توجد توصيات.';

  @override
  String get genericErrorTitle => 'حدث خطأ';

  @override
  String get retry => 'إعادة المحاولة';

  @override
  String get save => 'حفظ';

  @override
  String get delete => 'حذف';

  @override
  String get close => 'إغلاق';

  @override
  String get confirm => 'تأكيد';

  @override
  String get requiredField => 'هذا الحقل مطلوب';

  @override
  String requiredValue(String label) {
    return '$label مطلوب';
  }

  @override
  String get notSpecified => 'غير محدد';

  @override
  String get unknownItem => 'عنصر غير معروف';

  @override
  String get artifactDetailsTitle => 'تفاصيل العنصر';

  @override
  String get detailsTab => 'التفاصيل';

  @override
  String get assessmentTab => 'التقييم';

  @override
  String get evidenceTab => 'الأدلة';

  @override
  String get remediationPlansTab => 'خطط المعالجة';

  @override
  String artifactLoadError(Object error) {
    return 'تعذّر تحميل العنصر: $error';
  }

  @override
  String get definition => 'التعريف';

  @override
  String get noDefinition => 'لا يوجد تعريف.';

  @override
  String get tagsHeading => 'العلامات';

  @override
  String get mappingsHeading => 'الارتباطات المرجعية';

  @override
  String get referenceLabel => 'المرجع';

  @override
  String get relationshipsHeading => 'العلاقات';

  @override
  String get targetLabel => 'الهدف';

  @override
  String get sourceLabel => 'المصدر';

  @override
  String get operationalState => 'الحالة التشغيلية';

  @override
  String get effectivenessLabel => 'الفعالية';

  @override
  String get exceptionState => 'حالة الاستثناء';

  @override
  String get exceptionManagedTooltip => 'تُدار عبر مسار اعتماد الاستثناءات';

  @override
  String get ownershipPlanning => 'الملكية والتخطيط';

  @override
  String get currentMaturityLevel => 'مستوى النضج الحالي';

  @override
  String get overrideCatalogPriority => 'تجاوز أولوية الكتالوج أو القالب';

  @override
  String get effectiveNow => 'الفعالة الآن';

  @override
  String get customPriority => 'الأولوية المخصصة';

  @override
  String get overrideReviewFrequency => 'تجاوز تكرار المراجعة';

  @override
  String get customReviewFrequency => 'تكرار المراجعة المخصص';

  @override
  String get assignedOwner => 'المالك المعيّن';

  @override
  String get dueDate => 'تاريخ الاستحقاق';

  @override
  String get clearDate => 'مسح التاريخ';

  @override
  String get currentStateNotes => 'ملاحظات الحالة الحالية';

  @override
  String get newAssessmentRecord => 'سجل التقييم الجديد';

  @override
  String get assessorName => 'اسم المقيّم';

  @override
  String get assessorRequired => 'اسم المقيّم مطلوب';

  @override
  String get scoreLabel => 'الدرجة (0–100)';

  @override
  String get scoreValidation => 'أدخل درجة بين 0 و100';

  @override
  String get assessmentComment => 'تعليق التقييم';

  @override
  String get saveAssessment => 'حفظ التقييم';

  @override
  String get assessmentSaved => 'تم حفظ التقييم.';

  @override
  String assessmentSaveError(Object error) {
    return 'تعذّر حفظ التقييم: $error';
  }

  @override
  String get assessmentHistory => 'سجل التقييمات';

  @override
  String get noPreviousAssessments => 'لا توجد تقييمات سابقة.';

  @override
  String get unscored => 'بلا درجة';

  @override
  String get manageException => 'إدارة الاستثناء';

  @override
  String get deleteEvidenceTitle => 'حذف الدليل';

  @override
  String get deleteEvidenceConfirm => 'هل تريد حذف هذا الدليل نهائياً؟';

  @override
  String get evidenceDeleted => 'تم حذف الدليل';

  @override
  String evidenceDeleteError(Object error) {
    return 'تعذّر حذف الدليل: $error';
  }

  @override
  String get evidenceDetails => 'تفاصيل الدليل';

  @override
  String get evidenceType => 'نوع الدليل';

  @override
  String get evidenceCollector => 'جامع الدليل';

  @override
  String get evidenceAddedAt => 'تاريخ الإضافة';

  @override
  String get fileSize => 'الحجم';

  @override
  String get sha256Fingerprint => 'البصمة (SHA-256)';

  @override
  String get unsupportedEvidencePreview =>
      'تم التحقق من الملف، لكن هذا النوع لا يُعرض داخل التطبيق.';

  @override
  String evidenceOpenError(Object error) {
    return 'تعذّر فتح الدليل بأمان: $error';
  }

  @override
  String get noEvidence => 'لا توجد أدلة مرفقة.';

  @override
  String get addEvidence => 'إضافة دليل';

  @override
  String get integrityValid => 'تم التحقق من سلامة الدليل';

  @override
  String get integrityMissing => 'ملف الدليل مفقود';

  @override
  String get integrityCorrupted => 'فشل تحقق بصمة الدليل';

  @override
  String get integrityUnsafePath => 'مسار الدليل غير آمن';

  @override
  String get integrityVerifying => 'جارٍ التحقق';

  @override
  String get addEvidenceTitle => 'إضافة دليل جديد';

  @override
  String get evidenceDescriptionOptional => 'وصف الدليل (اختياري)';

  @override
  String get chooseFile => 'اختيار ملف...';

  @override
  String get saveEvidence => 'حفظ الدليل';

  @override
  String evidenceAddError(Object error) {
    return 'تعذّرت إضافة الدليل: $error';
  }

  @override
  String get noTemplates => 'لا توجد قوالب متاحة.';

  @override
  String get unknownTemplate => 'قالب غير معروف';

  @override
  String get templateDetails => 'تفاصيل القالب';

  @override
  String get templateApplied => 'تم تطبيق القالب بنجاح';

  @override
  String templateApplyError(Object error) {
    return 'تعذّر تطبيق القالب: $error';
  }

  @override
  String get applicationActorAudit => 'توثيق منفذ تطبيق القالب';

  @override
  String get actorName => 'اسم المنفذ';

  @override
  String get actorRequiredAudit => 'الاسم مطلوب لمسار التدقيق';

  @override
  String get apply => 'تطبيق';

  @override
  String get applicationScope => 'نطاق التطبيق';

  @override
  String get versionLabel => 'الإصدار';

  @override
  String get noTemplateItems => 'لا توجد عناصر في هذا القالب.';

  @override
  String get applyTemplate => 'تطبيق القالب';

  @override
  String get artifactCount => 'عنصر';

  @override
  String exceptionSubmitError(Object error) {
    return 'تعذّر إرسال الاستثناء للمراجعة: $error';
  }

  @override
  String get approveExceptionTitle => 'اعتماد الاستثناء';

  @override
  String get approverName => 'اسم المُعتمد';

  @override
  String get approve => 'اعتماد';

  @override
  String exceptionApproveError(Object error) {
    return 'تعذّر اعتماد الاستثناء: $error';
  }

  @override
  String get noExceptions => 'لا توجد استثناءات مسجلة في هذا الملف.';

  @override
  String get workflowLabel => 'سير العمل';

  @override
  String get typeLabel => 'النوع';

  @override
  String get justificationLabel => 'المبرر';

  @override
  String get expiryLabel => 'الانتهاء';

  @override
  String get submitForReview => 'إرسال للمراجعة';

  @override
  String get exceptionJustificationRequired => 'يجب إدخال مبرر الاستثناء';

  @override
  String exceptionSaveError(Object error) {
    return 'تعذّر حفظ الاستثناء: $error';
  }

  @override
  String get exceptionType => 'نوع الاستثناء';

  @override
  String get justificationRequiredLabel => 'المبرر (إلزامي)';

  @override
  String get expiryDate => 'تاريخ الانتهاء';

  @override
  String get riskAcceptedByOptional => 'مُتقبل الخطر (اختياري)';

  @override
  String get saveDraft => 'حفظ كمسودة';

  @override
  String get reportPreview => 'معاينة التقرير';

  @override
  String get exportJson => 'تصدير JSON';

  @override
  String get exportHtml => 'تصدير HTML';

  @override
  String get saveHtmlReport => 'حفظ تقرير HTML';

  @override
  String get saveJsonReport => 'حفظ تقرير JSON';

  @override
  String reportSaved(String path) {
    return 'تم حفظ التقرير محلياً: $path';
  }

  @override
  String reportSaveError(Object error) {
    return 'تعذّر حفظ التقرير: $error';
  }

  @override
  String get savedSuccessfully => 'تم الحفظ بنجاح';

  @override
  String saveError(Object error) {
    return 'تعذّر الحفظ: $error';
  }

  @override
  String get archiveProfileTitle => 'أرشفة الملف؟';

  @override
  String get archiveProfileWarning =>
      'سيُزال هذا الملف من الاستخدام النشط. هل تريد المتابعة؟';

  @override
  String archiveError(Object error) {
    return 'تعذّرت أرشفة الملف: $error';
  }

  @override
  String get saveBackupDialog => 'حفظ نسخة SecureGuide الاحتياطية';

  @override
  String get backupSaved => 'تم التحقق من النسخة الاحتياطية وحفظها.';

  @override
  String backupError(Object error) {
    return 'تعذّر إنشاء النسخة الاحتياطية: $error';
  }

  @override
  String get chooseBackupDialog => 'اختيار نسخة SecureGuide احتياطية';

  @override
  String get restoreBackupTitle => 'استعادة النسخة الاحتياطية؟';

  @override
  String get restoreBackupWarning =>
      'سيُتحقق من المخطط وسلامة SQLite أولاً، ثم تُحفظ قاعدة البيانات الحالية كنسخة تعافٍ قبل الاستبدال.';

  @override
  String get validateAndRestore => 'تحقق واستعد';

  @override
  String restoreSuccess(String path) {
    return 'تمت الاستعادة. نسخة التعافي محفوظة في: $path';
  }

  @override
  String restoreRejected(Object error) {
    return 'رُفضت الاستعادة: $error';
  }

  @override
  String errorWithDetails(Object error) {
    return 'خطأ: $error';
  }

  @override
  String get profileKind => 'نوع الملف';

  @override
  String get organizationSize => 'حجم المنظمة';

  @override
  String get industry => 'القطاع';

  @override
  String get country => 'البلد';

  @override
  String get targetMaturity => 'المستوى المستهدف';

  @override
  String get maturityInitial => 'مبتدئ';

  @override
  String get maturityManaged => 'مدار';

  @override
  String get maturityDefined => 'محدد';

  @override
  String get maturityRepeatable => 'قابل للتكرار';

  @override
  String get maturityOptimized => 'مُحسن';

  @override
  String get descriptionLabel => 'الوصف';

  @override
  String get backupRestore => 'النسخ الاحتياطي والاستعادة';

  @override
  String get createLocalBackup => 'إنشاء نسخة احتياطية محلية';

  @override
  String get restoreBackup => 'استعادة نسخة احتياطية';

  @override
  String get archiveProfile => 'أرشفة الملف';

  @override
  String get all => 'الكل';

  @override
  String get taskTodo => 'قيد الانتظار';

  @override
  String get taskInProgress => 'قيد التنفيذ';

  @override
  String get taskBlocked => 'متوقف';

  @override
  String get taskDone => 'مكتمل';

  @override
  String get noTasks => 'لا توجد مهام حالياً.';

  @override
  String get untitledTask => 'مهمة بدون عنوان';

  @override
  String get statusLabel => 'الحالة';

  @override
  String get priorityLabel => 'الأولوية';

  @override
  String get assignedToLabel => 'مسند إلى';

  @override
  String get startTask => 'البدء';

  @override
  String get blockTask => 'إيقاف';

  @override
  String get completeTask => 'إكمال';

  @override
  String get auditTaskUpdate => 'توثيق تحديث المهمة';

  @override
  String get changeNote => 'ملاحظة التغيير';

  @override
  String get blueprintsTitle => 'المخططات التنفيذية';

  @override
  String get noBlueprints => 'لا توجد مخططات مرتبطة بهذا الملف.';

  @override
  String get unnamedBlueprint => 'مخطط بدون اسم';

  @override
  String get blueprintDetails => 'تفاصيل المخطط';

  @override
  String get createdAtLabel => 'تاريخ الإنشاء';

  @override
  String get createdByLabel => 'بواسطة';

  @override
  String get approvedByLabel => 'معتمد بواسطة';

  @override
  String get proposedActions => 'الإجراءات المقترحة';

  @override
  String get untitled => 'بدون عنوان';

  @override
  String get expectedOutputs => 'المخرجات المتوقعة';

  @override
  String get requiredEvidence => 'الأدلة المطلوبة';

  @override
  String get generationRules => 'قواعد التوليد';

  @override
  String get patternEnrichments => 'إثراءات الأنماط';

  @override
  String get returnToDraft => 'إعادة كمسودة';

  @override
  String get approveBlueprint => 'اعتماد المخطط';

  @override
  String get submitBlueprintReviewTitle => 'إرسال المخطط للمراجعة';

  @override
  String get approveBlueprintTitle => 'اعتماد المخطط';

  @override
  String get reviewResolutionNote => 'ملاحظة حسم المراجعة';

  @override
  String get returnBlueprintDraftTitle => 'إعادة المخطط إلى مسودة';

  @override
  String get returnReason => 'سبب الإعادة';
}
