/// Widget-level proof of the catalog slice: the screen lists catalog items with
/// the profile's selection overlay, and adding an unselected artifact takes the
/// governed `selectArtifacts` write path, after which the row reflects it.
library;

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:secureguide_mobile/l10n/app_localizations.dart';
import 'package:secureguide_mobile/read_model_contract.dart';
import 'package:secureguide_mobile/src/screens/catalog_screen.dart';

import 'support/fake_secure_guide_client.dart';

void main() {
  testWidgets('lists catalog items and selecting an unselected one writes', (
    tester,
  ) async {
    final catalog = loadGolden('catalog');
    final client = FakeSecureGuideClient(
      dashboardView: DashboardView.fromJson(loadGolden('dashboard')),
      profiles: ProfilesView.fromJson(loadGolden('profiles')).profiles,
      catalogItems: (catalog['items'] as List).cast<Map<String, dynamic>>(),
    );

    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('ar'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: CatalogScreen(client: client, profileId: 'P-HQ'),
      ),
    );
    await tester.pumpAndSettle();

    // The one artifact the demo workflow never selected (A-POLICY) is the only
    // row offering an add button.
    expect(find.text('Security policy'), findsOneWidget);
    expect(find.byIcon(Icons.add_circle_outline), findsOneWidget);

    await tester.tap(find.byIcon(Icons.add_circle_outline));
    await tester.pump(); // run _select through the write + setState
    await tester.pumpAndSettle(); // settle the catalog reload

    // The governed write ran and the row now reflects the new selection.
    expect(client.lastSelected, contains('A-POLICY'));
    expect(find.byIcon(Icons.add_circle_outline), findsNothing);
    expect(find.byIcon(Icons.assignment_outlined), findsWidgets);

    await tester.tap(find.text('Security policy'));
    await tester.pumpAndSettle();
    expect(find.text('تفاصيل العنصر'), findsOneWidget);
    expect(find.text('Security policy'), findsOneWidget);
  });

  testWidgets('catalog filters follow the active English locale', (
    tester,
  ) async {
    final catalog = loadGolden('catalog');
    final client = FakeSecureGuideClient(
      dashboardView: DashboardView.fromJson(loadGolden('dashboard')),
      profiles: ProfilesView.fromJson(loadGolden('profiles')).profiles,
      catalogItems: (catalog['items'] as List).cast<Map<String, dynamic>>(),
    );

    await tester.pumpWidget(
      MaterialApp(
        locale: const Locale('en'),
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: CatalogScreen(client: client, profileId: 'P-HQ'),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.filter_list));
    await tester.pumpAndSettle();

    expect(find.text('Catalog filters'), findsOneWidget);
    expect(find.text('Artifact type'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Sub-domain'),
      300,
      scrollable: find.byType(Scrollable).last,
    );
    expect(find.text('Sub-domain'), findsOneWidget);
    expect(find.text('Clear'), findsOneWidget);
    expect(find.text('Apply'), findsOneWidget);
  });
}
