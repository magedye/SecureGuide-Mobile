import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:secureguide_mobile/core/database/database_helper.dart';
import 'package:secureguide_mobile/src/client/local_secure_guide_client.dart';
import 'package:secureguide_mobile/src/repositories/local_blueprint_repository.dart';
import 'package:secureguide_mobile/src/repositories/local_task_repository.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tempDirectory;
  late Database database;
  late LocalBlueprintRepository blueprints;
  late LocalTaskRepository tasks;
  const blueprintId = 'BP-LOCAL-001';
  const taskId = 'TASK-LOCAL-001';

  setUpAll(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    tempDirectory = await Directory.systemTemp.createTemp('local-workflows-');
    final databasePath = p.join(tempDirectory.path, 'catalog.db');
    await File('assets/catalog.db').copy(databasePath);
    DatabaseHelper.instance.setDatabasePathForTesting(databasePath);
    final client = LocalSecureGuideClient();
    final profile = await client.createProfile(name: 'Workflow profile');
    database = await DatabaseHelper.instance.database;
    final artifact = (await database.query(
      'security_artifacts',
      columns: ['id', 'primary_domain', 'sub_domain'],
      orderBy: 'id',
      limit: 1,
    )).single;
    final artifactId = artifact['id'] as String;
    final selection = await client.selectArtifacts(
      [artifactId],
      profileId: profile.id,
      selectedBy: 'workflow-author',
    );
    final profileArtifactId = selection.profileArtifactIds.single;

    await database.transaction((txn) async {
      await txn.insert('approved_blueprints', {
        'id': blueprintId,
        'profile_id': profile.id,
        'artifact_id': artifactId,
        'profile_artifact_id': profileArtifactId,
        'version': 1,
        'source_blueprint_id': 'generated-local-001',
        'source_payload_hash': List.filled(64, 'a').join(),
        'engine_version': '1.0.0',
        'blueprint_version': '1.0.0',
        'rule_set_id': 'local-test-rules',
        'rule_set_version': '1.0.0',
        'rule_set_hash': List.filled(64, 'b').join(),
        'action_plan_type': 'CONTROL_IMPLEMENTATION',
        'title': 'Governed local blueprint',
        'generation_confidence': 0.81,
        'generation_requires_review': 1,
        'workflow_status': 'DRAFT',
        'created_by': 'workflow-author',
        'change_summary': 'Initial governed snapshot',
        'last_actor': 'workflow-author',
        'last_actor_role': 'AUTHOR',
      });
      await txn.insert('approved_blueprint_rules', {
        'blueprint_id': blueprintId,
        'rule_id': 'RULE-001',
        'rule_version': '1.0.0',
        'stage': 'ARTIFACT_TYPE',
        'priority': 1,
        'rationale': 'A traceable local rule.',
        'base_confidence': 0.81,
      });
      await txn.insert('approved_blueprint_actions', {
        'id': 'ACT-LOCAL-001',
        'blueprint_id': blueprintId,
        'source_action_id': 'source-action-001',
        'action_code': 'ACT-001',
        'semantic_key': 'local.action',
        'title': 'Implement locally',
        'description': 'Implement and verify the local action.',
        'category': 'IMPLEMENTATION',
        'phase': 'IMPLEMENT',
        'display_order': 1,
        'rationale': 'Required by the rule.',
        'confidence': 0.81,
        'taskable': 1,
        'requires_human_review': 1,
      });
      await txn.insert('approved_blueprint_action_rules', {
        'action_id': 'ACT-LOCAL-001',
        'rule_id': 'RULE-001',
        'rule_version': '1.0.0',
      });
      await txn.insert('approved_blueprint_outputs', {
        'id': 'OUT-LOCAL-001',
        'blueprint_id': blueprintId,
        'source_output_id': 'source-output-001',
        'output_code': 'OUT-001',
        'semantic_key': 'local.output',
        'title': 'Implementation record',
        'description': 'The expected implementation record.',
        'rationale': 'Demonstrates completion.',
      });
      await txn.insert('approved_blueprint_output_rules', {
        'output_id': 'OUT-LOCAL-001',
        'rule_id': 'RULE-001',
        'rule_version': '1.0.0',
      });
      await txn.insert('approved_blueprint_evidence', {
        'id': 'EVD-LOCAL-001',
        'blueprint_id': blueprintId,
        'source_evidence_id': 'source-evidence-001',
        'evidence_code': 'EVD-001',
        'semantic_key': 'local.evidence',
        'title': 'Verification report',
        'evidence_type': 'REPORT',
        'description': 'A local verification report.',
        'rationale': 'Verifies the implementation.',
        'mandatory': 1,
        'confidence': 0.81,
        'requires_human_review': 0,
      });
      await txn.insert('approved_blueprint_evidence_rules', {
        'evidence_id': 'EVD-LOCAL-001',
        'rule_id': 'RULE-001',
        'rule_version': '1.0.0',
      });
      await txn.insert('approved_blueprint_pattern_enrichments', {
        'id': 'ENR-LOCAL-001',
        'blueprint_id': blueprintId,
        'source_pattern_id': 'OPP-001',
        'pattern_source_row': 1,
        'library_id': 'local-patterns',
        'library_version': '1.0.0',
        'library_sha256': List.filled(64, 'c').join(),
        'recommended_artifact_type': 'ART-CTR',
        'primary_domain': artifact['primary_domain'],
        'sub_domain': artifact['sub_domain'],
        'pattern_priority': 'PRI-MEDIUM',
        'copied_title_ar': 'نمط تشغيلي محلي',
        'copied_text_ar': 'نسخة مجمدة من نص النمط التشغيلي.',
        'selected_by': 'workflow-author',
        'selection_reason': 'Adds local implementation context.',
      });
      await txn.insert('approved_blueprint_review_findings', {
        'id': 'FND-LOCAL-001',
        'blueprint_id': blueprintId,
        'finding_type': 'REVIEW_REASON',
        'finding_code': 'LOW_CONFIDENCE',
        'field_name': 'generation_confidence',
        'detail': 'Human approval must resolve the generation review flag.',
        'quality': 0.81,
      });
    });

    blueprints = LocalBlueprintRepository(database: Future.value(database));
    tasks = LocalTaskRepository(database: Future.value(database));
  });

  tearDownAll(() async {
    await database.close();
    await tempDirectory.delete(recursive: true);
  });

  test('typed blueprint reads include all normalized collections', () async {
    final profileId =
        (await database.query(
              'approved_blueprints',
              columns: ['profile_id'],
              where: 'id = ?',
              whereArgs: [blueprintId],
            )).single['profile_id']
            as String;
    final list = await blueprints.list(profileId);
    expect(list.blueprints, hasLength(1));
    expect(list.blueprints.single.id, blueprintId);
    expect(list.blueprints.single.actionCount, 1);
    expect(list.blueprints.single.generationRequiresReview, isTrue);

    final detail = (await blueprints.detail(blueprintId)).blueprint;
    expect(detail.actions.single.actionCode, 'ACT-001');
    expect(detail.actions.single.sourceRules.single.ruleId, 'RULE-001');
    expect(detail.expectedOutputs.single.outputCode, 'OUT-001');
    expect(detail.expectedOutputs.single.sourceRules, hasLength(1));
    expect(detail.evidence.single.evidenceType, 'REPORT');
    expect(detail.evidence.single.mandatory, isTrue);
    expect(detail.appliedRules.single.baseConfidence, 0.81);
    expect(detail.patternEnrichments.single.sourcePatternId, 'OPP-001');
    expect(detail.reviewFindings.single.quality, 0.81);
  });

  test(
    'blueprint transitions require actors and expected affected rows',
    () async {
      await expectLater(
        blueprints.approve(blueprintId, actor: 'premature-approver'),
        throwsA(isA<StateError>()),
      );
      await expectLater(
        blueprints.submit(blueprintId, actor: '   '),
        throwsA(isA<ArgumentError>()),
      );

      await blueprints.submit(blueprintId, actor: 'accountable-author');
      await expectLater(
        blueprints.submit(blueprintId, actor: 'accountable-author'),
        throwsA(isA<StateError>()),
      );
      await blueprints.approve(
        blueprintId,
        actor: 'accountable-approver',
        resolutionNote: 'Reviewed and accepted after human verification.',
      );

      final row = (await database.query(
        'approved_blueprints',
        where: 'id = ?',
        whereArgs: [blueprintId],
      )).single;
      expect(row['workflow_status'], 'APPROVED');
      expect(row['approved_by'], 'accountable-approver');
      final events = await database.query(
        'blueprint_review_events',
        where: 'blueprint_id = ?',
        whereArgs: [blueprintId],
        orderBy: 'id',
      );
      expect(events.map((event) => event['event_type']), [
        'CREATED',
        'SUBMITTED',
        'APPROVED',
      ]);
    },
  );

  test(
    'typed task queue captures actors and storage-enforced transitions',
    () async {
      final blueprint = (await database.query(
        'approved_blueprints',
        where: 'id = ?',
        whereArgs: [blueprintId],
      )).single;
      await database.insert('profile_tasks', {
        'id': taskId,
        'profile_id': blueprint['profile_id'],
        'profile_artifact_id': blueprint['profile_artifact_id'],
        'blueprint_id': blueprintId,
        'blueprint_action_id': 'ACT-LOCAL-001',
        'source_semantic_key': 'local.action',
        'title': 'Implement locally',
        'description': 'Implement and verify the local action.',
        'status': 'TODO',
        'priority': 'PRI-HIGH',
        'assigned_to': 'security-team',
        'created_by': 'accountable-approver',
        'last_changed_by': 'accountable-approver',
      });

      var queue = await tasks.list(blueprint['profile_id'] as String);
      expect(queue.tasks.single.blueprintVersion, 1);
      expect(queue.tasks.single.artifactId, blueprint['artifact_id']);
      expect(queue.tasks.single.assignedTo, 'security-team');

      await tasks.updateStatus(
        taskId,
        'IN_PROGRESS',
        actor: 'task-owner',
        note: 'Implementation started.',
      );
      await tasks.updateStatus(
        taskId,
        'DONE',
        actor: 'task-owner',
        note: 'Implementation and verification complete.',
      );
      queue = await tasks.list(
        blueprint['profile_id'] as String,
        status: 'DONE',
      );
      expect(queue.tasks.single.status, 'DONE');
      expect(queue.tasks.single.lastChangedBy, 'task-owner');
      expect(queue.tasks.single.completedAt, isNotNull);

      final events = await database.query(
        'profile_task_events',
        where: 'task_id = ?',
        whereArgs: [taskId],
        orderBy: 'id',
      );
      expect(events.map((event) => event['event_type']), [
        'CREATED',
        'STARTED',
        'COMPLETED',
      ]);
      expect(events.last['actor'], 'task-owner');
      await expectLater(
        tasks.updateStatus(
          taskId,
          'BLOCKED',
          actor: 'task-owner',
          note: 'Invalid after completion.',
        ),
        throwsA(anything),
      );
    },
  );
}
