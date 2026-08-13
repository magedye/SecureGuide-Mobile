import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider_platform_interface/path_provider_platform_interface.dart';
import 'package:plugin_platform_interface/plugin_platform_interface.dart';
import 'package:secureguide_mobile/src/client/evidence_manager.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

final class MockPathProviderPlatform extends Fake
    with MockPlatformInterfaceMixin
    implements PathProviderPlatform {
  MockPathProviderPlatform(this.temporaryPath);

  final String temporaryPath;

  @override
  Future<String?> getApplicationDocumentsPath() async => temporaryPath;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory temporaryDirectory;
  late Database database;
  late EvidenceManager manager;

  setUpAll(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    temporaryDirectory = await Directory.systemTemp.createTemp(
      'evidence-manager-',
    );
    PathProviderPlatform.instance = MockPathProviderPlatform(
      temporaryDirectory.path,
    );
    final databasePath = p.join(temporaryDirectory.path, 'catalog.db');
    await File('assets/catalog.db').copy(databasePath);
    database = await databaseFactory.openDatabase(
      databasePath,
      options: OpenDatabaseOptions(
        onConfigure: (db) => db.execute('PRAGMA foreign_keys=ON'),
      ),
    );
    final artifactId =
        (await database.query(
              'security_artifacts',
              columns: ['id'],
              limit: 1,
            )).single['id']
            as String;
    await database.insert('enterprise_profiles', {
      'id': 'PRF-TEST',
      'name': 'Evidence profile',
    });
    await database.insert('enterprise_profiles', {
      'id': 'PRF-OTHER',
      'name': 'Other profile',
    });
    await database.insert('profile_artifacts', {
      'id': 'PA-123',
      'profile_id': 'PRF-TEST',
      'artifact_id': artifactId,
    });
    manager = EvidenceManager(database: Future.value(database));
  });

  tearDownAll(() async {
    await database.close();
    await temporaryDirectory.delete(recursive: true);
  });

  test('add, safely preview, verify, corrupt, and delete evidence', () async {
    final source = File(p.join(temporaryDirectory.path, 'source.txt'));
    await source.writeAsString('Hello Evidence!');

    final record = await manager.addEvidence(
      profileArtifactId: 'PA-123',
      profileId: 'PRF-TEST',
      evidenceType: 'DOCUMENT',
      file: source,
      collectedBy: 'offline-auditor',
      description: 'Test document',
    );

    expect(record.fileSize, 15);
    expect(record.contentHash, hasLength(64));
    expect(record.collectedBy, 'offline-auditor');
    expect(record.mimeType, 'text/plain');
    expect(
      await manager.verifyEvidence(record.id, profileId: 'PRF-TEST'),
      EvidenceIntegrity.valid,
    );
    final preview = await manager.loadPreview(record.id, profileId: 'PRF-TEST');
    expect(preview.text, 'Hello Evidence!');

    await expectLater(
      manager.verifyEvidence(record.id, profileId: 'PRF-OTHER'),
      throwsA(isA<StateError>()),
    );

    final savedFile = File(record.evidenceUrl!);
    await savedFile.writeAsString('Corrupted Evidence!');
    expect(
      await manager.verifyEvidence(record.id, profileId: 'PRF-TEST'),
      EvidenceIntegrity.corrupted,
    );
    await expectLater(
      manager.loadPreview(record.id, profileId: 'PRF-TEST'),
      throwsA(isA<StateError>()),
    );

    await manager.deleteEvidence(record.id, profileId: 'PRF-TEST');
    expect(
      await manager.getEvidenceForArtifact('PA-123', profileId: 'PRF-TEST'),
      isEmpty,
    );
    expect(await savedFile.exists(), isFalse);
  });

  test(
    'unsafe profile identifiers and oversized metadata are rejected',
    () async {
      final source = File(p.join(temporaryDirectory.path, 'small.txt'));
      await source.writeAsString('safe');
      await expectLater(
        manager.addEvidence(
          profileArtifactId: 'PA-123',
          profileId: '../escape',
          evidenceType: 'DOCUMENT',
          file: source,
          collectedBy: 'auditor',
        ),
        throwsA(isA<ArgumentError>()),
      );
      await expectLater(
        manager.addEvidence(
          profileArtifactId: 'PA-123',
          profileId: 'PRF-TEST',
          evidenceType: 'NOT-CONTROLLED',
          file: source,
          collectedBy: 'auditor',
        ),
        throwsA(isA<ArgumentError>()),
      );
    },
  );
}
