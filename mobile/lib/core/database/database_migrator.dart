import 'dart:isolate';

import 'package:sqlite3/sqlite3.dart';

import 'generated_migrations.dart';

final class DatabaseMigrationException implements Exception {
  const DatabaseMigrationException(this.message);

  final String message;

  @override
  String toString() => 'DatabaseMigrationException: $message';
}

final class DatabaseMigrator {
  const DatabaseMigrator._();

  static int get latestVersion => int.parse(embeddedMigrations.last.version);

  static Future<List<String>> migrate(
    String databasePath, {
    List<EmbeddedMigration> migrations = embeddedMigrations,
  }) => Isolate.run(() => _migrateSync(databasePath, migrations));

  static Future<void> validate(String databasePath) =>
      Isolate.run(() => _validateSync(databasePath));

  static List<String> _migrateSync(
    String databasePath,
    List<EmbeddedMigration> migrations,
  ) {
    if (migrations.isEmpty) {
      throw const DatabaseMigrationException('migration bundle is empty');
    }

    final database = sqlite3.open(databasePath);
    final applied = <String>[];
    try {
      database
        ..execute('PRAGMA foreign_keys = ON')
        ..execute('PRAGMA busy_timeout = 30000');

      final migrationTable = database.select(
        "SELECT 1 FROM sqlite_master "
        "WHERE type = 'table' AND name = 'schema_migrations'",
      );
      if (migrationTable.isEmpty) {
        throw const DatabaseMigrationException(
          'schema_migrations is missing; refusing an untraceable upgrade',
        );
      }

      for (final migration in migrations) {
        final exists = database.select(
          'SELECT 1 FROM schema_migrations WHERE version = ?',
          [migration.version],
        );
        if (exists.isNotEmpty) {
          continue;
        }

        database.execute('BEGIN IMMEDIATE');
        try {
          database.execute(migration.sql);
          final recorded = database.select(
            'SELECT 1 FROM schema_migrations WHERE version = ?',
            [migration.version],
          );
          if (recorded.isEmpty) {
            throw DatabaseMigrationException(
              '${migration.filename} did not record its schema version',
            );
          }
          database.execute('COMMIT');
          applied.add(migration.version);
        } catch (_) {
          if (!database.autocommit) {
            database.execute('ROLLBACK');
          }
          rethrow;
        }
      }

      database.userVersion = int.parse(migrations.last.version);
      _validateOpenDatabase(database);
      return applied;
    } finally {
      database.close();
    }
  }

  static void _validateSync(String databasePath) {
    final database = sqlite3.open(databasePath, mode: OpenMode.readOnly);
    try {
      _validateOpenDatabase(database);
    } finally {
      database.close();
    }
  }

  static void _validateOpenDatabase(Database database) {
    final integrity = database
        .select('PRAGMA integrity_check')
        .single
        .values
        .first;
    if (integrity != 'ok') {
      throw DatabaseMigrationException('integrity_check failed: $integrity');
    }
    final foreignKeyIssues = database.select('PRAGMA foreign_key_check');
    if (foreignKeyIssues.isNotEmpty) {
      throw DatabaseMigrationException(
        'foreign_key_check found ${foreignKeyIssues.length} issue(s)',
      );
    }
    const requiredTables = {
      'schema_migrations',
      'security_artifacts',
      'enterprise_profiles',
      'profile_artifacts',
      'profile_assessments',
      'profile_evidence',
      'profile_exceptions',
      'application_state',
    };
    final tables = database
        .select("SELECT name FROM sqlite_master WHERE type='table'")
        .map((row) => row['name'] as String)
        .toSet();
    final missing = requiredTables.difference(tables);
    if (missing.isNotEmpty) {
      throw DatabaseMigrationException(
        'required tables missing: ${missing.join(',')}',
      );
    }
    final singleton = database
        .select(
          'SELECT COUNT(*) AS n FROM application_state WHERE singleton_id=1',
        )
        .single['n'];
    if (singleton != 1) {
      throw const DatabaseMigrationException(
        'application_state singleton is missing',
      );
    }
  }
}
