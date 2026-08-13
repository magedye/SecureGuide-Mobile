import 'package:sqflite/sqflite.dart';
import '../../../core/database/database_helper.dart';

class ProfileReportData {
  const ProfileReportData({
    required this.profileName,
    required this.date,
    required this.totalArtifacts,
    required this.implemented,
    required this.pending,
    required this.exceptions,
    required this.domainBreakdown,
    required this.artifactDetails,
  });

  final String profileName;
  final String date;
  final int totalArtifacts;
  final int implemented;
  final int pending;
  final int exceptions;
  final List<Map<String, dynamic>> domainBreakdown;
  final List<Map<String, dynamic>> artifactDetails;

  Map<String, dynamic> toJson() => {
    'profileName': profileName,
    'generatedAt': date,
    'summary': {
      'totalArtifacts': totalArtifacts,
      'implemented': implemented,
      'pending': pending,
      'exceptions': exceptions,
    },
    'domainBreakdown': domainBreakdown,
    'artifactDetails': artifactDetails,
  };
}

class ReportGenerator {
  ReportGenerator({Future<Database>? database})
    : _db = database ?? DatabaseHelper.instance.database;

  final Future<Database> _db;

  Future<ProfileReportData> generateReport(
    String profileId, {
    bool omitDrafts = true,
  }) async {
    final db = await _db;

    // Fetch profile details
    final profileRows = await db.query(
      'enterprise_profiles',
      where: 'id = ?',
      whereArgs: [profileId],
    );
    final profileName = profileRows.isNotEmpty
        ? profileRows.first['name'] as String
        : 'Unknown Profile';

    final visibilityClause = omitDrafts
        ? " AND artifact_id IN ("
              "SELECT id FROM security_artifacts "
              "WHERE publication_status NOT IN ('DRAFT', 'UNDER_REVIEW')"
              ")"
        : '';

    final summaryRows = await db.rawQuery(
      '''
      SELECT
        COUNT(*) AS total_items,
        SUM(CASE WHEN implementation_status = 'STS-FULL' THEN 1 ELSE 0 END)
          AS implemented_full,
        SUM(CASE
          WHEN exception_status NOT IN ('EXC-NOT-APPLICABLE', 'EXC-UNAVAILABLE')
           AND implementation_status <> 'STS-FULL'
          THEN 1 ELSE 0 END) AS open_gaps,
        SUM(CASE WHEN exception_status <> 'EXC-NONE' THEN 1 ELSE 0 END)
          AS with_exception
      FROM v_profile_operational_items
      WHERE profile_id = ?$visibilityClause
    ''',
      [profileId],
    );
    final summary = summaryRows.single;
    final total = (summary['total_items'] as num?)?.toInt() ?? 0;
    final implemented = (summary['implemented_full'] as num?)?.toInt() ?? 0;
    final pending = (summary['open_gaps'] as num?)?.toInt() ?? 0;
    final exceptions = (summary['with_exception'] as num?)?.toInt() ?? 0;

    // Fetch domain breakdown
    final domainRows = await db.rawQuery(
      '''
      SELECT primary_domain,
             COUNT(*) AS total,
             SUM(CASE WHEN implementation_status = 'STS-FULL' THEN 1 ELSE 0 END)
               AS imp
      FROM v_profile_operational_items
      WHERE profile_id = ?$visibilityClause
      GROUP BY primary_domain
      ORDER BY primary_domain ASC
    ''',
      [profileId],
    );

    // Fetch artifact details
    final artifactQuery =
        'SELECT * FROM v_profile_operational_items '
        'WHERE profile_id = ?$visibilityClause '
        'ORDER BY primary_domain ASC, effective_priority ASC';

    final artifacts = await db.rawQuery(artifactQuery, [profileId]);

    return ProfileReportData(
      profileName: profileName,
      date: DateTime.now().toUtc().toIso8601String(),
      totalArtifacts: total,
      implemented: implemented,
      pending: pending,
      exceptions: exceptions,
      domainBreakdown: domainRows,
      artifactDetails: artifacts,
    );
  }
}
