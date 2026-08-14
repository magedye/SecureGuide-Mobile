import 'package:flutter/material.dart';
import '../../l10n/app_localizations.dart';
import '../../read_model_contract.dart';
import '../client/secure_guide_client.dart';

class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key, required this.client, required this.profileId});

  final SecureGuideClient client;
  final String profileId;

  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  TasksView? _view;
  bool _loading = true;
  Object? _error;
  String? _statusFilter;
  String? _assignedToFilter;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final view = await widget.client.tasks(
        widget.profileId,
        status: _statusFilter,
        assignedTo: _assignedToFilter,
      );
      if (!mounted) return;
      setState(() {
        _view = view;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.tasks),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
      ),
      body: Column(
        children: [
          _buildFilters(),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildFilters() {
    final l10n = AppLocalizations.of(context)!;
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
      child: Row(
        children: [
          _buildStatusChip(l10n.all, null),
          const SizedBox(width: 8),
          _buildStatusChip(l10n.taskTodo, 'TODO'),
          const SizedBox(width: 8),
          _buildStatusChip(l10n.taskInProgress, 'IN_PROGRESS'),
          const SizedBox(width: 8),
          _buildStatusChip(l10n.taskBlocked, 'BLOCKED'),
          const SizedBox(width: 8),
          _buildStatusChip(l10n.taskDone, 'DONE'),
        ],
      ),
    );
  }

  Widget _buildStatusChip(String label, String? statusValue) {
    final isSelected = _statusFilter == statusValue;
    return FilterChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          setState(() {
            _statusFilter = statusValue;
          });
          _load();
        }
      },
    );
  }

  Widget _buildBody() {
    final l10n = AppLocalizations.of(context)!;
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              l10n.genericErrorTitle,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(_error.toString()),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: _load, child: Text(l10n.retry)),
          ],
        ),
      );
    }

    final tasks = _view?.tasks ?? [];
    if (tasks.isEmpty) {
      return Center(child: Text(l10n.noTasks));
    }

    return ListView.builder(
      itemCount: tasks.length,
      itemBuilder: (context, index) {
        final task = tasks[index];
        final id = task.id;
        if (id == null) return const SizedBox.shrink();

        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ExpansionTile(
            title: Text(task.title ?? l10n.untitledTask),
            subtitle: Text(
              '${l10n.statusLabel}: ${task.status} | '
              '${l10n.priorityLabel}: ${task.priority ?? l10n.notSpecified}',
            ),
            children: [
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (task.description != null) Text(task.description!),
                    const SizedBox(height: 8),
                    Text(
                      '${l10n.dueDate}: '
                      '${task.dueDate ?? l10n.notSpecified}',
                    ),
                    Text(
                      '${l10n.assignedToLabel}: '
                      '${task.assignedTo ?? l10n.notSpecified}',
                    ),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      alignment: WrapAlignment.spaceEvenly,
                      children: [
                        if (task.status != 'IN_PROGRESS')
                          ElevatedButton(
                            onPressed: () => _updateStatus(id, 'IN_PROGRESS'),
                            child: Text(l10n.startTask),
                          ),
                        if (task.status != 'BLOCKED' && task.status != 'DONE')
                          OutlinedButton(
                            onPressed: () => _updateStatus(id, 'BLOCKED'),
                            child: Text(l10n.blockTask),
                          ),
                        if (task.status != 'DONE')
                          ElevatedButton(
                            onPressed: () => _updateStatus(id, 'DONE'),
                            child: Text(l10n.completeTask),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _updateStatus(String taskId, String newStatus) async {
    final input = await _requestTaskUpdate();
    if (input == null) return;
    try {
      await widget.client.updateTaskStatus(
        taskId,
        newStatus,
        input.note,
        actor: input.actor,
      );
      _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<_TaskUpdateInput?> _requestTaskUpdate() async {
    final l10n = AppLocalizations.of(context)!;
    final actorController = TextEditingController();
    final noteController = TextEditingController();
    var actorError = false;
    var noteError = false;
    final result = await showDialog<_TaskUpdateInput>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(l10n.auditTaskUpdate),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                key: const Key('task-update-actor'),
                controller: actorController,
                autofocus: true,
                decoration: InputDecoration(
                  labelText: l10n.actorName,
                  errorText: actorError ? l10n.actorRequiredAudit : null,
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                key: const Key('task-update-note'),
                controller: noteController,
                decoration: InputDecoration(
                  labelText: l10n.changeNote,
                  errorText: noteError ? l10n.requiredField : null,
                ),
                maxLines: 3,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(l10n.cancel),
            ),
            FilledButton(
              onPressed: () {
                final actor = actorController.text.trim();
                final note = noteController.text.trim();
                if (actor.isEmpty || note.isEmpty) {
                  setDialogState(() {
                    actorError = actor.isEmpty;
                    noteError = note.isEmpty;
                  });
                  return;
                }
                Navigator.pop(context, _TaskUpdateInput(actor, note));
              },
              child: Text(l10n.save),
            ),
          ],
        ),
      ),
    );
    actorController.dispose();
    noteController.dispose();
    return result;
  }
}

final class _TaskUpdateInput {
  const _TaskUpdateInput(this.actor, this.note);

  final String actor;
  final String note;
}
