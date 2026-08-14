import 'dart:convert';
import 'dart:io';

import 'package:secureguide_mobile/read_model_contract.dart';
import 'package:secureguide_mobile/src/client/secure_guide_client.dart';

/// Load a shared golden fixture by surface name (resolves from the package dir
/// or the repo root). The same fixtures the Python + contract tests are pinned
/// to, so widget tests exercise the real wire shapes.
Map<String, dynamic> loadGolden(String name) {
  const candidates = [
    '../tests/fixtures/read_models/',
    'tests/fixtures/read_models/',
  ];
  for (final dir in candidates) {
    final file = File('$dir$name.json');
    if (file.existsSync()) {
      return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
    }
  }
  throw StateError(
    'golden fixture "$name" not found (cwd=${Directory.current.path})',
  );
}

Map<String, ProfileArtifactView> _initialArtifactViews(
  ProfileArtifactView? view,
) {
  final artifactId = view?.artifact.artifactId;
  if (view == null || artifactId == null) return {};
  return {artifactId: view};
}

/// In-memory [SecureGuideClient] for widget tests: no sidecar, no network.
/// Reads return canned views; writes mutate local state and are recorded so a
/// test can assert the UI took the governed write path.
class FakeSecureGuideClient implements SecureGuideClient {
  FakeSecureGuideClient({
    required this.dashboardView,
    required List<ProfileSummary> profiles,
    List<Map<String, dynamic>> catalogItems = const [],
    ProfileArtifactView? profileArtifactView,
  }) : _profiles = List.of(profiles),
       _catalogItems = catalogItems
           .map((m) => Map<String, dynamic>.of(m))
           .toList(),
       _selected = {
         for (final m in catalogItems)
           if (m['isSelected'] == true) m['id'] as String,
       },
       _profileArtifactViews = _initialArtifactViews(profileArtifactView);

  final DashboardView dashboardView;
  List<ProfileSummary> _profiles;
  final List<Map<String, dynamic>> _catalogItems;
  final Set<String> _selected;
  final Map<String, ProfileArtifactView> _profileArtifactViews;

  ProfileSummary? lastCreated;
  String? lastActivated;
  List<String>? lastSelected;
  AssessmentRecord? lastAssessment;

  @override
  Future<ProfilesView> profiles() async =>
      ProfilesView(profiles: List.of(_profiles));

  @override
  Future<DashboardView> dashboard({String? profileId}) async => dashboardView;

  @override
  Future<CatalogView> catalog(
    CatalogFilter filter, {
    String locale = 'en',
    bool selectedOnly = false,
    int limit = 100,
    int offset = 0,
  }) async {
    var items = _catalogItems;
    final query = filter.searchQuery;
    if (query != null && query.trim().isNotEmpty) {
      final needle = query.toLowerCase();
      items = items
          .where(
            (m) => (m['title'] as String? ?? '').toLowerCase().contains(needle),
          )
          .toList();
    }
    final rendered = [
      for (final m in items) {...m, 'isSelected': _selected.contains(m['id'])},
    ];
    return CatalogView.fromJson({
      'contractVersion': kContractVersion,
      'locale': locale,
      'query': query,
      'limit': limit,
      'offset': offset,
      'count': rendered.length,
      'items': rendered,
    });
  }

  @override
  Future<SelectionResult> selectArtifacts(
    List<String> artifactIds, {
    String? profileId,
    String selectedBy = 'app-user',
    String? inclusionStatus,
    String? selectionReason,
  }) async {
    lastSelected = artifactIds;
    var created = 0;
    for (final id in artifactIds) {
      if (_selected.add(id)) created++;
    }
    return SelectionResult(
      profileId: profileId,
      requested: artifactIds.length,
      created: created,
      existing: artifactIds.length - created,
      originsAdded: created,
    );
  }

  @override
  Future<TemplateView> templates() async => const TemplateView();

  @override
  Future<CatalogView> templateItems(
    String templateId, {
    int limit = 100,
    int offset = 0,
  }) async => const CatalogView();

  @override
  Future<ProfileSummary> applyTemplate(
    String profileId,
    String templateId, {
    required String appliedBy,
  }) async {
    return ProfileSummary(id: profileId, name: 'Fake Profile');
  }

  @override
  Future<ProfileSummary> createProfile({
    required String name,
    String? profileKind,
    String? organizationSize,
    String? industry,
    String? country,
    String? targetMaturityLevel,
    String? description,
    bool activate = false,
  }) async {
    final created = ProfileSummary(
      id: 'PRF-$name',
      name: name,
      isActive: activate,
    );
    _profiles = [..._profiles, created];
    lastCreated = created;
    return created;
  }

  @override
  Future<ProfileSummary> activateProfile(String profileId) async {
    lastActivated = profileId;
    return _profiles.firstWhere(
      (p) => p.id == profileId,
      orElse: () => ProfileSummary(id: profileId, isActive: true),
    );
  }

  @override
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
  }) async {
    return _profiles.firstWhere((p) => p.id == profileId);
  }

  @override
  Future<void> archiveProfile(String profileId) async {
    // No-op for now
  }

  @override
  Future<ProfileArtifactView> profileArtifact(
    String artifactId, {
    String? profileId,
  }) async {
    final existing = _profileArtifactViews[artifactId];
    if (existing != null) return existing;
    final source = _catalogItems.firstWhere((m) => m['id'] == artifactId);
    final view = ProfileArtifactView(
      profileId: profileId,
      artifact: OperationalItem(
        profileArtifactId: source['profileArtifactId'] as String?,
        artifactId: artifactId,
        type: source['type'] as String?,
        titleEn: source['title'] as String?,
        primaryDomain: source['primaryDomain'] as String?,
        subDomain: source['subDomain'] as String?,
        effectivePriority: source['effectivePriority'] as String?,
        implementationStatus: source['implementationStatus'] as String?,
        verificationStatus: source['verificationStatus'] as String?,
        effectiveness: source['effectiveness'] as String?,
        exceptionStatus: source['exceptionStatus'] as String?,
      ),
    );
    _profileArtifactViews[artifactId] = view;
    return view;
  }

  @override
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
  }) async {
    final current = await profileArtifact(artifactId, profileId: profileId);
    final old = current.artifact;
    final artifact = OperationalItem(
      profileArtifactId: old.profileArtifactId,
      artifactId: old.artifactId,
      type: old.type,
      titleEn: old.titleEn,
      titleAr: old.titleAr,
      definitionShortEn: old.definitionShortEn,
      definitionShortAr: old.definitionShortAr,
      primaryDomain: old.primaryDomain,
      subDomain: old.subDomain,
      source: old.source,
      sourceDocument: old.sourceDocument,
      obligationLevel: old.obligationLevel,
      testability: old.testability,
      inclusionStatus: old.inclusionStatus,
      effectivePriority: priorityOverride ?? old.effectivePriority,
      effectiveReviewFrequency:
          reviewFrequencyOverride ?? old.effectiveReviewFrequency,
      priorityOverride: clearPriorityOverride
          ? null
          : priorityOverride ?? old.priorityOverride,
      reviewFrequencyOverride: clearReviewFrequencyOverride
          ? null
          : reviewFrequencyOverride ?? old.reviewFrequencyOverride,
      implementationStatus: implementationStatus ?? old.implementationStatus,
      verificationStatus: verificationStatus ?? old.verificationStatus,
      effectiveness: effectiveness ?? old.effectiveness,
      exceptionStatus: old.exceptionStatus,
      currentMaturityLevel: currentMaturityLevel ?? old.currentMaturityLevel,
      assignedOwner: clearAssignedOwner
          ? null
          : assignedOwner ?? old.assignedOwner,
      dueDate: clearDueDate ? null : dueDate ?? old.dueDate,
      notes: clearNotes ? null : notes ?? old.notes,
      evidenceCount: old.evidenceCount,
      originCount: old.originCount,
      lastAssessmentAt: '<ts>',
      selectedAt: old.selectedAt,
      updatedAt: '<ts>',
    );
    final assessment = AssessmentRecord(
      id: 'ASM-FAKE',
      profileArtifactId: artifact.profileArtifactId,
      assessmentDate: '<ts>',
      assessorName: assessorName,
      score: score,
      implementationStatus: artifact.implementationStatus,
      verificationStatus: artifact.verificationStatus,
      effectiveness: artifact.effectiveness,
      exceptionStatus: artifact.exceptionStatus,
      comments: comments,
    );
    lastAssessment = assessment;
    _profileArtifactViews[artifactId] = ProfileArtifactView(
      profileId: profileId,
      artifact: artifact,
      assessments: [assessment, ...current.assessments],
    );
    for (final item in _catalogItems.where((m) => m['id'] == artifactId)) {
      item['implementationStatus'] = artifact.implementationStatus;
      item['verificationStatus'] = artifact.verificationStatus;
      item['effectiveness'] = artifact.effectiveness;
    }
    return AssessmentResult(assessment: assessment, artifact: artifact);
  }

  @override
  Future<BlueprintsView> blueprints(
    String profileId, {
    String? artifactId,
  }) async {
    return const BlueprintsView(blueprints: []);
  }

  @override
  Future<BlueprintDetailView> blueprint(String blueprintId) async {
    throw UnimplementedError(
      'FakeSecureGuideClient does not implement blueprint',
    );
  }

  @override
  Future<TasksView> tasks(
    String profileId, {
    String? status,
    String? assignedTo,
  }) async {
    return const TasksView(tasks: []);
  }

  @override
  Future<void> updateTaskStatus(
    String taskId,
    String newStatus,
    String note, {
    required String actor,
  }) async {
    // No-op for now
  }
}
