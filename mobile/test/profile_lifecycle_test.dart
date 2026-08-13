import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:secureguide_mobile/core/database/database_helper.dart';
import 'package:secureguide_mobile/src/client/local_secure_guide_client.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tempDir;
  late LocalSecureGuideClient client;

  setUpAll(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    tempDir = await Directory.systemTemp.createTemp('profile-lifecycle-');
    final databasePath = p.join(tempDir.path, 'catalog.db');
    await File('assets/catalog.db').copy(databasePath);
    DatabaseHelper.instance.setDatabasePathForTesting(databasePath);
    client = LocalSecureGuideClient();
    await DatabaseHelper.instance.database;
  });

  tearDownAll(() async {
    final database = await DatabaseHelper.instance.database;
    await database.close();
    await tempDir.delete(recursive: true);
  });

  test('archive preserves profile history and clears active context', () async {
    final created = await client.createProfile(
      name: 'Archive proof',
      activate: true,
    );
    final database = await DatabaseHelper.instance.database;
    final artifactId =
        (await database.query(
              'security_artifacts',
              columns: ['id'],
              limit: 1,
            )).single['id']
            as String;

    await client.selectArtifacts([artifactId], profileId: created.id);
    await client.archiveProfile(created.id!);

    expect(
      (await client.profiles()).profiles.where((p) => p.id == created.id),
      isEmpty,
    );
    final archived = (await database.query(
      'enterprise_profiles',
      where: 'id = ?',
      whereArgs: [created.id],
    )).single;
    expect(archived['archived_at'], isNotNull);
    expect(
      (await database.query(
        'profile_artifacts',
        where: 'profile_id = ?',
        whereArgs: [created.id],
      )),
      hasLength(1),
    );
    expect(
      (await database.query(
        'application_state',
        where: 'singleton_id = 1',
      )).single['active_profile_id'],
      isNull,
    );
    await expectLater(client.activateProfile(created.id!), throwsA(anything));
  });

  test('profile writes validate controlled values and fail closed', () async {
    await expectLater(client.dashboard(), throwsA(isA<StateError>()));

    await expectLater(client.createProfile(name: '   '), throwsArgumentError);
    await expectLater(
      client.createProfile(
        name: 'Invalid maturity',
        targetMaturityLevel: 'MAT-MEASURED',
      ),
      throwsArgumentError,
    );

    final created = await client.createProfile(
      name: '  Governed profile  ',
      profileKind: '   ',
      targetMaturityLevel: 'REPEATABLE',
      description: '  Profile description  ',
    );
    expect(created.name, 'Governed profile');
    expect(created.profileKind, isNull);
    expect(created.targetMaturityLevel, 'REPEATABLE');
    expect(created.description, 'Profile description');

    final updated = await client.updateProfile(
      created.id!,
      targetMaturityLevel: 'MANAGED',
    );
    expect(updated.id, created.id);
    expect(updated.targetMaturityLevel, 'MANAGED');

    final cleared = await client.updateProfile(
      created.id!,
      clearTargetMaturityLevel: true,
    );
    expect(cleared.id, created.id);
    expect(cleared.targetMaturityLevel, isNull);

    await expectLater(
      client.updateProfile(
        created.id!,
        targetMaturityLevel: 'INITIAL',
        clearTargetMaturityLevel: true,
      ),
      throwsArgumentError,
    );
    await expectLater(
      client.updateProfile(created.id!, targetMaturityLevel: 'MAT-INITIAL'),
      throwsArgumentError,
    );
    await expectLater(
      client.activateProfile('missing-profile'),
      throwsA(isA<StateError>()),
    );
    await expectLater(
      client.updateProfile('missing-profile', name: 'Wrong target'),
      throwsA(isA<StateError>()),
    );
  });

  test(
    'artifact selection is unique, governed, atomic, and only strengthens',
    () async {
      final profile = await client.createProfile(name: 'Selection proof');
      final database = await DatabaseHelper.instance.database;
      final artifactRows = await database.query(
        'security_artifacts',
        columns: ['id'],
        where:
            "is_active = 1 AND publication_status IN ('APPROVED','PUBLISHED')",
        orderBy: 'id',
        limit: 2,
      );
      expect(artifactRows, hasLength(2));
      final firstId = artifactRows[0]['id'] as String;
      final secondId = artifactRows[1]['id'] as String;

      final initial = await client.selectArtifacts(
        [firstId, firstId],
        profileId: profile.id,
        selectedBy: ' selector ',
        inclusionStatus: 'OPTIONAL',
      );
      expect(initial.requested, 1);
      expect(initial.created, 1);
      expect(initial.existing, 0);
      expect(initial.originsAdded, 1);
      expect(initial.profileArtifactIds, hasLength(1));

      final strengthened = await client.selectArtifacts(
        [firstId],
        profileId: profile.id,
        selectedBy: 'selector',
        inclusionStatus: 'MANDATORY',
      );
      expect(strengthened.created, 0);
      expect(strengthened.existing, 1);
      expect(strengthened.originsAdded, 0);
      await client.selectArtifacts(
        [firstId],
        profileId: profile.id,
        selectedBy: 'selector',
        inclusionStatus: 'OPTIONAL',
      );
      final selectedRow = (await database.query(
        'profile_artifacts',
        columns: ['inclusion_status'],
        where: 'profile_id = ? AND artifact_id = ?',
        whereArgs: [profile.id, firstId],
      )).single;
      expect(selectedRow['inclusion_status'], 'MANDATORY');

      await expectLater(
        client.selectArtifacts([], profileId: profile.id),
        throwsArgumentError,
      );
      await expectLater(
        client.selectArtifacts(
          [secondId],
          profileId: profile.id,
          inclusionStatus: 'REQUIRED',
        ),
        throwsArgumentError,
      );
      await expectLater(
        client.selectArtifacts([
          secondId,
          'missing-artifact',
        ], profileId: profile.id),
        throwsA(isA<StateError>()),
      );
      expect(
        await database.query(
          'profile_artifacts',
          where: 'profile_id = ? AND artifact_id = ?',
          whereArgs: [profile.id, secondId],
        ),
        isEmpty,
      );
    },
  );

  test(
    'real SQLite dashboard and assessment preserve profile-scoped state',
    () async {
      final active = await client.createProfile(
        name: 'Unrelated active profile',
        activate: true,
      );
      final requested = await client.createProfile(
        name: 'Dashboard proof profile',
      );
      final database = await DatabaseHelper.instance.database;
      final reference = (await database.query(
        'security_artifacts',
        columns: [
          'id',
          'title_en',
          'definition_short_en',
          'source',
          'source_document',
        ],
        orderBy: 'id',
        limit: 1,
      )).single;
      final artifactId = reference['id'] as String;
      await database.update(
        'security_artifacts',
        {'title_ar': 'عنوان عربي لعنصر الاختبار'},
        where: 'id = ?',
        whereArgs: [artifactId],
      );
      await client.selectArtifacts(
        [artifactId],
        profileId: requested.id,
        selectedBy: 'dashboard-test',
      );

      final initialDetail = await client.profileArtifact(
        artifactId,
        profileId: requested.id,
      );
      expect(initialDetail.artifact.titleEn, reference['title_en']);
      expect(initialDetail.artifact.titleAr, 'عنوان عربي لعنصر الاختبار');
      expect(
        initialDetail.artifact.definitionShortEn,
        reference['definition_short_en'],
      );
      expect(initialDetail.artifact.source, reference['source']);
      expect(
        initialDetail.artifact.sourceDocument,
        reference['source_document'],
      );

      final initialDashboard = await client.dashboard(profileId: requested.id);
      expect(initialDashboard.profile.id, requested.id);
      expect(initialDashboard.profile.id, isNot(active.id));
      expect(initialDashboard.counts.totalItems, 1);
      expect(initialDashboard.counts.applicableItems, 1);
      expect(initialDashboard.counts.notApplied, 1);
      expect(initialDashboard.counts.openGaps, 1);
      expect(initialDashboard.gaps, hasLength(1));
      expect(initialDashboard.gaps.single.artifactId, artifactId);
      expect(initialDashboard.gaps.single.titleAr, 'عنوان عربي لعنصر الاختبار');
      expect(initialDashboard.score.formulaVersion, 'profile-score-v1');
      expect(initialDashboard.score.totalControls, 1);
      expect(initialDashboard.recommendations, hasLength(1));
      expect(
        initialDashboard.recommendations.single.reasonCodes,
        contains(anyOf('dependencies:ready', 'dependencies:blocked')),
      );

      final assessed = await client.assessArtifact(
        artifactId,
        profileId: requested.id,
        assessorName: '  accountable assessor  ',
        implementationStatus: 'STS-PARTIAL',
        verificationStatus: 'VER-FAIL',
        effectiveness: 'EFF-LOW',
        currentMaturityLevel: 'MANAGED',
        assignedOwner: 'Security owner',
        dueDate: '2000-01-01',
        notes: 'Profile-specific implementation note',
        priorityOverride: 'PRI-LOW',
        reviewFrequencyOverride: 'MONTHLY',
        score: 42,
        comments: 'Snapshot comment',
      );
      expect(assessed.assessment.assessorName, 'accountable assessor');
      expect(assessed.assessment.score, 42);
      expect(assessed.artifact.implementationStatus, 'STS-PARTIAL');
      expect(assessed.artifact.verificationStatus, 'VER-FAIL');
      expect(assessed.artifact.effectiveness, 'EFF-LOW');
      expect(assessed.artifact.currentMaturityLevel, 'MANAGED');
      expect(assessed.artifact.assignedOwner, 'Security owner');
      expect(assessed.artifact.dueDate, '2000-01-01');
      expect(assessed.artifact.notes, 'Profile-specific implementation note');
      expect(assessed.artifact.priorityOverride, 'PRI-LOW');
      expect(assessed.artifact.effectivePriority, 'PRI-LOW');
      expect(assessed.artifact.reviewFrequencyOverride, 'MONTHLY');
      expect(assessed.artifact.effectiveReviewFrequency, 'MONTHLY');

      final assessedDashboard = await client.dashboard(profileId: requested.id);
      expect(assessedDashboard.counts.implementedPartial, 1);
      expect(assessedDashboard.counts.notApplied, 0);
      expect(assessedDashboard.counts.verifiedFail, 1);
      expect(assessedDashboard.counts.openGaps, 1);
      expect(assessedDashboard.counts.overdueItems, 1);
      expect(assessedDashboard.score.overall, 50);
      expect(assessedDashboard.score.assessedControls, 1);
      expect(assessedDashboard.score.verifiedFail, 1);
      expect(assessedDashboard.score.effectivenessKnownCount, 1);
      expect(assessedDashboard.gaps.single.priority, 'PRI-LOW');
      expect(assessedDashboard.reviewQueue, hasLength(1));
      expect(assessedDashboard.reviewQueue.single.artifactId, artifactId);

      final cleared = await client.assessArtifact(
        artifactId,
        profileId: requested.id,
        assessorName: 'state clearer',
        clearAssignedOwner: true,
        clearDueDate: true,
        clearNotes: true,
        clearPriorityOverride: true,
        clearReviewFrequencyOverride: true,
      );
      expect(cleared.artifact.assignedOwner, isNull);
      expect(cleared.artifact.dueDate, isNull);
      expect(cleared.artifact.notes, isNull);
      expect(cleared.artifact.priorityOverride, isNull);
      expect(cleared.artifact.reviewFrequencyOverride, isNull);
      expect(cleared.artifact.currentMaturityLevel, 'MANAGED');
      final detailAfterClear = await client.profileArtifact(
        artifactId,
        profileId: requested.id,
      );
      expect(detailAfterClear.assessments, hasLength(2));

      await expectLater(
        client.assessArtifact(
          artifactId,
          profileId: requested.id,
          assessorName: '   ',
        ),
        throwsArgumentError,
      );
      await expectLater(
        client.assessArtifact(
          artifactId,
          profileId: requested.id,
          assessorName: 'auditor',
          score: 101,
        ),
        throwsArgumentError,
      );
    },
  );
}
