/// Dart mirror of the SecureGuide `read-model-v1` wire contract.
///
/// These data classes mirror the Python read-model layer
/// (`secureguide/read_models.py`) one-to-one, using the same `camelCase` keys.
/// This first slice covers only the two surfaces needed to prove the contract
/// end-to-end before any screen: `profiles` and `dashboard`.
///
/// Fidelity rules that keep the mirror honest against the golden fixtures:
///
/// * Numeric fields are typed `num?` and passed through untouched, so an int
///   stays an int and a double stays a double on round-trip (`fromJson` then
///   `toJson` reproduces the exact JSON).
/// * Every field the contract emits is emitted back by `toJson`, including
///   `null`s — no key is dropped.
/// * No logic lives here: this is a transport mirror, not a view model. Screens
///   bind to these objects; they never re-derive scoring/exception/approval.
library;

/// The wire contract version this mirror targets. Must stay equal to the Python
/// `secureguide.read_models.CONTRACT_VERSION`.
const String kContractVersion = 'read-model-v1';

List<T> _mapList<T>(Object? raw, T Function(Map<String, dynamic>) from) =>
    (raw as List<dynamic>? ?? const <dynamic>[])
        .map((e) => from(e as Map<String, dynamic>))
        .toList();

/// Enterprise profile as shown in the selector and dashboard header.
class ProfileSummary {
  const ProfileSummary({
    this.id,
    this.name,
    this.description,
    this.profileKind,
    this.organizationSize,
    this.industry,
    this.country,
    this.targetMaturityLevel,
    this.isActive,
  });

  final String? id;
  final String? name;
  final String? description;
  final String? profileKind;
  final String? organizationSize;
  final String? industry;
  final String? country;
  final String? targetMaturityLevel;
  final bool? isActive;

  factory ProfileSummary.fromJson(Map<String, dynamic> json) => ProfileSummary(
    id: json['id'] as String?,
    name: json['name'] as String?,
    description: json['description'] as String?,
    profileKind: json['profileKind'] as String?,
    organizationSize: json['organizationSize'] as String?,
    industry: json['industry'] as String?,
    country: json['country'] as String?,
    targetMaturityLevel: json['targetMaturityLevel'] as String?,
    isActive: json['isActive'] as bool?,
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'description': description,
    'profileKind': profileKind,
    'organizationSize': organizationSize,
    'industry': industry,
    'country': country,
    'targetMaturityLevel': targetMaturityLevel,
    'isActive': isActive,
  };
}

/// The auditable `profile-score-v1` result, passed through unchanged.
class ScoreView {
  const ScoreView({
    this.overall,
    this.band,
    this.capped,
    this.formulaVersion,
    this.assessmentCoverage,
    this.riskReductionPct,
    this.implementationScoreRaw,
    this.verificationCoverage,
    this.verificationAssessmentCoverage,
    this.effectivenessKnown,
    this.assessedControls,
    this.totalControls,
    this.remainingCriticalRisk,
    this.criticalTotal,
    this.criticalCompliant,
    this.criticalAccepted,
    this.verifiedPass,
    this.verifiedFail,
    this.effectivenessKnownCount,
    this.domainScores = const {},
  });

  final num? overall;
  final String? band;
  final bool? capped;
  final String? formulaVersion;
  final num? assessmentCoverage;
  final num? riskReductionPct;
  final num? implementationScoreRaw;
  final num? verificationCoverage;
  final num? verificationAssessmentCoverage;
  final num? effectivenessKnown;
  final num? assessedControls;
  final num? totalControls;
  final num? remainingCriticalRisk;
  final num? criticalTotal;
  final num? criticalCompliant;
  final num? criticalAccepted;
  final num? verifiedPass;
  final num? verifiedFail;
  final num? effectivenessKnownCount;

  /// Domain code (e.g. `SD-03`) -> percentage. Keys are data, not field names.
  final Map<String, num> domainScores;

  factory ScoreView.fromJson(Map<String, dynamic> json) => ScoreView(
    overall: json['overall'] as num?,
    band: json['band'] as String?,
    capped: json['capped'] as bool?,
    formulaVersion: json['formulaVersion'] as String?,
    assessmentCoverage: json['assessmentCoverage'] as num?,
    riskReductionPct: json['riskReductionPct'] as num?,
    implementationScoreRaw: json['implementationScoreRaw'] as num?,
    verificationCoverage: json['verificationCoverage'] as num?,
    verificationAssessmentCoverage:
        json['verificationAssessmentCoverage'] as num?,
    effectivenessKnown: json['effectivenessKnown'] as num?,
    assessedControls: json['assessedControls'] as num?,
    totalControls: json['totalControls'] as num?,
    remainingCriticalRisk: json['remainingCriticalRisk'] as num?,
    criticalTotal: json['criticalTotal'] as num?,
    criticalCompliant: json['criticalCompliant'] as num?,
    criticalAccepted: json['criticalAccepted'] as num?,
    verifiedPass: json['verifiedPass'] as num?,
    verifiedFail: json['verifiedFail'] as num?,
    effectivenessKnownCount: json['effectivenessKnownCount'] as num?,
    domainScores: (json['domainScores'] as Map<String, dynamic>? ?? const {})
        .map((key, value) => MapEntry(key, value as num)),
  );

  Map<String, dynamic> toJson() => {
    'overall': overall,
    'band': band,
    'capped': capped,
    'formulaVersion': formulaVersion,
    'assessmentCoverage': assessmentCoverage,
    'riskReductionPct': riskReductionPct,
    'implementationScoreRaw': implementationScoreRaw,
    'verificationCoverage': verificationCoverage,
    'verificationAssessmentCoverage': verificationAssessmentCoverage,
    'effectivenessKnown': effectivenessKnown,
    'assessedControls': assessedControls,
    'totalControls': totalControls,
    'remainingCriticalRisk': remainingCriticalRisk,
    'criticalTotal': criticalTotal,
    'criticalCompliant': criticalCompliant,
    'criticalAccepted': criticalAccepted,
    'verifiedPass': verifiedPass,
    'verifiedFail': verifiedFail,
    'effectivenessKnownCount': effectivenessKnownCount,
    'domainScores': domainScores,
  };
}

/// Rollup counts from `v_profile_dashboard`.
class DashboardCounts {
  const DashboardCounts({
    this.totalItems,
    this.applicableItems,
    this.implementedFull,
    this.implementedPartial,
    this.notApplied,
    this.verifiedPass,
    this.verifiedFail,
    this.withException,
    this.openGaps,
    this.overdueItems,
  });

  final num? totalItems;
  final num? applicableItems;
  final num? implementedFull;
  final num? implementedPartial;
  final num? notApplied;
  final num? verifiedPass;
  final num? verifiedFail;
  final num? withException;
  final num? openGaps;
  final num? overdueItems;

  factory DashboardCounts.fromJson(Map<String, dynamic> json) =>
      DashboardCounts(
        totalItems: json['totalItems'] as num?,
        applicableItems: json['applicableItems'] as num?,
        implementedFull: json['implementedFull'] as num?,
        implementedPartial: json['implementedPartial'] as num?,
        notApplied: json['notApplied'] as num?,
        verifiedPass: json['verifiedPass'] as num?,
        verifiedFail: json['verifiedFail'] as num?,
        withException: json['withException'] as num?,
        openGaps: json['openGaps'] as num?,
        overdueItems: json['overdueItems'] as num?,
      );

  Map<String, dynamic> toJson() => {
    'totalItems': totalItems,
    'applicableItems': applicableItems,
    'implementedFull': implementedFull,
    'implementedPartial': implementedPartial,
    'notApplied': notApplied,
    'verifiedPass': verifiedPass,
    'verifiedFail': verifiedFail,
    'withException': withException,
    'openGaps': openGaps,
    'overdueItems': overdueItems,
  };
}

/// One open gap from `v_gap_analysis`.
class GapItem {
  const GapItem({
    this.artifactId,
    this.titleEn,
    this.primaryDomain,
    this.subDomain,
    this.priority,
    this.implementationStatus,
    this.verificationStatus,
    this.effectiveness,
    this.exceptionStatus,
    this.assignedOwner,
    this.dueDate,
  });

  final String? artifactId;
  final String? titleEn;
  final String? primaryDomain;
  final String? subDomain;
  final String? priority;
  final String? implementationStatus;
  final String? verificationStatus;
  final String? effectiveness;
  final String? exceptionStatus;
  final String? assignedOwner;
  final String? dueDate;

  factory GapItem.fromJson(Map<String, dynamic> json) => GapItem(
    artifactId: json['artifactId'] as String?,
    titleEn: json['titleEn'] as String?,
    primaryDomain: json['primaryDomain'] as String?,
    subDomain: json['subDomain'] as String?,
    priority: json['priority'] as String?,
    implementationStatus: json['implementationStatus'] as String?,
    verificationStatus: json['verificationStatus'] as String?,
    effectiveness: json['effectiveness'] as String?,
    exceptionStatus: json['exceptionStatus'] as String?,
    assignedOwner: json['assignedOwner'] as String?,
    dueDate: json['dueDate'] as String?,
  );

  Map<String, dynamic> toJson() => {
    'artifactId': artifactId,
    'titleEn': titleEn,
    'primaryDomain': primaryDomain,
    'subDomain': subDomain,
    'priority': priority,
    'implementationStatus': implementationStatus,
    'verificationStatus': verificationStatus,
    'effectiveness': effectiveness,
    'exceptionStatus': exceptionStatus,
    'assignedOwner': assignedOwner,
    'dueDate': dueDate,
  };
}

/// One deterministic recommendation from the scoring engine.
class RecommendationItem {
  const RecommendationItem({
    this.artifactId,
    this.priority,
    this.dependencyReady,
    this.reasonCodes = const [],
  });

  final String? artifactId;
  final String? priority;
  final bool? dependencyReady;
  final List<String> reasonCodes;

  factory RecommendationItem.fromJson(Map<String, dynamic> json) =>
      RecommendationItem(
        artifactId: json['artifactId'] as String?,
        priority: json['priority'] as String?,
        dependencyReady: json['dependencyReady'] as bool?,
        reasonCodes: (json['reasonCodes'] as List<dynamic>? ?? const [])
            .map((e) => e as String)
            .toList(),
      );

  Map<String, dynamic> toJson() => {
    'artifactId': artifactId,
    'priority': priority,
    'dependencyReady': dependencyReady,
    'reasonCodes': reasonCodes,
  };
}

/// A selected artifact with its single-profile operational state
/// (`v_profile_operational_items`); also the dashboard review-queue item.
class OperationalItem {
  const OperationalItem({
    this.profileArtifactId,
    this.artifactId,
    this.type,
    this.titleEn,
    this.titleAr,
    this.definitionShortEn,
    this.definitionShortAr,
    this.primaryDomain,
    this.subDomain,
    this.source,
    this.sourceDocument,
    this.obligationLevel,
    this.testability,
    this.inclusionStatus,
    this.effectivePriority,
    this.effectiveReviewFrequency,
    this.priorityOverride,
    this.reviewFrequencyOverride,
    this.implementationStatus,
    this.verificationStatus,
    this.effectiveness,
    this.exceptionStatus,
    this.currentMaturityLevel,
    this.assignedOwner,
    this.dueDate,
    this.notes,
    this.evidenceCount,
    this.originCount,
    this.lastAssessmentAt,
    this.selectedAt,
    this.updatedAt,
  });

  final String? profileArtifactId;
  final String? artifactId;
  final String? type;
  final String? titleEn;
  final String? titleAr;
  final String? definitionShortEn;
  final String? definitionShortAr;
  final String? primaryDomain;
  final String? subDomain;
  final String? source;
  final String? sourceDocument;
  final String? obligationLevel;
  final String? testability;
  final String? inclusionStatus;
  final String? effectivePriority;
  final String? effectiveReviewFrequency;
  final String? priorityOverride;
  final String? reviewFrequencyOverride;
  final String? implementationStatus;
  final String? verificationStatus;
  final String? effectiveness;
  final String? exceptionStatus;
  final String? currentMaturityLevel;
  final String? assignedOwner;
  final String? dueDate;
  final String? notes;
  final num? evidenceCount;
  final num? originCount;
  final String? lastAssessmentAt;
  final String? selectedAt;
  final String? updatedAt;

  factory OperationalItem.fromJson(Map<String, dynamic> json) =>
      OperationalItem(
        profileArtifactId: json['profileArtifactId'] as String?,
        artifactId: json['artifactId'] as String?,
        type: json['type'] as String?,
        titleEn: json['titleEn'] as String?,
        titleAr: json['titleAr'] as String?,
        definitionShortEn: json['definitionShortEn'] as String?,
        definitionShortAr: json['definitionShortAr'] as String?,
        primaryDomain: json['primaryDomain'] as String?,
        subDomain: json['subDomain'] as String?,
        source: json['source'] as String?,
        sourceDocument: json['sourceDocument'] as String?,
        obligationLevel: json['obligationLevel'] as String?,
        testability: json['testability'] as String?,
        inclusionStatus: json['inclusionStatus'] as String?,
        effectivePriority: json['effectivePriority'] as String?,
        effectiveReviewFrequency: json['effectiveReviewFrequency'] as String?,
        priorityOverride: json['priorityOverride'] as String?,
        reviewFrequencyOverride: json['reviewFrequencyOverride'] as String?,
        implementationStatus: json['implementationStatus'] as String?,
        verificationStatus: json['verificationStatus'] as String?,
        effectiveness: json['effectiveness'] as String?,
        exceptionStatus: json['exceptionStatus'] as String?,
        currentMaturityLevel: json['currentMaturityLevel'] as String?,
        assignedOwner: json['assignedOwner'] as String?,
        dueDate: json['dueDate'] as String?,
        notes: json['notes'] as String?,
        evidenceCount: json['evidenceCount'] as num?,
        originCount: json['originCount'] as num?,
        lastAssessmentAt: json['lastAssessmentAt'] as String?,
        selectedAt: json['selectedAt'] as String?,
        updatedAt: json['updatedAt'] as String?,
      );

  Map<String, dynamic> toJson() => {
    'profileArtifactId': profileArtifactId,
    'artifactId': artifactId,
    'type': type,
    'titleEn': titleEn,
    'titleAr': titleAr,
    'definitionShortEn': definitionShortEn,
    'definitionShortAr': definitionShortAr,
    'primaryDomain': primaryDomain,
    'subDomain': subDomain,
    'source': source,
    'sourceDocument': sourceDocument,
    'obligationLevel': obligationLevel,
    'testability': testability,
    'inclusionStatus': inclusionStatus,
    'effectivePriority': effectivePriority,
    'effectiveReviewFrequency': effectiveReviewFrequency,
    'priorityOverride': priorityOverride,
    'reviewFrequencyOverride': reviewFrequencyOverride,
    'implementationStatus': implementationStatus,
    'verificationStatus': verificationStatus,
    'effectiveness': effectiveness,
    'exceptionStatus': exceptionStatus,
    'currentMaturityLevel': currentMaturityLevel,
    'assignedOwner': assignedOwner,
    'dueDate': dueDate,
    'notes': notes,
    'evidenceCount': evidenceCount,
    'originCount': originCount,
    'lastAssessmentAt': lastAssessmentAt,
    'selectedAt': selectedAt,
    'updatedAt': updatedAt,
  };
}

/// Envelope for the `profiles()` surface.
class ProfilesView {
  const ProfilesView({
    this.contractVersion = kContractVersion,
    this.profiles = const [],
  });

  final String contractVersion;
  final List<ProfileSummary> profiles;

  factory ProfilesView.fromJson(Map<String, dynamic> json) => ProfilesView(
    contractVersion: json['contractVersion'] as String,
    profiles: _mapList(json['profiles'], ProfileSummary.fromJson),
  );

  Map<String, dynamic> toJson() => {
    'contractVersion': contractVersion,
    'profiles': profiles.map((e) => e.toJson()).toList(),
  };
}

/// Envelope for the `dashboard()` surface.
class DashboardView {
  const DashboardView({
    this.contractVersion = kContractVersion,
    required this.profile,
    required this.counts,
    required this.score,
    this.gaps = const [],
    this.recommendations = const [],
    this.reviewQueue = const [],
  });

  final String contractVersion;
  final ProfileSummary profile;
  final DashboardCounts counts;
  final ScoreView score;
  final List<GapItem> gaps;
  final List<RecommendationItem> recommendations;
  final List<OperationalItem> reviewQueue;

  factory DashboardView.fromJson(Map<String, dynamic> json) => DashboardView(
    contractVersion: json['contractVersion'] as String,
    profile: ProfileSummary.fromJson(json['profile'] as Map<String, dynamic>),
    counts: DashboardCounts.fromJson(json['counts'] as Map<String, dynamic>),
    score: ScoreView.fromJson(json['score'] as Map<String, dynamic>),
    gaps: _mapList(json['gaps'], GapItem.fromJson),
    recommendations: _mapList(
      json['recommendations'],
      RecommendationItem.fromJson,
    ),
    reviewQueue: _mapList(json['reviewQueue'], OperationalItem.fromJson),
  );

  Map<String, dynamic> toJson() => {
    'contractVersion': contractVersion,
    'profile': profile.toJson(),
    'counts': counts.toJson(),
    'score': score.toJson(),
    'gaps': gaps.map((e) => e.toJson()).toList(),
    'recommendations': recommendations.map((e) => e.toJson()).toList(),
    'reviewQueue': reviewQueue.map((e) => e.toJson()).toList(),
  };
}

/// A Master-Catalog artifact with an optional active-profile state overlay
/// (from `SecureGuideService.search_catalog`).
class CatalogItem {
  const CatalogItem({
    this.id,
    this.type,
    this.title,
    this.definitionShort,
    this.primaryDomain,
    this.subDomain,
    this.source,
    this.sourceDocument,
    this.obligationLevel,
    this.testability,
    this.aiReviewStatus,
    this.publicationStatus,
    this.effectivePriority,
    this.isSelected,
    this.profileArtifactId,
    this.inclusionStatus,
    this.implementationStatus,
    this.verificationStatus,
    this.effectiveness,
    this.exceptionStatus,
    this.assignedOwner,
    this.dueDate,
    this.evidenceCount,
  });

  final String? id;
  final String? type;
  final String? title;
  final String? definitionShort;
  final String? primaryDomain;
  final String? subDomain;
  final String? source;
  final String? sourceDocument;
  final String? obligationLevel;
  final String? testability;
  final String? aiReviewStatus;
  final String? publicationStatus;
  final String? effectivePriority;
  final bool? isSelected;
  final String? profileArtifactId;
  final String? inclusionStatus;
  final String? implementationStatus;
  final String? verificationStatus;
  final String? effectiveness;
  final String? exceptionStatus;
  final String? assignedOwner;
  final String? dueDate;
  final num? evidenceCount;

  factory CatalogItem.fromJson(Map<String, dynamic> json) => CatalogItem(
    id: json['id'] as String?,
    type: json['type'] as String?,
    title: json['title'] as String?,
    definitionShort: json['definitionShort'] as String?,
    primaryDomain: json['primaryDomain'] as String?,
    subDomain: json['subDomain'] as String?,
    source: json['source'] as String?,
    sourceDocument: json['sourceDocument'] as String?,
    obligationLevel: json['obligationLevel'] as String?,
    testability: json['testability'] as String?,
    aiReviewStatus: json['aiReviewStatus'] as String?,
    publicationStatus: json['publicationStatus'] as String?,
    effectivePriority: json['effectivePriority'] as String?,
    isSelected: json['isSelected'] as bool?,
    profileArtifactId: json['profileArtifactId'] as String?,
    inclusionStatus: json['inclusionStatus'] as String?,
    implementationStatus: json['implementationStatus'] as String?,
    verificationStatus: json['verificationStatus'] as String?,
    effectiveness: json['effectiveness'] as String?,
    exceptionStatus: json['exceptionStatus'] as String?,
    assignedOwner: json['assignedOwner'] as String?,
    dueDate: json['dueDate'] as String?,
    evidenceCount: json['evidenceCount'] as num?,
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'type': type,
    'title': title,
    'definitionShort': definitionShort,
    'primaryDomain': primaryDomain,
    'subDomain': subDomain,
    'source': source,
    'sourceDocument': sourceDocument,
    'obligationLevel': obligationLevel,
    'testability': testability,
    'aiReviewStatus': aiReviewStatus,
    'publicationStatus': publicationStatus,
    'effectivePriority': effectivePriority,
    'isSelected': isSelected,
    'profileArtifactId': profileArtifactId,
    'inclusionStatus': inclusionStatus,
    'implementationStatus': implementationStatus,
    'verificationStatus': verificationStatus,
    'effectiveness': effectiveness,
    'exceptionStatus': exceptionStatus,
    'assignedOwner': assignedOwner,
    'dueDate': dueDate,
    'evidenceCount': evidenceCount,
  };
}

/// An operational task from `v_profile_task_queue`.
class TaskItem {
  const TaskItem({
    this.id,
    this.title,
    this.description,
    this.status,
    this.priority,
    this.assignedTo,
    this.dueDate,
    this.artifactId,
    this.artifactTitleEn,
    this.primaryDomain,
    this.subDomain,
    this.blueprintId,
    this.blueprintVersion,
    this.actionPlanType,
    this.sourceSemanticKey,
    this.lastChangedBy,
    this.lastChangeNote,
    this.completedAt,
    this.updatedAt,
  });

  final String? id;
  final String? title;
  final String? description;
  final String? status;
  final String? priority;
  final String? assignedTo;
  final String? dueDate;
  final String? artifactId;
  final String? artifactTitleEn;
  final String? primaryDomain;
  final String? subDomain;
  final String? blueprintId;
  final num? blueprintVersion;
  final String? actionPlanType;
  final String? sourceSemanticKey;
  final String? lastChangedBy;
  final String? lastChangeNote;
  final String? completedAt;
  final String? updatedAt;

  factory TaskItem.fromJson(Map<String, dynamic> json) => TaskItem(
    id: json['id'] as String?,
    title: json['title'] as String?,
    description: json['description'] as String?,
    status: json['status'] as String?,
    priority: json['priority'] as String?,
    assignedTo: json['assignedTo'] as String?,
    dueDate: json['dueDate'] as String?,
    artifactId: json['artifactId'] as String?,
    artifactTitleEn: json['artifactTitleEn'] as String?,
    primaryDomain: json['primaryDomain'] as String?,
    subDomain: json['subDomain'] as String?,
    blueprintId: json['blueprintId'] as String?,
    blueprintVersion: json['blueprintVersion'] as num?,
    actionPlanType: json['actionPlanType'] as String?,
    sourceSemanticKey: json['sourceSemanticKey'] as String?,
    lastChangedBy: json['lastChangedBy'] as String?,
    lastChangeNote: json['lastChangeNote'] as String?,
    completedAt: json['completedAt'] as String?,
    updatedAt: json['updatedAt'] as String?,
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'description': description,
    'status': status,
    'priority': priority,
    'assignedTo': assignedTo,
    'dueDate': dueDate,
    'artifactId': artifactId,
    'artifactTitleEn': artifactTitleEn,
    'primaryDomain': primaryDomain,
    'subDomain': subDomain,
    'blueprintId': blueprintId,
    'blueprintVersion': blueprintVersion,
    'actionPlanType': actionPlanType,
    'sourceSemanticKey': sourceSemanticKey,
    'lastChangedBy': lastChangedBy,
    'lastChangeNote': lastChangeNote,
    'completedAt': completedAt,
    'updatedAt': updatedAt,
  };
}

/// Envelope for the `catalog()` surface — one page of catalog results.
class CatalogView {
  const CatalogView({
    this.contractVersion = kContractVersion,
    this.locale,
    this.query,
    this.limit,
    this.offset,
    this.count,
    this.items = const [],
  });

  final String contractVersion;
  final String? locale;
  final String? query;
  final num? limit;
  final num? offset;
  final num? count;
  final List<CatalogItem> items;

  factory CatalogView.fromJson(Map<String, dynamic> json) => CatalogView(
    contractVersion: json['contractVersion'] as String,
    locale: json['locale'] as String?,
    query: json['query'] as String?,
    limit: json['limit'] as num?,
    offset: json['offset'] as num?,
    count: json['count'] as num?,
    items: _mapList(json['items'], CatalogItem.fromJson),
  );

  Map<String, dynamic> toJson() => {
    'contractVersion': contractVersion,
    'locale': locale,
    'query': query,
    'limit': limit,
    'offset': offset,
    'count': count,
    'items': items.map((e) => e.toJson()).toList(),
  };
}

/// Envelope for the `tasks()` surface.
class TasksView {
  const TasksView({
    this.contractVersion = kContractVersion,
    this.tasks = const [],
  });

  final String contractVersion;
  final List<TaskItem> tasks;

  factory TasksView.fromJson(Map<String, dynamic> json) => TasksView(
    contractVersion: json['contractVersion'] as String,
    tasks: _mapList(json['tasks'], TaskItem.fromJson),
  );

  Map<String, dynamic> toJson() => {
    'contractVersion': contractVersion,
    'tasks': tasks.map((e) => e.toJson()).toList(),
  };
}

/// A governed blueprint row from `v_profile_blueprints`, for list views.
class BlueprintSummary {
  const BlueprintSummary({
    this.id,
    this.artifactId,
    this.artifactTitleEn,
    this.artifactTitleAr,
    this.title,
    this.version,
    this.workflowStatus,
    this.actionPlanType,
    this.generationConfidence,
    this.generationRequiresReview,
    this.actionCount,
    this.evidenceCount,
    this.taskCount,
    this.createdBy,
    this.approvedBy,
    this.approvedAt,
    this.updatedAt,
  });

  final String? id;
  final String? artifactId;
  final String? artifactTitleEn;
  final String? artifactTitleAr;
  final String? title;
  final num? version;
  final String? workflowStatus;
  final String? actionPlanType;
  final num? generationConfidence;
  final bool? generationRequiresReview;
  final num? actionCount;
  final num? evidenceCount;
  final num? taskCount;
  final String? createdBy;
  final String? approvedBy;
  final String? approvedAt;
  final String? updatedAt;

  factory BlueprintSummary.fromJson(Map<String, dynamic> json) =>
      BlueprintSummary(
        id: json['id'] as String?,
        artifactId: json['artifactId'] as String?,
        artifactTitleEn: json['artifactTitleEn'] as String?,
        artifactTitleAr: json['artifactTitleAr'] as String?,
        title: json['title'] as String?,
        version: json['version'] as num?,
        workflowStatus: json['workflowStatus'] as String?,
        actionPlanType: json['actionPlanType'] as String?,
        generationConfidence: json['generationConfidence'] as num?,
        generationRequiresReview: json['generationRequiresReview'] as bool?,
        actionCount: json['actionCount'] as num?,
        evidenceCount: json['evidenceCount'] as num?,
        taskCount: json['taskCount'] as num?,
        createdBy: json['createdBy'] as String?,
        approvedBy: json['approvedBy'] as String?,
        approvedAt: json['approvedAt'] as String?,
        updatedAt: json['updatedAt'] as String?,
      );

  Map<String, dynamic> toJson() => {
    'id': id,
    'artifactId': artifactId,
    'artifactTitleEn': artifactTitleEn,
    'artifactTitleAr': artifactTitleAr,
    'title': title,
    'version': version,
    'workflowStatus': workflowStatus,
    'actionPlanType': actionPlanType,
    'generationConfidence': generationConfidence,
    'generationRequiresReview': generationRequiresReview,
    'actionCount': actionCount,
    'evidenceCount': evidenceCount,
    'taskCount': taskCount,
    'createdBy': createdBy,
    'approvedBy': approvedBy,
    'approvedAt': approvedAt,
    'updatedAt': updatedAt,
  };
}

/// Envelope for the `blueprints()` surface.
class BlueprintsView {
  const BlueprintsView({
    this.contractVersion = kContractVersion,
    this.blueprints = const [],
  });

  final String contractVersion;
  final List<BlueprintSummary> blueprints;

  factory BlueprintsView.fromJson(Map<String, dynamic> json) => BlueprintsView(
    contractVersion: json['contractVersion'] as String,
    blueprints: _mapList(json['blueprints'], BlueprintSummary.fromJson),
  );

  Map<String, dynamic> toJson() => {
    'contractVersion': contractVersion,
    'blueprints': blueprints.map((e) => e.toJson()).toList(),
  };
}

/// A rule (id + version) that emitted a blueprint action/output/evidence item.
class SourceRule {
  const SourceRule({this.ruleId, this.ruleVersion});

  final String? ruleId;
  final String? ruleVersion;

  factory SourceRule.fromJson(Map<String, dynamic> json) => SourceRule(
    ruleId: json['ruleId'] as String?,
    ruleVersion: json['ruleVersion'] as String?,
  );

  Map<String, dynamic> toJson() => {
    'ruleId': ruleId,
    'ruleVersion': ruleVersion,
  };
}

/// A classification rule that fired during generation.
class AppliedRule {
  const AppliedRule({
    this.ruleId,
    this.ruleVersion,
    this.stage,
    this.priority,
    this.rationale,
    this.baseConfidence,
  });

  final String? ruleId;
  final String? ruleVersion;
  final String? stage;
  final num? priority;
  final String? rationale;
  final num? baseConfidence;

  factory AppliedRule.fromJson(Map<String, dynamic> json) => AppliedRule(
    ruleId: json['ruleId'] as String?,
    ruleVersion: json['ruleVersion'] as String?,
    stage: json['stage'] as String?,
    priority: json['priority'] as num?,
    rationale: json['rationale'] as String?,
    baseConfidence: json['baseConfidence'] as num?,
  );

  Map<String, dynamic> toJson() => {
    'ruleId': ruleId,
    'ruleVersion': ruleVersion,
    'stage': stage,
    'priority': priority,
    'rationale': rationale,
    'baseConfidence': baseConfidence,
  };
}

/// A generated implementation action; `taskable` ones become tasks once approved.
class BlueprintAction {
  const BlueprintAction({
    this.id,
    this.actionCode,
    this.semanticKey,
    this.title,
    this.description,
    this.category,
    this.phase,
    this.displayOrder,
    this.rationale,
    this.confidence,
    this.taskable,
    this.requiresHumanReview,
    this.sourceCitation,
    this.sourceRules = const [],
  });

  final String? id;
  final String? actionCode;
  final String? semanticKey;
  final String? title;
  final String? description;
  final String? category;
  final String? phase;
  final num? displayOrder;
  final String? rationale;
  final num? confidence;
  final bool? taskable;
  final bool? requiresHumanReview;
  final String? sourceCitation;
  final List<SourceRule> sourceRules;

  factory BlueprintAction.fromJson(Map<String, dynamic> json) =>
      BlueprintAction(
        id: json['id'] as String?,
        actionCode: json['actionCode'] as String?,
        semanticKey: json['semanticKey'] as String?,
        title: json['title'] as String?,
        description: json['description'] as String?,
        category: json['category'] as String?,
        phase: json['phase'] as String?,
        displayOrder: json['displayOrder'] as num?,
        rationale: json['rationale'] as String?,
        confidence: json['confidence'] as num?,
        taskable: json['taskable'] as bool?,
        requiresHumanReview: json['requiresHumanReview'] as bool?,
        sourceCitation: json['sourceCitation'] as String?,
        sourceRules: _mapList(json['sourceRules'], SourceRule.fromJson),
      );

  Map<String, dynamic> toJson() => {
    'id': id,
    'actionCode': actionCode,
    'semanticKey': semanticKey,
    'title': title,
    'description': description,
    'category': category,
    'phase': phase,
    'displayOrder': displayOrder,
    'rationale': rationale,
    'confidence': confidence,
    'taskable': taskable,
    'requiresHumanReview': requiresHumanReview,
    'sourceCitation': sourceCitation,
    'sourceRules': sourceRules.map((e) => e.toJson()).toList(),
  };
}

/// An expected output artifact the plan should produce.
class ExpectedOutput {
  const ExpectedOutput({
    this.id,
    this.outputCode,
    this.semanticKey,
    this.title,
    this.description,
    this.rationale,
    this.sourceRules = const [],
  });

  final String? id;
  final String? outputCode;
  final String? semanticKey;
  final String? title;
  final String? description;
  final String? rationale;
  final List<SourceRule> sourceRules;

  factory ExpectedOutput.fromJson(Map<String, dynamic> json) => ExpectedOutput(
    id: json['id'] as String?,
    outputCode: json['outputCode'] as String?,
    semanticKey: json['semanticKey'] as String?,
    title: json['title'] as String?,
    description: json['description'] as String?,
    rationale: json['rationale'] as String?,
    sourceRules: _mapList(json['sourceRules'], SourceRule.fromJson),
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'outputCode': outputCode,
    'semanticKey': semanticKey,
    'title': title,
    'description': description,
    'rationale': rationale,
    'sourceRules': sourceRules.map((e) => e.toJson()).toList(),
  };
}

/// A required evidence item for the plan.
class EvidenceRequirement {
  const EvidenceRequirement({
    this.id,
    this.evidenceCode,
    this.semanticKey,
    this.title,
    this.evidenceType,
    this.description,
    this.rationale,
    this.mandatory,
    this.confidence,
    this.requiresHumanReview,
    this.sourceCitation,
    this.sourceRules = const [],
  });

  final String? id;
  final String? evidenceCode;
  final String? semanticKey;
  final String? title;
  final String? evidenceType;
  final String? description;
  final String? rationale;
  final bool? mandatory;
  final num? confidence;
  final bool? requiresHumanReview;
  final String? sourceCitation;
  final List<SourceRule> sourceRules;

  factory EvidenceRequirement.fromJson(Map<String, dynamic> json) =>
      EvidenceRequirement(
        id: json['id'] as String?,
        evidenceCode: json['evidenceCode'] as String?,
        semanticKey: json['semanticKey'] as String?,
        title: json['title'] as String?,
        evidenceType: json['evidenceType'] as String?,
        description: json['description'] as String?,
        rationale: json['rationale'] as String?,
        mandatory: json['mandatory'] as bool?,
        confidence: json['confidence'] as num?,
        requiresHumanReview: json['requiresHumanReview'] as bool?,
        sourceCitation: json['sourceCitation'] as String?,
        sourceRules: _mapList(json['sourceRules'], SourceRule.fromJson),
      );

  Map<String, dynamic> toJson() => {
    'id': id,
    'evidenceCode': evidenceCode,
    'semanticKey': semanticKey,
    'title': title,
    'evidenceType': evidenceType,
    'description': description,
    'rationale': rationale,
    'mandatory': mandatory,
    'confidence': confidence,
    'requiresHumanReview': requiresHumanReview,
    'sourceCitation': sourceCitation,
    'sourceRules': sourceRules.map((e) => e.toJson()).toList(),
  };
}

/// A non-authoritative operational-pattern enrichment frozen onto a draft.
class PatternEnrichment {
  const PatternEnrichment({
    this.id,
    this.sourcePatternId,
    this.recommendedArtifactType,
    this.primaryDomain,
    this.subDomain,
    this.patternPriority,
    this.copiedTitleAr,
    this.copiedTextAr,
    this.safetyReviewRequired,
    this.safetyAcknowledged,
    this.safetyNoteAr,
    this.libraryVersion,
    this.selectedBy,
    this.selectionReason,
    this.selectedAt,
  });

  final String? id;
  final String? sourcePatternId;
  final String? recommendedArtifactType;
  final String? primaryDomain;
  final String? subDomain;
  final String? patternPriority;
  final String? copiedTitleAr;
  final String? copiedTextAr;
  final bool? safetyReviewRequired;
  final bool? safetyAcknowledged;
  final String? safetyNoteAr;
  final String? libraryVersion;
  final String? selectedBy;
  final String? selectionReason;
  final String? selectedAt;

  factory PatternEnrichment.fromJson(Map<String, dynamic> json) =>
      PatternEnrichment(
        id: json['id'] as String?,
        sourcePatternId: json['sourcePatternId'] as String?,
        recommendedArtifactType: json['recommendedArtifactType'] as String?,
        primaryDomain: json['primaryDomain'] as String?,
        subDomain: json['subDomain'] as String?,
        patternPriority: json['patternPriority'] as String?,
        copiedTitleAr: json['copiedTitleAr'] as String?,
        copiedTextAr: json['copiedTextAr'] as String?,
        safetyReviewRequired: json['safetyReviewRequired'] as bool?,
        safetyAcknowledged: json['safetyAcknowledged'] as bool?,
        safetyNoteAr: json['safetyNoteAr'] as String?,
        libraryVersion: json['libraryVersion'] as String?,
        selectedBy: json['selectedBy'] as String?,
        selectionReason: json['selectionReason'] as String?,
        selectedAt: json['selectedAt'] as String?,
      );

  Map<String, dynamic> toJson() => {
    'id': id,
    'sourcePatternId': sourcePatternId,
    'recommendedArtifactType': recommendedArtifactType,
    'primaryDomain': primaryDomain,
    'subDomain': subDomain,
    'patternPriority': patternPriority,
    'copiedTitleAr': copiedTitleAr,
    'copiedTextAr': copiedTextAr,
    'safetyReviewRequired': safetyReviewRequired,
    'safetyAcknowledged': safetyAcknowledged,
    'safetyNoteAr': safetyNoteAr,
    'libraryVersion': libraryVersion,
    'selectedBy': selectedBy,
    'selectionReason': selectionReason,
    'selectedAt': selectedAt,
  };
}

/// A generation review reason / normalization / conflict finding.
class ReviewFinding {
  const ReviewFinding({
    this.findingType,
    this.findingCode,
    this.fieldName,
    this.inputValue,
    this.canonicalValue,
    this.detail,
    this.quality,
  });

  final String? findingType;
  final String? findingCode;
  final String? fieldName;
  final String? inputValue;
  final String? canonicalValue;
  final String? detail;
  final String? quality;

  factory ReviewFinding.fromJson(Map<String, dynamic> json) => ReviewFinding(
    findingType: json['findingType'] as String?,
    findingCode: json['findingCode'] as String?,
    fieldName: json['fieldName'] as String?,
    inputValue: json['inputValue'] as String?,
    canonicalValue: json['canonicalValue'] as String?,
    detail: json['detail'] as String?,
    quality: json['quality'] as String?,
  );

  Map<String, dynamic> toJson() => {
    'findingType': findingType,
    'findingCode': findingCode,
    'fieldName': fieldName,
    'inputValue': inputValue,
    'canonicalValue': canonicalValue,
    'detail': detail,
    'quality': quality,
  };
}

/// The full governed-blueprint snapshot with its nested collections. Unlike the
/// list summary, this carries no artifact titles or rollup counts — counts are
/// the nested array lengths.
class BlueprintDetail {
  const BlueprintDetail({
    this.id,
    this.artifactId,
    this.title,
    this.version,
    this.workflowStatus,
    this.actionPlanType,
    this.generationConfidence,
    this.generationRequiresReview,
    this.profileId,
    this.profileArtifactId,
    this.parentBlueprintId,
    this.ruleSetId,
    this.ruleSetVersion,
    this.ruleSetHash,
    this.engineVersion,
    this.changeSummary,
    this.reviewResolutionNote,
    this.createdBy,
    this.submittedBy,
    this.submittedAt,
    this.approvedBy,
    this.approvedAt,
    this.updatedAt,
    this.appliedRules = const [],
    this.actions = const [],
    this.expectedOutputs = const [],
    this.evidence = const [],
    this.patternEnrichments = const [],
    this.reviewFindings = const [],
  });

  final String? id;
  final String? artifactId;
  final String? title;
  final num? version;
  final String? workflowStatus;
  final String? actionPlanType;
  final num? generationConfidence;
  final bool? generationRequiresReview;
  final String? profileId;
  final String? profileArtifactId;
  final String? parentBlueprintId;
  final String? ruleSetId;
  final String? ruleSetVersion;
  final String? ruleSetHash;
  final String? engineVersion;
  final String? changeSummary;
  final String? reviewResolutionNote;
  final String? createdBy;
  final String? submittedBy;
  final String? submittedAt;
  final String? approvedBy;
  final String? approvedAt;
  final String? updatedAt;
  final List<AppliedRule> appliedRules;
  final List<BlueprintAction> actions;
  final List<ExpectedOutput> expectedOutputs;
  final List<EvidenceRequirement> evidence;
  final List<PatternEnrichment> patternEnrichments;
  final List<ReviewFinding> reviewFindings;

  factory BlueprintDetail.fromJson(
    Map<String, dynamic> json,
  ) => BlueprintDetail(
    id: json['id'] as String?,
    artifactId: json['artifactId'] as String?,
    title: json['title'] as String?,
    version: json['version'] as num?,
    workflowStatus: json['workflowStatus'] as String?,
    actionPlanType: json['actionPlanType'] as String?,
    generationConfidence: json['generationConfidence'] as num?,
    generationRequiresReview: json['generationRequiresReview'] as bool?,
    profileId: json['profileId'] as String?,
    profileArtifactId: json['profileArtifactId'] as String?,
    parentBlueprintId: json['parentBlueprintId'] as String?,
    ruleSetId: json['ruleSetId'] as String?,
    ruleSetVersion: json['ruleSetVersion'] as String?,
    ruleSetHash: json['ruleSetHash'] as String?,
    engineVersion: json['engineVersion'] as String?,
    changeSummary: json['changeSummary'] as String?,
    reviewResolutionNote: json['reviewResolutionNote'] as String?,
    createdBy: json['createdBy'] as String?,
    submittedBy: json['submittedBy'] as String?,
    submittedAt: json['submittedAt'] as String?,
    approvedBy: json['approvedBy'] as String?,
    approvedAt: json['approvedAt'] as String?,
    updatedAt: json['updatedAt'] as String?,
    appliedRules: _mapList(json['appliedRules'], AppliedRule.fromJson),
    actions: _mapList(json['actions'], BlueprintAction.fromJson),
    expectedOutputs: _mapList(json['expectedOutputs'], ExpectedOutput.fromJson),
    evidence: _mapList(json['evidence'], EvidenceRequirement.fromJson),
    patternEnrichments: _mapList(
      json['patternEnrichments'],
      PatternEnrichment.fromJson,
    ),
    reviewFindings: _mapList(json['reviewFindings'], ReviewFinding.fromJson),
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'artifactId': artifactId,
    'title': title,
    'version': version,
    'workflowStatus': workflowStatus,
    'actionPlanType': actionPlanType,
    'generationConfidence': generationConfidence,
    'generationRequiresReview': generationRequiresReview,
    'profileId': profileId,
    'profileArtifactId': profileArtifactId,
    'parentBlueprintId': parentBlueprintId,
    'ruleSetId': ruleSetId,
    'ruleSetVersion': ruleSetVersion,
    'ruleSetHash': ruleSetHash,
    'engineVersion': engineVersion,
    'changeSummary': changeSummary,
    'reviewResolutionNote': reviewResolutionNote,
    'createdBy': createdBy,
    'submittedBy': submittedBy,
    'submittedAt': submittedAt,
    'approvedBy': approvedBy,
    'approvedAt': approvedAt,
    'updatedAt': updatedAt,
    'appliedRules': appliedRules.map((e) => e.toJson()).toList(),
    'actions': actions.map((e) => e.toJson()).toList(),
    'expectedOutputs': expectedOutputs.map((e) => e.toJson()).toList(),
    'evidence': evidence.map((e) => e.toJson()).toList(),
    'patternEnrichments': patternEnrichments.map((e) => e.toJson()).toList(),
    'reviewFindings': reviewFindings.map((e) => e.toJson()).toList(),
  };
}

/// Envelope for the `blueprint(...)` detail surface.
class BlueprintDetailView {
  const BlueprintDetailView({
    this.contractVersion = kContractVersion,
    required this.blueprint,
  });

  final String contractVersion;
  final BlueprintDetail blueprint;

  factory BlueprintDetailView.fromJson(Map<String, dynamic> json) =>
      BlueprintDetailView(
        contractVersion: json['contractVersion'] as String,
        blueprint: BlueprintDetail.fromJson(
          json['blueprint'] as Map<String, dynamic>,
        ),
      );

  Map<String, dynamic> toJson() => {
    'contractVersion': contractVersion,
    'blueprint': blueprint.toJson(),
  };
}

/// Result of a `selectArtifacts` write — a summary the UI uses to refresh.
class SelectionResult {
  const SelectionResult({
    this.profileId,
    this.requested,
    this.created,
    this.existing,
    this.originsAdded,
    this.profileArtifactIds = const [],
  });

  final String? profileId;
  final num? requested;
  final num? created;
  final num? existing;
  final num? originsAdded;
  final List<String> profileArtifactIds;

  factory SelectionResult.fromJson(Map<String, dynamic> json) =>
      SelectionResult(
        profileId: json['profileId'] as String?,
        requested: json['requested'] as num?,
        created: json['created'] as num?,
        existing: json['existing'] as num?,
        originsAdded: json['originsAdded'] as num?,
        profileArtifactIds:
            (json['profileArtifactIds'] as List<dynamic>? ?? const [])
                .map((e) => e as String)
                .toList(),
      );

  Map<String, dynamic> toJson() => {
    'profileId': profileId,
    'requested': requested,
    'created': created,
    'existing': existing,
    'originsAdded': originsAdded,
    'profileArtifactIds': profileArtifactIds,
  };
}

/// Immutable assessment snapshot recorded for one profile artifact.
class AssessmentRecord {
  const AssessmentRecord({
    this.id,
    this.profileArtifactId,
    this.assessmentDate,
    this.assessorName,
    this.score,
    this.implementationStatus,
    this.verificationStatus,
    this.effectiveness,
    this.exceptionStatus,
    this.comments,
  });

  final String? id;
  final String? profileArtifactId;
  final String? assessmentDate;
  final String? assessorName;
  final num? score;
  final String? implementationStatus;
  final String? verificationStatus;
  final String? effectiveness;
  final String? exceptionStatus;
  final String? comments;

  factory AssessmentRecord.fromJson(Map<String, dynamic> json) =>
      AssessmentRecord(
        id: json['id'] as String?,
        profileArtifactId: json['profileArtifactId'] as String?,
        assessmentDate: json['assessmentDate'] as String?,
        assessorName: json['assessorName'] as String?,
        score: json['score'] as num?,
        implementationStatus: json['implementationStatus'] as String?,
        verificationStatus: json['verificationStatus'] as String?,
        effectiveness: json['effectiveness'] as String?,
        exceptionStatus: json['exceptionStatus'] as String?,
        comments: json['comments'] as String?,
      );

  Map<String, dynamic> toJson() => {
    'id': id,
    'profileArtifactId': profileArtifactId,
    'assessmentDate': assessmentDate,
    'assessorName': assessorName,
    'score': score,
    'implementationStatus': implementationStatus,
    'verificationStatus': verificationStatus,
    'effectiveness': effectiveness,
    'exceptionStatus': exceptionStatus,
    'comments': comments,
  };
}

/// Read envelope for one selected artifact and its immutable assessment log.
class ProfileArtifactView {
  const ProfileArtifactView({
    this.contractVersion = kContractVersion,
    this.profileId,
    required this.artifact,
    this.assessments = const [],
  });

  final String contractVersion;
  final String? profileId;
  final OperationalItem artifact;
  final List<AssessmentRecord> assessments;

  factory ProfileArtifactView.fromJson(Map<String, dynamic> json) =>
      ProfileArtifactView(
        contractVersion: json['contractVersion'] as String,
        profileId: json['profileId'] as String?,
        artifact: OperationalItem.fromJson(
          json['artifact'] as Map<String, dynamic>,
        ),
        assessments: _mapList(json['assessments'], AssessmentRecord.fromJson),
      );

  Map<String, dynamic> toJson() => {
    'contractVersion': contractVersion,
    'profileId': profileId,
    'artifact': artifact.toJson(),
    'assessments': assessments.map((e) => e.toJson()).toList(),
  };
}

/// Write response for an assessment plus the refreshed current state.
class AssessmentResult {
  const AssessmentResult({
    this.contractVersion = kContractVersion,
    required this.assessment,
    required this.artifact,
  });

  final String contractVersion;
  final AssessmentRecord assessment;
  final OperationalItem artifact;

  factory AssessmentResult.fromJson(Map<String, dynamic> json) =>
      AssessmentResult(
        contractVersion: json['contractVersion'] as String,
        assessment: AssessmentRecord.fromJson(
          json['assessment'] as Map<String, dynamic>,
        ),
        artifact: OperationalItem.fromJson(
          json['artifact'] as Map<String, dynamic>,
        ),
      );

  Map<String, dynamic> toJson() => {
    'contractVersion': contractVersion,
    'assessment': assessment.toJson(),
    'artifact': artifact.toJson(),
  };
}
