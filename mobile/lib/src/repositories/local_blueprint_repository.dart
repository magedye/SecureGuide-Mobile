import 'package:sqflite/sqflite.dart';

import '../../core/database/database_helper.dart';
import '../../read_model_contract.dart';

/// Typed SQLite boundary for profile-scoped governed blueprints.
final class LocalBlueprintRepository {
  LocalBlueprintRepository({Future<Database>? database})
    : _database = database ?? DatabaseHelper.instance.database;

  final Future<Database> _database;

  Future<BlueprintsView> list(
    String profileId, {
    String? profileArtifactId,
  }) async {
    final db = await _database;
    var sql = 'SELECT * FROM v_profile_blueprints WHERE profile_id = ?';
    final args = <Object?>[profileId];
    if (profileArtifactId != null && profileArtifactId.isNotEmpty) {
      sql += ' AND profile_artifact_id = ?';
      args.add(profileArtifactId);
    }
    sql += ' ORDER BY updated_at DESC, version DESC';
    final rows = await db.rawQuery(sql, args);
    return BlueprintsView(blueprints: rows.map(_blueprintSummary).toList());
  }

  Future<BlueprintDetailView> detail(String blueprintId) async {
    final db = await _database;
    final rows = await db.query(
      'approved_blueprints',
      where: 'id = ?',
      whereArgs: [blueprintId],
      limit: 1,
    );
    if (rows.isEmpty) {
      throw StateError('BLUEPRINT_NOT_FOUND');
    }

    final appliedRuleRows = await db.query(
      'approved_blueprint_rules',
      where: 'blueprint_id = ?',
      whereArgs: [blueprintId],
      orderBy: 'stage, priority DESC, rule_id',
    );
    final actionRows = await db.query(
      'approved_blueprint_actions',
      where: 'blueprint_id = ?',
      whereArgs: [blueprintId],
      orderBy: 'display_order, id',
    );
    final outputRows = await db.query(
      'approved_blueprint_outputs',
      where: 'blueprint_id = ?',
      whereArgs: [blueprintId],
      orderBy: 'semantic_key, id',
    );
    final evidenceRows = await db.query(
      'approved_blueprint_evidence',
      where: 'blueprint_id = ?',
      whereArgs: [blueprintId],
      orderBy: 'mandatory DESC, semantic_key, id',
    );
    final enrichmentRows = await db.query(
      'approved_blueprint_pattern_enrichments',
      where: 'blueprint_id = ?',
      whereArgs: [blueprintId],
      orderBy: 'selected_at, id',
    );
    final findingRows = await db.query(
      'approved_blueprint_review_findings',
      where: 'blueprint_id = ?',
      whereArgs: [blueprintId],
      orderBy: 'finding_type, finding_code, id',
    );

    final actionRules = await _sourceRules(
      db,
      table: 'approved_blueprint_action_rules',
      ownerColumn: 'action_id',
      ownerIds: actionRows.map((row) => row['id'] as String),
    );
    final outputRules = await _sourceRules(
      db,
      table: 'approved_blueprint_output_rules',
      ownerColumn: 'output_id',
      ownerIds: outputRows.map((row) => row['id'] as String),
    );
    final evidenceRules = await _sourceRules(
      db,
      table: 'approved_blueprint_evidence_rules',
      ownerColumn: 'evidence_id',
      ownerIds: evidenceRows.map((row) => row['id'] as String),
    );

    final row = rows.single;
    return BlueprintDetailView(
      blueprint: BlueprintDetail(
        id: row['id'] as String?,
        artifactId: row['artifact_id'] as String?,
        title: row['title'] as String?,
        version: row['version'] as num?,
        workflowStatus: row['workflow_status'] as String?,
        actionPlanType: row['action_plan_type'] as String?,
        generationConfidence: row['generation_confidence'] as num?,
        generationRequiresReview: _flag(row['generation_requires_review']),
        profileId: row['profile_id'] as String?,
        profileArtifactId: row['profile_artifact_id'] as String?,
        parentBlueprintId: row['parent_blueprint_id'] as String?,
        ruleSetId: row['rule_set_id'] as String?,
        ruleSetVersion: row['rule_set_version'] as String?,
        ruleSetHash: row['rule_set_hash'] as String?,
        engineVersion: row['engine_version'] as String?,
        changeSummary: row['change_summary'] as String?,
        reviewResolutionNote: row['review_resolution_note'] as String?,
        createdBy: row['created_by'] as String?,
        submittedBy: row['submitted_by'] as String?,
        submittedAt: row['submitted_at'] as String?,
        approvedBy: row['approved_by'] as String?,
        approvedAt: row['approved_at'] as String?,
        updatedAt: row['updated_at'] as String?,
        appliedRules: appliedRuleRows.map(_appliedRule).toList(),
        actions: actionRows
            .map(
              (item) =>
                  _action(item, actionRules[item['id'] as String] ?? const []),
            )
            .toList(),
        expectedOutputs: outputRows
            .map(
              (item) =>
                  _output(item, outputRules[item['id'] as String] ?? const []),
            )
            .toList(),
        evidence: evidenceRows
            .map(
              (item) => _evidence(
                item,
                evidenceRules[item['id'] as String] ?? const [],
              ),
            )
            .toList(),
        patternEnrichments: enrichmentRows.map(_enrichment).toList(),
        reviewFindings: findingRows.map(_reviewFinding).toList(),
      ),
    );
  }

  Future<void> submit(String blueprintId, {required String actor}) =>
      _transition(
        blueprintId,
        from: 'DRAFT',
        to: 'UNDER_REVIEW',
        actor: actor,
        values: {
          'submitted_by': actor.trim(),
          'submitted_at': DateTime.now().toUtc().toIso8601String(),
          'last_actor_role': 'AUTHOR',
        },
      );

  Future<void> approve(
    String blueprintId, {
    required String actor,
    String? resolutionNote,
  }) => _transition(
    blueprintId,
    from: 'UNDER_REVIEW',
    to: 'APPROVED',
    actor: actor,
    values: {
      'approved_by': actor.trim(),
      'approved_at': DateTime.now().toUtc().toIso8601String(),
      'last_actor_role': 'APPROVER',
      if (resolutionNote?.trim().isNotEmpty == true)
        'review_resolution_note': resolutionNote!.trim(),
    },
  );

  Future<void> returnToDraft(
    String blueprintId, {
    required String actor,
    required String note,
  }) {
    if (note.trim().isEmpty) {
      throw ArgumentError.value(note, 'note', 'must not be empty');
    }
    return _transition(
      blueprintId,
      from: 'UNDER_REVIEW',
      to: 'DRAFT',
      actor: actor,
      values: {'last_actor_role': 'REVIEWER', 'change_summary': note.trim()},
    );
  }

  Future<void> _transition(
    String blueprintId, {
    required String from,
    required String to,
    required String actor,
    required Map<String, Object?> values,
  }) async {
    final accountableActor = actor.trim();
    if (accountableActor.isEmpty) {
      throw ArgumentError.value(actor, 'actor', 'must not be empty');
    }
    final db = await _database;
    final affected = await db.update(
      'approved_blueprints',
      {...values, 'workflow_status': to, 'last_actor': accountableActor},
      where: 'id = ? AND workflow_status = ?',
      whereArgs: [blueprintId, from],
    );
    if (affected != 1) {
      throw StateError('BLUEPRINT_TRANSITION_REJECTED:$from->$to');
    }
  }

  static BlueprintSummary _blueprintSummary(Map<String, Object?> row) =>
      BlueprintSummary(
        id: row['id'] as String?,
        artifactId: row['artifact_id'] as String?,
        artifactTitleEn: row['artifact_title_en'] as String?,
        artifactTitleAr: row['artifact_title_ar'] as String?,
        title: row['title'] as String?,
        version: row['version'] as num?,
        workflowStatus: row['workflow_status'] as String?,
        actionPlanType: row['action_plan_type'] as String?,
        generationConfidence: row['generation_confidence'] as num?,
        generationRequiresReview: _flag(row['generation_requires_review']),
        actionCount: row['action_count'] as num?,
        evidenceCount: row['evidence_count'] as num?,
        taskCount: row['task_count'] as num?,
        createdBy: row['created_by'] as String?,
        approvedBy: row['approved_by'] as String?,
        approvedAt: row['approved_at'] as String?,
        updatedAt: row['updated_at'] as String?,
      );

  static AppliedRule _appliedRule(Map<String, Object?> row) => AppliedRule(
    ruleId: row['rule_id'] as String?,
    ruleVersion: row['rule_version'] as String?,
    stage: row['stage'] as String?,
    priority: row['priority'] as num?,
    rationale: row['rationale'] as String?,
    baseConfidence: row['base_confidence'] as num?,
  );

  static BlueprintAction _action(
    Map<String, Object?> row,
    List<SourceRule> rules,
  ) => BlueprintAction(
    id: row['id'] as String?,
    actionCode: row['action_code'] as String?,
    semanticKey: row['semantic_key'] as String?,
    title: row['title'] as String?,
    description: row['description'] as String?,
    category: row['category'] as String?,
    phase: row['phase'] as String?,
    displayOrder: row['display_order'] as num?,
    rationale: row['rationale'] as String?,
    confidence: row['confidence'] as num?,
    taskable: _flag(row['taskable']),
    requiresHumanReview: _flag(row['requires_human_review']),
    sourceCitation: row['source_citation'] as String?,
    sourceRules: rules,
  );

  static ExpectedOutput _output(
    Map<String, Object?> row,
    List<SourceRule> rules,
  ) => ExpectedOutput(
    id: row['id'] as String?,
    outputCode: row['output_code'] as String?,
    semanticKey: row['semantic_key'] as String?,
    title: row['title'] as String?,
    description: row['description'] as String?,
    rationale: row['rationale'] as String?,
    sourceRules: rules,
  );

  static EvidenceRequirement _evidence(
    Map<String, Object?> row,
    List<SourceRule> rules,
  ) => EvidenceRequirement(
    id: row['id'] as String?,
    evidenceCode: row['evidence_code'] as String?,
    semanticKey: row['semantic_key'] as String?,
    title: row['title'] as String?,
    evidenceType: row['evidence_type'] as String?,
    description: row['description'] as String?,
    rationale: row['rationale'] as String?,
    mandatory: _flag(row['mandatory']),
    confidence: row['confidence'] as num?,
    requiresHumanReview: _flag(row['requires_human_review']),
    sourceCitation: row['source_citation'] as String?,
    sourceRules: rules,
  );

  static PatternEnrichment _enrichment(Map<String, Object?> row) =>
      PatternEnrichment(
        id: row['id'] as String?,
        sourcePatternId: row['source_pattern_id'] as String?,
        recommendedArtifactType: row['recommended_artifact_type'] as String?,
        primaryDomain: row['primary_domain'] as String?,
        subDomain: row['sub_domain'] as String?,
        patternPriority: row['pattern_priority'] as String?,
        copiedTitleAr: row['copied_title_ar'] as String?,
        copiedTextAr: row['copied_text_ar'] as String?,
        safetyReviewRequired: _flag(row['safety_review_required']),
        safetyAcknowledged: _flag(row['safety_acknowledged']),
        safetyNoteAr: row['safety_note_ar'] as String?,
        libraryVersion: row['library_version'] as String?,
        selectedBy: row['selected_by'] as String?,
        selectionReason: row['selection_reason'] as String?,
        selectedAt: row['selected_at'] as String?,
      );

  static ReviewFinding _reviewFinding(Map<String, Object?> row) =>
      ReviewFinding(
        findingType: row['finding_type'] as String?,
        findingCode: row['finding_code'] as String?,
        fieldName: row['field_name'] as String?,
        inputValue: row['input_value'] as String?,
        canonicalValue: row['canonical_value'] as String?,
        detail: row['detail'] as String?,
        quality: row['quality'] as num?,
      );

  static Future<Map<String, List<SourceRule>>> _sourceRules(
    Database db, {
    required String table,
    required String ownerColumn,
    required Iterable<String> ownerIds,
  }) async {
    final ids = ownerIds.toList();
    if (ids.isEmpty) return const {};
    final rows = await db.rawQuery(
      'SELECT $ownerColumn,rule_id,rule_version FROM $table '
      'WHERE $ownerColumn IN (${List.filled(ids.length, '?').join(',')}) '
      'ORDER BY $ownerColumn,rule_id,rule_version',
      ids,
    );
    final result = <String, List<SourceRule>>{};
    for (final row in rows) {
      final ownerId = row[ownerColumn] as String;
      result
          .putIfAbsent(ownerId, () => [])
          .add(
            SourceRule(
              ruleId: row['rule_id'] as String?,
              ruleVersion: row['rule_version'] as String?,
            ),
          );
    }
    return result;
  }

  static bool? _flag(Object? value) => switch (value) {
    null => null,
    bool flag => flag,
    int number => number != 0,
    _ => throw StateError('INVALID_SQLITE_BOOLEAN:$value'),
  };
}
