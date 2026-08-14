import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:secureguide_mobile/core/database/catalog_content_upgrader.dart';
import 'package:secureguide_mobile/core/database/database_migrator.dart';
import 'package:sqlite3/sqlite3.dart';

void main() {
  late Directory temporaryDirectory;
  late String installedPath;
  late String candidatePath;

  setUp(() async {
    temporaryDirectory = await Directory.systemTemp.createTemp(
      'secureguide-catalog-upgrade-',
    );
    installedPath = p.join(temporaryDirectory.path, 'installed.db');
    candidatePath = p.join(temporaryDirectory.path, 'candidate.db');
    await File(p.join('..', 'catalog.db')).copy(installedPath);
    await File(p.join('assets', 'catalog.db')).copy(candidatePath);
    await DatabaseMigrator.migrate(installedPath);
    await DatabaseMigrator.migrate(candidatePath);
    _seedOperationalData(installedPath);
  });

  tearDown(() async {
    if (await temporaryDirectory.exists()) {
      await temporaryDirectory.delete(recursive: true);
    }
  });

  test(
    'catalog upgrade preserves profiles, assessments, evidence, and exceptions',
    () async {
      final result = await CatalogContentUpgrader.upgrade(
        installedPath,
        candidatePath,
      );
      expect(result.applied, isTrue);
      expect(result.oldArtifactCount, 4);
      expect(result.newArtifactCount, 1218);
      expect(result.operationalSnapshotAfter, result.operationalSnapshotBefore);

      final database = sqlite3.open(installedPath, mode: OpenMode.readOnly);
      final candidate = sqlite3.open(candidatePath, mode: OpenMode.readOnly);
      try {
        expect(_count(database, 'enterprise_profiles'), 2);
        expect(_count(database, 'profile_artifacts'), 3);
        expect(_count(database, 'profile_assessments'), 1);
        expect(_count(database, 'profile_evidence'), 1);
        expect(_count(database, 'profile_exceptions'), 1);
        expect(
          database
              .select(
                'SELECT active_profile_id FROM application_state '
                'WHERE singleton_id=1',
              )
              .single['active_profile_id'],
          'P2',
        );
        expect(_count(database, 'raw_artifacts'), 4265);
        expect(_count(database, 'staging_artifacts'), 0);
        expect(
          _count(database, 'external_references'),
          _count(candidate, 'external_references'),
        );
        expect(
          database.select('PRAGMA integrity_check').single.values.first,
          'ok',
        );
        expect(database.select('PRAGMA foreign_key_check'), isEmpty);
      } finally {
        candidate.close();
        database.close();
      }
    },
  );

  test(
    'stable-ID conflict rolls back without changing operational rows',
    () async {
      final candidate = sqlite3.open(candidatePath);
      candidate.execute(
        "UPDATE security_artifacts SET type='ART-STD' WHERE id='SG-CTR-AI-02'",
      );
      candidate.close();

      await expectLater(
        CatalogContentUpgrader.upgrade(installedPath, candidatePath),
        throwsA(
          isA<CatalogContentUpgradeException>().having(
            (error) => error.message,
            'message',
            contains('stable-ID'),
          ),
        ),
      );
      final database = sqlite3.open(installedPath, mode: OpenMode.readOnly);
      try {
        expect(_count(database, 'security_artifacts'), 4);
        expect(_count(database, 'enterprise_profiles'), 2);
        expect(_count(database, 'profile_assessments'), 1);
        expect(_count(database, 'profile_evidence'), 1);
        expect(_count(database, 'profile_exceptions'), 1);
      } finally {
        database.close();
      }
    },
  );

  test('historical artifact alias remaps an installed profile reference', () async {
    final candidate = sqlite3.open(candidatePath, mode: OpenMode.readOnly);
    late final String oldId;
    late final String currentId;
    try {
      final alias = candidate
          .select(
            'SELECT old_artifact_id,artifact_id FROM catalog_artifact_id_aliases '
            "WHERE artifact_id NOT IN ('SG-CTR-AI-02','SG-CTR-AI-05','SG-REQ-AI-06') "
            'ORDER BY old_artifact_id LIMIT 1',
          )
          .single;
      oldId = alias['old_artifact_id'] as String;
      currentId = alias['artifact_id'] as String;
    } finally {
      candidate.close();
    }

    final installed = sqlite3.open(installedPath);
    try {
      final columns = installed
          .select('PRAGMA table_info(security_artifacts)')
          .map((row) => row['name'] as String)
          .toList();
      final insertColumns = columns.map((column) => '"$column"').join(',');
      final selectColumns = columns
          .map((column) => column == 'id' ? '?' : '"$column"')
          .join(',');
      installed.execute(
        'INSERT INTO security_artifacts($insertColumns) '
        'SELECT $selectColumns FROM security_artifacts WHERE id=?',
        [oldId, 'SG-CTR-AI-02'],
      );
      installed.execute(
        'INSERT INTO profile_artifacts(id,profile_id,artifact_id) VALUES(?,?,?)',
        ['PA-ALIAS', 'P2', oldId],
      );
    } finally {
      installed.close();
    }

    final result = await CatalogContentUpgrader.upgrade(
      installedPath,
      candidatePath,
    );
    expect(result.applied, isTrue);
    expect(result.operationalSnapshotAfter, result.operationalSnapshotBefore);
    final verified = sqlite3.open(installedPath, mode: OpenMode.readOnly);
    try {
      expect(
        verified
            .select(
              "SELECT artifact_id FROM profile_artifacts WHERE id='PA-ALIAS'",
            )
            .single['artifact_id'],
        currentId,
      );
      expect(
        verified.select('SELECT 1 FROM security_artifacts WHERE id=?', [oldId]),
        isEmpty,
      );
      expect(verified.select('PRAGMA foreign_key_check'), isEmpty);
    } finally {
      verified.close();
    }
  });
}

int _count(Database database, String table) =>
    database.select('SELECT COUNT(*) AS n FROM "$table"').single['n'] as int;

void _seedOperationalData(String databasePath) {
  final database = sqlite3.open(databasePath);
  try {
    database
      ..execute('PRAGMA foreign_keys=ON')
      ..execute(
        "INSERT INTO enterprise_profiles(id,name,profile_kind) VALUES"
        "('P1','Head Office','organization'),('P2','Cloud Audit','audit')",
      )
      ..execute(
        "UPDATE application_state SET active_profile_id='P2' "
        'WHERE singleton_id=1',
      )
      ..execute(
        'INSERT INTO profile_artifacts('
        'id,profile_id,artifact_id,implementation_status,verification_status,effectiveness) '
        'VALUES(?,?,?,?,?,?)',
        ['PA1', 'P1', 'SG-CTR-AI-02', 'STS-FULL', 'VER-PASS', 'EFF-HIGH'],
      )
      ..execute(
        'INSERT INTO profile_artifacts(id,profile_id,artifact_id) VALUES(?,?,?)',
        ['PA2', 'P1', 'SG-CTR-AI-05'],
      )
      ..execute(
        'INSERT INTO profile_artifacts(id,profile_id,artifact_id) VALUES(?,?,?)',
        ['PA3', 'P2', 'SG-REQ-AI-06'],
      )
      ..execute(
        'INSERT INTO profile_assessments('
        'id,profile_artifact_id,assessor_name,score,implementation_status,'
        'verification_status,effectiveness,comments) VALUES(?,?,?,?,?,?,?,?)',
        [
          'AS1',
          'PA1',
          'auditor',
          100,
          'STS-FULL',
          'VER-PASS',
          'EFF-HIGH',
          'Verified',
        ],
      )
      ..execute(
        'INSERT INTO profile_evidence('
        'id,profile_artifact_id,assessment_id,evidence_type,description,'
        'collected_by,content_hash) VALUES(?,?,?,?,?,?,?)',
        [
          'EV1',
          'PA1',
          'AS1',
          'REPORT',
          'Quarterly verification',
          'auditor',
          'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
        ],
      )
      ..execute(
        'INSERT INTO profile_exceptions('
        'id,profile_artifact_id,exception_status,justification) VALUES(?,?,?,?)',
        ['EX1', 'PA2', 'EXC-DEFERRED', 'Scheduled remediation window.'],
      );
  } finally {
    database.close();
  }
}
