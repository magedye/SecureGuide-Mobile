import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:secureguide_mobile/core/database/database_helper.dart';
import 'package:secureguide_mobile/src/client/local_secure_guide_client.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tempDirectory;
  late LocalSecureGuideClient client;

  setUpAll(() async {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
    tempDirectory = await Directory.systemTemp.createTemp(
      'template-application-',
    );
    final databasePath = p.join(tempDirectory.path, 'catalog.db');
    await File('assets/catalog.db').copy(databasePath);
    DatabaseHelper.instance.setDatabasePathForTesting(databasePath);
    client = LocalSecureGuideClient();
    await DatabaseHelper.instance.database;
  });

  tearDownAll(() async {
    final database = await DatabaseHelper.instance.database;
    await database.close();
    await tempDirectory.delete(recursive: true);
  });

  test(
    'template application is transactional, traceable, and idempotent',
    () async {
      final profile = await client.createProfile(name: 'Template target');
      final database = await DatabaseHelper.instance.database;
      final template = (await database.query('templates')).single;
      final templateId = template['id'] as String;

      final firstTemplateItem = (await database.query(
        'template_items',
        where: 'template_id = ?',
        whereArgs: [templateId],
        orderBy: 'id',
        limit: 1,
      )).single;
      final firstArtifact = (await database.query(
        'security_artifacts',
        columns: ['definition_short_en'],
        where: 'id = ?',
        whereArgs: [firstTemplateItem['artifact_id']],
      )).single;
      final templateView = await client.templateItems(templateId);
      expect(
        templateView.items.first.definitionShort,
        firstArtifact['definition_short_en'],
      );
      await client.selectArtifacts(
        [firstTemplateItem['artifact_id'] as String],
        profileId: profile.id,
        selectedBy: 'manual-selector',
        inclusionStatus: 'OPTIONAL',
        selectionReason: 'Selected before applying the template',
      );

      await client.applyTemplate(
        profile.id!,
        templateId,
        appliedBy: 'release-reviewer',
      );
      await client.applyTemplate(
        profile.id!,
        templateId,
        appliedBy: 'release-reviewer',
      );

      expect(
        await database.query(
          'profile_templates',
          where: 'profile_id = ?',
          whereArgs: [profile.id],
        ),
        hasLength(1),
      );
      expect(
        await database.query(
          'profile_artifacts',
          where: 'profile_id = ?',
          whereArgs: [profile.id],
        ),
        hasLength(4),
      );
      final origins = await database.rawQuery(
        '''SELECT o.*,pt.template_version,pt.applied_by
           FROM profile_artifact_origins o
           JOIN profile_artifacts pa ON pa.id=o.profile_artifact_id
           LEFT JOIN profile_templates pt ON pt.id=o.profile_template_id
          WHERE pa.profile_id=?''',
        [profile.id],
      );
      expect(
        origins.where((row) => row['origin_type'] == 'TEMPLATE'),
        hasLength(4),
      );
      expect(
        origins.where((row) => row['origin_type'] == 'MANUAL'),
        hasLength(1),
      );
      expect(
        origins.where((row) => row['origin_type'] == 'TEMPLATE'),
        everyElement(
          allOf(
            containsPair('template_version', template['version']),
            containsPair('applied_by', 'release-reviewer'),
          ),
        ),
      );
      expect(
        await database.query('v_profile_origin_governance_issues'),
        isEmpty,
      );

      final defaults = await database.query(
        'profile_artifacts',
        where: 'profile_id = ?',
        whereArgs: [profile.id],
      );
      expect(
        defaults,
        everyElement(
          allOf(
            containsPair('template_priority_default', isNotNull),
            containsPair('template_review_frequency_default', isNotNull),
          ),
        ),
      );
      final preselected = defaults.singleWhere(
        (row) => row['artifact_id'] == firstTemplateItem['artifact_id'],
      );
      expect(preselected['template_item_id'], firstTemplateItem['id']);
      expect(
        preselected['inclusion_status'],
        firstTemplateItem['inclusion_status'],
      );
    },
  );

  test('same template applied to another profile remains isolated', () async {
    final database = await DatabaseHelper.instance.database;
    final templateId =
        (await database.query('templates', columns: ['id'])).single['id']
            as String;
    final other = await client.createProfile(name: 'Other target');

    await client.applyTemplate(
      other.id!,
      templateId,
      appliedBy: 'other-reviewer',
    );

    final rows = await database.query(
      'profile_artifacts',
      where: 'profile_id = ?',
      whereArgs: [other.id],
    );
    expect(rows, hasLength(4));
    expect(
      await database.rawQuery(
        '''SELECT COUNT(*) AS n
             FROM profile_artifact_origins o
             JOIN profile_artifacts pa ON pa.id=o.profile_artifact_id
            WHERE pa.profile_id=? AND o.selected_by='other-reviewer' ''',
        [other.id],
      ),
      contains(containsPair('n', 4)),
    );
  });

  test('invalid profile rolls back without application history', () async {
    final database = await DatabaseHelper.instance.database;
    final templateId =
        (await database.query('templates', columns: ['id'])).single['id']
            as String;

    await expectLater(
      client.applyTemplate(
        'missing-profile',
        templateId,
        appliedBy: 'reviewer',
      ),
      throwsA(isA<StateError>()),
    );
    expect(
      await database.query(
        'profile_templates',
        where: 'profile_id = ?',
        whereArgs: ['missing-profile'],
      ),
      isEmpty,
    );
  });
}
