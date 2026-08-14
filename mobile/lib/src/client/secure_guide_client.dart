import '../../read_model_contract.dart';

/// The application boundary the UI binds to.
///
/// Screens depend on `read-model-v1` view objects and delegate persistence and
/// business rules to the local implementation rather than executing SQL.
abstract interface class SecureGuideClient {
  Future<ProfilesView> profiles();

  Future<DashboardView> dashboard({String? profileId});

  Future<BlueprintsView> blueprints(String profileId, {String? artifactId});

  Future<BlueprintDetailView> blueprint(String blueprintId);

  Future<TasksView> tasks(
    String profileId, {
    String? status,
    String? assignedTo,
  });

  Future<void> updateTaskStatus(
    String taskId,
    String newStatus,
    String note, {
    required String actor,
  });

  /// Create an enterprise profile; returns the created profile.
  Future<ProfileSummary> createProfile({
    required String name,
    String? profileKind,
    String? organizationSize,
    String? industry,
    String? country,
    String? targetMaturityLevel,
    String? description,
    bool activate,
  });

  /// Make [profileId] the active profile; returns it.
  Future<ProfileSummary> activateProfile(String profileId);
  Future<ProfileSummary> updateProfile(
    String profileId, {
    String? name,
    String? profileKind,
    String? organizationSize,
    String? industry,
    String? country,
    String? targetMaturityLevel,
    bool clearTargetMaturityLevel = false,
    String? description,
  });
  Future<void> archiveProfile(String profileId);

  /// One page of the master catalog with the profile's selection overlay.
  Future<CatalogView> catalog(
    CatalogFilter filter, {
    String locale = 'en',
    bool selectedOnly = false,
    int limit = 100,
    int offset = 0,
  });

  /// Select catalog artifacts into a profile; returns a selection summary.
  Future<SelectionResult> selectArtifacts(
    List<String> artifactIds, {
    String? profileId,
    String selectedBy = 'app-user',
    String? inclusionStatus,
    String? selectionReason,
  });

  /// Fetch available templates.
  Future<TemplateView> templates();

  /// Fetch the items inside a template.
  Future<CatalogView> templateItems(
    String templateId, {
    int limit = 100,
    int offset = 0,
  });

  /// Apply a template to a profile.
  Future<ProfileSummary> applyTemplate(
    String profileId,
    String templateId, {
    required String appliedBy,
  });

  /// Current profile state and immutable assessment history for one selection.
  Future<ProfileArtifactView> profileArtifact(
    String artifactId, {
    String? profileId,
  });

  /// Record a governed assessment and return the refreshed current state.
  Future<AssessmentResult> assessArtifact(
    String artifactId, {
    String? profileId,
    required String assessorName,
    String? implementationStatus,
    String? verificationStatus,
    String? effectiveness,
    String? currentMaturityLevel,
    String? assignedOwner,
    bool clearAssignedOwner = false,
    String? dueDate,
    bool clearDueDate = false,
    String? notes,
    bool clearNotes = false,
    String? priorityOverride,
    String? reviewFrequencyOverride,
    bool clearPriorityOverride = false,
    bool clearReviewFrequencyOverride = false,
    num? score,
    String? comments,
  });
}
