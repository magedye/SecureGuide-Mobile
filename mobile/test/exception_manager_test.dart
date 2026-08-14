import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:secureguide_mobile/src/client/exception_manager.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  sqfliteFfiInit();

  late Directory tempDirectory;
  late Database database;
  late ExceptionManager manager;

  setUp(() async {
    tempDirectory = await Directory.systemTemp.createTemp(
      'secureguide_exception_test_',
    );
    final databasePath = p.join(tempDirectory.path, 'catalog.db');
    await File(p.join('assets', 'catalog.db')).copy(databasePath);
    database = await databaseFactoryFfi.openDatabase(
      databasePath,
      options: OpenDatabaseOptions(
        onConfigure: (db) => db.execute('PRAGMA foreign_keys = ON'),
      ),
    );
    await database.insert('enterprise_profiles', {
      'id': 'P-1',
      'name': 'Test profile',
    });
    await database.insert('profile_artifacts', {
      'id': 'PA-1',
      'profile_id': 'P-1',
      'artifact_id': 'SG-CTR-AI-02',
      'inclusion_status': 'MANDATORY',
    });
    manager = ExceptionManager(database: Future.value(database));
  });

  tearDown(() async {
    await database.close();
    await tempDirectory.delete(recursive: true);
  });

  test(
    'draft and submitted exceptions do not alter active profile state',
    () async {
      final draft = await manager.saveDraft(
        profileArtifactId: 'PA-1',
        exceptionStatus: 'EXC-DEFERRED',
        justification: 'Scheduled remediation',
        expiryDate: '2099-01-01',
      );
      expect(draft.workflowStatus, 'DRAFT');
      await _expectNoActiveException(database);

      final submitted = await manager.submit(draft.id);
      expect(submitted.workflowStatus, 'SUBMITTED');
      await _expectNoActiveException(database);

      final listed = await manager.listForProfile('P-1');
      expect(listed.single['artifact_id'], 'SG-CTR-AI-02');
      expect(listed.single['workflow_status'], 'SUBMITTED');
    },
  );

  test('approval atomically activates the governed exception', () async {
    final draft = await manager.saveDraft(
      profileArtifactId: 'PA-1',
      exceptionStatus: 'EXC-DEFERRED',
      justification: 'Scheduled remediation',
      expiryDate: '2099-01-01',
    );
    await manager.submit(draft.id);

    final approved = await manager.approve(
      draft.id,
      approvedBy: 'security-approver',
    );
    expect(approved.workflowStatus, 'APPROVED');
    expect(approved.approvedBy, 'security-approver');

    final profileArtifact = (await database.query(
      'profile_artifacts',
      where: 'id = ?',
      whereArgs: ['PA-1'],
    )).single;
    expect(profileArtifact['exception_status'], 'EXC-DEFERRED');
    expect(profileArtifact['active_exception_id'], draft.id);
    final governanceCount = await database.rawQuery(
      'SELECT COUNT(*) AS count FROM v_exception_governance_issues',
    );
    expect(governanceCount.single['count'], 0);
    final eventCount = await database.rawQuery(
      'SELECT COUNT(*) AS count FROM profile_exception_events WHERE exception_id = ?',
      [draft.id],
    );
    expect(eventCount.single['count'], 3);
  });

  test('approval fails closed without a future expiry date', () async {
    final draft = await manager.saveDraft(
      profileArtifactId: 'PA-1',
      exceptionStatus: 'EXC-DEFERRED',
      justification: 'Missing expiry',
    );
    await manager.submit(draft.id);

    await expectLater(
      manager.approve(draft.id, approvedBy: 'security-approver'),
      throwsA(isA<StateError>()),
    );
    await _expectNoActiveException(database);
  });
}

Future<void> _expectNoActiveException(Database database) async {
  final profileArtifact = (await database.query(
    'profile_artifacts',
    where: 'id = ?',
    whereArgs: ['PA-1'],
  )).single;
  expect(profileArtifact['exception_status'], 'EXC-NONE');
  expect(profileArtifact['active_exception_id'], isNull);
}
