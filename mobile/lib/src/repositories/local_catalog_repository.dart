import 'package:sqflite/sqflite.dart';

import '../../read_model_contract.dart';

/// Profile-aware, read-only catalog access for the standalone SQLite runtime.
final class LocalCatalogRepository {
  const LocalCatalogRepository(this._db);

  final Database _db;

  Future<CatalogView> search(
    CatalogFilter filter, {
    required String locale,
    required bool selectedOnly,
    required int limit,
    required int offset,
  }) async {
    var profileId = filter.profileId ?? '';
    if (profileId.isEmpty) {
      final active = await _db.rawQuery(
        'SELECT profile_id FROM v_active_profile_context LIMIT 1',
      );
      if (active.isNotEmpty) {
        profileId = active.first['profile_id'] as String? ?? '';
      }
    }

    final normalizedLocale = locale.toLowerCase().startsWith('ar')
        ? 'ar'
        : 'en';
    final preferredTitle = normalizedLocale == 'ar'
        ? "COALESCE(NULLIF(loc.title,''),NULLIF(a.title_ar,''),a.title_en)"
        : "COALESCE(NULLIF(loc.title,''),NULLIF(a.title_en,''),a.title_ar)";
    final preferredShort = normalizedLocale == 'ar'
        ? "COALESCE(NULLIF(loc.definition_short,''),NULLIF(a.definition_short_ar,''),a.definition_short_en)"
        : "COALESCE(NULLIF(loc.definition_short,''),NULLIF(a.definition_short_en,''),a.definition_short_ar)";
    const effectivePriority =
        'COALESCE(pa.priority_override,pa.template_priority_default,a.priority)';

    var sql =
        '''
      SELECT a.id,a.type,$preferredTitle AS localized_title,
             $preferredShort AS localized_definition_short,
             a.primary_domain,a.sub_domain,a.source,a.source_document,
             a.obligation_level,a.testability,a.ai_review_status,
             a.publication_status,$effectivePriority AS effective_priority,
             pa.id AS profile_artifact_id,pa.inclusion_status,
             pa.implementation_status,pa.verification_status,
             pa.effectiveness,pa.exception_status,pa.assigned_owner,pa.due_date,
             (SELECT COUNT(*) FROM profile_evidence evidence
               WHERE evidence.profile_artifact_id=pa.id) AS evidence_count
        FROM security_artifacts a
        LEFT JOIN artifact_localizations loc
          ON loc.artifact_id=a.id AND loc.locale=?
        LEFT JOIN profile_artifacts pa
          ON pa.artifact_id=a.id AND pa.profile_id=?
    ''';
    final args = <Object?>[normalizedLocale, profileId];
    final predicates = <String>[
      'a.is_active=1',
      "a.publication_status IN ('APPROVED','PUBLISHED')",
    ];

    final query = filter.searchQuery?.trim();
    if (query != null && query.isNotEmpty) {
      final needle = '%${query.toLowerCase()}%';
      predicates.add('''(
        lower($preferredTitle) LIKE ?
        OR lower(COALESCE($preferredShort,'')) LIKE ?
        OR lower(COALESCE(a.source_document,'')) LIKE ?
        OR lower(a.id) LIKE ?
        OR EXISTS (
          SELECT 1 FROM artifact_tags tag
           WHERE tag.artifact_id=a.id AND lower(tag.tag_value) LIKE ?
        )
      )''');
      args.addAll([needle, needle, needle, needle, needle]);
    }

    _appendListFilter(predicates, args, 'a.type', filter.types);
    _appendListFilter(
      predicates,
      args,
      'a.primary_domain',
      filter.primaryDomains,
    );
    _appendListFilter(predicates, args, 'a.sub_domain', filter.subDomains);
    _appendListFilter(predicates, args, effectivePriority, filter.priorities);
    if (filter.testability?.isNotEmpty == true) {
      predicates.add('a.testability=?');
      args.add(filter.testability);
    }
    if (filter.implementationStatus?.isNotEmpty == true) {
      predicates.add('pa.implementation_status=?');
      args.add(filter.implementationStatus);
    }
    if (selectedOnly) predicates.add('pa.id IS NOT NULL');

    final safeLimit = limit.clamp(1, 500);
    final safeOffset = offset < 0 ? 0 : offset;
    sql += ' WHERE ${predicates.join(' AND ')}';
    sql += ' ORDER BY $preferredTitle,a.id LIMIT ? OFFSET ?';
    args.addAll([safeLimit, safeOffset]);

    final rows = await _db.rawQuery(sql, args);
    final items = rows.map(_mapItem).toList(growable: false);
    return CatalogView(
      locale: normalizedLocale,
      query: query,
      limit: safeLimit,
      offset: safeOffset,
      count: items.length,
      items: items,
    );
  }

  static void _appendListFilter(
    List<String> predicates,
    List<Object?> args,
    String column,
    List<String>? values,
  ) {
    if (values == null || values.isEmpty) return;
    predicates.add("$column IN (${List.filled(values.length, '?').join(',')})");
    args.addAll(values);
  }

  static CatalogItem _mapItem(Map<String, Object?> row) => CatalogItem(
    id: row['id'] as String?,
    type: row['type'] as String?,
    title: row['localized_title'] as String?,
    definitionShort: row['localized_definition_short'] as String?,
    primaryDomain: row['primary_domain'] as String?,
    subDomain: row['sub_domain'] as String?,
    source: row['source'] as String?,
    sourceDocument: row['source_document'] as String?,
    obligationLevel: row['obligation_level'] as String?,
    testability: row['testability'] as String?,
    aiReviewStatus: row['ai_review_status'] as String?,
    publicationStatus: row['publication_status'] as String?,
    effectivePriority: row['effective_priority'] as String?,
    isSelected: row['profile_artifact_id'] != null,
    profileArtifactId: row['profile_artifact_id'] as String?,
    inclusionStatus: row['inclusion_status'] as String?,
    implementationStatus: row['implementation_status'] as String?,
    verificationStatus: row['verification_status'] as String?,
    effectiveness: row['effectiveness'] as String?,
    exceptionStatus: row['exception_status'] as String?,
    assignedOwner: row['assigned_owner'] as String?,
    dueDate: row['due_date'] as String?,
    evidenceCount: row['evidence_count'] as num?,
  );
}
