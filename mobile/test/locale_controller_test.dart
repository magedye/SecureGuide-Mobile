import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:secureguide_mobile/core/localization/locale_controller.dart';
import 'package:secureguide_mobile/main.dart';
import 'package:secureguide_mobile/read_model_contract.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

import 'support/fake_secure_guide_client.dart';

final class MemoryLocalePreferenceStore implements LocalePreferenceStore {
  MemoryLocalePreferenceStore(this.value);

  String? value;

  @override
  Future<String?> read() async => value;

  @override
  Future<void> write(String languageCode) async {
    value = languageCode;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tempDirectory;
  late Database database;
  late SqliteLocalePreferenceStore store;

  setUpAll(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    tempDirectory = await Directory.systemTemp.createTemp('locale-controller-');
    final databasePath = p.join(tempDirectory.path, 'catalog.db');
    await File('assets/catalog.db').copy(databasePath);
    database = await databaseFactory.openDatabase(databasePath);
    store = SqliteLocalePreferenceStore(database: Future.value(database));
  });

  tearDownAll(() async {
    await database.close();
    await tempDirectory.delete(recursive: true);
  });

  testWidgets('language toggle persists and drives RTL and LTR layouts', (
    tester,
  ) async {
    final client = FakeSecureGuideClient(
      dashboardView: DashboardView.fromJson(loadGolden('dashboard')),
      profiles: const <ProfileSummary>[],
    );
    final memoryStore = MemoryLocalePreferenceStore('ar');
    final controller = LocaleController(store: memoryStore);
    await controller.load();
    expect(controller.locale.languageCode, 'ar');

    await tester.pumpWidget(
      SecureGuideApp(client: client, localeController: controller),
    );
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    final toggle = find.byKey(const Key('locale-toggle'));
    expect(toggle, findsOneWidget);
    expect(find.text('لا توجد ملفات مؤسسية بعد.'), findsOneWidget);
    expect(Directionality.of(tester.element(toggle)), TextDirection.rtl);

    await tester.tap(toggle);
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    expect(find.text('No enterprise profiles yet.'), findsOneWidget);
    expect(Directionality.of(tester.element(toggle)), TextDirection.ltr);
    expect(memoryStore.value, 'en');

    final reloaded = LocaleController(store: memoryStore);
    await reloaded.load();
    expect(reloaded.locale.languageCode, 'en');
    await tester.pumpWidget(const SizedBox.shrink());
    reloaded.dispose();
    controller.dispose();
  });

  test('SQLite rejects locale values outside the controlled list', () async {
    await store.write('en');
    await expectLater(
      database.update('application_state', {
        'locale': 'fr',
      }, where: 'singleton_id = 1'),
      throwsA(anything),
    );
    expect(await store.read(), 'en');
  });
}
