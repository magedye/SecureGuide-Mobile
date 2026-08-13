import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  setUpAll(() {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  });

  test(
    'bundled database copy can be opened with foreign keys enabled',
    () async {
      final tempDir = await Directory.systemTemp.createTemp('secureguide-db-');
      addTearDown(() => tempDir.delete(recursive: true));
      final copiedPath = p.join(tempDir.path, 'catalog.db');
      await File('assets/catalog.db').copy(copiedPath);

      final db = await databaseFactory.openDatabase(
        copiedPath,
        options: OpenDatabaseOptions(
          onConfigure: (database) async {
            await database.execute('PRAGMA foreign_keys = ON');
          },
        ),
      );
      addTearDown(db.close);

      final tables = await db.query(
        'sqlite_master',
        where: 'type = ?',
        whereArgs: ['table'],
      );
      expect(
        tables.any((table) => table['name'] == 'enterprise_profiles'),
        isTrue,
      );
      expect((await db.rawQuery('PRAGMA foreign_keys')).single.values.first, 1);
    },
  );
}
