import 'package:sqflite/sqflite.dart';
import 'package:uuid/uuid.dart';

import '../../core/database/database_helper.dart';
import '../../read_model_contract.dart';

class ExceptionManager {
  ExceptionManager({Future<Database>? database})
    : _db = database ?? DatabaseHelper.instance.database;

  final Future<Database> _db;

  Future<ExceptionRecord> saveDraft({
    required String profileArtifactId,
    required String exceptionStatus,
    required String justification,
    String? expiryDate,
    String? riskAcceptedBy,
  }) async {
    final db = await _db;

    final existing = await db.query(
      'profile_exceptions',
      where: "profile_artifact_id = ? AND workflow_status = 'DRAFT'",
      whereArgs: [profileArtifactId],
      orderBy: 'created_at DESC',
      limit: 1,
    );

    final String id;
    final String createdAt;

    if (existing.isNotEmpty) {
      id = existing.first['id'] as String;
      createdAt = existing.first['created_at'] as String;

      await db.update(
        'profile_exceptions',
        {
          'exception_status': exceptionStatus,
          'justification': justification,
          'expiry_date': expiryDate,
          'risk_accepted_by': riskAcceptedBy,
          'updated_at': DateTime.now().toUtc().toIso8601String(),
        },
        where: 'id = ?',
        whereArgs: [id],
      );
    } else {
      id = const Uuid().v4();
      createdAt = DateTime.now().toUtc().toIso8601String();

      await db.insert('profile_exceptions', {
        'id': id,
        'profile_artifact_id': profileArtifactId,
        'exception_status': exceptionStatus,
        'justification': justification,
        'expiry_date': expiryDate,
        'risk_accepted_by': riskAcceptedBy,
        'workflow_status': 'DRAFT',
        'exception_source': 'USER',
        'created_at': createdAt,
      });
    }

    return (await _exceptionById(db, id))!;
  }

  Future<ExceptionRecord?> getDraftForArtifact(String profileArtifactId) async {
    final db = await _db;
    final rows = await db.query(
      'profile_exceptions',
      where: "profile_artifact_id = ? AND workflow_status = 'DRAFT'",
      whereArgs: [profileArtifactId],
      orderBy: 'created_at DESC',
      limit: 1,
    );
    if (rows.isEmpty) return null;
    return ExceptionRecord.fromJson(rows.first);
  }

  Future<List<Map<String, dynamic>>> listForProfile(String profileId) async {
    final db = await _db;
    return db.rawQuery(
      '''
      SELECT
        pe.id AS exception_id,
        pe.exception_status,
        pe.workflow_status,
        pe.justification,
        pe.expiry_date,
        pe.risk_accepted_by,
        pa.id AS profile_artifact_id,
        sa.id AS artifact_id,
        COALESCE(sa.title_ar, sa.title_en, sa.id) AS artifact_title
      FROM profile_exceptions pe
      JOIN profile_artifacts pa ON pe.profile_artifact_id = pa.id
      JOIN security_artifacts sa ON pa.artifact_id = sa.id
      WHERE pa.profile_id = ?
      ORDER BY pe.created_at DESC
    ''',
      [profileId],
    );
  }

  Future<ExceptionRecord> submit(String exceptionId) async {
    final db = await _db;
    return db.transaction((transaction) async {
      final current = await _exceptionById(transaction, exceptionId);
      if (current == null) {
        throw StateError('Exception not found: $exceptionId');
      }
      if (current.workflowStatus != 'DRAFT') {
        throw StateError('Only DRAFT exceptions can be submitted');
      }
      await transaction.update(
        'profile_exceptions',
        {
          'workflow_status': 'SUBMITTED',
          'updated_at': DateTime.now().toUtc().toIso8601String(),
        },
        where: 'id = ?',
        whereArgs: [exceptionId],
      );
      return (await _exceptionById(transaction, exceptionId))!;
    });
  }

  Future<ExceptionRecord> approve(
    String exceptionId, {
    required String approvedBy,
  }) async {
    final approver = approvedBy.trim();
    if (approver.isEmpty) {
      throw ArgumentError.value(approvedBy, 'approvedBy', 'is required');
    }

    final db = await _db;
    return db.transaction((transaction) async {
      final current = await _exceptionById(transaction, exceptionId);
      if (current == null) {
        throw StateError('Exception not found: $exceptionId');
      }
      if (current.workflowStatus != 'SUBMITTED') {
        throw StateError('Only SUBMITTED exceptions can be approved');
      }
      if (current.expiryDate == null || current.expiryDate!.trim().isEmpty) {
        throw StateError('Approval requires an expiry date');
      }
      if (current.exceptionStatus == 'EXC-RISK-ACCEPTED' &&
          (current.riskAcceptedBy == null ||
              current.riskAcceptedBy!.trim().isEmpty)) {
        throw StateError('Risk acceptance requires an accountable person');
      }

      final approvalDate = DateTime.now().toUtc().toIso8601String();
      final expiryDate = DateTime.tryParse(current.expiryDate!);
      if (expiryDate == null || !expiryDate.isAfter(DateTime.now().toUtc())) {
        throw StateError('Expiry date must be in the future');
      }

      await transaction.update(
        'profile_exceptions',
        {
          'workflow_status': 'APPROVED',
          'approved_by': approver,
          'approval_date': approvalDate,
          'updated_at': approvalDate,
        },
        where: 'id = ?',
        whereArgs: [exceptionId],
      );
      await transaction.update(
        'profile_artifacts',
        {
          'exception_status': current.exceptionStatus,
          'active_exception_id': exceptionId,
        },
        where: 'id = ?',
        whereArgs: [current.profileArtifactId],
      );
      return (await _exceptionById(transaction, exceptionId))!;
    });
  }

  Future<ExceptionRecord?> _exceptionById(
    DatabaseExecutor executor,
    String exceptionId,
  ) async {
    final rows = await executor.query(
      'profile_exceptions',
      where: 'id = ?',
      whereArgs: [exceptionId],
      limit: 1,
    );
    return rows.isEmpty ? null : ExceptionRecord.fromJson(rows.single);
  }
}
