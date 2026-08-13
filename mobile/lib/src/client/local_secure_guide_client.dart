import 'package:sqflite/sqflite.dart';
import 'package:uuid/uuid.dart';

import '../../core/database/database_helper.dart';
import '../../read_model_contract.dart';
import '../core/scoring/scoring_engine.dart';
import '../repositories/local_blueprint_repository.dart';
import '../repositories/local_catalog_repository.dart';
import '../repositories/local_task_repository.dart';
import 'secure_guide_client.dart';
import 'task_manager.dart';

const _implementationStatuses = <String>{
  'STS-NOT-APPLIED',
  'STS-PLANNED',
  'STS-PARTIAL',
  'STS-FULL',
  'STS-NEEDS-IMPROVEMENT',
};
const _verificationStatuses = <String>{
  'VER-NOT-VERIFIED',
  'VER-PASS',
  'VER-FAIL',
};
const _effectivenessValues = <String>{
  'EFF-UNKNOWN',
  'EFF-LOW',
  'EFF-MEDIUM',
  'EFF-HIGH',
};
const _maturityLevels = <String>{
  'INITIAL',
  'REPEATABLE',
  'DEFINED',
  'MANAGED',
  'OPTIMIZED',
};
const _priorities = <String>{
  'PRI-LOW',
  'PRI-MEDIUM',
  'PRI-HIGH',
  'PRI-CRITICAL',
};
const _reviewFrequencies = <String>{
  'CONTINUOUS',
  'DAILY',
  'WEEKLY',
  'MONTHLY',
  'QUARTERLY',
  'SEMI-ANNUAL',
  'ANNUAL',
  'BIENNIAL',
  'AD-HOC',
};
const _inclusionStatuses = <String>{
  'MANDATORY',
  'RECOMMENDED',
  'OPTIONAL',
  'CONDITIONAL',
};
const _inclusionRank = <String, int>{
  'OPTIONAL': 1,
  'CONDITIONAL': 2,
  'RECOMMENDED': 3,
  'MANDATORY': 4,
};
const _priorityRank = <String, int>{
  'PRI-LOW': 1,
  'PRI-MEDIUM': 2,
  'PRI-HIGH': 3,
  'PRI-CRITICAL': 4,
};
const _reviewRank = <String, int>{
  'CONTINUOUS': 1,
  'DAILY': 2,
  'WEEKLY': 3,
  'MONTHLY': 4,
  'QUARTERLY': 5,
  'SEMI-ANNUAL': 6,
  'ANNUAL': 7,
  'BIENNIAL': 8,
  'AD-HOC': 9,
};

String? _cleanOptional(String? value) {
  if (value == null) return null;
  final cleaned = value.trim();
  return cleaned.isEmpty ? null : cleaned;
}

String? _stronger(String? current, String? candidate, Map<String, int> ranks) {
  if (candidate == null) return current;
  if (current == null) return candidate;
  return ranks[candidate]! > ranks[current]! ? candidate : current;
}

String? _moreFrequent(String? current, String? candidate) {
  if (candidate == null) return current;
  if (current == null) return candidate;
  return _reviewRank[candidate]! < _reviewRank[current]! ? candidate : current;
}

ProfileSummary _profileSummary(
  Map<String, Object?> row, {
  required bool isActive,
}) => ProfileSummary(
  id: row['id'] as String?,
  name: row['name'] as String?,
  description: row['description'] as String?,
  profileKind: row['profile_kind'] as String?,
  organizationSize: row['organization_size'] as String?,
  industry: row['industry'] as String?,
  country: row['country'] as String?,
  targetMaturityLevel: row['target_maturity_level'] as String?,
  isActive: isActive,
);

class LocalSecureGuideClient implements SecureGuideClient {
  Future<Database> get _db => DatabaseHelper.instance.database;

  @override
  Future<ProfilesView> profiles() async {
    final db = await _db;

    String? activeId;
    final activeProfileRes = await db.rawQuery(
      'SELECT profile_id FROM v_active_profile_context LIMIT 1',
    );
    if (activeProfileRes.isNotEmpty) {
      activeId = activeProfileRes.first['profile_id'] as String?;
    }

    final rows = await db.query(
      'enterprise_profiles',
      where: 'archived_at IS NULL',
      orderBy: 'created_at ASC',
    );
    final profiles = rows
        .map((row) => _profileSummary(row, isActive: row['id'] == activeId))
        .toList();

    return ProfilesView(profiles: profiles);
  }

  @override
  Future<DashboardView> dashboard({String? profileId}) async {
    final db = await _db;
    final views = await profiles();
    final matchingProfiles = profileId == null
        ? views.profiles.where((profile) => profile.isActive == true)
        : views.profiles.where((profile) => profile.id == profileId);
    if (matchingProfiles.isEmpty) {
      if (profileId != null) {
        throw StateError('PROFILE_NOT_FOUND: $profileId');
      }
      throw StateError('ACTIVE_PROFILE_REQUIRED');
    }
    final profile = matchingProfiles.first;
    final resolvedProfileId = profile.id!;

    final dashboardRows = await db.query(
      'v_profile_dashboard',
      where: 'profile_id = ?',
      whereArgs: [resolvedProfileId],
    );
    final dashboardRow = dashboardRows.isEmpty
        ? const <String, Object?>{}
        : dashboardRows.first;
    final counts = DashboardCounts(
      totalItems: dashboardRow['total_items'] as num? ?? 0,
      applicableItems: dashboardRow['applicable_items'] as num? ?? 0,
      implementedFull: dashboardRow['implemented_full'] as num? ?? 0,
      implementedPartial: dashboardRow['implemented_partial'] as num? ?? 0,
      notApplied: dashboardRow['not_applied'] as num? ?? 0,
      verifiedPass: dashboardRow['verified_pass'] as num? ?? 0,
      verifiedFail: dashboardRow['verified_fail'] as num? ?? 0,
      withException: dashboardRow['with_exception'] as num? ?? 0,
      openGaps: dashboardRow['open_gaps'] as num? ?? 0,
      overdueItems: dashboardRow['overdue_items'] as num? ?? 0,
    );

    final dependencyRows = await db.rawQuery('''
      SELECT source_id, target_id
      FROM artifact_relationships
      WHERE relation_type IN ('REL-DEP', 'DEP')
      ''');
    final dependencies = <String, List<String>>{};
    for (final row in dependencyRows) {
      dependencies
          .putIfAbsent(row['source_id'] as String, () => <String>[])
          .add(row['target_id'] as String);
    }

    final platformRows = await db.query('artifact_platforms');
    final platforms = <String, List<String>>{};
    for (final row in platformRows) {
      platforms
          .putIfAbsent(row['artifact_id'] as String, () => <String>[])
          .add(row['platform_code'] as String);
    }

    final controlRows = await db.rawQuery(
      '''
      SELECT a.id,
             a.primary_domain AS domain,
             a.tier,
             a.scoring_weight,
             a.risk_reduction,
             a.effort_level,
             COALESCE(pa.priority_override, pa.template_priority_default,
                      a.priority) AS effective_priority,
             pa.implementation_status,
             pa.verification_status,
             pa.effectiveness,
             pa.exception_status
      FROM profile_artifacts pa
      JOIN security_artifacts a ON a.id = pa.artifact_id
      WHERE pa.profile_id = ? AND a.is_active = 1
      ORDER BY a.id
      ''',
      [resolvedProfileId],
    );
    final controls = controlRows.map((row) {
      final artifactId = row['id'] as String;
      final exceptionType = switch (row['exception_status']) {
        'EXC-NOT-APPLICABLE' => 'not_applicable',
        'EXC-UNAVAILABLE' => 'not_available',
        'EXC-DEFERRED' => 'deferred',
        'EXC-RISK-ACCEPTED' => 'accepted_risk',
        _ => null,
      };
      final userStatus = switch (row['implementation_status']) {
        'STS-FULL' => ScoringEngine.implemented,
        'STS-PARTIAL' || 'STS-NEEDS-IMPROVEMENT' => ScoringEngine.partial,
        _ => ScoringEngine.notAssessed,
      };
      final effectivePriority = row['effective_priority'] as String?;
      return <String, dynamic>{
        'id': artifactId,
        'domain': row['domain'],
        'tier': row['tier'] ?? 'essential',
        'priority':
            effectivePriority?.replaceFirst('PRI-', '').toLowerCase() ??
            'medium',
        'effort': row['effort_level'] ?? 'medium',
        'scoring_weight': row['scoring_weight'] ?? 0,
        'risk_reduction': row['risk_reduction'] ?? 3,
        'dependencies': dependencies[artifactId] ?? const <String>[],
        'platform_ids': platforms[artifactId] ?? const <String>[],
        'user_status': userStatus,
        'verification_status': row['verification_status'],
        'effectiveness': row['effectiveness'],
        'exception_type': exceptionType,
        'excluded':
            exceptionType == 'not_applicable' ||
            exceptionType == 'not_available',
        'disabled': false,
      };
    }).toList();

    final settings = <String, dynamic>{'view_tier': 'full', 'platforms': []};
    final policy = await _loadScoringPolicy(db);
    final scoreResult = ScoringEngine.score(controls, settings, policy);
    final score = ScoreView(
      overall: scoreResult['overall'] as num?,
      band: scoreResult['band'] as String?,
      capped: scoreResult['capped'] as bool?,
      formulaVersion: scoreResult['formula_version'] as String?,
      assessmentCoverage: scoreResult['assessment_coverage'] as num?,
      riskReductionPct: scoreResult['risk_reduction_pct'] as num?,
      implementationScoreRaw: scoreResult['implementation_score_raw'] as num?,
      verificationCoverage: scoreResult['verification_coverage'] as num?,
      verificationAssessmentCoverage:
          scoreResult['verification_assessment_coverage'] as num?,
      effectivenessKnown: scoreResult['effectiveness_known'] as num?,
      assessedControls: scoreResult['assessed_controls'] as num?,
      totalControls: scoreResult['total_controls'] as num?,
      remainingCriticalRisk: scoreResult['remaining_critical_risk'] as num?,
      criticalTotal: scoreResult['critical_total'] as num?,
      criticalCompliant: scoreResult['critical_compliant'] as num?,
      criticalAccepted: scoreResult['critical_accepted'] as num?,
      verifiedPass: scoreResult['verified_pass'] as num?,
      verifiedFail: scoreResult['verified_fail'] as num?,
      effectivenessKnownCount: scoreResult['effectiveness_known_count'] as num?,
      domainScores:
          (scoreResult['domain_scores'] as Map<String, dynamic>? ?? const {})
              .map((key, value) => MapEntry(key, value as num)),
    );

    final gapRows = await db.rawQuery(
      '''
      SELECT * FROM v_gap_analysis
      WHERE profile_id = ?
      ORDER BY CASE priority
        WHEN 'PRI-CRITICAL' THEN 1
        WHEN 'PRI-HIGH' THEN 2
        WHEN 'PRI-MEDIUM' THEN 3
        ELSE 4 END,
        due_date IS NULL, due_date, artifact_id
      LIMIT 20
      ''',
      [resolvedProfileId],
    );
    final gaps = gapRows
        .map(
          (row) => GapItem(
            artifactId: row['artifact_id'] as String?,
            titleEn: row['title_en'] as String?,
            titleAr: row['title_ar'] as String?,
            primaryDomain: row['primary_domain'] as String?,
            subDomain: row['sub_domain'] as String?,
            priority: row['priority'] as String?,
            implementationStatus: row['implementation_status'] as String?,
            verificationStatus: row['verification_status'] as String?,
            effectiveness: row['effectiveness'] as String?,
            exceptionStatus: row['exception_status'] as String?,
            assignedOwner: row['assigned_owner'] as String?,
            dueDate: row['due_date'] as String?,
          ),
        )
        .toList();

    final recommendationRows = ScoringEngine.recommend(
      controls,
      settings,
      policy,
    ).take(20);
    final recommendations = recommendationRows
        .map(
          (row) => RecommendationItem(
            artifactId: row['artifactId'] as String?,
            priority: row['priority'] as String?,
            dependencyReady: row['dependencyReady'] as bool?,
            reasonCodes:
                (row['reasonCodes'] as List?)?.cast<String>().toList() ?? [],
          ),
        )
        .toList();

    final reviewRows = await db.rawQuery(
      '''
      SELECT * FROM v_profile_operational_items
      WHERE profile_id = ?
        AND (
          verification_status = 'VER-FAIL'
          OR effectiveness = 'EFF-LOW'
          OR (
            due_date IS NOT NULL
            AND due_date < date('now')
            AND implementation_status <> 'STS-FULL'
          )
        )
      ORDER BY due_date IS NULL, due_date, artifact_id
      ''',
      [resolvedProfileId],
    );

    return DashboardView(
      profile: profile,
      counts: counts,
      score: score,
      gaps: gaps,
      recommendations: recommendations,
      reviewQueue: reviewRows.map(_operationalItemFromRow).toList(),
    );
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
    final cleanName = name.trim();
    if (cleanName.isEmpty) {
      throw ArgumentError.value(name, 'name', 'must not be empty');
    }
    if (targetMaturityLevel != null &&
        !_maturityLevels.contains(targetMaturityLevel)) {
      throw ArgumentError.value(
        targetMaturityLevel,
        'targetMaturityLevel',
        'must be a controlled maturity level',
      );
    }
    final db = await _db;
    final id = const Uuid().v4();
    final cleanProfileKind = _cleanOptional(profileKind);
    final cleanOrganizationSize = _cleanOptional(organizationSize);
    final cleanIndustry = _cleanOptional(industry);
    final cleanCountry = _cleanOptional(country);
    final cleanDescription = _cleanOptional(description);
    await db.transaction((txn) async {
      await txn.insert('enterprise_profiles', {
        'id': id,
        'name': cleanName,
        'profile_kind': cleanProfileKind,
        'organization_size': cleanOrganizationSize,
        'industry': cleanIndustry,
        'country': cleanCountry,
        'target_maturity_level': targetMaturityLevel,
        'description': cleanDescription,
      });

      if (activate) {
        final updated = await txn.update('application_state', {
          'active_profile_id': id,
        }, where: 'singleton_id = 1');
        if (updated != 1) {
          throw StateError('APPLICATION_STATE_SINGLETON_MISSING');
        }
      }
    });

    return ProfileSummary(
      id: id,
      name: cleanName,
      profileKind: cleanProfileKind,
      organizationSize: cleanOrganizationSize,
      industry: cleanIndustry,
      country: cleanCountry,
      targetMaturityLevel: targetMaturityLevel,
      description: cleanDescription,
      isActive: activate,
    );
  }

  @override
  Future<ProfileSummary> activateProfile(String profileId) async {
    final db = await _db;
    final profile = await db.transaction((txn) async {
      final rows = await txn.query(
        'enterprise_profiles',
        where: 'id = ? AND archived_at IS NULL',
        whereArgs: [profileId],
        limit: 1,
      );
      if (rows.isEmpty) {
        throw StateError('PROFILE_NOT_FOUND_OR_ARCHIVED');
      }
      final updated = await txn.update('application_state', {
        'active_profile_id': profileId,
      }, where: 'singleton_id = 1');
      if (updated != 1) {
        throw StateError('APPLICATION_STATE_SINGLETON_MISSING');
      }
      return rows.single;
    });
    return _profileSummary(profile, isActive: true);
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
    if (name != null && name.trim().isEmpty) {
      throw ArgumentError.value(name, 'name', 'must not be empty');
    }
    if (clearTargetMaturityLevel && targetMaturityLevel != null) {
      throw ArgumentError(
        'targetMaturityLevel and clearTargetMaturityLevel are mutually exclusive',
      );
    }
    if (targetMaturityLevel != null &&
        !_maturityLevels.contains(targetMaturityLevel)) {
      throw ArgumentError.value(
        targetMaturityLevel,
        'targetMaturityLevel',
        'must be a controlled maturity level',
      );
    }
    final db = await _db;
    final updates = <String, Object?>{};
    if (name != null) updates['name'] = name.trim();
    if (profileKind != null) {
      updates['profile_kind'] = _cleanOptional(profileKind);
    }
    if (organizationSize != null) {
      updates['organization_size'] = _cleanOptional(organizationSize);
    }
    if (industry != null) updates['industry'] = _cleanOptional(industry);
    if (country != null) updates['country'] = _cleanOptional(country);
    if (clearTargetMaturityLevel) {
      updates['target_maturity_level'] = null;
    } else if (targetMaturityLevel != null) {
      updates['target_maturity_level'] = targetMaturityLevel;
    }
    if (description != null) {
      updates['description'] = _cleanOptional(description);
    }

    final profile = await db.transaction((txn) async {
      final existing = await txn.query(
        'enterprise_profiles',
        where: 'id = ? AND archived_at IS NULL',
        whereArgs: [profileId],
        limit: 1,
      );
      if (existing.isEmpty) {
        throw StateError('PROFILE_NOT_FOUND_OR_ARCHIVED');
      }
      if (updates.isNotEmpty) {
        updates['updated_at'] = DateTime.now().toUtc().toIso8601String();
        final updated = await txn.update(
          'enterprise_profiles',
          updates,
          where: 'id = ? AND archived_at IS NULL',
          whereArgs: [profileId],
        );
        if (updated != 1) {
          throw StateError('PROFILE_UPDATE_FAILED');
        }
      }
      final refreshed = await txn.query(
        'enterprise_profiles',
        where: 'id = ? AND archived_at IS NULL',
        whereArgs: [profileId],
        limit: 1,
      );
      return refreshed.single;
    });
    final state = await db.query(
      'application_state',
      columns: ['active_profile_id'],
      where: 'singleton_id = 1',
      limit: 1,
    );
    if (state.isEmpty) {
      throw StateError('APPLICATION_STATE_SINGLETON_MISSING');
    }
    return _profileSummary(
      profile,
      isActive: state.single['active_profile_id'] == profileId,
    );
  }

  @override
  Future<void> archiveProfile(String profileId) async {
    final db = await _db;
    final updated = await db.update(
      'enterprise_profiles',
      {'archived_at': DateTime.now().toUtc().toIso8601String()},
      where: 'id = ?',
      whereArgs: [profileId],
    );
    if (updated != 1) {
      throw StateError('PROFILE_NOT_FOUND');
    }
  }

  @override
  Future<CatalogView> catalog(
    CatalogFilter filter, {
    String locale = 'en',
    bool selectedOnly = false,
    int limit = 100,
    int offset = 0,
  }) async {
    final db = await _db;
    return LocalCatalogRepository(db).search(
      filter,
      locale: locale,
      selectedOnly: selectedOnly,
      limit: limit,
      offset: offset,
    );
  }

  @override
  Future<SelectionResult> selectArtifacts(
    List<String> artifactIds, {
    String? profileId,
    String selectedBy = 'app-user',
    String? inclusionStatus,
    String? selectionReason,
  }) async {
    final db = await _db;
    final uniqueArtifactIds = artifactIds.toSet().toList(growable: false);
    if (uniqueArtifactIds.isEmpty) {
      throw ArgumentError.value(
        artifactIds,
        'artifactIds',
        'must contain at least one artifact',
      );
    }
    if (selectedBy.trim().isEmpty) {
      throw ArgumentError.value(selectedBy, 'selectedBy', 'must not be empty');
    }
    if (inclusionStatus != null &&
        !_inclusionStatuses.contains(inclusionStatus)) {
      throw ArgumentError.value(
        inclusionStatus,
        'inclusionStatus',
        'must be a controlled inclusion status',
      );
    }

    int created = 0;
    int originsAdded = 0;
    final ids = <String>[];
    late String resolvedProfileId;
    await db.transaction((txn) async {
      resolvedProfileId = profileId ?? '';
      if (resolvedProfileId.isEmpty) {
        final active = await txn.rawQuery(
          'SELECT profile_id FROM v_active_profile_context LIMIT 1',
        );
        if (active.isNotEmpty) {
          resolvedProfileId = active.first['profile_id'] as String;
        }
      }
      if (resolvedProfileId.isEmpty) {
        throw StateError('ACTIVE_PROFILE_REQUIRED');
      }
      final profiles = await txn.query(
        'enterprise_profiles',
        columns: ['id'],
        where: 'id = ? AND archived_at IS NULL',
        whereArgs: [resolvedProfileId],
        limit: 1,
      );
      if (profiles.isEmpty) {
        throw StateError('PROFILE_NOT_FOUND_OR_ARCHIVED');
      }

      final placeholders = List.filled(uniqueArtifactIds.length, '?').join(',');
      final selectableRows = await txn.rawQuery(
        '''SELECT id FROM security_artifacts
           WHERE id IN ($placeholders)
             AND is_active = 1
             AND publication_status IN ('APPROVED','PUBLISHED')''',
        uniqueArtifactIds,
      );
      final selectableIds = selectableRows
          .map((row) => row['id'] as String)
          .toSet();
      final missing = uniqueArtifactIds
          .where((artifactId) => !selectableIds.contains(artifactId))
          .toList(growable: false);
      if (missing.isNotEmpty) {
        throw StateError('ARTIFACTS_NOT_SELECTABLE: ${missing.join(', ')}');
      }

      for (final artId in uniqueArtifactIds) {
        final existing = await txn.query(
          'profile_artifacts',
          columns: ['id', 'inclusion_status'],
          where: 'profile_id = ? AND artifact_id = ?',
          whereArgs: [resolvedProfileId, artId],
        );
        if (existing.isEmpty) {
          final id = const Uuid().v4();
          await txn.insert('profile_artifacts', {
            'id': id,
            'profile_id': resolvedProfileId,
            'artifact_id': artId,
            'inclusion_status': inclusionStatus,
            'implementation_status': 'STS-NOT-APPLIED',
            'verification_status': 'VER-NOT-VERIFIED',
            'exception_status': 'EXC-NONE',
          });
          created++;
          ids.add(id);
        } else {
          ids.add(existing.first['id'] as String);
          if (inclusionStatus != null) {
            final current = existing.first['inclusion_status'] as String?;
            final effective = _stronger(
              current,
              inclusionStatus,
              _inclusionRank,
            );
            if (effective != current) {
              await txn.update(
                'profile_artifacts',
                {'inclusion_status': effective},
                where: 'id = ?',
                whereArgs: [ids.last],
              );
            }
          }
        }

        final profileArtifactId = ids.last;
        final manualOrigin = await txn.query(
          'profile_artifact_origins',
          columns: ['id'],
          where: "profile_artifact_id = ? AND origin_type = 'MANUAL'",
          whereArgs: [profileArtifactId],
          limit: 1,
        );
        if (manualOrigin.isEmpty) {
          await txn.insert('profile_artifact_origins', {
            'id': const Uuid().v4(),
            'profile_artifact_id': profileArtifactId,
            'origin_type': 'MANUAL',
            'origin_reference': 'mobile-catalog',
            'inclusion_status': inclusionStatus,
            'selection_reason': _cleanOptional(selectionReason),
            'selected_by': selectedBy.trim(),
          });
          originsAdded++;
        }
      }
    });

    return SelectionResult(
      profileId: resolvedProfileId,
      requested: uniqueArtifactIds.length,
      created: created,
      existing: uniqueArtifactIds.length - created,
      originsAdded: originsAdded,
      profileArtifactIds: ids,
    );
  }

  @override
  Future<BlueprintsView> blueprints(String profileId, {String? artifactId}) =>
      LocalBlueprintRepository().list(profileId, profileArtifactId: artifactId);

  @override
  Future<BlueprintDetailView> blueprint(String blueprintId) =>
      LocalBlueprintRepository().detail(blueprintId);

  @override
  Future<TasksView> tasks(
    String profileId, {
    String? status,
    String? assignedTo,
  }) => LocalTaskRepository().list(
    profileId,
    status: status,
    assignedTo: assignedTo,
  );

  @override
  Future<void> updateTaskStatus(
    String taskId,
    String newStatus,
    String note, {
    required String actor,
  }) => TaskManager().updateTaskStatus(taskId, newStatus, note, actor);

  @override
  Future<TemplateView> templates() async {
    final db = await _db;
    final rows = await db.query('templates', orderBy: 'name ASC');
    final mapped = rows
        .map(
          (r) => TemplateSummary(
            id: r['id'] as String?,
            name: r['name'] as String?,
            description: r['description'] as String?,
            version: r['version'] as String?,
            scopeNote: r['scope_note'] as String?,
            category: r['category'] as String?,
            createdAt: r['created_at'] as String?,
          ),
        )
        .toList();
    return TemplateView(templates: mapped);
  }

  @override
  Future<CatalogView> templateItems(
    String templateId, {
    int limit = 100,
    int offset = 0,
  }) async {
    final db = await _db;
    final sql = '''
      SELECT sa.*,
             ti.inclusion_status, ti.priority_override, ti.review_frequency_override, ti.applicability_condition
      FROM template_items ti
      JOIN security_artifacts sa ON sa.id = ti.artifact_id
      WHERE ti.template_id = ?
      ORDER BY sa.id ASC
      LIMIT ? OFFSET ?
    ''';
    final rows = await db.rawQuery(sql, [templateId, limit, offset]);

    final items = rows
        .map(
          (r) => CatalogItem(
            id: r['id'] as String?,
            title: r['title_en'] as String?,
            definitionShort: r['definition_short_en'] as String?,
            type: r['type'] as String?,
            primaryDomain: r['primary_domain'] as String?,
            isSelected: false,
          ),
        )
        .toList();

    return CatalogView(items: items, count: items.length);
  }

  @override
  Future<ProfileSummary> applyTemplate(
    String profileId,
    String templateId, {
    required String appliedBy,
  }) async {
    final db = await _db;
    final actor = appliedBy.trim();
    if (actor.isEmpty) {
      throw ArgumentError.value(appliedBy, 'appliedBy', 'must not be empty');
    }

    await db.transaction((txn) async {
      final profile = await txn.query(
        'enterprise_profiles',
        columns: ['id'],
        where: 'id = ? AND archived_at IS NULL',
        whereArgs: [profileId],
        limit: 1,
      );
      if (profile.isEmpty) {
        throw StateError('PROFILE_NOT_FOUND_OR_ARCHIVED');
      }

      final templates = await txn.query(
        'templates',
        columns: ['id', 'version'],
        where: 'id = ?',
        whereArgs: [templateId],
        limit: 1,
      );
      if (templates.isEmpty) {
        throw StateError('TEMPLATE_NOT_FOUND');
      }
      final version = templates.single['version'] as String;

      final items = await txn.rawQuery(
        '''
        SELECT ti.*
          FROM template_items ti
          JOIN security_artifacts sa ON sa.id = ti.artifact_id
         WHERE ti.template_id = ?
           AND sa.is_active = 1
           AND sa.publication_status IN ('APPROVED','PUBLISHED')
         ORDER BY ti.id
        ''',
        [templateId],
      );
      if (items.isEmpty) {
        throw StateError('TEMPLATE_HAS_NO_APPROVED_ITEMS');
      }

      final priorApplications = await txn.query(
        'profile_templates',
        columns: ['id'],
        where: 'profile_id = ? AND template_id = ? AND template_version = ?',
        whereArgs: [profileId, templateId, version],
        limit: 1,
      );
      final profileTemplateId = priorApplications.isEmpty
          ? const Uuid().v4()
          : priorApplications.single['id'] as String;
      if (priorApplications.isEmpty) {
        await txn.insert('profile_templates', {
          'id': profileTemplateId,
          'profile_id': profileId,
          'template_id': templateId,
          'template_version': version,
          'applied_by': actor,
          'note': 'Applied from the offline template workspace.',
        });
      }

      for (final item in items) {
        final artifactId = item['artifact_id'] as String;
        final selected = await txn.query(
          'profile_artifacts',
          columns: [
            'id',
            'template_item_id',
            'inclusion_status',
            'template_priority_default',
            'template_review_frequency_default',
          ],
          where: 'profile_id = ? AND artifact_id = ?',
          whereArgs: [profileId, artifactId],
          limit: 1,
        );

        late final String profileArtifactId;
        if (selected.isEmpty) {
          profileArtifactId = const Uuid().v4();
          await txn.insert('profile_artifacts', {
            'id': profileArtifactId,
            'profile_id': profileId,
            'artifact_id': artifactId,
            'inclusion_status': item['inclusion_status'],
            'template_priority_default': item['priority_override'],
            'template_review_frequency_default':
                item['review_frequency_override'],
            'implementation_status': 'STS-NOT-APPLIED',
            'verification_status': 'VER-NOT-VERIFIED',
            'exception_status': 'EXC-NONE',
          });
        } else {
          profileArtifactId = selected.single['id'] as String;
          final defaults = <String, Object?>{};
          if (selected.single['template_item_id'] == null) {
            defaults['template_item_id'] = item['id'];
          }
          final currentInclusion =
              selected.single['inclusion_status'] as String?;
          final effectiveInclusion = _stronger(
            currentInclusion,
            item['inclusion_status'] as String?,
            _inclusionRank,
          );
          if (effectiveInclusion != currentInclusion) {
            defaults['inclusion_status'] = effectiveInclusion;
          }
          final currentPriority =
              selected.single['template_priority_default'] as String?;
          final effectivePriority = _stronger(
            currentPriority,
            item['priority_override'] as String?,
            _priorityRank,
          );
          if (effectivePriority != currentPriority) {
            defaults['template_priority_default'] = effectivePriority;
          }
          final currentReview =
              selected.single['template_review_frequency_default'] as String?;
          final effectiveReview = _moreFrequent(
            currentReview,
            item['review_frequency_override'] as String?,
          );
          if (effectiveReview != currentReview) {
            defaults['template_review_frequency_default'] = effectiveReview;
          }
          if (defaults.isNotEmpty) {
            await txn.update(
              'profile_artifacts',
              defaults,
              where: 'id = ?',
              whereArgs: [profileArtifactId],
            );
          }
        }

        final priorOrigins = await txn.query(
          'profile_artifact_origins',
          columns: ['id'],
          where: '''profile_artifact_id = ? AND origin_type = 'TEMPLATE'
                    AND profile_template_id = ? AND template_item_id = ?''',
          whereArgs: [profileArtifactId, profileTemplateId, item['id']],
          limit: 1,
        );
        if (priorOrigins.isEmpty) {
          await txn.insert('profile_artifact_origins', {
            'id': const Uuid().v4(),
            'profile_artifact_id': profileArtifactId,
            'origin_type': 'TEMPLATE',
            'template_item_id': item['id'],
            'profile_template_id': profileTemplateId,
            'origin_reference': '$templateId@$version',
            'inclusion_status': item['inclusion_status'],
            'selection_reason': item['inclusion_reason'],
            'selected_by': actor,
          });
        }
      }

      await txn.update(
        'enterprise_profiles',
        {'source_template_id': templateId},
        where: 'id = ? AND source_template_id IS NULL',
        whereArgs: [profileId],
      );
    });

    final profilesList = await profiles();
    final matching = profilesList.profiles.where((p) => p.id == profileId);
    if (matching.isEmpty) {
      throw StateError('PROFILE_NOT_FOUND_OR_ARCHIVED');
    }
    return matching.single;
  }

  @override
  Future<ProfileArtifactView> profileArtifact(
    String artifactId, {
    String? profileId,
  }) async {
    final db = await _db;
    String resolvedProfileId = profileId ?? '';
    if (resolvedProfileId.isEmpty) {
      final active = await db.rawQuery(
        'SELECT profile_id FROM v_active_profile_context LIMIT 1',
      );
      if (active.isNotEmpty) {
        resolvedProfileId = active.first['profile_id'] as String;
      }
    }
    if (resolvedProfileId.isEmpty) {
      throw StateError('ACTIVE_PROFILE_REQUIRED');
    }

    final rows = await db.query(
      'v_profile_operational_items',
      where: 'profile_id = ? AND artifact_id = ?',
      whereArgs: [resolvedProfileId, artifactId],
      limit: 1,
    );

    if (rows.isEmpty) {
      throw Exception('Artifact not found in profile');
    }
    final r = rows.first;

    final assessmentsRes = await db.query(
      'profile_assessments',
      where: 'profile_artifact_id = ?',
      whereArgs: [r['profile_artifact_id']],
      orderBy: 'assessment_date DESC, id DESC',
    );

    final item = _operationalItemFromRow(r);

    final assessments = assessmentsRes
        .map(
          (a) => AssessmentRecord(
            id: a['id'] as String?,
            profileArtifactId: a['profile_artifact_id'] as String?,
            assessmentDate: a['assessment_date'] as String?,
            assessorName: a['assessor_name'] as String?,
            score: a['score'] as num?,
            implementationStatus: a['implementation_status'] as String?,
            verificationStatus: a['verification_status'] as String?,
            effectiveness: a['effectiveness'] as String?,
            exceptionStatus: a['exception_status'] as String?,
            comments: a['comments'] as String?,
          ),
        )
        .toList();

    final tagsRes = await db.query(
      'artifact_tags',
      where: 'artifact_id = ?',
      whereArgs: [artifactId],
    );
    final mappingsRes = await db.query(
      'framework_mappings',
      where: 'artifact_id = ?',
      whereArgs: [artifactId],
    );
    final relationshipsRes = await db.query(
      'artifact_relationships',
      where: 'source_id = ? OR target_id = ?',
      whereArgs: [artifactId, artifactId],
    );

    final tags = tagsRes
        .map(
          (t) => ArtifactTag(
            tagType: t['tag_type'] as String,
            tagValue: t['tag_value'] as String,
          ),
        )
        .toList();

    final mappings = mappingsRes
        .map(
          (m) => FrameworkMapping(
            framework: m['framework'] as String,
            version: m['version'] as String,
            reference: m['reference'] as String,
            category: m['category'] as String?,
            mappingStrength: m['mapping_strength'] as String,
            rationale: m['rationale'] as String?,
          ),
        )
        .toList();

    final relationships = relationshipsRes
        .map(
          (rel) => ArtifactRelationship(
            sourceId: rel['source_id'] as String,
            targetId: rel['target_id'] as String,
            relationType: rel['relation_type'] as String,
            description: rel['description'] as String?,
          ),
        )
        .toList();

    return ProfileArtifactView(
      contractVersion: kContractVersion,
      profileId: resolvedProfileId,
      artifact: item,
      assessments: assessments,
      tags: tags,
      mappings: mappings,
      relationships: relationships,
    );
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
    final normalizedAssessor = assessorName.trim();
    if (normalizedAssessor.isEmpty) {
      throw ArgumentError.value(assessorName, 'assessorName', 'is required');
    }
    _validateControlledValue(
      implementationStatus,
      _implementationStatuses,
      'implementationStatus',
    );
    _validateControlledValue(
      verificationStatus,
      _verificationStatuses,
      'verificationStatus',
    );
    _validateControlledValue(
      effectiveness,
      _effectivenessValues,
      'effectiveness',
    );
    _validateControlledValue(
      currentMaturityLevel,
      _maturityLevels,
      'currentMaturityLevel',
    );
    _validateControlledValue(priorityOverride, _priorities, 'priorityOverride');
    _validateControlledValue(
      reviewFrequencyOverride,
      _reviewFrequencies,
      'reviewFrequencyOverride',
    );
    if (score != null && (!score.isFinite || score < 0 || score > 100)) {
      throw ArgumentError.value(score, 'score', 'must be between 0 and 100');
    }

    final db = await _db;
    String resolvedProfileId = profileId ?? '';
    if (resolvedProfileId.isEmpty) {
      final active = await db.rawQuery(
        'SELECT profile_id FROM v_active_profile_context LIMIT 1',
      );
      if (active.isNotEmpty) {
        resolvedProfileId = active.first['profile_id'] as String;
      }
    }
    if (resolvedProfileId.isEmpty) {
      throw StateError('ACTIVE_PROFILE_REQUIRED');
    }

    final assessmentId = const Uuid().v4();
    final assessmentDate = DateTime.now().toUtc().toIso8601String();
    final changes = <String, Object?>{};
    if (implementationStatus != null) {
      changes['implementation_status'] = implementationStatus;
    }
    if (verificationStatus != null) {
      changes['verification_status'] = verificationStatus;
    }
    if (effectiveness != null) changes['effectiveness'] = effectiveness;
    if (currentMaturityLevel != null) {
      changes['current_maturity_level'] = currentMaturityLevel;
    }
    if (assignedOwner != null) changes['assigned_owner'] = assignedOwner;
    if (dueDate != null) changes['due_date'] = dueDate;
    if (notes != null) changes['notes'] = notes;
    if (priorityOverride != null) {
      changes['priority_override'] = priorityOverride;
    }
    if (reviewFrequencyOverride != null) {
      changes['review_frequency_override'] = reviewFrequencyOverride;
    }
    if (clearAssignedOwner) changes['assigned_owner'] = null;
    if (clearDueDate) changes['due_date'] = null;
    if (clearNotes) changes['notes'] = null;
    if (clearPriorityOverride) changes['priority_override'] = null;
    if (clearReviewFrequencyOverride) {
      changes['review_frequency_override'] = null;
    }

    await db.transaction((txn) async {
      final existing = await txn.query(
        'profile_artifacts',
        where: 'profile_id = ? AND artifact_id = ?',
        whereArgs: [resolvedProfileId, artifactId],
        limit: 1,
      );
      if (existing.isEmpty) {
        throw StateError(
          'ARTIFACT_NOT_SELECTED: $resolvedProfileId/$artifactId',
        );
      }
      final profileArtifactId = existing.single['id'] as String;
      if (changes.isNotEmpty) {
        final updated = await txn.update(
          'profile_artifacts',
          changes,
          where: 'id = ? AND profile_id = ?',
          whereArgs: [profileArtifactId, resolvedProfileId],
        );
        if (updated != 1) {
          throw StateError('PROFILE_ARTIFACT_UPDATE_CONFLICT');
        }
      }
      final current = (await txn.query(
        'profile_artifacts',
        where: 'id = ? AND profile_id = ?',
        whereArgs: [profileArtifactId, resolvedProfileId],
        limit: 1,
      )).single;
      await txn.insert('profile_assessments', {
        'id': assessmentId,
        'profile_artifact_id': profileArtifactId,
        'assessment_date': assessmentDate,
        'assessor_name': normalizedAssessor,
        'score': score,
        'implementation_status': current['implementation_status'],
        'verification_status': current['verification_status'],
        'effectiveness': current['effectiveness'],
        'exception_status': current['exception_status'],
        'comments': comments,
      });
    });

    final updatedView = await profileArtifact(
      artifactId,
      profileId: resolvedProfileId,
    );

    return AssessmentResult(
      assessment: updatedView.assessments.firstWhere(
        (assessment) => assessment.id == assessmentId,
      ),
      artifact: updatedView.artifact,
    );
  }
}

Future<Map<String, dynamic>> _loadScoringPolicy(Database database) async {
  final policyRows = await database.query(
    'scoring_policy',
    columns: [
      'critical_cap',
      'dependency_clamp_ceiling',
      'accepted_risk_lifts_cap',
    ],
    where: 'id = ?',
    whereArgs: ['default'],
    limit: 1,
  );
  final bandRows = await database.query(
    'scoring_bands',
    columns: ['min_score', 'label_en'],
    where: 'policy_id = ?',
    whereArgs: ['default'],
    orderBy: 'min_score',
  );
  if (policyRows.isEmpty || bandRows.isEmpty) {
    return Map<String, dynamic>.from(ScoringEngine.defaultPolicy);
  }
  final policy = policyRows.single;
  return <String, dynamic>{
    'critical_cap': policy['critical_cap'],
    'dependency_clamp_ceiling': policy['dependency_clamp_ceiling'],
    'accepted_risk_lifts_cap': policy['accepted_risk_lifts_cap'],
    'bands': bandRows
        .map((band) => [band['min_score'], band['label_en']])
        .toList(),
  };
}

void _validateControlledValue(
  String? value,
  Set<String> allowed,
  String parameterName,
) {
  if (value != null && !allowed.contains(value)) {
    throw ArgumentError.value(value, parameterName, 'is not controlled');
  }
}

OperationalItem _operationalItemFromRow(Map<String, Object?> row) =>
    OperationalItem(
      profileArtifactId: row['profile_artifact_id'] as String?,
      artifactId: row['artifact_id'] as String?,
      type: row['type'] as String?,
      titleEn: row['title_en'] as String?,
      titleAr: row['title_ar'] as String?,
      definitionShortEn: row['definition_short_en'] as String?,
      definitionShortAr: row['definition_short_ar'] as String?,
      primaryDomain: row['primary_domain'] as String?,
      subDomain: row['sub_domain'] as String?,
      source: row['source'] as String?,
      sourceDocument: row['source_document'] as String?,
      obligationLevel: row['obligation_level'] as String?,
      testability: row['testability'] as String?,
      inclusionStatus: row['inclusion_status'] as String?,
      effectivePriority: row['effective_priority'] as String?,
      effectiveReviewFrequency: row['effective_review_frequency'] as String?,
      priorityOverride: row['priority_override'] as String?,
      reviewFrequencyOverride: row['review_frequency_override'] as String?,
      implementationStatus: row['implementation_status'] as String?,
      verificationStatus: row['verification_status'] as String?,
      effectiveness: row['effectiveness'] as String?,
      exceptionStatus: row['exception_status'] as String?,
      currentMaturityLevel: row['current_maturity_level'] as String?,
      assignedOwner: row['assigned_owner'] as String?,
      dueDate: row['due_date'] as String?,
      notes: row['notes'] as String?,
      evidenceCount: row['evidence_count'] as num?,
      originCount: row['origin_count'] as num?,
      lastAssessmentAt: row['last_assessment_at'] as String?,
      selectedAt: row['selected_at'] as String?,
      updatedAt: row['updated_at'] as String?,
    );
