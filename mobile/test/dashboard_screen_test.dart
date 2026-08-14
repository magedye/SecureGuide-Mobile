/// Widget-level proof of the vertical slice: the app shell picks the active
/// profile and renders its dashboard, and the create-profile flow takes the
/// governed write path — all driven by an in-memory fake fed from the SAME
/// golden fixtures the contract is pinned to. No running sidecar needed.
library;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:secureguide_mobile/core/localization/locale_controller.dart';
import 'package:secureguide_mobile/main.dart';
import 'package:secureguide_mobile/read_model_contract.dart';

import 'support/fake_secure_guide_client.dart';

FakeSecureGuideClient _client() => FakeSecureGuideClient(
  dashboardView: DashboardView.fromJson(loadGolden('dashboard')),
  profiles: ProfilesView.fromJson(loadGolden('profiles')).profiles,
);

void main() {
  testWidgets('shell shows the active profile and renders its dashboard', (
    tester,
  ) async {
    await tester.pumpWidget(
      SecureGuideApp(
        client: _client(),
        localeController: LocaleController(initialLocale: const Locale('ar')),
      ),
    );
    await tester.pumpAndSettle();

    // Active profile from the profiles golden surfaces in the app bar.
    expect(find.text('المقر الرئيسي'), findsWidgets);

    // Dashboard content from the dashboard golden.
    expect(find.text('At Risk'), findsOneWidget); // band chip
    expect(find.text('33.3%'), findsOneWidget); // overall score
    expect(find.text('Security logging'), findsOneWidget); // an open gap
    expect(find.text('الفجوات المفتوحة'), findsOneWidget); // a stat tile label
    expect(find.text('الفجوات المفتوحة (2)'), findsOneWidget); // section title
  });

  testWidgets('creating a profile calls the write path and surfaces it', (
    tester,
  ) async {
    final client = _client();
    await tester.pumpWidget(
      SecureGuideApp(
        client: client,
        localeController: LocaleController(initialLocale: const Locale('ar')),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.add)); // the create-profile FAB
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'فرع جدة');
    await tester.tap(find.text('إنشاء'));
    await tester.pumpAndSettle();

    expect(client.lastCreated?.name, 'فرع جدة');
    expect(find.text('فرع جدة'), findsWidgets); // now the app bar title
  });

  testWidgets('dashboard header has no overflow on a narrow Arabic viewport', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(393, 852);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      SecureGuideApp(
        client: _client(),
        localeController: LocaleController(initialLocale: const Locale('ar')),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('33.3%'), findsOneWidget);
    expect(find.byIcon(Icons.picture_as_pdf), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
