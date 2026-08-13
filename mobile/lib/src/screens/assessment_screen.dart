import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import 'blueprint_list_screen.dart';

import 'exception_request_dialog.dart';
import '../client/exception_manager.dart';

import 'evidence_tab.dart';

import '../../read_model_contract.dart';
import '../client/secure_guide_client.dart';

const _implementationStatuses = <String>[
  'STS-NOT-APPLIED',
  'STS-PLANNED',
  'STS-PARTIAL',
  'STS-FULL',
  'STS-NEEDS-IMPROVEMENT',
];
const _verificationStatuses = <String>[
  'VER-NOT-VERIFIED',
  'VER-PASS',
  'VER-FAIL',
];
const _effectivenessValues = <String>[
  'EFF-UNKNOWN',
  'EFF-LOW',
  'EFF-MEDIUM',
  'EFF-HIGH',
];
const _maturityLevels = <String>[
  'INITIAL',
  'REPEATABLE',
  'DEFINED',
  'MANAGED',
  'OPTIMIZED',
];
const _priorities = <String>[
  'PRI-LOW',
  'PRI-MEDIUM',
  'PRI-HIGH',
  'PRI-CRITICAL',
];
const _reviewFrequencies = <String>[
  'CONTINUOUS',
  'DAILY',
  'WEEKLY',
  'MONTHLY',
  'QUARTERLY',
  'SEMI-ANNUAL',
  'ANNUAL',
  'BIENNIAL',
  'AD-HOC',
];

/// Profile-scoped assessment workspace. It edits only the current operational
/// state and appends an immutable assessment snapshot through the governed
/// write contract. Exception state is intentionally read-only here.
class AssessmentScreen extends StatefulWidget {
  const AssessmentScreen({
    super.key,
    required this.client,
    required this.artifactId,
    this.profileId,
  });

  final SecureGuideClient client;
  final String artifactId;
  final String? profileId;

  @override
  State<AssessmentScreen> createState() => _AssessmentScreenState();
}

class _AssessmentScreenState extends State<AssessmentScreen> {
  final _formKey = GlobalKey<FormState>();
  final _assessor = TextEditingController();
  final _owner = TextEditingController();
  final _dueDate = TextEditingController();
  final _notes = TextEditingController();
  final _score = TextEditingController();
  final _comments = TextEditingController();

  ProfileArtifactView? _view;
  Object? _error;
  bool _loading = true;
  bool _saving = false;
  bool _initialized = false;
  String? _implementationStatus;
  String? _verificationStatus;
  String? _effectiveness;
  String? _maturityLevel;
  String? _priorityOverride;
  String? _reviewFrequencyOverride;
  bool _usePriorityOverride = false;
  bool _useReviewOverride = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _assessor.dispose();
    _owner.dispose();
    _dueDate.dispose();
    _notes.dispose();
    _score.dispose();
    _comments.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final view = await widget.client.profileArtifact(
        widget.artifactId,
        profileId: widget.profileId,
      );
      if (!mounted) return;
      if (!_initialized) _initializeForm(view);
      setState(() {
        _view = view;
        _error = null;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error;
        _loading = false;
      });
    }
  }

  void _initializeForm(ProfileArtifactView view) {
    final artifact = view.artifact;
    _implementationStatus = artifact.implementationStatus;
    _verificationStatus = artifact.verificationStatus;
    _effectiveness = artifact.effectiveness;
    _maturityLevel = artifact.currentMaturityLevel;
    _priorityOverride = artifact.priorityOverride;
    _reviewFrequencyOverride = artifact.reviewFrequencyOverride;
    _usePriorityOverride = _priorityOverride != null;
    _useReviewOverride = _reviewFrequencyOverride != null;
    _owner.text = artifact.assignedOwner ?? '';
    _dueDate.text = artifact.dueDate ?? '';
    _notes.text = artifact.notes ?? '';
    if (view.assessments.isNotEmpty && view.assessments.first.score != null) {
      _score.text = '${view.assessments.first.score}';
    }
    _initialized = true;
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    final messenger = ScaffoldMessenger.of(context);
    final l10n = AppLocalizations.of(context)!;
    try {
      final score = _score.text.trim().isEmpty
          ? null
          : num.parse(_score.text.trim());
      final result = await widget.client.assessArtifact(
        widget.artifactId,
        profileId: widget.profileId,
        assessorName: _assessor.text.trim(),
        implementationStatus: _implementationStatus,
        verificationStatus: _verificationStatus,
        effectiveness: _effectiveness,
        currentMaturityLevel: _maturityLevel,
        assignedOwner: _owner.text.trim().isEmpty ? null : _owner.text.trim(),
        clearAssignedOwner: _owner.text.trim().isEmpty,
        dueDate: _dueDate.text.trim().isEmpty ? null : _dueDate.text.trim(),
        clearDueDate: _dueDate.text.trim().isEmpty,
        notes: _notes.text.trim().isEmpty ? null : _notes.text.trim(),
        clearNotes: _notes.text.trim().isEmpty,
        priorityOverride: _usePriorityOverride ? _priorityOverride : null,
        reviewFrequencyOverride: _useReviewOverride
            ? _reviewFrequencyOverride
            : null,
        clearPriorityOverride: !_usePriorityOverride,
        clearReviewFrequencyOverride: !_useReviewOverride,
        score: score,
        comments: _comments.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _view = ProfileArtifactView(
          profileId: _view?.profileId ?? widget.profileId,
          artifact: result.artifact,
          assessments: [result.assessment, ...?_view?.assessments],
        );
        _comments.clear();
        _saving = false;
      });
      messenger.showSnackBar(SnackBar(content: Text(l10n.assessmentSaved)));
    } catch (error) {
      if (!mounted) return;
      setState(() => _saving = false);
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.assessmentSaveError(error))),
      );
    }
  }

  Future<void> _pickDueDate() async {
    final initial = DateTime.tryParse(_dueDate.text) ?? DateTime.now();
    final selected = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (selected == null) return;
    _dueDate.text = selected.toIso8601String().substring(0, 10);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return DefaultTabController(
      length: 4,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l10n.artifactDetailsTitle),
          bottom: TabBar(
            tabs: [
              Tab(text: l10n.detailsTab),
              Tab(key: const Key('assessmentTab'), text: l10n.assessmentTab),
              Tab(key: const Key('evidenceTab'), text: l10n.evidenceTab),
              Tab(text: l10n.remediationPlansTab),
            ],
          ),
        ),
        body: _body(),
      ),
    );
  }

  Widget _body() {
    final l10n = AppLocalizations.of(context)!;
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                l10n.artifactLoadError(_error!),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              OutlinedButton(onPressed: _load, child: Text(l10n.retry)),
            ],
          ),
        ),
      );
    }
    final view = _view!;
    return TabBarView(
      children: [
        _buildDetailsTab(view),
        _buildAssessmentTab(view),
        EvidenceTab(
          profileArtifactId:
              view.artifact.profileArtifactId ?? widget.artifactId,
          profileId: widget.profileId ?? 'unknown',
        ),
        BlueprintListScreen(
          client: widget.client,
          profileId: widget.profileId ?? 'unknown',
        ),
      ],
    );
  }

  Widget _buildDetailsTab(ProfileArtifactView view) {
    final l10n = AppLocalizations.of(context)!;
    final artifact = view.artifact;
    final isArabic = Localizations.localeOf(context).languageCode == 'ar';
    final title = isArabic
        ? artifact.titleAr ?? artifact.titleEn
        : artifact.titleEn ?? artifact.titleAr;
    final definition = isArabic
        ? artifact.definitionShortAr ?? artifact.definitionShortEn
        : artifact.definitionShortEn ?? artifact.definitionShortAr;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          title ?? artifact.artifactId ?? '—',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
        if (artifact.type != null) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              Chip(
                label: Text(artifact.type!),
                backgroundColor: Colors.blue.withValues(alpha: 0.1),
              ),
              const SizedBox(width: 8),
              if (artifact.primaryDomain != null)
                Chip(
                  label: Text(artifact.primaryDomain!),
                  backgroundColor: Colors.purple.withValues(alpha: 0.1),
                ),
            ],
          ),
        ],
        const SizedBox(height: 16),
        Text(
          l10n.definition,
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 4),
        Text(definition ?? l10n.noDefinition),
        const Divider(height: 32),
        if (view.tags.isNotEmpty) ...[
          Text(
            l10n.tagsHeading,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: view.tags
                .map(
                  (t) => Chip(
                    label: Text('${t.tagType}: ${t.tagValue}'),
                    backgroundColor: Colors.grey.shade200,
                  ),
                )
                .toList(),
          ),
          const Divider(height: 32),
        ],
        if (view.mappings.isNotEmpty) ...[
          Text(
            l10n.mappingsHeading,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          ...view.mappings.map(
            (m) => ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text('${m.framework} ${m.version}'),
              subtitle: Text(
                '${l10n.referenceLabel}: ${m.reference} '
                '(${m.mappingStrength})',
              ),
              leading: const Icon(Icons.bookmark_outline),
            ),
          ),
          const Divider(height: 32),
        ],
        if (view.relationships.isNotEmpty) ...[
          Text(
            l10n.relationshipsHeading,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          ...view.relationships.map(
            (r) => ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(r.relationType),
              subtitle: Text(
                r.sourceId == artifact.artifactId
                    ? '${l10n.targetLabel}: ${r.targetId}'
                    : '${l10n.sourceLabel}: ${r.sourceId}',
              ),
              leading: const Icon(Icons.link),
            ),
          ),
          const SizedBox(height: 32),
        ],
      ],
    );
  }

  Widget _buildAssessmentTab(ProfileArtifactView view) {
    final l10n = AppLocalizations.of(context)!;
    final artifact = view.artifact;
    return Form(
      key: _formKey,
      child: SingleChildScrollView(
        key: const Key('assessmentScroll'),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _section(l10n.operationalState),
            _dropdown(
              fieldKey: const Key('implementationStatus'),
              label: l10n.implementationStatus,
              value: _implementationStatus,
              values: _implementationStatuses,
              onChanged: (value) =>
                  setState(() => _implementationStatus = value),
            ),
            _dropdown(
              label: l10n.verificationStatus,
              value: _verificationStatus,
              values: _verificationStatuses,
              onChanged: (value) => setState(() => _verificationStatus = value),
            ),
            _dropdown(
              label: l10n.effectivenessLabel,
              value: _effectiveness,
              values: _effectivenessValues,
              onChanged: (value) => setState(() => _effectiveness = value),
            ),
            Card(
              child: ListTile(
                leading: const Icon(Icons.rule_folder_outlined),
                title: Text(l10n.exceptionState),
                subtitle: Text(artifact.exceptionStatus ?? 'EXC-NONE'),
                trailing: Tooltip(
                  message: l10n.exceptionManagedTooltip,
                  child: const Icon(Icons.lock_outline),
                ),
              ),
            ),
            const SizedBox(height: 20),
            _section(l10n.ownershipPlanning),
            _dropdown(
              label: l10n.currentMaturityLevel,
              value: _maturityLevel,
              values: _maturityLevels,
              required: false,
              onChanged: (value) => setState(() => _maturityLevel = value),
            ),
            SwitchListTile(
              value: _usePriorityOverride,
              title: Text(l10n.overrideCatalogPriority),
              subtitle: Text(
                '${l10n.effectiveNow}: '
                '${artifact.effectivePriority ?? '—'}',
              ),
              onChanged: (value) => setState(() {
                _usePriorityOverride = value;
                if (value) {
                  _priorityOverride ??=
                      artifact.effectivePriority ?? 'PRI-MEDIUM';
                }
              }),
            ),
            if (_usePriorityOverride)
              _dropdown(
                label: l10n.customPriority,
                value: _priorityOverride,
                values: _priorities,
                onChanged: (value) => setState(() => _priorityOverride = value),
              ),
            SwitchListTile(
              value: _useReviewOverride,
              title: Text(l10n.overrideReviewFrequency),
              subtitle: Text(
                '${l10n.effectiveNow}: '
                '${artifact.effectiveReviewFrequency ?? '—'}',
              ),
              onChanged: (value) => setState(() {
                _useReviewOverride = value;
                if (value) {
                  _reviewFrequencyOverride ??=
                      artifact.effectiveReviewFrequency ?? 'AD-HOC';
                }
              }),
            ),
            if (_useReviewOverride)
              _dropdown(
                label: l10n.customReviewFrequency,
                value: _reviewFrequencyOverride,
                values: _reviewFrequencies,
                onChanged: (value) =>
                    setState(() => _reviewFrequencyOverride = value),
              ),
            TextFormField(
              controller: _owner,
              decoration: InputDecoration(labelText: l10n.assignedOwner),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _dueDate,
              readOnly: true,
              onTap: _pickDueDate,
              decoration: InputDecoration(
                labelText: l10n.dueDate,
                suffixIcon: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (_dueDate.text.isNotEmpty)
                      IconButton(
                        tooltip: l10n.clearDate,
                        onPressed: () => setState(_dueDate.clear),
                        icon: const Icon(Icons.clear),
                      ),
                    const Icon(Icons.calendar_today_outlined),
                    const SizedBox(width: 12),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _notes,
              minLines: 2,
              maxLines: 4,
              decoration: InputDecoration(labelText: l10n.currentStateNotes),
            ),
            const SizedBox(height: 20),
            _section(l10n.newAssessmentRecord),
            TextFormField(
              key: const Key('assessmentAssessor'),
              controller: _assessor,
              decoration: InputDecoration(labelText: l10n.assessorName),
              validator: (value) => value == null || value.trim().isEmpty
                  ? l10n.assessorRequired
                  : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              key: const Key('assessmentScore'),
              controller: _score,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: InputDecoration(labelText: l10n.scoreLabel),
              validator: (value) {
                if (value == null || value.trim().isEmpty) return null;
                final score = num.tryParse(value.trim());
                if (score == null || score < 0 || score > 100) {
                  return l10n.scoreValidation;
                }
                return null;
              },
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _comments,
              minLines: 2,
              maxLines: 4,
              decoration: InputDecoration(labelText: l10n.assessmentComment),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              key: const Key('saveAssessment'),
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.save_outlined),
              label: Text(l10n.saveAssessment),
            ),
            const SizedBox(height: 28),
            KeyedSubtree(
              key: const Key('assessmentHistory'),
              child: _section(
                '${l10n.assessmentHistory} (${view.assessments.length})',
              ),
            ),
            if (view.assessments.isEmpty)
              Text(l10n.noPreviousAssessments)
            else
              ...view.assessments.map(_assessmentCard),
            const Divider(),
            _buildExceptionSection(view),
          ],
        ),
      ),
    );
  }

  Widget _buildExceptionSection(ProfileArtifactView view) {
    final l10n = AppLocalizations.of(context)!;
    final status = view.artifact.exceptionStatus ?? 'EXC-NONE';
    final isExempt = status != 'EXC-NONE';

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Icon(
                isExempt ? Icons.warning_amber_rounded : Icons.shield_outlined,
                color: isExempt ? Colors.orange : Colors.grey,
              ),
              const SizedBox(width: 8),
              Text(
                '${l10n.exceptionState}: $status',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: isExempt ? Colors.orange : Colors.grey,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: () async {
              final profileArtifactId = view.artifact.profileArtifactId;
              if (profileArtifactId == null) return;
              final manager = ExceptionManager();
              final existing = await manager.getDraftForArtifact(
                profileArtifactId,
              );
              if (!mounted) return;

              final result = await showDialog<ExceptionRecord>(
                context: context,
                builder: (_) => ExceptionRequestDialog(
                  profileArtifactId: profileArtifactId,
                  existingRecord: existing,
                ),
              );

              if (result != null) {
                // Refresh the whole screen to reflect new exception status
                setState(() => _loading = true);
                _load();
              }
            },
            icon: const Icon(Icons.rule),
            label: Text(l10n.manageException),
          ),
        ],
      ),
    );
  }

  Widget _section(String title) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Text(title, style: Theme.of(context).textTheme.titleMedium),
  );

  Widget _dropdown({
    Key? fieldKey,
    required String label,
    required String? value,
    required List<String> values,
    required ValueChanged<String?> onChanged,
    bool required = true,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: DropdownButtonFormField<String>(
      key: fieldKey,
      initialValue: values.contains(value) ? value : null,
      decoration: InputDecoration(labelText: label),
      items: [
        for (final item in values)
          DropdownMenuItem(value: item, child: Text(item)),
      ],
      onChanged: onChanged,
      validator: (current) => required && current == null
          ? AppLocalizations.of(context)!.requiredValue(label)
          : null,
    ),
  );

  Widget _assessmentCard(AssessmentRecord assessment) {
    final l10n = AppLocalizations.of(context)!;
    return Card(
      child: ListTile(
        title: Text(
          '${assessment.assessorName ?? '—'} · '
          '${assessment.score ?? l10n.unscored}',
        ),
        subtitle: Text(
          '${assessment.assessmentDate ?? '—'}\n'
          '${assessment.implementationStatus ?? '—'} · '
          '${assessment.verificationStatus ?? '—'} · '
          '${assessment.effectiveness ?? '—'}'
          '${assessment.comments == null || assessment.comments!.isEmpty ? '' : '\n${assessment.comments}'}',
        ),
        isThreeLine: true,
      ),
    );
  }
}
