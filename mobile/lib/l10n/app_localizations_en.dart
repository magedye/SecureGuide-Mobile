// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'SecureGuide';

  @override
  String get dashboard => 'Dashboard';

  @override
  String get catalog => 'Catalog';

  @override
  String get profiles => 'Profiles';

  @override
  String get searchHint => 'Search artifacts...';

  @override
  String get noArtifactsFound => 'No artifacts found';

  @override
  String get implementationStatus => 'Implementation';

  @override
  String get verificationStatus => 'Verification';

  @override
  String get switchToEnglish => 'Switch to English';

  @override
  String get switchToArabic => 'التبديل إلى العربية';

  @override
  String localeChangeError(Object error) {
    return 'Could not save the language preference: $error';
  }

  @override
  String localDataOpenError(Object error) {
    return 'SecureGuide could not open its local data.\n\n$error';
  }

  @override
  String get noProfiles => 'No enterprise profiles yet.';

  @override
  String get createProfileTooltip => 'New enterprise profile';

  @override
  String get tasks => 'Tasks';

  @override
  String get templates => 'Templates';

  @override
  String get exceptionLog => 'Exception log';

  @override
  String get profileSettings => 'Profile settings';

  @override
  String get chooseProfile => 'Choose profile';

  @override
  String get createProfileTitle => 'New enterprise profile';

  @override
  String get profileName => 'Profile name';

  @override
  String get cancel => 'Cancel';

  @override
  String get create => 'Create';

  @override
  String profileCreateError(Object error) {
    return 'Could not create the profile: $error';
  }

  @override
  String profileActivateError(Object error) {
    return 'Could not activate the profile: $error';
  }

  @override
  String get filter => 'Filter';

  @override
  String get catalogFiltersTitle => 'Catalog filters';

  @override
  String get artifactTypeFilter => 'Artifact type';

  @override
  String get primaryDomainFilter => 'Primary domain';

  @override
  String get subDomainFilter => 'Sub-domain';

  @override
  String get priorityFilter => 'Priority';

  @override
  String get testabilityFilter => 'Testability';

  @override
  String get clearFilters => 'Clear';

  @override
  String get applyFilters => 'Apply';

  @override
  String catalogLoadError(Object error) {
    return 'Could not load the catalog: $error';
  }

  @override
  String get noMatchingArtifacts => 'No matching artifacts.';

  @override
  String get openAssessment => 'Open assessment';

  @override
  String get addToProfile => 'Add to profile';

  @override
  String addToProfileError(Object error) {
    return 'Could not add the artifact: $error';
  }

  @override
  String dashboardLoadError(Object error) {
    return 'Could not load the dashboard: $error';
  }

  @override
  String get exportReport => 'Export report';

  @override
  String get totalScore => 'Total score';

  @override
  String get items => 'Items';

  @override
  String get fullyImplemented => 'Fully implemented';

  @override
  String get openGaps => 'Open gaps';

  @override
  String get overdue => 'Overdue';

  @override
  String get recommendations => 'Recommendations';

  @override
  String get noOpenGaps => 'No open gaps.';

  @override
  String get noRecommendations => 'No recommendations.';

  @override
  String get genericErrorTitle => 'Something went wrong';

  @override
  String get retry => 'Try again';

  @override
  String get save => 'Save';

  @override
  String get delete => 'Delete';

  @override
  String get close => 'Close';

  @override
  String get confirm => 'Confirm';

  @override
  String get requiredField => 'This field is required';

  @override
  String requiredValue(String label) {
    return '$label is required';
  }

  @override
  String get notSpecified => 'Not specified';

  @override
  String get unknownItem => 'Unknown artifact';

  @override
  String get artifactDetailsTitle => 'Artifact details';

  @override
  String get detailsTab => 'Details';

  @override
  String get assessmentTab => 'Assessment';

  @override
  String get evidenceTab => 'Evidence';

  @override
  String get remediationPlansTab => 'Remediation plans';

  @override
  String artifactLoadError(Object error) {
    return 'Could not load the artifact: $error';
  }

  @override
  String get definition => 'Definition';

  @override
  String get noDefinition => 'No definition is available.';

  @override
  String get tagsHeading => 'Tags';

  @override
  String get mappingsHeading => 'Mappings';

  @override
  String get referenceLabel => 'Reference';

  @override
  String get relationshipsHeading => 'Relationships';

  @override
  String get targetLabel => 'Target';

  @override
  String get sourceLabel => 'Source';

  @override
  String get operationalState => 'Operational state';

  @override
  String get effectivenessLabel => 'Effectiveness';

  @override
  String get exceptionState => 'Exception status';

  @override
  String get exceptionManagedTooltip =>
      'Managed through the exception approval workflow';

  @override
  String get ownershipPlanning => 'Ownership and planning';

  @override
  String get currentMaturityLevel => 'Current maturity level';

  @override
  String get overrideCatalogPriority => 'Override catalog or template priority';

  @override
  String get effectiveNow => 'Effective now';

  @override
  String get customPriority => 'Custom priority';

  @override
  String get overrideReviewFrequency => 'Override review frequency';

  @override
  String get customReviewFrequency => 'Custom review frequency';

  @override
  String get assignedOwner => 'Assigned owner';

  @override
  String get dueDate => 'Due date';

  @override
  String get clearDate => 'Clear date';

  @override
  String get currentStateNotes => 'Current-state notes';

  @override
  String get newAssessmentRecord => 'New assessment record';

  @override
  String get assessorName => 'Assessor name';

  @override
  String get assessorRequired => 'Assessor name is required';

  @override
  String get scoreLabel => 'Score (0–100)';

  @override
  String get scoreValidation => 'Enter a score between 0 and 100';

  @override
  String get assessmentComment => 'Assessment comment';

  @override
  String get saveAssessment => 'Save assessment';

  @override
  String get assessmentSaved => 'Assessment saved.';

  @override
  String assessmentSaveError(Object error) {
    return 'Could not save the assessment: $error';
  }

  @override
  String get assessmentHistory => 'Assessment history';

  @override
  String get noPreviousAssessments => 'No previous assessments.';

  @override
  String get unscored => 'No score';

  @override
  String get manageException => 'Manage exception';

  @override
  String get deleteEvidenceTitle => 'Delete evidence';

  @override
  String get deleteEvidenceConfirm => 'Permanently delete this evidence item?';

  @override
  String get evidenceDeleted => 'Evidence deleted';

  @override
  String evidenceDeleteError(Object error) {
    return 'Could not delete the evidence: $error';
  }

  @override
  String get evidenceDetails => 'Evidence details';

  @override
  String get evidenceType => 'Evidence type';

  @override
  String get evidenceCollector => 'Collected by';

  @override
  String get evidenceAddedAt => 'Added at';

  @override
  String get fileSize => 'Size';

  @override
  String get sha256Fingerprint => 'SHA-256 fingerprint';

  @override
  String get unsupportedEvidencePreview =>
      'The file passed integrity checks, but this type cannot be previewed in the app.';

  @override
  String evidenceOpenError(Object error) {
    return 'Could not open the evidence safely: $error';
  }

  @override
  String get noEvidence => 'No evidence attached.';

  @override
  String get addEvidence => 'Add evidence';

  @override
  String get integrityValid => 'Evidence integrity verified';

  @override
  String get integrityMissing => 'Evidence file is missing';

  @override
  String get integrityCorrupted => 'Evidence fingerprint verification failed';

  @override
  String get integrityUnsafePath => 'Evidence path is unsafe';

  @override
  String get integrityVerifying => 'Verifying';

  @override
  String get addEvidenceTitle => 'Add new evidence';

  @override
  String get evidenceDescriptionOptional => 'Evidence description (optional)';

  @override
  String get chooseFile => 'Choose file...';

  @override
  String get saveEvidence => 'Save evidence';

  @override
  String evidenceAddError(Object error) {
    return 'Could not add the evidence: $error';
  }

  @override
  String get noTemplates => 'No templates are available.';

  @override
  String get unknownTemplate => 'Unknown template';

  @override
  String get templateDetails => 'Template details';

  @override
  String get templateApplied => 'Template applied successfully';

  @override
  String templateApplyError(Object error) {
    return 'Could not apply the template: $error';
  }

  @override
  String get applicationActorAudit => 'Record who applied the template';

  @override
  String get actorName => 'Actor name';

  @override
  String get actorRequiredAudit => 'Actor name is required for the audit trail';

  @override
  String get apply => 'Apply';

  @override
  String get applicationScope => 'Application scope';

  @override
  String get versionLabel => 'Version';

  @override
  String get noTemplateItems => 'This template has no artifacts.';

  @override
  String get applyTemplate => 'Apply template';

  @override
  String get artifactCount => 'artifacts';

  @override
  String exceptionSubmitError(Object error) {
    return 'Could not submit the exception for review: $error';
  }

  @override
  String get approveExceptionTitle => 'Approve exception';

  @override
  String get approverName => 'Approver name';

  @override
  String get approve => 'Approve';

  @override
  String exceptionApproveError(Object error) {
    return 'Could not approve the exception: $error';
  }

  @override
  String get noExceptions => 'No exceptions are recorded for this profile.';

  @override
  String get workflowLabel => 'Workflow';

  @override
  String get typeLabel => 'Type';

  @override
  String get justificationLabel => 'Justification';

  @override
  String get expiryLabel => 'Expiry';

  @override
  String get submitForReview => 'Submit for review';

  @override
  String get exceptionJustificationRequired =>
      'An exception justification is required';

  @override
  String exceptionSaveError(Object error) {
    return 'Could not save the exception: $error';
  }

  @override
  String get exceptionType => 'Exception type';

  @override
  String get justificationRequiredLabel => 'Justification (required)';

  @override
  String get expiryDate => 'Expiry date';

  @override
  String get riskAcceptedByOptional => 'Risk accepted by (optional)';

  @override
  String get saveDraft => 'Save draft';

  @override
  String get reportPreview => 'Report preview';

  @override
  String get exportJson => 'Export JSON';

  @override
  String get exportHtml => 'Export HTML';

  @override
  String get saveHtmlReport => 'Save HTML report';

  @override
  String get saveJsonReport => 'Save JSON report';

  @override
  String reportSaved(String path) {
    return 'Report saved locally: $path';
  }

  @override
  String reportSaveError(Object error) {
    return 'Could not save the report: $error';
  }

  @override
  String get savedSuccessfully => 'Saved successfully';

  @override
  String saveError(Object error) {
    return 'Could not save: $error';
  }

  @override
  String get archiveProfileTitle => 'Archive profile?';

  @override
  String get archiveProfileWarning =>
      'This profile will be removed from active use. Continue?';

  @override
  String archiveError(Object error) {
    return 'Could not archive the profile: $error';
  }

  @override
  String get saveBackupDialog => 'Save SecureGuide backup';

  @override
  String get backupSaved => 'The backup was verified and saved.';

  @override
  String backupError(Object error) {
    return 'Could not create the backup: $error';
  }

  @override
  String get chooseBackupDialog => 'Choose a SecureGuide backup';

  @override
  String get restoreBackupTitle => 'Restore backup?';

  @override
  String get restoreBackupWarning =>
      'The schema and SQLite integrity will be verified first. The current database will then be preserved as a recovery copy before replacement.';

  @override
  String get validateAndRestore => 'Validate and restore';

  @override
  String restoreSuccess(String path) {
    return 'Restore completed. Recovery copy saved at: $path';
  }

  @override
  String restoreRejected(Object error) {
    return 'Restore rejected: $error';
  }

  @override
  String errorWithDetails(Object error) {
    return 'Error: $error';
  }

  @override
  String get profileKind => 'Profile kind';

  @override
  String get organizationSize => 'Organization size';

  @override
  String get industry => 'Industry';

  @override
  String get country => 'Country';

  @override
  String get targetMaturity => 'Target maturity';

  @override
  String get maturityInitial => 'Initial';

  @override
  String get maturityManaged => 'Managed';

  @override
  String get maturityDefined => 'Defined';

  @override
  String get maturityRepeatable => 'Repeatable';

  @override
  String get maturityOptimized => 'Optimized';

  @override
  String get descriptionLabel => 'Description';

  @override
  String get backupRestore => 'Backup and restore';

  @override
  String get createLocalBackup => 'Create local backup';

  @override
  String get restoreBackup => 'Restore backup';

  @override
  String get archiveProfile => 'Archive profile';

  @override
  String get all => 'All';

  @override
  String get taskTodo => 'To do';

  @override
  String get taskInProgress => 'In progress';

  @override
  String get taskBlocked => 'Blocked';

  @override
  String get taskDone => 'Done';

  @override
  String get noTasks => 'No tasks at present.';

  @override
  String get untitledTask => 'Untitled task';

  @override
  String get statusLabel => 'Status';

  @override
  String get priorityLabel => 'Priority';

  @override
  String get assignedToLabel => 'Assigned to';

  @override
  String get startTask => 'Start';

  @override
  String get blockTask => 'Block';

  @override
  String get completeTask => 'Complete';

  @override
  String get auditTaskUpdate => 'Record task update';

  @override
  String get changeNote => 'Change note';

  @override
  String get blueprintsTitle => 'Implementation blueprints';

  @override
  String get noBlueprints => 'No blueprints are linked to this profile.';

  @override
  String get unnamedBlueprint => 'Unnamed blueprint';

  @override
  String get blueprintDetails => 'Blueprint details';

  @override
  String get createdAtLabel => 'Created at';

  @override
  String get createdByLabel => 'Created by';

  @override
  String get approvedByLabel => 'Approved by';

  @override
  String get proposedActions => 'Proposed actions';

  @override
  String get untitled => 'Untitled';

  @override
  String get expectedOutputs => 'Expected outputs';

  @override
  String get requiredEvidence => 'Required evidence';

  @override
  String get generationRules => 'Generation rules';

  @override
  String get patternEnrichments => 'Pattern enrichments';

  @override
  String get returnToDraft => 'Return to draft';

  @override
  String get approveBlueprint => 'Approve blueprint';

  @override
  String get submitBlueprintReviewTitle => 'Submit blueprint for review';

  @override
  String get approveBlueprintTitle => 'Approve blueprint';

  @override
  String get reviewResolutionNote => 'Review resolution note';

  @override
  String get returnBlueprintDraftTitle => 'Return blueprint to draft';

  @override
  String get returnReason => 'Reason for return';
}
