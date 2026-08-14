import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:secureguide_mobile/core/database/database_migrator.dart';
import 'package:secureguide_mobile/core/database/generated_migrations.dart';
import 'package:sqlite3/sqlite3.dart';

void main() {
  late Directory tempDirectory;
  late String databasePath;

  setUp(() async {
    tempDirectory = await Directory.systemTemp.createTemp(
      'secureguide_migrator_test_',
    );
    databasePath = p.join(tempDirectory.path, 'catalog.db');

    final database = sqlite3.open(databasePath);
    database.execute('''
      CREATE TABLE schema_migrations (
        version TEXT PRIMARY KEY,
        description TEXT NOT NULL
      );
      INSERT INTO schema_migrations(version, description)
      VALUES ('001', 'baseline');
      CREATE TABLE profile_notes (
        id TEXT PRIMARY KEY,
        note TEXT NOT NULL
      );
      INSERT INTO profile_notes(id, note) VALUES ('P-1', 'preserve me');
      CREATE TABLE security_artifacts (id TEXT PRIMARY KEY);
      CREATE TABLE enterprise_profiles (id TEXT PRIMARY KEY);
      CREATE TABLE profile_artifacts (id TEXT PRIMARY KEY);
      CREATE TABLE application_state (
        singleton_id INTEGER PRIMARY KEY,
        profile_id TEXT
      );
      INSERT INTO application_state(singleton_id) VALUES (1);
    ''');
    database.userVersion = 1;
    database.close();
  });

  tearDown(() async {
    await tempDirectory.delete(recursive: true);
  });

  test('applies ordered migrations and preserves operational rows', () async {
    const migrations = <EmbeddedMigration>[
      EmbeddedMigration(
        version: '002',
        filename: '002_add_owner.sql',
        sha256: 'test-only',
        sql: '''
          ALTER TABLE profile_notes ADD COLUMN owner TEXT;
          INSERT INTO schema_migrations(version, description)
          VALUES ('002', 'add owner');
        ''',
      ),
      EmbeddedMigration(
        version: '003',
        filename: '003_add_index.sql',
        sha256: 'test-only',
        sql: '''
          CREATE INDEX idx_profile_notes_owner ON profile_notes(owner);
          INSERT INTO schema_migrations(version, description)
          VALUES ('003', 'add owner index');
        ''',
      ),
    ];

    final applied = await DatabaseMigrator.migrate(
      databasePath,
      migrations: migrations,
    );

    expect(applied, ['002', '003']);
    final database = sqlite3.open(databasePath);
    addTearDown(database.close);
    expect(database.userVersion, 3);
    expect(
      database
          .select("SELECT note FROM profile_notes WHERE id = 'P-1'")
          .single['note'],
      'preserve me',
    );
    expect(
      database
          .select('SELECT version FROM schema_migrations ORDER BY version')
          .map((row) => row['version']),
      ['001', '002', '003'],
    );
  });

  test('rolls back a failed migration including its version marker', () async {
    const migrations = <EmbeddedMigration>[
      EmbeddedMigration(
        version: '002',
        filename: '002_broken.sql',
        sha256: 'test-only',
        sql: '''
          INSERT INTO schema_migrations(version, description)
          VALUES ('002', 'must roll back');
          UPDATE profile_notes SET note = 'must roll back' WHERE id = 'P-1';
          INSERT INTO table_that_does_not_exist(id) VALUES ('x');
        ''',
      ),
    ];

    await expectLater(
      DatabaseMigrator.migrate(databasePath, migrations: migrations),
      throwsA(anything),
    );

    final database = sqlite3.open(databasePath);
    addTearDown(database.close);
    expect(database.userVersion, 1);
    expect(
      database
          .select("SELECT note FROM profile_notes WHERE id = 'P-1'")
          .single['note'],
      'preserve me',
    );
    expect(
      database.select("SELECT 1 FROM schema_migrations WHERE version = '002'"),
      isEmpty,
    );
  });

  test('generated migration bundle matches the canonical SQL files', () async {
    for (final migration in embeddedMigrations) {
      final source = File(p.join('..', 'migrations', migration.filename));
      expect(await source.exists(), isTrue, reason: migration.filename);
      final normalized = (await source.readAsString()).replaceAll('\r\n', '\n');
      expect(migration.sql, normalized, reason: migration.filename);
      expect(
        sha256.convert(utf8.encode(normalized)).toString(),
        migration.sha256,
        reason: migration.filename,
      );
    }
  });

  test('bundled catalog migrates to current and passes SQLite integrity gates',
      () async {
    final bundledPath = p.join('assets', 'catalog.db');
    final bundled = sqlite3.open(bundledPath);
    addTearDown(bundled.close);

    // The production asset is replaced only after a separately qualified
    // candidate passes release gates. A shipped install must therefore prove
    // it can apply every embedded forward migration before it is opened.
    expect(bundled.userVersion, lessThanOrEqualTo(DatabaseMigrator.latestVersion));
    expect(bundled.select('PRAGMA integrity_check').single.values.first, 'ok');
    expect(bundled.select('PRAGMA foreign_key_check'), isEmpty);

    final upgradedPath = p.join(tempDirectory.path, 'bundled-catalog.db');
    await File(bundledPath).copy(upgradedPath);
    await DatabaseMigrator.migrate(upgradedPath);
    final database = sqlite3.open(upgradedPath);
    addTearDown(database.close);

    expect(database.userVersion, DatabaseMigrator.latestVersion);
    expect(
      database
          .select('SELECT MAX(version) AS version FROM schema_migrations')
          .single['version'],
      embeddedMigrations.last.version,
    );
    expect(database.select('PRAGMA integrity_check').single.values.first, 'ok');
    expect(database.select('PRAGMA foreign_key_check'), isEmpty);
    expect(
      database
          .select('SELECT COUNT(*) AS n FROM security_artifacts')
          .single['n'],
      1218,
    );

    const requiredViews = {
      'v_profile_dashboard',
      'v_profile_operational_items',
      'v_blueprint_pattern_enrichments',
    };
    final views = database
        .select("SELECT name FROM sqlite_master WHERE type = 'view'")
        .map((row) => row['name'])
        .toSet();
    expect(views, containsAll(requiredViews));
  });
}
