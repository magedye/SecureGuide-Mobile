import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../read_model_contract.dart';
import '../client/blueprint_manager.dart';
import '../client/secure_guide_client.dart';

class BlueprintDetailScreen extends StatefulWidget {
  const BlueprintDetailScreen({
    super.key,
    required this.client,
    required this.blueprintId,
  });

  final SecureGuideClient client;
  final String blueprintId;

  @override
  State<BlueprintDetailScreen> createState() => _BlueprintDetailScreenState();
}

class _BlueprintDetailScreenState extends State<BlueprintDetailScreen> {
  BlueprintDetailView? _view;
  Object? _error;
  bool _loading = true;

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
      final view = await widget.client.blueprint(widget.blueprintId);
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
    final bp = _view?.blueprint;
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      appBar: AppBar(title: Text(bp?.title ?? l10n.blueprintDetails)),
      body: _buildBody(),
      bottomNavigationBar: bp != null ? _buildActionBar(bp) : null,
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

    final bp = _view!.blueprint;
    final actions = bp.actions;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${l10n.statusLabel}: ${bp.workflowStatus}',
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                const SizedBox(height: 8),
                Text('${l10n.createdAtLabel}: ${bp.updatedAt}'),
                Text('${l10n.createdByLabel}: ${bp.createdBy}'),
                if (bp.approvedBy != null)
                  Text(
                    '${l10n.approvedByLabel}: ${bp.approvedBy} '
                    '(${bp.approvedAt})',
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          '${l10n.proposedActions} (${actions.length})',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: 8),
        ...actions.map(
          (a) => Card(
            child: ListTile(
              title: Text(a.title ?? l10n.untitled),
              subtitle: Text(a.description ?? ''),
              leading: CircleAvatar(child: Text(a.displayOrder.toString())),
            ),
          ),
        ),
        if (bp.expectedOutputs.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(
            '${l10n.expectedOutputs} (${bp.expectedOutputs.length})',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          ...bp.expectedOutputs.map(
            (output) => ListTile(
              leading: const Icon(Icons.inventory_2_outlined),
              title: Text(output.title ?? output.outputCode ?? ''),
              subtitle: Text(output.description ?? ''),
            ),
          ),
        ],
        if (bp.evidence.isNotEmpty) ...[
          const SizedBox(height: 16),
          Text(
            '${l10n.requiredEvidence} (${bp.evidence.length})',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          ...bp.evidence.map(
            (evidence) => ListTile(
              leading: Icon(
                evidence.mandatory == true
                    ? Icons.verified_outlined
                    : Icons.fact_check_outlined,
              ),
              title: Text(evidence.title ?? evidence.evidenceCode ?? ''),
              subtitle: Text(evidence.description ?? ''),
              trailing: Text(evidence.evidenceType ?? ''),
            ),
          ),
        ],
        if (bp.appliedRules.isNotEmpty) ...[
          const SizedBox(height: 16),
          ExpansionTile(
            title: Text('${l10n.generationRules} (${bp.appliedRules.length})'),
            children: bp.appliedRules
                .map(
                  (rule) => ListTile(
                    title: Text('${rule.ruleId} @ ${rule.ruleVersion}'),
                    subtitle: Text(rule.rationale ?? ''),
                    trailing: Text(rule.stage ?? ''),
                  ),
                )
                .toList(),
          ),
        ],
        if (bp.patternEnrichments.isNotEmpty) ...[
          const SizedBox(height: 16),
          ExpansionTile(
            title: Text(
              '${l10n.patternEnrichments} '
              '(${bp.patternEnrichments.length})',
            ),
            children: bp.patternEnrichments
                .map(
                  (enrichment) => ListTile(
                    title: Text(
                      enrichment.copiedTitleAr ??
                          enrichment.sourcePatternId ??
                          '',
                    ),
                    subtitle: Text(enrichment.selectionReason ?? ''),
                    trailing: Text(enrichment.selectedBy ?? ''),
                  ),
                )
                .toList(),
          ),
        ],
      ],
    );
  }

  Widget _buildActionBar(BlueprintDetail bp) {
    final l10n = AppLocalizations.of(context)!;
    if (bp.id == null) return const SizedBox.shrink();

    if (bp.workflowStatus == 'DRAFT') {
      return BottomAppBar(
        child: Row(
          children: [
            Expanded(
              child: ElevatedButton.icon(
                onPressed: () => _submit(bp.id!),
                icon: const Icon(Icons.send),
                label: Text(l10n.submitForReview),
              ),
            ),
          ],
        ),
      );
    }

    if (bp.workflowStatus == 'UNDER_REVIEW') {
      return BottomAppBar(
        child: Row(
          children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => _returnToDraft(bp.id!),
                icon: const Icon(Icons.undo),
                label: Text(l10n.returnToDraft),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: ElevatedButton.icon(
                onPressed: () => _approve(bp),
                icon: const Icon(Icons.check),
                label: Text(l10n.approveBlueprint),
              ),
            ),
          ],
        ),
      );
    }

    return const SizedBox.shrink();
  }

  Future<void> _submit(String blueprintId) async {
    final l10n = AppLocalizations.of(context)!;
    final input = await _requestWorkflowInput(
      title: l10n.submitBlueprintReviewTitle,
    );
    if (input == null) return;
    try {
      await BlueprintManager().submitBlueprint(blueprintId, input.actor);
      _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _approve(BlueprintDetail blueprint) async {
    final l10n = AppLocalizations.of(context)!;
    final input = await _requestWorkflowInput(
      title: l10n.approveBlueprintTitle,
      noteLabel: l10n.reviewResolutionNote,
      noteRequired: blueprint.generationRequiresReview == true,
    );
    if (input == null || blueprint.id == null) return;
    try {
      await BlueprintManager().approveBlueprint(
        blueprint.id!,
        input.actor,
        resolutionNote: input.note,
      );
      _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<void> _returnToDraft(String blueprintId) async {
    final l10n = AppLocalizations.of(context)!;
    final input = await _requestWorkflowInput(
      title: l10n.returnBlueprintDraftTitle,
      noteLabel: l10n.returnReason,
      noteRequired: true,
    );
    if (input == null) return;
    try {
      await BlueprintManager().returnToDraft(
        blueprintId,
        input.actor,
        input.note!,
      );
      _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(e.toString())));
    }
  }

  Future<_WorkflowInput?> _requestWorkflowInput({
    required String title,
    String? noteLabel,
    bool noteRequired = false,
  }) async {
    final l10n = AppLocalizations.of(context)!;
    final actorController = TextEditingController();
    final noteController = TextEditingController();
    var actorError = false;
    var noteError = false;
    final result = await showDialog<_WorkflowInput>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(title),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                key: const Key('blueprint-workflow-actor'),
                controller: actorController,
                autofocus: true,
                decoration: InputDecoration(
                  labelText: l10n.actorName,
                  errorText: actorError ? l10n.actorRequiredAudit : null,
                ),
              ),
              if (noteLabel != null) ...[
                const SizedBox(height: 12),
                TextField(
                  key: const Key('blueprint-workflow-note'),
                  controller: noteController,
                  decoration: InputDecoration(
                    labelText: noteLabel,
                    errorText: noteError ? l10n.requiredField : null,
                  ),
                  maxLines: 3,
                ),
              ],
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
                final invalidActor = actor.isEmpty;
                final invalidNote = noteRequired && note.isEmpty;
                if (invalidActor || invalidNote) {
                  setDialogState(() {
                    actorError = invalidActor;
                    noteError = invalidNote;
                  });
                  return;
                }
                Navigator.pop(
                  context,
                  _WorkflowInput(actor, note.isEmpty ? null : note),
                );
              },
              child: Text(l10n.confirm),
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

final class _WorkflowInput {
  const _WorkflowInput(this.actor, this.note);

  final String actor;
  final String? note;
}
