import 'package:flutter/material.dart';
import '../../l10n/app_localizations.dart';
import '../../read_model_contract.dart';
import '../client/exception_manager.dart';

const _exceptionStatuses = <String>[
  'EXC-NOT-APPLICABLE',
  'EXC-RISK-ACCEPTED',
  'EXC-DEFERRED',
  'EXC-UNAVAILABLE',
];

class ExceptionRequestDialog extends StatefulWidget {
  const ExceptionRequestDialog({
    super.key,
    required this.profileArtifactId,
    this.existingRecord,
  });

  final String profileArtifactId;
  final ExceptionRecord? existingRecord;

  @override
  State<ExceptionRequestDialog> createState() => _ExceptionRequestDialogState();
}

class _ExceptionRequestDialogState extends State<ExceptionRequestDialog> {
  final _manager = ExceptionManager();
  final _justification = TextEditingController();
  final _riskAcceptedBy = TextEditingController();
  final _expiryDate = TextEditingController();

  late String _status;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _status =
        widget.existingRecord?.exceptionStatus ?? _exceptionStatuses.first;
    _justification.text = widget.existingRecord?.justification ?? '';
    _riskAcceptedBy.text = widget.existingRecord?.riskAcceptedBy ?? '';
    _expiryDate.text = widget.existingRecord?.expiryDate ?? '';
  }

  @override
  void dispose() {
    _justification.dispose();
    _riskAcceptedBy.dispose();
    _expiryDate.dispose();
    super.dispose();
  }

  Future<void> _pickExpiryDate() async {
    final initial = DateTime.tryParse(_expiryDate.text) ?? DateTime.now();
    final selected = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
    );
    if (selected == null) return;
    _expiryDate.text = selected.toIso8601String().substring(0, 10);
  }

  Future<void> _save() async {
    final l10n = AppLocalizations.of(context)!;
    final justification = _justification.text.trim();
    if (justification.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.exceptionJustificationRequired)),
      );
      return;
    }

    setState(() => _saving = true);
    try {
      final record = await _manager.saveDraft(
        profileArtifactId: widget.profileArtifactId,
        exceptionStatus: _status,
        justification: justification,
        expiryDate: _expiryDate.text.trim().isEmpty
            ? null
            : _expiryDate.text.trim(),
        riskAcceptedBy: _riskAcceptedBy.text.trim().isEmpty
            ? null
            : _riskAcceptedBy.text.trim(),
      );
      if (!mounted) return;
      Navigator.of(context).pop(record);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.exceptionSaveError(e))));
      setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return AlertDialog(
      title: Text(l10n.manageException),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            DropdownButtonFormField<String>(
              initialValue: _status,
              decoration: InputDecoration(labelText: l10n.exceptionType),
              items: _exceptionStatuses
                  .map((s) => DropdownMenuItem(value: s, child: Text(s)))
                  .toList(),
              onChanged: (v) {
                if (v != null) setState(() => _status = v);
              },
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _justification,
              decoration: InputDecoration(
                labelText: l10n.justificationRequiredLabel,
              ),
              maxLines: 3,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _expiryDate,
              decoration: InputDecoration(
                labelText: l10n.expiryDate,
                suffixIcon: IconButton(
                  icon: const Icon(Icons.calendar_today),
                  onPressed: _pickExpiryDate,
                ),
              ),
              readOnly: true,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _riskAcceptedBy,
              decoration: InputDecoration(
                labelText: l10n.riskAcceptedByOptional,
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l10n.cancel),
        ),
        ElevatedButton(
          onPressed: _saving ? null : _save,
          child: _saving
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(l10n.saveDraft),
        ),
      ],
    );
  }
}
