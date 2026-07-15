import 'package:flutter/material.dart';

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
  final _assessor = TextEditingController(text: 'app-user');
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
      messenger.showSnackBar(const SnackBar(content: Text('تم حفظ التقييم.')));
    } catch (error) {
      if (!mounted) return;
      setState(() => _saving = false);
      messenger.showSnackBar(
        SnackBar(content: Text('تعذّر حفظ التقييم: $error')),
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
    return Scaffold(
      appBar: AppBar(title: const Text('تقييم العنصر')),
      body: _body(),
    );
  }

  Widget _body() {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('تعذّر تحميل العنصر: $_error', textAlign: TextAlign.center),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: _load,
                child: const Text('إعادة المحاولة'),
              ),
            ],
          ),
        ),
      );
    }
    final view = _view!;
    final artifact = view.artifact;
    return Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            artifact.titleAr ?? artifact.titleEn ?? artifact.artifactId ?? '—',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 4),
          Text(
            '${artifact.type ?? '—'} · ${artifact.primaryDomain ?? '—'} · ${artifact.subDomain ?? '—'}',
          ),
          if ((artifact.definitionShortAr ?? artifact.definitionShortEn) !=
              null) ...[
            const SizedBox(height: 12),
            Text(artifact.definitionShortAr ?? artifact.definitionShortEn!),
          ],
          const SizedBox(height: 20),
          _section('الحالة التشغيلية'),
          _dropdown(
            label: 'حالة التطبيق',
            value: _implementationStatus,
            values: _implementationStatuses,
            onChanged: (value) => setState(() => _implementationStatus = value),
          ),
          _dropdown(
            label: 'حالة التحقق',
            value: _verificationStatus,
            values: _verificationStatuses,
            onChanged: (value) => setState(() => _verificationStatus = value),
          ),
          _dropdown(
            label: 'الفعالية',
            value: _effectiveness,
            values: _effectivenessValues,
            onChanged: (value) => setState(() => _effectiveness = value),
          ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.rule_folder_outlined),
              title: const Text('حالة الاستثناء'),
              subtitle: Text(artifact.exceptionStatus ?? 'EXC-NONE'),
              trailing: const Tooltip(
                message: 'تُدار عبر مسار اعتماد الاستثناءات',
                child: Icon(Icons.lock_outline),
              ),
            ),
          ),
          const SizedBox(height: 20),
          _section('الملكية والتخطيط'),
          _dropdown(
            label: 'مستوى النضج الحالي',
            value: _maturityLevel,
            values: _maturityLevels,
            required: false,
            onChanged: (value) => setState(() => _maturityLevel = value),
          ),
          SwitchListTile(
            value: _usePriorityOverride,
            title: const Text('تجاوز أولوية الكتالوج/القالب'),
            subtitle: Text(
              'الفعالة الآن: ${artifact.effectivePriority ?? '—'}',
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
              label: 'الأولوية المخصصة',
              value: _priorityOverride,
              values: _priorities,
              onChanged: (value) => setState(() => _priorityOverride = value),
            ),
          SwitchListTile(
            value: _useReviewOverride,
            title: const Text('تجاوز تكرار المراجعة'),
            subtitle: Text(
              'الفعال الآن: ${artifact.effectiveReviewFrequency ?? '—'}',
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
              label: 'تكرار المراجعة المخصص',
              value: _reviewFrequencyOverride,
              values: _reviewFrequencies,
              onChanged: (value) =>
                  setState(() => _reviewFrequencyOverride = value),
            ),
          TextFormField(
            controller: _owner,
            decoration: const InputDecoration(labelText: 'المالك المعيّن'),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _dueDate,
            readOnly: true,
            onTap: _pickDueDate,
            decoration: InputDecoration(
              labelText: 'تاريخ الاستحقاق',
              suffixIcon: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (_dueDate.text.isNotEmpty)
                    IconButton(
                      tooltip: 'مسح التاريخ',
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
            decoration: const InputDecoration(
              labelText: 'ملاحظات الحالة الحالية',
            ),
          ),
          const SizedBox(height: 20),
          _section('سجل التقييم الجديد'),
          TextFormField(
            key: const Key('assessmentAssessor'),
            controller: _assessor,
            decoration: const InputDecoration(labelText: 'اسم المقيّم'),
            validator: (value) => value == null || value.trim().isEmpty
                ? 'اسم المقيّم مطلوب'
                : null,
          ),
          const SizedBox(height: 12),
          TextFormField(
            key: const Key('assessmentScore'),
            controller: _score,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(labelText: 'الدرجة (0–100)'),
            validator: (value) {
              if (value == null || value.trim().isEmpty) return null;
              final score = num.tryParse(value.trim());
              if (score == null || score < 0 || score > 100) {
                return 'أدخل درجة بين 0 و100';
              }
              return null;
            },
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _comments,
            minLines: 2,
            maxLines: 4,
            decoration: const InputDecoration(labelText: 'تعليق التقييم'),
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
            label: const Text('حفظ التقييم'),
          ),
          const SizedBox(height: 28),
          KeyedSubtree(
            key: const Key('assessmentHistory'),
            child: _section('سجل التقييمات (${view.assessments.length})'),
          ),
          if (view.assessments.isEmpty)
            const Text('لا توجد تقييمات سابقة.')
          else
            ...view.assessments.map(_assessmentCard),
        ],
      ),
    );
  }

  Widget _section(String title) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Text(title, style: Theme.of(context).textTheme.titleMedium),
  );

  Widget _dropdown({
    required String label,
    required String? value,
    required List<String> values,
    required ValueChanged<String?> onChanged,
    bool required = true,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: DropdownButtonFormField<String>(
      initialValue: values.contains(value) ? value : null,
      decoration: InputDecoration(labelText: label),
      items: [
        for (final item in values)
          DropdownMenuItem(value: item, child: Text(item)),
      ],
      onChanged: onChanged,
      validator: (current) =>
          required && current == null ? '$label مطلوب' : null,
    ),
  );

  Widget _assessmentCard(AssessmentRecord assessment) => Card(
    child: ListTile(
      title: Text(
        '${assessment.assessorName ?? '—'} · ${assessment.score ?? 'بلا درجة'}',
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
