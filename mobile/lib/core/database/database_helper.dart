import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/services.dart' show rootBundle;
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';

import 'catalog_content_upgrader.dart';
import 'database_migrator.dart';

final class DatabaseRestoreResult {
  const DatabaseRestoreResult({
    required this.recoveryPath,
    required this.appliedMigrations,
  });

  final String recoveryPath;
  final List<String> appliedMigrations;
}

class DatabaseHelper {
  static const String _databaseName = "catalog.db";
  static int get _databaseVersion => DatabaseMigrator.latestVersion;

  DatabaseHelper._privateConstructor();
  static final DatabaseHelper instance = DatabaseHelper._privateConstructor();

  static Database? _database;

  static String? _testPath;

  void setDatabaseForTesting(Database db) {
    _database = db;
  }

  void setDatabasePathForTesting(String path) {
    _testPath = path;
  }

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDatabase();
    return _database!;
  }

  Future<Database> _initDatabase() async {
    String path;
    if (_testPath != null) {
      path = _testPath!;
    } else {
      Directory documentsDirectory = await getApplicationDocumentsDirectory();
      path = join(documentsDirectory.path, _databaseName);
    }

    // Check if the database exists
    bool exists = await databaseExists(path);

    if (!exists) {
      // Should happen only the first time you launch your application
      // print("Creating new copy from asset");

      // Make sure the parent directory exists
      try {
        await Directory(dirname(path)).create(recursive: true);
      } catch (_) {}

      // Copy from asset
      ByteData data = await rootBundle.load(join("assets", _databaseName));
      List<int> bytes = data.buffer.asUint8List(
        data.offsetInBytes,
        data.lengthInBytes,
      );

      // Write and flush the bytes written
      await File(path).writeAsBytes(bytes, flush: true);
      await DatabaseMigrator.migrate(path);
    } else {
      final stamp = DateTime.now().toUtc().microsecondsSinceEpoch;
      final candidatePath = '$path.catalog-candidate-$stamp';
      final recoveryPath = '$path.pre-catalog-upgrade-$stamp';
      final candidate = File(candidatePath);
      final recovery = File(recoveryPath);
      try {
        // Flutter asset keys always use POSIX separators, including on Windows.
        final data = await rootBundle.load('assets/$_databaseName');
        final bytes = data.buffer.asUint8List(
          data.offsetInBytes,
          data.lengthInBytes,
        );
        await candidate.writeAsBytes(bytes, flush: true);
        await File(path).copy(recoveryPath);
        await DatabaseMigrator.migrate(path);
        await DatabaseMigrator.migrate(candidatePath);
        await CatalogContentUpgrader.upgrade(path, candidatePath);
        await DatabaseMigrator.validate(path);
        if (await recovery.exists()) await recovery.delete();
      } catch (_) {
        // A failure before the recovery copy exists must never remove the
        // user's live database. Once the copy exists, restore it atomically on
        // the same filesystem after discarding the partially upgraded file.
        if (await recovery.exists()) {
          final live = File(path);
          if (await live.exists()) await live.delete();
          await recovery.rename(path);
        }
        rethrow;
      } finally {
        if (await candidate.exists()) await candidate.delete();
      }
    }

    // Open the migrated database through the asynchronous application driver.
    return await openDatabase(
      path,
      version: _databaseVersion,
      onConfigure: _onConfigure,
    );
  }

  Future _onConfigure(Database db) async {
    // Enable foreign keys
    await db.execute('PRAGMA foreign_keys = ON');
  }

  Future<String> _resolvedDatabasePath() async {
    if (_testPath != null) return _testPath!;
    final documentsDirectory = await getApplicationDocumentsDirectory();
    return join(documentsDirectory.path, _databaseName);
  }

  /// Securely copies the current catalog and profile data to [targetPath].
  /// SECURITY WARNING: The caller is responsible for ensuring [targetPath]
  /// is an authorized, non-world-readable directory or provided securely
  /// by the user (e.g., via the system Share sheet or scoped storage).
  /// Do not export to public external storage directories without explicit intent.
  Future<void> backupDatabase(String targetPath) async {
    final sourcePath = await _resolvedDatabasePath();
    if (normalize(absolute(sourcePath)) == normalize(absolute(targetPath))) {
      throw ArgumentError.value(
        targetPath,
        'targetPath',
        'matches live database',
      );
    }
    final db = await database;
    await db.rawQuery('PRAGMA wal_checkpoint(FULL)');
    await db.close();
    _database = null;

    try {
      await File(sourcePath).copy(targetPath);
      await DatabaseMigrator.validate(targetPath);
    } finally {
      _database = await _initDatabase();
    }
  }

  Future<DatabaseRestoreResult> restoreDatabase(String sourcePath) async {
    final source = File(sourcePath);
    if (!await source.exists()) {
      throw ArgumentError.value(sourcePath, 'sourcePath', 'does not exist');
    }
    final targetPath = await _resolvedDatabasePath();
    if (normalize(absolute(sourcePath)) == normalize(absolute(targetPath))) {
      throw ArgumentError.value(
        sourcePath,
        'sourcePath',
        'matches live database',
      );
    }
    final stamp = DateTime.now().toUtc().microsecondsSinceEpoch;
    final stagingPath = '$targetPath.restore-staging-$stamp';
    final recoveryPath = '$targetPath.pre-restore-$stamp';
    await source.copy(stagingPath);

    late final List<String> appliedMigrations;
    try {
      appliedMigrations = await DatabaseMigrator.migrate(stagingPath);
      await DatabaseMigrator.validate(stagingPath);
    } catch (_) {
      final staging = File(stagingPath);
      if (await staging.exists()) await staging.delete();
      rethrow;
    }

    if (_database != null) {
      await _database!.close();
      _database = null;
    }

    final target = File(targetPath);
    try {
      if (await target.exists()) await target.rename(recoveryPath);
      await File(stagingPath).rename(targetPath);
      _database = await _initDatabase();
      return DatabaseRestoreResult(
        recoveryPath: recoveryPath,
        appliedMigrations: appliedMigrations,
      );
    } catch (_) {
      if (_database != null) {
        await _database!.close();
        _database = null;
      }
      if (await target.exists()) await target.delete();
      final recovery = File(recoveryPath);
      if (await recovery.exists()) await recovery.rename(targetPath);
      final staging = File(stagingPath);
      if (await staging.exists()) await staging.delete();
      _database = await _initDatabase();
      rethrow;
    }
  }
}
