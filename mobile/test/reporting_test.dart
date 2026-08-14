import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:secureguide_mobile/src/core/reporting/pdf_exporter.dart';
import 'package:secureguide_mobile/src/core/reporting/report_exporter.dart';
import 'package:secureguide_mobile/src/core/reporting/report_generator.dart';
import 'package:secureguide_mobile/src/screens/report_preview_screen.dart';
import 'package:secureguide_mobile/l10n/app_localizations.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  sqfliteFfiInit();

  late Database database;

  setUp(() async {
    database = await databaseFactoryFfi.openDatabase(inMemoryDatabasePath);
    await database.execute('''
      CREATE TABLE enterprise_profiles(id TEXT PRIMARY KEY, name TEXT NOT NULL);
      CREATE TABLE security_artifacts(
        id TEXT PRIMARY KEY,
        publication_status TEXT NOT NULL
      );
      CREATE TABLE v_profile_operational_items(
        profile_artifact_id TEXT,
        profile_id TEXT,
        artifact_id TEXT,
        primary_domain TEXT,
        title_en TEXT,
        title_ar TEXT,
        implementation_status TEXT,
        verification_status TEXT,
        exception_status TEXT,
        effective_priority TEXT
      );
    ''');
    await database.insert('enterprise_profiles', {
      'id': 'P-1',
      'name': '<script>alert(1)</script>',
    });
    await database.insert('security_artifacts', {
      'id': 'A-PUBLISHED',
      'publication_status': 'APPROVED',
    });
    await database.insert('security_artifacts', {
      'id': 'A-DRAFT',
      'publication_status': 'DRAFT',
    });
    await database.insert('v_profile_operational_items', {
      'profile_artifact_id': 'PA-1',
      'profile_id': 'P-1',
      'artifact_id': 'A-PUBLISHED',
      'primary_domain': 'SD-03',
      'title_en': 'Identity governance',
      'title_ar': 'حوكمة الهوية',
      'implementation_status': 'STS-FULL',
      'verification_status': 'VER-PASS',
      'exception_status': 'EXC-NONE',
      'effective_priority': 'PRI-HIGH',
    });
    await database.insert('v_profile_operational_items', {
      'profile_artifact_id': 'PA-2',
      'profile_id': 'P-1',
      'artifact_id': 'A-DRAFT',
      'primary_domain': 'SD-04',
      'title_en': 'Draft setting',
      'implementation_status': 'STS-NOT-APPLIED',
      'verification_status': 'VER-NOT-VERIFIED',
      'exception_status': 'EXC-NONE',
      'effective_priority': 'PRI-LOW',
    });
  });

  tearDown(() async {
    await database.close();
  });

  test(
    'report uses controlled states and omits draft catalog artifacts',
    () async {
      final generator = ReportGenerator(database: Future.value(database));

      final report = await generator.generateReport('P-1');
      expect(report.totalArtifacts, 1);
      expect(report.implemented, 1);
      expect(report.pending, 0);
      expect(report.artifactDetails.single['artifact_id'], 'A-PUBLISHED');

      final withDrafts = await generator.generateReport(
        'P-1',
        omitDrafts: false,
      );
      expect(withDrafts.totalArtifacts, 2);
      expect(withDrafts.pending, 1);
    },
  );

  test(
    'JSON and HTML exports are local, structured, and HTML-escaped',
    () async {
      final report = await ReportGenerator(
        database: Future.value(database),
      ).generateReport('P-1');

      final json = jsonDecode(ReportExporter.toJson(report));
      expect(json['summary']['totalArtifacts'], 1);

      final html = ReportExporter.toHtml(report);
      expect(html, contains('<!doctype html>'));
      expect(html, contains('&lt;script&gt;alert(1)&lt;/script&gt;'));
      expect(html, isNot(contains('<script>alert(1)</script>')));

      final englishHtml = ReportExporter.toHtml(report, languageCode: 'en');
      expect(englishHtml, contains('<html lang="en" dir="ltr">'));
      expect(englishHtml, contains('SecureGuide report'));
      expect(englishHtml, contains('Identity governance'));
    },
  );

  test('PDF export uses bundled assets and produces a PDF offline', () async {
    final report = await ReportGenerator(
      database: Future.value(database),
    ).generateReport('P-1');

    final bytes = await PdfExporter.generatePdf(report);
    expect(utf8.decode(bytes.take(4).toList()), '%PDF');
    expect(bytes.length, greaterThan(1000));
  });

  testWidgets('report screen exposes PDF, HTML, and JSON export surfaces', (
    tester,
  ) async {
    const report = ProfileReportData(
      profileName: 'Offline profile',
      date: '2026-08-13T00:00:00Z',
      totalArtifacts: 1,
      implemented: 1,
      pending: 0,
      exceptions: 0,
      domainBreakdown: [],
      artifactDetails: [],
    );
    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: ReportPreviewScreen(
          profileId: 'P-1',
          report: Future<ProfileReportData>.value(report),
        ),
      ),
    );
    await tester.pump();

    expect(find.byKey(const Key('exportReportPdf')), findsOneWidget);
    expect(find.byKey(const Key('exportReportHtml')), findsOneWidget);
    expect(find.byKey(const Key('exportReportJson')), findsOneWidget);
  });
}
