import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';

import '../../l10n/app_localizations.dart';
import '../client/evidence_manager.dart';

const _evidenceTypes = <String>[
  'DOCUMENT',
  'SCREENSHOT',
  'LOG',
  'REPORT',
  'CONFIG',
  'ATTESTATION',
  'LINK',
  'OTHER',
];

class AddEvidenceSheet extends StatefulWidget {
  const AddEvidenceSheet({
    super.key,
    required this.profileArtifactId,
    required this.profileId,
    required this.manager,
  });

  final String profileArtifactId;
  final String profileId;
  final EvidenceManager manager;

  @override
  State<AddEvidenceSheet> createState() => _AddEvidenceSheetState();
}

class _AddEvidenceSheetState extends State<AddEvidenceSheet> {
  final _descriptionController = TextEditingController();
  final _collectedByController = TextEditingController();
  String _selectedType = 'DOCUMENT';
  File? _selectedFile;
  bool _saving = false;

  @override
  void dispose() {
    _descriptionController.dispose();
    _collectedByController.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.pickFiles();
    if (result != null && result.files.single.path != null) {
      setState(() {
        _selectedFile = File(result.files.single.path!);
      });
    }
  }

  Future<void> _save() async {
    if (_selectedFile == null || _collectedByController.text.trim().isEmpty) {
      return;
    }
    setState(() => _saving = true);
    final l10n = AppLocalizations.of(context)!;

    try {
      await widget.manager.addEvidence(
        profileArtifactId: widget.profileArtifactId,
        profileId: widget.profileId,
        evidenceType: _selectedType,
        file: _selectedFile!,
        collectedBy: _collectedByController.text.trim(),
        description: _descriptionController.text.trim().isEmpty
            ? null
            : _descriptionController.text.trim(),
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.evidenceAddError(e))));
      setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
      ),
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.addEvidenceTitle,
            style: Theme.of(context).textTheme.titleLarge,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            initialValue: _selectedType,
            decoration: InputDecoration(
              labelText: l10n.evidenceType,
              border: const OutlineInputBorder(),
            ),
            items: _evidenceTypes.map((type) {
              return DropdownMenuItem(value: type, child: Text(type));
            }).toList(),
            onChanged: (v) {
              if (v != null) setState(() => _selectedType = v);
            },
          ),
          const SizedBox(height: 16),
          TextField(
            key: const Key('evidence-collected-by'),
            controller: _collectedByController,
            onChanged: (_) => setState(() {}),
            decoration: InputDecoration(
              labelText: l10n.evidenceCollector,
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _descriptionController,
            decoration: InputDecoration(
              labelText: l10n.evidenceDescriptionOptional,
              border: const OutlineInputBorder(),
            ),
            maxLines: 3,
            minLines: 1,
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: _pickFile,
            icon: const Icon(Icons.attach_file),
            label: Text(
              _selectedFile != null
                  ? _selectedFile!.path.split(Platform.pathSeparator).last
                  : l10n.chooseFile,
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed:
                _saving ||
                    _selectedFile == null ||
                    _collectedByController.text.trim().isEmpty
                ? null
                : _save,
            child: _saving
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(l10n.saveEvidence),
          ),
        ],
      ),
    );
  }
}
