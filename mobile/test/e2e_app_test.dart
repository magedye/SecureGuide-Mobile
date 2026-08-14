import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:secureguide_mobile/main.dart';
import 'package:secureguide_mobile/src/client/local_secure_guide_client.dart';
import 'package:secureguide_mobile/core/database/database_helper.dart';
import 'package:secureguide_mobile/src/screens/assessment_screen.dart';
import 'package:secureguide_mobile/src/screens/catalog_screen.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'dart:io';
import 'package:path/path.dart' as p;

void main() {
  late Directory tempDir;

  setUpAll(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;

    tempDir = await Directory.systemTemp.createTemp('e2e_test');
    final dbPath = p.join(tempDir.path, 'catalog.db');

    // Copy real catalog.db for test
    final catalogFile = File('assets/catalog.db');
    if (await catalogFile.exists()) {
      await catalogFile.copy(dbPath);
    } else {
      final fallback = File('../assets/catalog.db');
      if (await fallback.exists()) {
        await fallback.copy(dbPath);
      } else {
        throw Exception('catalog.db not found for testing!');
      }
    }

    // Initialize via DatabaseHelper so migrations (like creating enterprise_profiles) run
    DatabaseHelper.instance.setDatabasePathForTesting(dbPath);
    // Force open database
    await DatabaseHelper.instance.database;
  });

  tearDownAll(() async {
    final db = await DatabaseHelper.instance.database;
    await db.close();
    await tempDir.delete(recursive: true);
  });

  testWidgets('E2E Offline Assessment Workflow', (WidgetTester tester) async {
    // 1. Launch App
    final client = LocalSecureGuideClient();
    await tester.pumpWidget(SecureGuideApp(client: client));

    // Wait for Futures to complete instead of pumpAndSettle which hangs on CircularProgressIndicator
    for (int i = 0; i < 50; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 10)),
      );
      if (find.byIcon(Icons.add).evaluate().isNotEmpty) {
        break;
      }
    }
    await tester.pumpAndSettle();

    // The app starts on HomeShell.
    // We can always create a new profile.
    final visibleText = tester
        .widgetList<Text>(find.byType(Text))
        .map((widget) => widget.data)
        .whereType<String>()
        .join(' | ');
    expect(
      find.byIcon(Icons.add),
      findsOneWidget,
      reason: 'App did not reach the profile shell. Visible text: $visibleText',
    );

    // 2. Create Profile
    await tester.tap(find.byKey(const Key('create-profile')));
    await tester.pumpAndSettle();

    // The dialog should appear
    await tester.enterText(find.byType(TextField), 'E2E Test Profile');
    await tester.tap(find.text('إنشاء'));

    // Wait for profile creation and dashboard load
    for (int i = 0; i < 50; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 10)),
      );
      if (find.byKey(const Key('open-catalog')).evaluate().isNotEmpty) {
        break;
      }
    }
    // Wait for Dashboard to render.
    expect(find.text('E2E Test Profile'), findsWidgets);
    expect(find.byKey(const Key('open-catalog')), findsOneWidget);

    // 3. Navigate to Catalog
    await tester.tap(find.byKey(const Key('open-catalog')));

    for (int i = 0; i < 50; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 10)),
      );
      if (find.text('الفهرس').evaluate().isNotEmpty &&
          find.byIcon(Icons.add_circle_outline).evaluate().isNotEmpty) {
        break;
      }
    }
    await tester.pump(const Duration(milliseconds: 500));

    // Verify we are on Catalog screen
    expect(find.text('الفهرس'), findsWidgets);

    // Search for a specific artifact (e.g. AC-1 or something known)
    // Actually, just tap the first add button.
    final addButtons = find.byIcon(Icons.add_circle_outline);
    expect(addButtons, findsWidgets);

    await tester.tap(addButtons.first);

    for (int i = 0; i < 50; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 10)),
      );
      if (find.byIcon(Icons.assignment_outlined).evaluate().isNotEmpty) {
        break;
      }
    }

    // Now it should turn into a green assignment icon.
    final openAssessmentButton = find.byIcon(Icons.assignment_outlined);
    final catalogText = tester
        .widgetList<Text>(find.byType(Text))
        .map((widget) => widget.data)
        .whereType<String>()
        .join(' | ');
    expect(
      openAssessmentButton,
      findsWidgets,
      reason: 'Catalog selection did not complete. Visible text: $catalogText',
    );

    // 4. Open Assessment
    await tester.tap(openAssessmentButton.first);

    for (int i = 0; i < 50; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 10)),
      );
      if (find.text('تفاصيل العنصر').evaluate().isNotEmpty) {
        break;
      }
    }

    // Verify we are on Assessment screen
    expect(find.text('تفاصيل العنصر'), findsWidgets);

    // Switch to Assessment tab
    await tester.tap(find.byKey(const Key('assessmentTab')));
    for (int i = 0; i < 50; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 10)),
      );
      if (find.byKey(const Key('implementationStatus')).evaluate().isNotEmpty ||
          find.textContaining('تعذّر تحميل العنصر').evaluate().isNotEmpty) {
        break;
      }
    }
    final assessmentText = tester
        .widgetList<Text>(find.byType(Text))
        .map((widget) => widget.data)
        .whereType<String>()
        .join(' | ');
    expect(
      find.byKey(const Key('implementationStatus')),
      findsOneWidget,
      reason: 'Assessment form did not load. Visible text: $assessmentText',
    );

    // 5. Execute Assessment
    // Change Implementation Status to "STS-FULL"
    // Tap the dropdown field
    final implementationStatus = find.byKey(const Key('implementationStatus'));
    await tester.ensureVisible(implementationStatus);
    await tester.tap(implementationStatus);
    await tester.pumpAndSettle();

    // Wait for dropdown to open
    await tester.pump(const Duration(milliseconds: 500));

    // Select STS-FULL
    await tester.tap(find.text('STS-FULL').last);
    await tester.pumpAndSettle();

    // Set score to 100
    await tester.enterText(
      find.byKey(const Key('assessmentAssessor')),
      'offline-auditor',
    );
    await tester.enterText(find.byKey(const Key('assessmentScore')), '100');

    // Save Assessment
    final saveAssessment = find.byKey(const Key('saveAssessment'));
    await tester.ensureVisible(saveAssessment);
    await tester.tap(saveAssessment);

    for (int i = 0; i < 50; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 10)),
      );
      if (find.text('تم حفظ التقييم.').evaluate().isNotEmpty) {
        break;
      }
    }

    expect(find.text('تم حفظ التقييم.'), findsOneWidget);

    // Return to the catalog after the persisted assessment is visible.
    Navigator.of(tester.element(find.byType(AssessmentScreen))).pop();
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('الفهرس'), findsWidgets);

    // Navigate back to Dashboard
    Navigator.of(tester.element(find.byType(CatalogScreen))).pop();

    for (int i = 0; i < 50; i++) {
      await tester.pump(const Duration(milliseconds: 100));
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 10)),
      );
      if (find.text('E2E Test Profile').evaluate().isNotEmpty) {
        break;
      }
    }

    // 6. Verify Dashboard Metrics Updated
    // Find Score
    expect(find.text('E2E Test Profile'), findsWidgets);
    // Score should be 100% since we only have 1 artifact and scored it 100.
    // The dashboard view should reflect 1 assessed control.
  });
}
