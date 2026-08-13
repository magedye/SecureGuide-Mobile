import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:secureguide_mobile/read_model_contract.dart';
import 'package:secureguide_mobile/src/repositories/local_catalog_repository.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tempDirectory;
  late Database database;
  late LocalCatalogRepository repository;

  setUpAll(() async {
    sqfliteFfiInit();
    tempDirectory = await Directory.systemTemp.createTemp('catalog-filter-');
    final path = p.join(tempDirectory.path, 'catalog.db');
    await File('assets/catalog.db').copy(path);
    database = await databaseFactoryFfi.openDatabase(
      path,
      options: OpenDatabaseOptions(
        onConfigure: (db) => db.execute('PRAGMA foreign_keys=ON'),
      ),
    );
    repository = LocalCatalogRepository(database);

    await database.insert('artifact_localizations', {
      'artifact_id': 'SG-CTR-AI-02',
      'locale': 'ar',
      'is_primary': 0,
      'title': 'اختبار جرد الأصول العربي',
      'definition_short': 'تعريف عربي قابل للبحث',
      'content_maturity': 'MINIMAL',
      'content_review_status': 'NOT_REVIEWED',
    });
    await database.insert('enterprise_profiles', {
      'id': 'PROFILE-CATALOG',
      'name': 'Catalog filter profile',
    });
    await database.insert('profile_artifacts', {
      'id': 'PA-CATALOG',
      'profile_id': 'PROFILE-CATALOG',
      'artifact_id': 'SG-CTR-AI-02',
      'priority_override': 'PRI-CRITICAL',
    });
  });

  tearDownAll(() async {
    await database.close();
    await tempDirectory.delete(recursive: true);
  });

  test(
    'search selects the requested locale and searches localized content',
    () async {
      final arabic = await repository.search(
        const CatalogFilter(searchQuery: 'تعريف عربي'),
        locale: 'ar',
        selectedOnly: false,
        limit: 100,
        offset: 0,
      );
      expect(arabic.locale, 'ar');
      expect(arabic.items, hasLength(1));
      expect(arabic.items.single.title, 'اختبار جرد الأصول العربي');

      final english = await repository.search(
        const CatalogFilter(searchQuery: 'Asset Inventory Currency'),
        locale: 'en',
        selectedOnly: false,
        limit: 100,
        offset: 0,
      );
      expect(
        english.items.single.title,
        'Asset Inventory Currency Maintenance',
      );
    },
  );

  test('sub-domain filtering uses the controlled SDT code', () async {
    final view = await repository.search(
      const CatalogFilter(subDomains: ['SD-08.05']),
      locale: 'en',
      selectedOnly: false,
      limit: 100,
      offset: 0,
    );

    expect(view.items, isNotEmpty);
    expect(view.items.map((item) => item.id), contains('SG-POL-AI-08'));
    expect(view.items.every((item) => item.subDomain == 'SD-08.05'), isTrue);
  });

  test(
    'priority and selection filters use the active profile overlay',
    () async {
      final view = await repository.search(
        const CatalogFilter(
          profileId: 'PROFILE-CATALOG',
          priorities: ['PRI-CRITICAL'],
        ),
        locale: 'en',
        selectedOnly: true,
        limit: 100,
        offset: 0,
      );

      expect(view.items, hasLength(1));
      expect(view.items.single.id, 'SG-CTR-AI-02');
      expect(view.items.single.isSelected, isTrue);
      expect(view.items.single.effectivePriority, 'PRI-CRITICAL');
    },
  );
}
