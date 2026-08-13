import 'dart:convert';
import 'dart:io';
import 'dart:isolate';

import 'package:crypto/crypto.dart';
import 'package:sqlite3/sqlite3.dart';

final class CatalogContentUpgradeException implements Exception {
  const CatalogContentUpgradeException(this.message);

  final String message;

  @override
  String toString() => 'CatalogContentUpgradeException: $message';
}

final class CatalogContentUpgradeResult {
  const CatalogContentUpgradeResult({
    required this.applied,
    required this.candidateSha256,
    required this.oldArtifactCount,
    required this.newArtifactCount,
    required this.operationalSnapshotBefore,
    required this.operationalSnapshotAfter,
  });

  final bool applied;
  final String candidateSha256;
  final int oldArtifactCount;
  final int newArtifactCount;
  final String operationalSnapshotBefore;
  final String operationalSnapshotAfter;
}

final class CatalogContentUpgrader {
  const CatalogContentUpgrader._();

  static const _stableTables = <String>[
    'source_catalogs',
    'source_import_manifests',
    'source_rights_versions',
    'security_artifacts',
    'raw_artifacts',
    'artifact_localizations',
    'artifact_source_lineage',
    'raw_artifact_dispositions',
    'artifact_platforms',
    'artifact_threats',
    'catalog_amani_provenance',
    'catalog_amani_assets',
    'artifact_actions',
    'artifact_tags',
    'templates',
    'template_items',
  ];

  static Future<CatalogContentUpgradeResult> upgrade(
    String installedPath,
    String candidatePath,
  ) => Isolate.run(() => _upgradeSync(installedPath, candidatePath));

  static String _fileSha256(String path) =>
      sha256.convert(File(path).readAsBytesSync()).toString();

  static List<String> _columns(Database database, String table) => database
      .select('PRAGMA table_info("$table")')
      .map((row) => row['name'] as String)
      .toList(growable: false);

  static List<String> _primaryKey(Database database, String table) {
    final rows = database.select('PRAGMA table_info("$table")').toList()
      ..sort(
        (left, right) => (left['pk'] as int).compareTo(right['pk'] as int),
      );
    return rows
        .where((row) => (row['pk'] as int) > 0)
        .map((row) => row['name'] as String)
        .toList(growable: false);
  }

  static String _operationalSnapshot(Database database) {
    final names = database
        .select(
          "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        )
        .map((row) => row['name'] as String)
        .where(
          (name) =>
              name == 'application_state' ||
              name == 'enterprise_profiles' ||
              name.startsWith('profile_') ||
              name.startsWith('approved_blueprint') ||
              name.startsWith('blueprint_'),
        );
    final payload = <String, Object?>{};
    for (final table in names) {
      final columns = _columns(database, table);
      final keys = _primaryKey(database, table);
      final order = keys.isEmpty ? columns : keys;
      payload[table] = database
          .select(
            'SELECT * FROM "$table" ORDER BY '
            '${order.map((column) => '"$column"').join(',')}',
          )
          .map(
            (row) => <String, Object?>{
              for (final column in columns) column: row[column],
            },
          )
          .toList(growable: false);
    }
    return sha256.convert(utf8.encode(jsonEncode(payload))).toString();
  }

  static int _upsertStableTable(
    Database installed,
    Database candidate,
    String table,
  ) {
    final targetColumns = _columns(installed, table);
    final sourceColumns = _columns(candidate, table).toSet();
    final columns = targetColumns.where(sourceColumns.contains).toList();
    final keys = _primaryKey(installed, table);
    if (keys.isEmpty) {
      throw CatalogContentUpgradeException(
        'catalog table $table has no stable primary key',
      );
    }
    final updates = columns.where((column) => !keys.contains(column)).toList();
    final rows = candidate.select(
      'SELECT ${columns.map((column) => '"$column"').join(',')} '
      'FROM "$table" ORDER BY ${keys.map((key) => '"$key"').join(',')}',
    );
    for (final row in rows) {
      final sql = StringBuffer()
        ..write(
          'INSERT INTO "$table"('
          '${columns.map((column) => '"$column"').join(',')}) '
          'VALUES(${List.filled(columns.length, '?').join(',')}) '
          'ON CONFLICT(${keys.map((key) => '"$key"').join(',')}) ',
        )
        ..write(
          updates.isEmpty
              ? 'DO NOTHING'
              : 'DO UPDATE SET ${updates.map((column) => '"$column"=excluded."$column"').join(',')}',
        );
      installed.execute(
        sql.toString(),
        columns.map((column) => row[column]).toList(),
      );
    }
    return rows.length;
  }

  static int _mergeFrameworkMappings(Database installed, Database candidate) {
    final rows = candidate.select(
      'SELECT artifact_id,framework,version,reference,mapping_strength,rationale '
      'FROM framework_mappings ORDER BY artifact_id,framework,version,reference',
    );
    for (final row in rows) {
      final existing = installed.select(
        'SELECT id FROM framework_mappings WHERE artifact_id=? AND framework=? '
        'AND version=? AND reference=?',
        [
          row['artifact_id'],
          row['framework'],
          row['version'],
          row['reference'],
        ],
      );
      if (existing.isEmpty) {
        installed.execute(
          'INSERT INTO framework_mappings('
          'artifact_id,framework,version,reference,mapping_strength,rationale) '
          'VALUES(?,?,?,?,?,?)',
          [
            row['artifact_id'],
            row['framework'],
            row['version'],
            row['reference'],
            row['mapping_strength'],
            row['rationale'],
          ],
        );
      } else {
        installed.execute(
          'UPDATE framework_mappings SET mapping_strength=?,rationale=? WHERE id=?',
          [row['mapping_strength'], row['rationale'], existing.single['id']],
        );
      }
    }
    return rows.length;
  }

  static int _mergeRemediationActions(Database installed, Database candidate) {
    final rows = candidate.select(
      'SELECT artifact_id,action,priority,effort_estimate,responsible_role '
      'FROM remediation_actions ORDER BY artifact_id,action',
    );
    for (final row in rows) {
      final existing = installed.select(
        'SELECT id FROM remediation_actions WHERE artifact_id=? AND action=?',
        [row['artifact_id'], row['action']],
      );
      if (existing.isEmpty) {
        installed.execute(
          'INSERT INTO remediation_actions('
          'artifact_id,action,priority,effort_estimate,responsible_role) '
          'VALUES(?,?,?,?,?)',
          [
            row['artifact_id'],
            row['action'],
            row['priority'],
            row['effort_estimate'],
            row['responsible_role'],
          ],
        );
      } else {
        installed.execute(
          'UPDATE remediation_actions SET priority=?,effort_estimate=?,responsible_role=? '
          'WHERE id=?',
          [
            row['priority'],
            row['effort_estimate'],
            row['responsible_role'],
            existing.single['id'],
          ],
        );
      }
    }
    return rows.length;
  }

  static CatalogContentUpgradeResult _upgradeSync(
    String installedPath,
    String candidatePath,
  ) {
    final candidateSha = _fileSha256(candidatePath);
    final installedShaBefore = _fileSha256(installedPath);
    final installed = sqlite3.open(installedPath);
    final candidate = sqlite3.open(candidatePath, mode: OpenMode.readOnly);
    try {
      installed
        ..execute('PRAGMA foreign_keys = ON')
        ..execute('PRAGMA busy_timeout = 30000');
      if (candidate.select('PRAGMA integrity_check').single.values.first !=
              'ok' ||
          candidate.select('PRAGMA foreign_key_check').isNotEmpty) {
        throw const CatalogContentUpgradeException(
          'candidate integrity validation failed',
        );
      }
      final previous = installed.select(
        "SELECT 1 FROM catalog_upgrade_runs WHERE candidate_sha256=? AND status='APPLIED'",
        [candidateSha],
      );
      final oldCount =
          installed
                  .select('SELECT COUNT(*) AS n FROM security_artifacts')
                  .single['n']
              as int;
      final before = _operationalSnapshot(installed);
      if (previous.isNotEmpty) {
        return CatalogContentUpgradeResult(
          applied: false,
          candidateSha256: candidateSha,
          oldArtifactCount: oldCount,
          newArtifactCount: oldCount,
          operationalSnapshotBefore: before,
          operationalSnapshotAfter: before,
        );
      }

      final candidateTypes = <String, String>{
        for (final row in candidate.select(
          'SELECT id,type FROM security_artifacts',
        ))
          row['id'] as String: row['type'] as String,
      };
      final missing = <String>[];
      final changed = <String>[];
      for (final row in installed.select(
        'SELECT id,type FROM security_artifacts WHERE is_custom=0 ORDER BY id',
      )) {
        final id = row['id'] as String;
        if (!candidateTypes.containsKey(id)) {
          missing.add(id);
        } else if (candidateTypes[id] != row['type']) {
          changed.add(id);
        }
      }
      if (missing.isNotEmpty || changed.isNotEmpty) {
        throw CatalogContentUpgradeException(
          'stable-ID guard failed: missing=${missing.take(3).toList()} '
          'changedTypes=${changed.take(3).toList()}',
        );
      }

      installed.execute('BEGIN IMMEDIATE');
      try {
        for (final table in _stableTables) {
          _upsertStableTable(installed, candidate, table);
        }
        _mergeFrameworkMappings(installed, candidate);
        _mergeRemediationActions(installed, candidate);
        installed
          ..execute('DELETE FROM promotion_batch_items')
          ..execute('DELETE FROM staging_artifacts');
        final after = _operationalSnapshot(installed);
        if (after != before) {
          throw const CatalogContentUpgradeException(
            'operational/profile snapshot changed during catalog upgrade',
          );
        }
        final closure = installed
            .select('SELECT * FROM v_catalog_closure')
            .single;
        if ((closure['missing_dispositions'] as int) != 0 ||
            (closure['missing_canonical_lineage'] as int) != 0) {
          throw const CatalogContentUpgradeException(
            'catalog closure validation failed after upgrade',
          );
        }
        if (installed.select('PRAGMA integrity_check').single.values.first !=
                'ok' ||
            installed.select('PRAGMA foreign_key_check').isNotEmpty) {
          throw const CatalogContentUpgradeException(
            'integrity validation failed after upgrade',
          );
        }
        final newCount =
            installed
                    .select('SELECT COUNT(*) AS n FROM security_artifacts')
                    .single['n']
                as int;
        installed.execute(
          'INSERT INTO catalog_upgrade_runs('
          'id,candidate_sha256,installed_sha256_before,operational_snapshot_before,'
          'operational_snapshot_after,status,old_artifact_count,new_artifact_count,'
          'actor,completed_at) '
          "VALUES(?,?,?, ?,?,'APPLIED',?,?,'mobile-runtime',datetime('now'))",
          [
            'CUG-${DateTime.now().toUtc().microsecondsSinceEpoch}',
            candidateSha,
            installedShaBefore,
            before,
            after,
            oldCount,
            newCount,
          ],
        );
        installed.execute('COMMIT');
        return CatalogContentUpgradeResult(
          applied: true,
          candidateSha256: candidateSha,
          oldArtifactCount: oldCount,
          newArtifactCount: newCount,
          operationalSnapshotBefore: before,
          operationalSnapshotAfter: after,
        );
      } catch (_) {
        if (!installed.autocommit) installed.execute('ROLLBACK');
        rethrow;
      }
    } finally {
      candidate.close();
      installed.close();
    }
  }
}
