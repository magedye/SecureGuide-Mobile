import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:secureguide_mobile/read_model_contract.dart';
import 'package:secureguide_mobile/src/screens/assessment_screen.dart';

import 'support/fake_secure_guide_client.dart';

void main() {
  testWidgets('loads, saves, and appends a governed assessment', (
    tester,
  ) async {
    final profileArtifact = ProfileArtifactView.fromJson(
      loadGolden('profile_artifact'),
    );
    final client = FakeSecureGuideClient(
      dashboardView: DashboardView.fromJson(loadGolden('dashboard')),
      profiles: ProfilesView.fromJson(loadGolden('profiles')).profiles,
      profileArtifactView: profileArtifact,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: AssessmentScreen(
          client: client,
          profileId: 'P-HQ',
          artifactId: 'A-IDENTITY',
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Identity governance'), findsOneWidget);
    expect(find.byIcon(Icons.lock_outline), findsOneWidget);
    final verticalScroll = find.byType(Scrollable).first;

    final implementation = find.byType(DropdownButtonFormField<String>).at(0);
    await tester.tap(implementation);
    await tester.pumpAndSettle();
    await tester.tap(find.text('STS-PARTIAL').last);
    await tester.pumpAndSettle();

    final verification = find.byType(DropdownButtonFormField<String>).at(1);
    await tester.tap(verification);
    await tester.pumpAndSettle();
    await tester.tap(find.text('VER-FAIL').last);
    await tester.pumpAndSettle();

    final assessor = find.byKey(const Key('assessmentAssessor'));
    await tester.scrollUntilVisible(assessor, 300, scrollable: verticalScroll);
    await tester.enterText(assessor, 'mobile-auditor');
    final score = find.byKey(const Key('assessmentScore'));
    await tester.scrollUntilVisible(score, 300, scrollable: verticalScroll);
    await tester.enterText(score, '55');

    final save = find.byKey(const Key('saveAssessment'));
    await tester.scrollUntilVisible(save, 300, scrollable: verticalScroll);
    await tester.tap(save);
    await tester.pumpAndSettle();

    expect(client.lastAssessment?.assessorName, 'mobile-auditor');
    expect(client.lastAssessment?.implementationStatus, 'STS-PARTIAL');
    expect(client.lastAssessment?.verificationStatus, 'VER-FAIL');
    expect(client.lastAssessment?.score, 55);
    expect(find.text('تم حفظ التقييم.'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const Key('assessmentHistory')),
      300,
      scrollable: verticalScroll,
    );
    expect(find.text('سجل التقييمات (2)'), findsOneWidget);
  });

  testWidgets('validates assessor and score before writing', (tester) async {
    final client = FakeSecureGuideClient(
      dashboardView: DashboardView.fromJson(loadGolden('dashboard')),
      profiles: ProfilesView.fromJson(loadGolden('profiles')).profiles,
      profileArtifactView: ProfileArtifactView.fromJson(
        loadGolden('profile_artifact'),
      ),
    );
    await tester.pumpWidget(
      MaterialApp(
        home: AssessmentScreen(
          client: client,
          profileId: 'P-HQ',
          artifactId: 'A-IDENTITY',
        ),
      ),
    );
    await tester.pumpAndSettle();

    final verticalScroll = find.byType(Scrollable).first;
    final assessor = find.byKey(const Key('assessmentAssessor'));
    await tester.scrollUntilVisible(assessor, 300, scrollable: verticalScroll);
    await tester.enterText(assessor, '');
    final score = find.byKey(const Key('assessmentScore'));
    await tester.scrollUntilVisible(score, 300, scrollable: verticalScroll);
    await tester.enterText(score, '101');
    final save = find.byKey(const Key('saveAssessment'));
    await tester.scrollUntilVisible(save, 300, scrollable: verticalScroll);
    await tester.tap(save);
    await tester.pump();

    expect(find.text('اسم المقيّم مطلوب'), findsOneWidget);
    expect(find.text('أدخل درجة بين 0 و100'), findsOneWidget);
    expect(client.lastAssessment, isNull);
  });
}
