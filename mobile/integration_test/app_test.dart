import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:secureguide_mobile/core/database/database_helper.dart';
import 'package:secureguide_mobile/main.dart' as app;
import 'package:secureguide_mobile/src/client/evidence_manager.dart';
import 'package:secureguide_mobile/src/client/local_secure_guide_client.dart';

Future<void> _pumpUntil(
  WidgetTester tester,
  Finder finder, {
  int attempts = 120,
}) async {
  for (var attempt = 0; attempt < attempts; attempt++) {
    await tester.pump(const Duration(milliseconds: 100));
    if (finder.evaluate().isNotEmpty) return;
  }
  final visibleText = tester
      .widgetList<Text>(find.byType(Text))
      .map((widget) => widget.data)
      .whereType<String>()
      .join(' | ');
  fail('Timed out waiting for $finder. Visible text: $visibleText');
}

Future<void> _tapWhenReady(WidgetTester tester, Finder finder) async {
  await _pumpUntil(tester, finder);
  await tester.pumpAndSettle();
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pump();
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('complete governed workflow persists without a network runtime', (
    tester,
  ) async {
    final unique = DateTime.now().toUtc().microsecondsSinceEpoch;
    final profileName = 'Offline acceptance $unique';
    debugPrint('OFFLINE_ACCEPTANCE_PROFILE=$profileName');

    app.main();
    await _tapWhenReady(tester, find.byKey(const Key('create-profile')));
    await _pumpUntil(tester, find.byKey(const Key('profile-name')));
    await tester.enterText(find.byKey(const Key('profile-name')), profileName);
    await _tapWhenReady(tester, find.byKey(const Key('create-profile-submit')));
    await _pumpUntil(tester, find.byKey(const Key('open-catalog')));
    expect(find.text(profileName), findsWidgets);

    await _tapWhenReady(tester, find.byKey(const Key('open-catalog')));
    final addArtifact = find.byWidgetPredicate(
      (widget) =>
          widget.key is ValueKey<String> &&
          (widget.key! as ValueKey<String>).value.startsWith('catalog-add-'),
      description: 'first governed catalog add action',
    );
    await _pumpUntil(tester, addArtifact);
    await _tapWhenReady(tester, addArtifact.first);

    final selectedArtifact = find.byWidgetPredicate(
      (widget) =>
          widget is ListTile &&
          widget.key is ValueKey<String> &&
          (widget.key! as ValueKey<String>).value.startsWith('catalog-item-') &&
          widget.onTap != null,
      description: 'selected catalog artifact',
    );
    await _pumpUntil(tester, selectedArtifact);

    // Create and verify evidence before the assessment screen is constructed,
    // so its independently managed evidence tab loads the persisted record.
    final database = await DatabaseHelper.instance.database;
    final profile = (await database.query(
      'enterprise_profiles',
      columns: ['id'],
      where: 'name=?',
      whereArgs: [profileName],
    )).single;
    final profileId = profile['id'] as String;
    final profileArtifact = (await database.query(
      'profile_artifacts',
      columns: ['id'],
      where: 'profile_id=?',
      whereArgs: [profileId],
      limit: 1,
    )).single;
    final profileArtifactId = profileArtifact['id'] as String;
    final temporaryDirectory = await getTemporaryDirectory();
    final evidenceSource = File(
      p.join(temporaryDirectory.path, 'offline-acceptance-$unique.txt'),
    );
    await evidenceSource.writeAsString(
      'SecureGuide offline evidence $unique',
      flush: true,
    );
    final evidence = await EvidenceManager().addEvidence(
      profileArtifactId: profileArtifactId,
      profileId: profileId,
      evidenceType: 'REPORT',
      file: evidenceSource,
      collectedBy: 'offline-device-auditor',
      description: 'Created while the device network was disabled',
    );
    expect(
      await EvidenceManager().verifyEvidence(evidence.id, profileId: profileId),
      EvidenceIntegrity.valid,
    );

    await _tapWhenReady(tester, selectedArtifact.first);
    await _pumpUntil(tester, find.byKey(const Key('assessmentTab')));

    await _tapWhenReady(tester, find.byKey(const Key('assessmentTab')));
    await _pumpUntil(tester, find.byKey(const Key('implementationStatus')));
    await _tapWhenReady(tester, find.byKey(const Key('implementationStatus')));
    final fullStatus = find.text('STS-FULL');
    await _pumpUntil(tester, fullStatus);
    await _tapWhenReady(tester, fullStatus.last);
    await tester.enterText(
      find.byKey(const Key('assessmentAssessor')),
      'offline-device-auditor',
    );
    await tester.enterText(find.byKey(const Key('assessmentScore')), '100');
    FocusManager.instance.primaryFocus?.unfocus();
    await SystemChannels.textInput.invokeMethod<void>('TextInput.hide');
    await tester.pumpAndSettle();
    final save = find.byKey(const Key('saveAssessment'));
    await _tapWhenReady(tester, save);
    await _pumpUntil(tester, find.text('تم حفظ التقييم.'));

    await _tapWhenReady(tester, find.byKey(const Key('evidenceTab')));
    await _pumpUntil(tester, find.text('REPORT'));
    expect(find.byIcon(Icons.verified), findsOneWidget);

    // Recreate the application root. The external acceptance runner additionally
    // force-stops and relaunches the package for process-level restart evidence.
    await tester.pumpWidget(const SizedBox.shrink());
    await tester.pump();
    await tester.pumpWidget(
      app.SecureGuideApp(client: LocalSecureGuideClient()),
    );
    await _pumpUntil(tester, find.text(profileName));

    expect(
      await database.query(
        'profile_assessments',
        where: 'profile_artifact_id=?',
        whereArgs: [profileArtifactId],
      ),
      isNotEmpty,
    );
    expect(
      await database.query(
        'profile_evidence',
        where: 'id=?',
        whereArgs: [evidence.id],
      ),
      hasLength(1),
    );
  });
}
