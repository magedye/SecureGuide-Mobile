import 'package:sqflite/sqflite.dart';

import '../../core/database/database_helper.dart';
import '../../read_model_contract.dart';

/// Typed SQLite boundary for profile-isolated task queues and transitions.
final class LocalTaskRepository {
  LocalTaskRepository({Future<Database>? database})
    : _database = database ?? DatabaseHelper.instance.database;

  final Future<Database> _database;

  Future<TasksView> list(
    String profileId, {
    String? status,
    String? assignedTo,
  }) async {
    final db = await _database;
    var sql = 'SELECT * FROM v_profile_task_queue WHERE profile_id = ?';
    final args = <Object?>[profileId];
    if (status != null && status.isNotEmpty) {
      sql += ' AND status = ?';
      args.add(status);
    }
    if (assignedTo != null && assignedTo.isNotEmpty) {
      sql += ' AND assigned_to = ?';
      args.add(assignedTo);
    }
    sql += ' ORDER BY due_date IS NULL, due_date, priority, updated_at DESC';
    final rows = await db.rawQuery(sql, args);
    return TasksView(tasks: rows.map(_task).toList());
  }

  Future<void> updateStatus(
    String taskId,
    String newStatus, {
    required String actor,
    required String note,
  }) async {
    const statuses = {'TODO', 'IN_PROGRESS', 'BLOCKED', 'DONE', 'CANCELLED'};
    if (!statuses.contains(newStatus)) {
      throw ArgumentError.value(newStatus, 'newStatus', 'is not controlled');
    }
    final accountableActor = actor.trim();
    if (accountableActor.isEmpty) {
      throw ArgumentError.value(actor, 'actor', 'must not be empty');
    }
    final db = await _database;
    await db.transaction((txn) async {
      final rows = await txn.query(
        'profile_tasks',
        columns: ['status'],
        where: 'id = ?',
        whereArgs: [taskId],
        limit: 1,
      );
      if (rows.isEmpty) throw StateError('TASK_NOT_FOUND');
      final currentStatus = rows.single['status'] as String;
      if (currentStatus == newStatus) return;

      final terminal = newStatus == 'DONE' || newStatus == 'CANCELLED';
      final affected = await txn.update(
        'profile_tasks',
        {
          'status': newStatus,
          'last_changed_by': accountableActor,
          'last_change_note': note.trim().isEmpty ? null : note.trim(),
          if (terminal)
            'completed_at': DateTime.now().toUtc().toIso8601String(),
          if (terminal) 'closed_by': accountableActor,
        },
        where: 'id = ? AND status = ?',
        whereArgs: [taskId, currentStatus],
      );
      if (affected != 1) {
        throw StateError('TASK_TRANSITION_REJECTED:$currentStatus->$newStatus');
      }
    });
  }

  static TaskItem _task(Map<String, Object?> row) => TaskItem(
    id: row['id'] as String?,
    title: row['title'] as String?,
    description: row['description'] as String?,
    status: row['status'] as String?,
    priority: row['priority'] as String?,
    assignedTo: row['assigned_to'] as String?,
    dueDate: row['due_date'] as String?,
    artifactId: row['artifact_id'] as String?,
    artifactTitleEn: row['artifact_title_en'] as String?,
    primaryDomain: row['primary_domain'] as String?,
    subDomain: row['sub_domain'] as String?,
    blueprintId: row['blueprint_id'] as String?,
    blueprintVersion: row['blueprint_version_number'] as num?,
    actionPlanType: row['action_plan_type'] as String?,
    sourceSemanticKey: row['source_semantic_key'] as String?,
    lastChangedBy: row['last_changed_by'] as String?,
    lastChangeNote: row['last_change_note'] as String?,
    completedAt: row['completed_at'] as String?,
    updatedAt: row['updated_at'] as String?,
  );
}
