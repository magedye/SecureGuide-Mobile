import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ar.dart';
import 'app_localizations_en.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ar'),
    Locale('en'),
  ];

  /// The title of the application
  ///
  /// In en, this message translates to:
  /// **'SecureGuide'**
  String get appTitle;

  /// No description provided for @dashboard.
  ///
  /// In en, this message translates to:
  /// **'Dashboard'**
  String get dashboard;

  /// No description provided for @catalog.
  ///
  /// In en, this message translates to:
  /// **'Catalog'**
  String get catalog;

  /// No description provided for @profiles.
  ///
  /// In en, this message translates to:
  /// **'Profiles'**
  String get profiles;

  /// No description provided for @searchHint.
  ///
  /// In en, this message translates to:
  /// **'Search artifacts...'**
  String get searchHint;

  /// No description provided for @noArtifactsFound.
  ///
  /// In en, this message translates to:
  /// **'No artifacts found'**
  String get noArtifactsFound;

  /// No description provided for @implementationStatus.
  ///
  /// In en, this message translates to:
  /// **'Implementation'**
  String get implementationStatus;

  /// No description provided for @verificationStatus.
  ///
  /// In en, this message translates to:
  /// **'Verification'**
  String get verificationStatus;

  /// No description provided for @switchToEnglish.
  ///
  /// In en, this message translates to:
  /// **'Switch to English'**
  String get switchToEnglish;

  /// No description provided for @switchToArabic.
  ///
  /// In en, this message translates to:
  /// **'التبديل إلى العربية'**
  String get switchToArabic;

  /// No description provided for @localeChangeError.
  ///
  /// In en, this message translates to:
  /// **'Could not save the language preference: {error}'**
  String localeChangeError(Object error);

  /// No description provided for @localDataOpenError.
  ///
  /// In en, this message translates to:
  /// **'SecureGuide could not open its local data.\n\n{error}'**
  String localDataOpenError(Object error);

  /// No description provided for @noProfiles.
  ///
  /// In en, this message translates to:
  /// **'No enterprise profiles yet.'**
  String get noProfiles;

  /// No description provided for @createProfileTooltip.
  ///
  /// In en, this message translates to:
  /// **'New enterprise profile'**
  String get createProfileTooltip;

  /// No description provided for @tasks.
  ///
  /// In en, this message translates to:
  /// **'Tasks'**
  String get tasks;

  /// No description provided for @templates.
  ///
  /// In en, this message translates to:
  /// **'Templates'**
  String get templates;

  /// No description provided for @exceptionLog.
  ///
  /// In en, this message translates to:
  /// **'Exception log'**
  String get exceptionLog;

  /// No description provided for @profileSettings.
  ///
  /// In en, this message translates to:
  /// **'Profile settings'**
  String get profileSettings;

  /// No description provided for @chooseProfile.
  ///
  /// In en, this message translates to:
  /// **'Choose profile'**
  String get chooseProfile;

  /// No description provided for @createProfileTitle.
  ///
  /// In en, this message translates to:
  /// **'New enterprise profile'**
  String get createProfileTitle;

  /// No description provided for @profileName.
  ///
  /// In en, this message translates to:
  /// **'Profile name'**
  String get profileName;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @create.
  ///
  /// In en, this message translates to:
  /// **'Create'**
  String get create;

  /// No description provided for @profileCreateError.
  ///
  /// In en, this message translates to:
  /// **'Could not create the profile: {error}'**
  String profileCreateError(Object error);

  /// No description provided for @profileActivateError.
  ///
  /// In en, this message translates to:
  /// **'Could not activate the profile: {error}'**
  String profileActivateError(Object error);

  /// No description provided for @filter.
  ///
  /// In en, this message translates to:
  /// **'Filter'**
  String get filter;

  /// No description provided for @catalogFiltersTitle.
  ///
  /// In en, this message translates to:
  /// **'Catalog filters'**
  String get catalogFiltersTitle;

  /// No description provided for @artifactTypeFilter.
  ///
  /// In en, this message translates to:
  /// **'Artifact type'**
  String get artifactTypeFilter;

  /// No description provided for @primaryDomainFilter.
  ///
  /// In en, this message translates to:
  /// **'Primary domain'**
  String get primaryDomainFilter;

  /// No description provided for @subDomainFilter.
  ///
  /// In en, this message translates to:
  /// **'Sub-domain'**
  String get subDomainFilter;

  /// No description provided for @priorityFilter.
  ///
  /// In en, this message translates to:
  /// **'Priority'**
  String get priorityFilter;

  /// No description provided for @testabilityFilter.
  ///
  /// In en, this message translates to:
  /// **'Testability'**
  String get testabilityFilter;

  /// No description provided for @clearFilters.
  ///
  /// In en, this message translates to:
  /// **'Clear'**
  String get clearFilters;

  /// No description provided for @applyFilters.
  ///
  /// In en, this message translates to:
  /// **'Apply'**
  String get applyFilters;

  /// No description provided for @catalogLoadError.
  ///
  /// In en, this message translates to:
  /// **'Could not load the catalog: {error}'**
  String catalogLoadError(Object error);

  /// No description provided for @noMatchingArtifacts.
  ///
  /// In en, this message translates to:
  /// **'No matching artifacts.'**
  String get noMatchingArtifacts;

  /// No description provided for @openAssessment.
  ///
  /// In en, this message translates to:
  /// **'Open assessment'**
  String get openAssessment;

  /// No description provided for @addToProfile.
  ///
  /// In en, this message translates to:
  /// **'Add to profile'**
  String get addToProfile;

  /// No description provided for @addToProfileError.
  ///
  /// In en, this message translates to:
  /// **'Could not add the artifact: {error}'**
  String addToProfileError(Object error);

  /// No description provided for @dashboardLoadError.
  ///
  /// In en, this message translates to:
  /// **'Could not load the dashboard: {error}'**
  String dashboardLoadError(Object error);

  /// No description provided for @exportReport.
  ///
  /// In en, this message translates to:
  /// **'Export report'**
  String get exportReport;

  /// No description provided for @totalScore.
  ///
  /// In en, this message translates to:
  /// **'Total score'**
  String get totalScore;

  /// No description provided for @items.
  ///
  /// In en, this message translates to:
  /// **'Items'**
  String get items;

  /// No description provided for @fullyImplemented.
  ///
  /// In en, this message translates to:
  /// **'Fully implemented'**
  String get fullyImplemented;

  /// No description provided for @openGaps.
  ///
  /// In en, this message translates to:
  /// **'Open gaps'**
  String get openGaps;

  /// No description provided for @overdue.
  ///
  /// In en, this message translates to:
  /// **'Overdue'**
  String get overdue;

  /// No description provided for @recommendations.
  ///
  /// In en, this message translates to:
  /// **'Recommendations'**
  String get recommendations;

  /// No description provided for @noOpenGaps.
  ///
  /// In en, this message translates to:
  /// **'No open gaps.'**
  String get noOpenGaps;

  /// No description provided for @noRecommendations.
  ///
  /// In en, this message translates to:
  /// **'No recommendations.'**
  String get noRecommendations;

  /// No description provided for @genericErrorTitle.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong'**
  String get genericErrorTitle;

  /// No description provided for @retry.
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get retry;

  /// No description provided for @save.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get save;

  /// No description provided for @delete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get delete;

  /// No description provided for @close.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get close;

  /// No description provided for @confirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get confirm;

  /// No description provided for @requiredField.
  ///
  /// In en, this message translates to:
  /// **'This field is required'**
  String get requiredField;

  /// No description provided for @requiredValue.
  ///
  /// In en, this message translates to:
  /// **'{label} is required'**
  String requiredValue(String label);

  /// No description provided for @notSpecified.
  ///
  /// In en, this message translates to:
  /// **'Not specified'**
  String get notSpecified;

  /// No description provided for @unknownItem.
  ///
  /// In en, this message translates to:
  /// **'Unknown artifact'**
  String get unknownItem;

  /// No description provided for @artifactDetailsTitle.
  ///
  /// In en, this message translates to:
  /// **'Artifact details'**
  String get artifactDetailsTitle;

  /// No description provided for @detailsTab.
  ///
  /// In en, this message translates to:
  /// **'Details'**
  String get detailsTab;

  /// No description provided for @assessmentTab.
  ///
  /// In en, this message translates to:
  /// **'Assessment'**
  String get assessmentTab;

  /// No description provided for @evidenceTab.
  ///
  /// In en, this message translates to:
  /// **'Evidence'**
  String get evidenceTab;

  /// No description provided for @remediationPlansTab.
  ///
  /// In en, this message translates to:
  /// **'Remediation plans'**
  String get remediationPlansTab;

  /// No description provided for @artifactLoadError.
  ///
  /// In en, this message translates to:
  /// **'Could not load the artifact: {error}'**
  String artifactLoadError(Object error);

  /// No description provided for @definition.
  ///
  /// In en, this message translates to:
  /// **'Definition'**
  String get definition;

  /// No description provided for @noDefinition.
  ///
  /// In en, this message translates to:
  /// **'No definition is available.'**
  String get noDefinition;

  /// No description provided for @tagsHeading.
  ///
  /// In en, this message translates to:
  /// **'Tags'**
  String get tagsHeading;

  /// No description provided for @mappingsHeading.
  ///
  /// In en, this message translates to:
  /// **'Mappings'**
  String get mappingsHeading;

  /// No description provided for @referenceLabel.
  ///
  /// In en, this message translates to:
  /// **'Reference'**
  String get referenceLabel;

  /// No description provided for @relationshipsHeading.
  ///
  /// In en, this message translates to:
  /// **'Relationships'**
  String get relationshipsHeading;

  /// No description provided for @targetLabel.
  ///
  /// In en, this message translates to:
  /// **'Target'**
  String get targetLabel;

  /// No description provided for @sourceLabel.
  ///
  /// In en, this message translates to:
  /// **'Source'**
  String get sourceLabel;

  /// No description provided for @operationalState.
  ///
  /// In en, this message translates to:
  /// **'Operational state'**
  String get operationalState;

  /// No description provided for @effectivenessLabel.
  ///
  /// In en, this message translates to:
  /// **'Effectiveness'**
  String get effectivenessLabel;

  /// No description provided for @exceptionState.
  ///
  /// In en, this message translates to:
  /// **'Exception status'**
  String get exceptionState;

  /// No description provided for @exceptionManagedTooltip.
  ///
  /// In en, this message translates to:
  /// **'Managed through the exception approval workflow'**
  String get exceptionManagedTooltip;

  /// No description provided for @ownershipPlanning.
  ///
  /// In en, this message translates to:
  /// **'Ownership and planning'**
  String get ownershipPlanning;

  /// No description provided for @currentMaturityLevel.
  ///
  /// In en, this message translates to:
  /// **'Current maturity level'**
  String get currentMaturityLevel;

  /// No description provided for @overrideCatalogPriority.
  ///
  /// In en, this message translates to:
  /// **'Override catalog or template priority'**
  String get overrideCatalogPriority;

  /// No description provided for @effectiveNow.
  ///
  /// In en, this message translates to:
  /// **'Effective now'**
  String get effectiveNow;

  /// No description provided for @customPriority.
  ///
  /// In en, this message translates to:
  /// **'Custom priority'**
  String get customPriority;

  /// No description provided for @overrideReviewFrequency.
  ///
  /// In en, this message translates to:
  /// **'Override review frequency'**
  String get overrideReviewFrequency;

  /// No description provided for @customReviewFrequency.
  ///
  /// In en, this message translates to:
  /// **'Custom review frequency'**
  String get customReviewFrequency;

  /// No description provided for @assignedOwner.
  ///
  /// In en, this message translates to:
  /// **'Assigned owner'**
  String get assignedOwner;

  /// No description provided for @dueDate.
  ///
  /// In en, this message translates to:
  /// **'Due date'**
  String get dueDate;

  /// No description provided for @clearDate.
  ///
  /// In en, this message translates to:
  /// **'Clear date'**
  String get clearDate;

  /// No description provided for @currentStateNotes.
  ///
  /// In en, this message translates to:
  /// **'Current-state notes'**
  String get currentStateNotes;

  /// No description provided for @newAssessmentRecord.
  ///
  /// In en, this message translates to:
  /// **'New assessment record'**
  String get newAssessmentRecord;

  /// No description provided for @assessorName.
  ///
  /// In en, this message translates to:
  /// **'Assessor name'**
  String get assessorName;

  /// No description provided for @assessorRequired.
  ///
  /// In en, this message translates to:
  /// **'Assessor name is required'**
  String get assessorRequired;

  /// No description provided for @scoreLabel.
  ///
  /// In en, this message translates to:
  /// **'Score (0–100)'**
  String get scoreLabel;

  /// No description provided for @scoreValidation.
  ///
  /// In en, this message translates to:
  /// **'Enter a score between 0 and 100'**
  String get scoreValidation;

  /// No description provided for @assessmentComment.
  ///
  /// In en, this message translates to:
  /// **'Assessment comment'**
  String get assessmentComment;

  /// No description provided for @saveAssessment.
  ///
  /// In en, this message translates to:
  /// **'Save assessment'**
  String get saveAssessment;

  /// No description provided for @assessmentSaved.
  ///
  /// In en, this message translates to:
  /// **'Assessment saved.'**
  String get assessmentSaved;

  /// No description provided for @assessmentSaveError.
  ///
  /// In en, this message translates to:
  /// **'Could not save the assessment: {error}'**
  String assessmentSaveError(Object error);

  /// No description provided for @assessmentHistory.
  ///
  /// In en, this message translates to:
  /// **'Assessment history'**
  String get assessmentHistory;

  /// No description provided for @noPreviousAssessments.
  ///
  /// In en, this message translates to:
  /// **'No previous assessments.'**
  String get noPreviousAssessments;

  /// No description provided for @unscored.
  ///
  /// In en, this message translates to:
  /// **'No score'**
  String get unscored;

  /// No description provided for @manageException.
  ///
  /// In en, this message translates to:
  /// **'Manage exception'**
  String get manageException;

  /// No description provided for @deleteEvidenceTitle.
  ///
  /// In en, this message translates to:
  /// **'Delete evidence'**
  String get deleteEvidenceTitle;

  /// No description provided for @deleteEvidenceConfirm.
  ///
  /// In en, this message translates to:
  /// **'Permanently delete this evidence item?'**
  String get deleteEvidenceConfirm;

  /// No description provided for @evidenceDeleted.
  ///
  /// In en, this message translates to:
  /// **'Evidence deleted'**
  String get evidenceDeleted;

  /// No description provided for @evidenceDeleteError.
  ///
  /// In en, this message translates to:
  /// **'Could not delete the evidence: {error}'**
  String evidenceDeleteError(Object error);

  /// No description provided for @evidenceDetails.
  ///
  /// In en, this message translates to:
  /// **'Evidence details'**
  String get evidenceDetails;

  /// No description provided for @evidenceType.
  ///
  /// In en, this message translates to:
  /// **'Evidence type'**
  String get evidenceType;

  /// No description provided for @evidenceCollector.
  ///
  /// In en, this message translates to:
  /// **'Collected by'**
  String get evidenceCollector;

  /// No description provided for @evidenceAddedAt.
  ///
  /// In en, this message translates to:
  /// **'Added at'**
  String get evidenceAddedAt;

  /// No description provided for @fileSize.
  ///
  /// In en, this message translates to:
  /// **'Size'**
  String get fileSize;

  /// No description provided for @sha256Fingerprint.
  ///
  /// In en, this message translates to:
  /// **'SHA-256 fingerprint'**
  String get sha256Fingerprint;

  /// No description provided for @unsupportedEvidencePreview.
  ///
  /// In en, this message translates to:
  /// **'The file passed integrity checks, but this type cannot be previewed in the app.'**
  String get unsupportedEvidencePreview;

  /// No description provided for @evidenceOpenError.
  ///
  /// In en, this message translates to:
  /// **'Could not open the evidence safely: {error}'**
  String evidenceOpenError(Object error);

  /// No description provided for @noEvidence.
  ///
  /// In en, this message translates to:
  /// **'No evidence attached.'**
  String get noEvidence;

  /// No description provided for @addEvidence.
  ///
  /// In en, this message translates to:
  /// **'Add evidence'**
  String get addEvidence;

  /// No description provided for @integrityValid.
  ///
  /// In en, this message translates to:
  /// **'Evidence integrity verified'**
  String get integrityValid;

  /// No description provided for @integrityMissing.
  ///
  /// In en, this message translates to:
  /// **'Evidence file is missing'**
  String get integrityMissing;

  /// No description provided for @integrityCorrupted.
  ///
  /// In en, this message translates to:
  /// **'Evidence fingerprint verification failed'**
  String get integrityCorrupted;

  /// No description provided for @integrityUnsafePath.
  ///
  /// In en, this message translates to:
  /// **'Evidence path is unsafe'**
  String get integrityUnsafePath;

  /// No description provided for @integrityVerifying.
  ///
  /// In en, this message translates to:
  /// **'Verifying'**
  String get integrityVerifying;

  /// No description provided for @addEvidenceTitle.
  ///
  /// In en, this message translates to:
  /// **'Add new evidence'**
  String get addEvidenceTitle;

  /// No description provided for @evidenceDescriptionOptional.
  ///
  /// In en, this message translates to:
  /// **'Evidence description (optional)'**
  String get evidenceDescriptionOptional;

  /// No description provided for @chooseFile.
  ///
  /// In en, this message translates to:
  /// **'Choose file...'**
  String get chooseFile;

  /// No description provided for @saveEvidence.
  ///
  /// In en, this message translates to:
  /// **'Save evidence'**
  String get saveEvidence;

  /// No description provided for @evidenceAddError.
  ///
  /// In en, this message translates to:
  /// **'Could not add the evidence: {error}'**
  String evidenceAddError(Object error);

  /// No description provided for @noTemplates.
  ///
  /// In en, this message translates to:
  /// **'No templates are available.'**
  String get noTemplates;

  /// No description provided for @unknownTemplate.
  ///
  /// In en, this message translates to:
  /// **'Unknown template'**
  String get unknownTemplate;

  /// No description provided for @templateDetails.
  ///
  /// In en, this message translates to:
  /// **'Template details'**
  String get templateDetails;

  /// No description provided for @templateApplied.
  ///
  /// In en, this message translates to:
  /// **'Template applied successfully'**
  String get templateApplied;

  /// No description provided for @templateApplyError.
  ///
  /// In en, this message translates to:
  /// **'Could not apply the template: {error}'**
  String templateApplyError(Object error);

  /// No description provided for @applicationActorAudit.
  ///
  /// In en, this message translates to:
  /// **'Record who applied the template'**
  String get applicationActorAudit;

  /// No description provided for @actorName.
  ///
  /// In en, this message translates to:
  /// **'Actor name'**
  String get actorName;

  /// No description provided for @actorRequiredAudit.
  ///
  /// In en, this message translates to:
  /// **'Actor name is required for the audit trail'**
  String get actorRequiredAudit;

  /// No description provided for @apply.
  ///
  /// In en, this message translates to:
  /// **'Apply'**
  String get apply;

  /// No description provided for @applicationScope.
  ///
  /// In en, this message translates to:
  /// **'Application scope'**
  String get applicationScope;

  /// No description provided for @versionLabel.
  ///
  /// In en, this message translates to:
  /// **'Version'**
  String get versionLabel;

  /// No description provided for @noTemplateItems.
  ///
  /// In en, this message translates to:
  /// **'This template has no artifacts.'**
  String get noTemplateItems;

  /// No description provided for @applyTemplate.
  ///
  /// In en, this message translates to:
  /// **'Apply template'**
  String get applyTemplate;

  /// No description provided for @artifactCount.
  ///
  /// In en, this message translates to:
  /// **'artifacts'**
  String get artifactCount;

  /// No description provided for @exceptionSubmitError.
  ///
  /// In en, this message translates to:
  /// **'Could not submit the exception for review: {error}'**
  String exceptionSubmitError(Object error);

  /// No description provided for @approveExceptionTitle.
  ///
  /// In en, this message translates to:
  /// **'Approve exception'**
  String get approveExceptionTitle;

  /// No description provided for @approverName.
  ///
  /// In en, this message translates to:
  /// **'Approver name'**
  String get approverName;

  /// No description provided for @approve.
  ///
  /// In en, this message translates to:
  /// **'Approve'**
  String get approve;

  /// No description provided for @exceptionApproveError.
  ///
  /// In en, this message translates to:
  /// **'Could not approve the exception: {error}'**
  String exceptionApproveError(Object error);

  /// No description provided for @noExceptions.
  ///
  /// In en, this message translates to:
  /// **'No exceptions are recorded for this profile.'**
  String get noExceptions;

  /// No description provided for @workflowLabel.
  ///
  /// In en, this message translates to:
  /// **'Workflow'**
  String get workflowLabel;

  /// No description provided for @typeLabel.
  ///
  /// In en, this message translates to:
  /// **'Type'**
  String get typeLabel;

  /// No description provided for @justificationLabel.
  ///
  /// In en, this message translates to:
  /// **'Justification'**
  String get justificationLabel;

  /// No description provided for @expiryLabel.
  ///
  /// In en, this message translates to:
  /// **'Expiry'**
  String get expiryLabel;

  /// No description provided for @submitForReview.
  ///
  /// In en, this message translates to:
  /// **'Submit for review'**
  String get submitForReview;

  /// No description provided for @exceptionJustificationRequired.
  ///
  /// In en, this message translates to:
  /// **'An exception justification is required'**
  String get exceptionJustificationRequired;

  /// No description provided for @exceptionSaveError.
  ///
  /// In en, this message translates to:
  /// **'Could not save the exception: {error}'**
  String exceptionSaveError(Object error);

  /// No description provided for @exceptionType.
  ///
  /// In en, this message translates to:
  /// **'Exception type'**
  String get exceptionType;

  /// No description provided for @justificationRequiredLabel.
  ///
  /// In en, this message translates to:
  /// **'Justification (required)'**
  String get justificationRequiredLabel;

  /// No description provided for @expiryDate.
  ///
  /// In en, this message translates to:
  /// **'Expiry date'**
  String get expiryDate;

  /// No description provided for @riskAcceptedByOptional.
  ///
  /// In en, this message translates to:
  /// **'Risk accepted by (optional)'**
  String get riskAcceptedByOptional;

  /// No description provided for @saveDraft.
  ///
  /// In en, this message translates to:
  /// **'Save draft'**
  String get saveDraft;

  /// No description provided for @reportPreview.
  ///
  /// In en, this message translates to:
  /// **'Report preview'**
  String get reportPreview;

  /// No description provided for @exportJson.
  ///
  /// In en, this message translates to:
  /// **'Export JSON'**
  String get exportJson;

  /// No description provided for @exportHtml.
  ///
  /// In en, this message translates to:
  /// **'Export HTML'**
  String get exportHtml;

  /// No description provided for @saveHtmlReport.
  ///
  /// In en, this message translates to:
  /// **'Save HTML report'**
  String get saveHtmlReport;

  /// No description provided for @saveJsonReport.
  ///
  /// In en, this message translates to:
  /// **'Save JSON report'**
  String get saveJsonReport;

  /// No description provided for @reportSaved.
  ///
  /// In en, this message translates to:
  /// **'Report saved locally: {path}'**
  String reportSaved(String path);

  /// No description provided for @reportSaveError.
  ///
  /// In en, this message translates to:
  /// **'Could not save the report: {error}'**
  String reportSaveError(Object error);

  /// No description provided for @savedSuccessfully.
  ///
  /// In en, this message translates to:
  /// **'Saved successfully'**
  String get savedSuccessfully;

  /// No description provided for @saveError.
  ///
  /// In en, this message translates to:
  /// **'Could not save: {error}'**
  String saveError(Object error);

  /// No description provided for @archiveProfileTitle.
  ///
  /// In en, this message translates to:
  /// **'Archive profile?'**
  String get archiveProfileTitle;

  /// No description provided for @archiveProfileWarning.
  ///
  /// In en, this message translates to:
  /// **'This profile will be removed from active use. Continue?'**
  String get archiveProfileWarning;

  /// No description provided for @archiveError.
  ///
  /// In en, this message translates to:
  /// **'Could not archive the profile: {error}'**
  String archiveError(Object error);

  /// No description provided for @saveBackupDialog.
  ///
  /// In en, this message translates to:
  /// **'Save SecureGuide backup'**
  String get saveBackupDialog;

  /// No description provided for @backupSaved.
  ///
  /// In en, this message translates to:
  /// **'The backup was verified and saved.'**
  String get backupSaved;

  /// No description provided for @backupError.
  ///
  /// In en, this message translates to:
  /// **'Could not create the backup: {error}'**
  String backupError(Object error);

  /// No description provided for @chooseBackupDialog.
  ///
  /// In en, this message translates to:
  /// **'Choose a SecureGuide backup'**
  String get chooseBackupDialog;

  /// No description provided for @restoreBackupTitle.
  ///
  /// In en, this message translates to:
  /// **'Restore backup?'**
  String get restoreBackupTitle;

  /// No description provided for @restoreBackupWarning.
  ///
  /// In en, this message translates to:
  /// **'The schema and SQLite integrity will be verified first. The current database will then be preserved as a recovery copy before replacement.'**
  String get restoreBackupWarning;

  /// No description provided for @validateAndRestore.
  ///
  /// In en, this message translates to:
  /// **'Validate and restore'**
  String get validateAndRestore;

  /// No description provided for @restoreSuccess.
  ///
  /// In en, this message translates to:
  /// **'Restore completed. Recovery copy saved at: {path}'**
  String restoreSuccess(String path);

  /// No description provided for @restoreRejected.
  ///
  /// In en, this message translates to:
  /// **'Restore rejected: {error}'**
  String restoreRejected(Object error);

  /// No description provided for @errorWithDetails.
  ///
  /// In en, this message translates to:
  /// **'Error: {error}'**
  String errorWithDetails(Object error);

  /// No description provided for @profileKind.
  ///
  /// In en, this message translates to:
  /// **'Profile kind'**
  String get profileKind;

  /// No description provided for @organizationSize.
  ///
  /// In en, this message translates to:
  /// **'Organization size'**
  String get organizationSize;

  /// No description provided for @industry.
  ///
  /// In en, this message translates to:
  /// **'Industry'**
  String get industry;

  /// No description provided for @country.
  ///
  /// In en, this message translates to:
  /// **'Country'**
  String get country;

  /// No description provided for @targetMaturity.
  ///
  /// In en, this message translates to:
  /// **'Target maturity'**
  String get targetMaturity;

  /// No description provided for @maturityInitial.
  ///
  /// In en, this message translates to:
  /// **'Initial'**
  String get maturityInitial;

  /// No description provided for @maturityManaged.
  ///
  /// In en, this message translates to:
  /// **'Managed'**
  String get maturityManaged;

  /// No description provided for @maturityDefined.
  ///
  /// In en, this message translates to:
  /// **'Defined'**
  String get maturityDefined;

  /// No description provided for @maturityRepeatable.
  ///
  /// In en, this message translates to:
  /// **'Repeatable'**
  String get maturityRepeatable;

  /// No description provided for @maturityOptimized.
  ///
  /// In en, this message translates to:
  /// **'Optimized'**
  String get maturityOptimized;

  /// No description provided for @descriptionLabel.
  ///
  /// In en, this message translates to:
  /// **'Description'**
  String get descriptionLabel;

  /// No description provided for @backupRestore.
  ///
  /// In en, this message translates to:
  /// **'Backup and restore'**
  String get backupRestore;

  /// No description provided for @createLocalBackup.
  ///
  /// In en, this message translates to:
  /// **'Create local backup'**
  String get createLocalBackup;

  /// No description provided for @restoreBackup.
  ///
  /// In en, this message translates to:
  /// **'Restore backup'**
  String get restoreBackup;

  /// No description provided for @archiveProfile.
  ///
  /// In en, this message translates to:
  /// **'Archive profile'**
  String get archiveProfile;

  /// No description provided for @all.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get all;

  /// No description provided for @taskTodo.
  ///
  /// In en, this message translates to:
  /// **'To do'**
  String get taskTodo;

  /// No description provided for @taskInProgress.
  ///
  /// In en, this message translates to:
  /// **'In progress'**
  String get taskInProgress;

  /// No description provided for @taskBlocked.
  ///
  /// In en, this message translates to:
  /// **'Blocked'**
  String get taskBlocked;

  /// No description provided for @taskDone.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get taskDone;

  /// No description provided for @noTasks.
  ///
  /// In en, this message translates to:
  /// **'No tasks at present.'**
  String get noTasks;

  /// No description provided for @untitledTask.
  ///
  /// In en, this message translates to:
  /// **'Untitled task'**
  String get untitledTask;

  /// No description provided for @statusLabel.
  ///
  /// In en, this message translates to:
  /// **'Status'**
  String get statusLabel;

  /// No description provided for @priorityLabel.
  ///
  /// In en, this message translates to:
  /// **'Priority'**
  String get priorityLabel;

  /// No description provided for @assignedToLabel.
  ///
  /// In en, this message translates to:
  /// **'Assigned to'**
  String get assignedToLabel;

  /// No description provided for @startTask.
  ///
  /// In en, this message translates to:
  /// **'Start'**
  String get startTask;

  /// No description provided for @blockTask.
  ///
  /// In en, this message translates to:
  /// **'Block'**
  String get blockTask;

  /// No description provided for @completeTask.
  ///
  /// In en, this message translates to:
  /// **'Complete'**
  String get completeTask;

  /// No description provided for @auditTaskUpdate.
  ///
  /// In en, this message translates to:
  /// **'Record task update'**
  String get auditTaskUpdate;

  /// No description provided for @changeNote.
  ///
  /// In en, this message translates to:
  /// **'Change note'**
  String get changeNote;

  /// No description provided for @blueprintsTitle.
  ///
  /// In en, this message translates to:
  /// **'Implementation blueprints'**
  String get blueprintsTitle;

  /// No description provided for @noBlueprints.
  ///
  /// In en, this message translates to:
  /// **'No blueprints are linked to this profile.'**
  String get noBlueprints;

  /// No description provided for @unnamedBlueprint.
  ///
  /// In en, this message translates to:
  /// **'Unnamed blueprint'**
  String get unnamedBlueprint;

  /// No description provided for @blueprintDetails.
  ///
  /// In en, this message translates to:
  /// **'Blueprint details'**
  String get blueprintDetails;

  /// No description provided for @createdAtLabel.
  ///
  /// In en, this message translates to:
  /// **'Created at'**
  String get createdAtLabel;

  /// No description provided for @createdByLabel.
  ///
  /// In en, this message translates to:
  /// **'Created by'**
  String get createdByLabel;

  /// No description provided for @approvedByLabel.
  ///
  /// In en, this message translates to:
  /// **'Approved by'**
  String get approvedByLabel;

  /// No description provided for @proposedActions.
  ///
  /// In en, this message translates to:
  /// **'Proposed actions'**
  String get proposedActions;

  /// No description provided for @untitled.
  ///
  /// In en, this message translates to:
  /// **'Untitled'**
  String get untitled;

  /// No description provided for @expectedOutputs.
  ///
  /// In en, this message translates to:
  /// **'Expected outputs'**
  String get expectedOutputs;

  /// No description provided for @requiredEvidence.
  ///
  /// In en, this message translates to:
  /// **'Required evidence'**
  String get requiredEvidence;

  /// No description provided for @generationRules.
  ///
  /// In en, this message translates to:
  /// **'Generation rules'**
  String get generationRules;

  /// No description provided for @patternEnrichments.
  ///
  /// In en, this message translates to:
  /// **'Pattern enrichments'**
  String get patternEnrichments;

  /// No description provided for @returnToDraft.
  ///
  /// In en, this message translates to:
  /// **'Return to draft'**
  String get returnToDraft;

  /// No description provided for @approveBlueprint.
  ///
  /// In en, this message translates to:
  /// **'Approve blueprint'**
  String get approveBlueprint;

  /// No description provided for @submitBlueprintReviewTitle.
  ///
  /// In en, this message translates to:
  /// **'Submit blueprint for review'**
  String get submitBlueprintReviewTitle;

  /// No description provided for @approveBlueprintTitle.
  ///
  /// In en, this message translates to:
  /// **'Approve blueprint'**
  String get approveBlueprintTitle;

  /// No description provided for @reviewResolutionNote.
  ///
  /// In en, this message translates to:
  /// **'Review resolution note'**
  String get reviewResolutionNote;

  /// No description provided for @returnBlueprintDraftTitle.
  ///
  /// In en, this message translates to:
  /// **'Return blueprint to draft'**
  String get returnBlueprintDraftTitle;

  /// No description provided for @returnReason.
  ///
  /// In en, this message translates to:
  /// **'Reason for return'**
  String get returnReason;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['ar', 'en'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ar':
      return AppLocalizationsAr();
    case 'en':
      return AppLocalizationsEn();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
