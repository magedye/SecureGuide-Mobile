import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';
import 'package:uuid/uuid.dart';

import '../../core/database/database_helper.dart';

const _evidenceTypes = {
  'DOCUMENT',
  'SCREENSHOT',
  'LOG',
  'REPORT',
  'CONFIG',
  'ATTESTATION',
  'LINK',
  'OTHER',
};

enum EvidenceIntegrity { valid, missing, corrupted, unsafePath }

final class EvidenceRecord {
  const EvidenceRecord({
    required this.id,
    required this.profileArtifactId,
    this.assessmentId,
    required this.evidenceType,
    this.evidenceUrl,
    this.title,
    this.description,
    this.collectedBy,
    required this.collectedAt,
    this.contentHash,
    this.mimeType,
    this.fileSize,
  });

  final String id;
  final String profileArtifactId;
  final String? assessmentId;
  final String evidenceType;
  final String? evidenceUrl;
  final String? title;
  final String? description;
  final String? collectedBy;
  final String collectedAt;
  final String? contentHash;
  final String? mimeType;
  final int? fileSize;

  factory EvidenceRecord.fromMap(Map<String, Object?> map) => EvidenceRecord(
    id: map['id'] as String,
    profileArtifactId: map['profile_artifact_id'] as String,
    assessmentId: map['assessment_id'] as String?,
    evidenceType: map['evidence_type'] as String,
    evidenceUrl: map['evidence_url'] as String?,
    title: map['title'] as String?,
    description: map['description'] as String?,
    collectedBy: map['collected_by'] as String?,
    collectedAt: map['collected_at'] as String,
    contentHash: map['content_hash'] as String?,
    mimeType: map['mime_type'] as String?,
    fileSize: map['file_size'] as int?,
  );
}

final class EvidencePreview {
  const EvidencePreview({required this.record, required this.bytes, this.text});

  final EvidenceRecord record;
  final Uint8List bytes;
  final String? text;

  bool get isImage => record.mimeType?.startsWith('image/') == true;
}

final class EvidenceManager {
  EvidenceManager({Future<Database>? database}) : _databaseOverride = database;

  static const maxEvidenceBytes = 50 * 1024 * 1024;
  static const maxPreviewBytes = 5 * 1024 * 1024;

  final Future<Database>? _databaseOverride;

  Future<Database> get _database =>
      _databaseOverride ?? DatabaseHelper.instance.database;

  Future<EvidenceRecord> addEvidence({
    required String profileArtifactId,
    required String profileId,
    String? assessmentId,
    required String evidenceType,
    required File file,
    required String collectedBy,
    String? description,
  }) async {
    if (!_evidenceTypes.contains(evidenceType)) {
      throw ArgumentError.value(
        evidenceType,
        'evidenceType',
        'is not controlled',
      );
    }
    final actor = collectedBy.trim();
    if (actor.isEmpty) {
      throw ArgumentError.value(
        collectedBy,
        'collectedBy',
        'must not be empty',
      );
    }
    _validateIdentifier(profileId, 'profileId');
    if (!await file.exists()) throw StateError('EVIDENCE_SOURCE_MISSING');
    final size = await file.length();
    if (size > maxEvidenceBytes) throw StateError('EVIDENCE_FILE_TOO_LARGE');

    final db = await _database;
    final selection = await db.rawQuery(
      '''SELECT 1 FROM profile_artifacts
          WHERE id=? AND profile_id=?''',
      [profileArtifactId, profileId],
    );
    if (selection.isEmpty) throw StateError('PROFILE_ARTIFACT_NOT_FOUND');

    final sourceHash = await _hash(file);
    final evidenceRoot = await _evidenceRoot(profileId, create: true);
    final id = const Uuid().v4();
    final extension = _safeExtension(file.path);
    final destination = File(p.join(evidenceRoot.path, '$id$extension'));
    final partial = File('${destination.path}.partial');

    try {
      await file.copy(partial.path);
      if (await _hash(partial) != sourceHash) {
        throw StateError('EVIDENCE_COPY_HASH_MISMATCH');
      }
      await partial.rename(destination.path);

      final record = <String, Object?>{
        'id': id,
        'profile_artifact_id': profileArtifactId,
        'assessment_id': assessmentId,
        'evidence_type': evidenceType,
        'evidence_url': destination.path,
        'title': p.basename(file.path),
        'description': description,
        'collected_by': actor,
        'collected_at': DateTime.now().toUtc().toIso8601String(),
        'content_hash': sourceHash,
        'mime_type': _mimeType(extension),
        'file_size': size,
      };
      await db.insert('profile_evidence', record);
      return EvidenceRecord.fromMap(record);
    } catch (_) {
      if (await partial.exists()) await partial.delete();
      if (await destination.exists()) await destination.delete();
      rethrow;
    }
  }

  Future<List<EvidenceRecord>> getEvidenceForArtifact(
    String profileArtifactId, {
    required String profileId,
  }) async {
    final db = await _database;
    final rows = await db.rawQuery(
      '''SELECT e.*
           FROM profile_evidence e
           JOIN profile_artifacts pa ON pa.id=e.profile_artifact_id
          WHERE e.profile_artifact_id=? AND pa.profile_id=?
          ORDER BY e.collected_at DESC,e.id''',
      [profileArtifactId, profileId],
    );
    return rows.map(EvidenceRecord.fromMap).toList();
  }

  Future<EvidenceIntegrity> verifyEvidence(
    String evidenceId, {
    required String profileId,
  }) async {
    final record = await _record(evidenceId, profileId);
    final storedPath = record.evidenceUrl;
    if (storedPath == null) return EvidenceIntegrity.missing;
    final file = File(storedPath);
    if (!await file.exists()) return EvidenceIntegrity.missing;
    if (!await _isInsideProfileRoot(file, profileId)) {
      return EvidenceIntegrity.unsafePath;
    }
    if (record.fileSize != null && await file.length() != record.fileSize) {
      return EvidenceIntegrity.corrupted;
    }
    if (record.contentHash == null || await _hash(file) != record.contentHash) {
      return EvidenceIntegrity.corrupted;
    }
    return EvidenceIntegrity.valid;
  }

  Future<EvidencePreview> loadPreview(
    String evidenceId, {
    required String profileId,
  }) async {
    final record = await _record(evidenceId, profileId);
    final integrity = await verifyEvidence(evidenceId, profileId: profileId);
    if (integrity != EvidenceIntegrity.valid) {
      throw StateError('EVIDENCE_INTEGRITY_${integrity.name.toUpperCase()}');
    }
    final file = File(record.evidenceUrl!);
    if (await file.length() > maxPreviewBytes) {
      throw StateError('EVIDENCE_PREVIEW_TOO_LARGE');
    }
    final bytes = await file.readAsBytes();
    final text = record.mimeType?.startsWith('text/') == true
        ? utf8.decode(bytes, allowMalformed: false)
        : null;
    return EvidencePreview(record: record, bytes: bytes, text: text);
  }

  Future<void> deleteEvidence(
    String evidenceId, {
    required String profileId,
  }) async {
    final record = await _record(evidenceId, profileId);
    final path = record.evidenceUrl;
    File? original;
    File? quarantined;
    if (path != null) {
      original = File(path);
      if (await original.exists()) {
        if (!await _isInsideProfileRoot(original, profileId)) {
          throw StateError('EVIDENCE_PATH_OUTSIDE_PROFILE');
        }
        quarantined = File('$path.deleting');
        await original.rename(quarantined.path);
      }
    }

    try {
      final db = await _database;
      final affected = await db.rawDelete(
        '''DELETE FROM profile_evidence
            WHERE id=? AND EXISTS (
              SELECT 1 FROM profile_artifacts pa
               WHERE pa.id=profile_evidence.profile_artifact_id
                 AND pa.profile_id=?
            )''',
        [evidenceId, profileId],
      );
      if (affected != 1) throw StateError('EVIDENCE_DELETE_REJECTED');
      if (quarantined != null && await quarantined.exists()) {
        await quarantined.delete();
      }
    } catch (_) {
      if (quarantined != null &&
          original != null &&
          await quarantined.exists()) {
        await quarantined.rename(original.path);
      }
      rethrow;
    }
  }

  Future<EvidenceRecord> _record(String evidenceId, String profileId) async {
    final db = await _database;
    final rows = await db.rawQuery(
      '''SELECT e.*
           FROM profile_evidence e
           JOIN profile_artifacts pa ON pa.id=e.profile_artifact_id
          WHERE e.id=? AND pa.profile_id=?''',
      [evidenceId, profileId],
    );
    if (rows.length != 1) throw StateError('EVIDENCE_NOT_FOUND_IN_PROFILE');
    return EvidenceRecord.fromMap(rows.single);
  }

  Future<Directory> _evidenceRoot(
    String profileId, {
    bool create = false,
  }) async {
    _validateIdentifier(profileId, 'profileId');
    final appDirectory = await getApplicationDocumentsDirectory();
    final root = Directory(p.join(appDirectory.path, 'evidence', profileId));
    if (create) await root.create(recursive: true);
    return root;
  }

  Future<bool> _isInsideProfileRoot(File file, String profileId) async {
    final root = await _evidenceRoot(profileId);
    if (!await root.exists() || !await file.exists()) return false;
    final resolvedRoot = p.normalize(await root.resolveSymbolicLinks());
    final resolvedFile = p.normalize(await file.resolveSymbolicLinks());
    return p.isWithin(resolvedRoot, resolvedFile);
  }

  static Future<String> _hash(File file) async =>
      (await sha256.bind(file.openRead()).first).toString();

  static String _safeExtension(String path) {
    final extension = p.extension(path).toLowerCase();
    return RegExp(r'^\.[a-z0-9]{1,10}$').hasMatch(extension) ? extension : '';
  }

  static String _mimeType(String extension) => switch (extension) {
    '.png' => 'image/png',
    '.jpg' || '.jpeg' => 'image/jpeg',
    '.gif' => 'image/gif',
    '.webp' => 'image/webp',
    '.txt' || '.log' || '.md' || '.csv' || '.json' => 'text/plain',
    '.pdf' => 'application/pdf',
    _ => 'application/octet-stream',
  };

  static void _validateIdentifier(String value, String name) {
    if (!RegExp(r'^[A-Za-z0-9_-]{1,128}$').hasMatch(value)) {
      throw ArgumentError.value(value, name, 'contains unsafe path characters');
    }
  }
}
