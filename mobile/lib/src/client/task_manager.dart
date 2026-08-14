import '../repositories/local_task_repository.dart';

class TaskManager {
  TaskManager({LocalTaskRepository? repository})
    : _repository = repository ?? LocalTaskRepository();

  final LocalTaskRepository _repository;

  Future<void> updateTaskStatus(
    String taskId,
    String newStatus,
    String note,
    String actor,
  ) => _repository.updateStatus(taskId, newStatus, actor: actor, note: note);
}
