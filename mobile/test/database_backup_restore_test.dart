import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:secureguide_mobile/core/database/database_helper.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory temporaryDirectory;
  late String livePath;

  setUpAll(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    temporaryDirectory = await Directory.systemTemp.createTemp(
      'database-backup-restore-',
    );
    livePath = p.join(temporaryDirectory.path, 'catalog.db');
    await File('assets/catalog.db').copy(livePath);
    DatabaseHelper.instance.setDatabasePathForTesting(livePath);
    await DatabaseHelper.instance.database;
  });

  tearDownAll(() async {
    final database = await DatabaseHelper.instance.database;
    await database.close();
    await temporaryDirectory.delete(recursive: true);
  });

  test(
    'validated backup restores atomically and preserves recovery copy',
    () async {
      var database = await DatabaseHelper.instance.database;
      await database.insert('enterprise_profiles', {
        'id': 'PROFILE-BACKUP',
        'name': 'State inside backup',
      });
      final backupPath = p.join(temporaryDirectory.path, 'verified-backup.db');
      await DatabaseHelper.instance.backupDatabase(backupPath);

      database = await DatabaseHelper.instance.database;
      await database.update(
        'enterprise_profiles',
        {'name': 'State after backup'},
        where: 'id = ?',
        whereArgs: ['PROFILE-BACKUP'],
      );

      final result = await DatabaseHelper.instance.restoreDatabase(backupPath);
      database = await DatabaseHelper.instance.database;
      expect(
        (await database.query(
          'enterprise_profiles',
          columns: ['name'],
          where: 'id = ?',
          whereArgs: ['PROFILE-BACKUP'],
        )).single['name'],
        'State inside backup',
      );
      expect(await File(result.recoveryPath).exists(), isTrue);
      expect(await File(backupPath).exists(), isTrue);
      expect(result.appliedMigrations, isEmpty);
    },
  );

  test(
    'invalid restore is rejected before live database replacement',
    () async {
      final invalidPath = p.join(temporaryDirectory.path, 'invalid.db');
      await File(invalidPath).writeAsString('not a sqlite database');

      await expectLater(
        DatabaseHelper.instance.restoreDatabase(invalidPath),
        throwsA(anything),
      );
      final database = await DatabaseHelper.instance.database;
      expect(
        (await database.query(
          'enterprise_profiles',
          columns: ['name'],
          where: 'id = ?',
          whereArgs: ['PROFILE-BACKUP'],
        )).single['name'],
        'State inside backup',
      );
    },
  );
}
