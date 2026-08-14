import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../../core/database/database_helper.dart';
import '../../l10n/app_localizations.dart';
import '../client/secure_guide_client.dart';

class ProfileSettingsScreen extends StatefulWidget {
  const ProfileSettingsScreen({
    super.key,
    required this.client,
    required this.profileId,
    required this.onProfileArchived,
  });

  final SecureGuideClient client;
  final String profileId;
  final VoidCallback onProfileArchived;

  @override
  State<ProfileSettingsScreen> createState() => _ProfileSettingsScreenState();
}

class _ProfileSettingsScreenState extends State<ProfileSettingsScreen> {
  final _formKey = GlobalKey<FormState>();

  bool _loading = true;
  Object? _error;

  String? _name;
  String? _profileKind;
  String? _organizationSize;
  String? _industry;
  String? _country;
  String? _targetMaturityLevel;
  String? _description;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    try {
      final profilesView = await widget.client.profiles();
      final current = profilesView.profiles.firstWhere(
        (p) => p.id == widget.profileId,
      );

      if (!mounted) return;
      setState(() {
        _name = current.name;
        _profileKind = current.profileKind;
        _organizationSize = current.organizationSize;
        _industry = current.industry;
        _country = current.country;
        _targetMaturityLevel = current.targetMaturityLevel;
        _description = current.description;
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

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    _formKey.currentState!.save();
    final l10n = AppLocalizations.of(context)!;

    setState(() => _loading = true);
    try {
      await widget.client.updateProfile(
        widget.profileId,
        name: _name,
        profileKind: _profileKind,
        organizationSize: _organizationSize,
        industry: _industry,
        country: _country,
        targetMaturityLevel: _targetMaturityLevel,
        clearTargetMaturityLevel: _targetMaturityLevel == null,
        description: _description,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.savedSuccessfully)));
      setState(() => _loading = false);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.saveError(e))));
      setState(() => _loading = false);
    }
  }

  Future<void> _archive() async {
    final l10n = AppLocalizations.of(context)!;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.archiveProfileTitle),
        content: Text(l10n.archiveProfileWarning),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(l10n.cancel),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: Text(l10n.confirm),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    setState(() => _loading = true);
    try {
      await widget.client.archiveProfile(widget.profileId);
      if (!mounted) return;
      widget.onProfileArchived();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.archiveError(e))));
      setState(() => _loading = false);
    }
  }

  Future<void> _backup() async {
    final l10n = AppLocalizations.of(context)!;
    setState(() => _loading = true);
    final temporaryDirectory = await getTemporaryDirectory();
    final temporaryPath = p.join(
      temporaryDirectory.path,
      'secureguide-backup-${DateTime.now().toUtc().millisecondsSinceEpoch}.db',
    );
    try {
      await DatabaseHelper.instance.backupDatabase(temporaryPath);
      final bytes = await File(temporaryPath).readAsBytes();
      final savedPath = await FilePicker.saveFile(
        dialogTitle: l10n.saveBackupDialog,
        fileName: 'secureguide-backup.db',
        bytes: bytes,
      );
      if (!mounted) return;
      if (savedPath != null) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(l10n.backupSaved)));
      }
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.backupError(error))));
    } finally {
      final temporaryFile = File(temporaryPath);
      if (await temporaryFile.exists()) await temporaryFile.delete();
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _restore() async {
    final l10n = AppLocalizations.of(context)!;
    final selection = await FilePicker.pickFiles(
      dialogTitle: l10n.chooseBackupDialog,
      type: FileType.custom,
      allowedExtensions: const ['db'],
    );
    final sourcePath = selection?.files.single.path;
    if (sourcePath == null || !mounted) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.restoreBackupTitle),
        content: Text(l10n.restoreBackupWarning),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(l10n.validateAndRestore),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    setState(() => _loading = true);
    try {
      final result = await DatabaseHelper.instance.restoreDatabase(sourcePath);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.restoreSuccess(result.recoveryPath))),
      );
      widget.onProfileArchived();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.restoreRejected(error))));
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (_error != null) {
      return Scaffold(
        body: Center(child: Text(l10n.errorWithDetails(_error!))),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.profileSettings),
        actions: [
          IconButton(
            icon: const Icon(Icons.save),
            tooltip: l10n.save,
            onPressed: _save,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                initialValue: _name,
                decoration: InputDecoration(
                  labelText: l10n.profileName,
                  border: const OutlineInputBorder(),
                ),
                validator: (value) => value == null || value.trim().isEmpty
                    ? l10n.requiredField
                    : null,
                onSaved: (value) => _name = value?.trim(),
              ),
              const SizedBox(height: 16),
              TextFormField(
                initialValue: _profileKind,
                decoration: InputDecoration(
                  labelText: l10n.profileKind,
                  border: const OutlineInputBorder(),
                ),
                onSaved: (value) => _profileKind = value?.trim(),
              ),
              const SizedBox(height: 16),
              TextFormField(
                initialValue: _organizationSize,
                decoration: InputDecoration(
                  labelText: l10n.organizationSize,
                  border: const OutlineInputBorder(),
                ),
                onSaved: (value) => _organizationSize = value?.trim(),
              ),
              const SizedBox(height: 16),
              TextFormField(
                initialValue: _industry,
                decoration: InputDecoration(
                  labelText: l10n.industry,
                  border: const OutlineInputBorder(),
                ),
                onSaved: (value) => _industry = value?.trim(),
              ),
              const SizedBox(height: 16),
              TextFormField(
                initialValue: _country,
                decoration: InputDecoration(
                  labelText: l10n.country,
                  border: const OutlineInputBorder(),
                ),
                onSaved: (value) => _country = value?.trim(),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: _targetMaturityLevel,
                decoration: InputDecoration(
                  labelText: l10n.targetMaturity,
                  border: const OutlineInputBorder(),
                ),
                items: [
                  DropdownMenuItem(value: null, child: Text(l10n.notSpecified)),
                  DropdownMenuItem(
                    value: 'INITIAL',
                    child: Text(l10n.maturityInitial),
                  ),
                  DropdownMenuItem(
                    value: 'REPEATABLE',
                    child: Text(l10n.maturityRepeatable),
                  ),
                  DropdownMenuItem(
                    value: 'DEFINED',
                    child: Text(l10n.maturityDefined),
                  ),
                  DropdownMenuItem(
                    value: 'MANAGED',
                    child: Text(l10n.maturityManaged),
                  ),
                  DropdownMenuItem(
                    value: 'OPTIMIZED',
                    child: Text(l10n.maturityOptimized),
                  ),
                ],
                onChanged: (value) =>
                    setState(() => _targetMaturityLevel = value),
                onSaved: (value) => _targetMaturityLevel = value,
              ),
              const SizedBox(height: 16),
              TextFormField(
                initialValue: _description,
                maxLines: 3,
                decoration: InputDecoration(
                  labelText: l10n.descriptionLabel,
                  border: const OutlineInputBorder(),
                ),
                onSaved: (value) => _description = value?.trim(),
              ),
              const SizedBox(height: 48),
              Text(
                l10n.backupRestore,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                key: const Key('backup-database'),
                icon: const Icon(Icons.backup_outlined),
                label: Text(l10n.createLocalBackup),
                onPressed: _backup,
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                key: const Key('restore-database'),
                icon: const Icon(Icons.restore_page_outlined),
                label: Text(l10n.restoreBackup),
                onPressed: _restore,
              ),
              const SizedBox(height: 48),
              OutlinedButton.icon(
                icon: const Icon(Icons.delete, color: Colors.red),
                label: Text(
                  l10n.archiveProfile,
                  style: const TextStyle(color: Colors.red),
                ),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.all(16),
                  side: const BorderSide(color: Colors.red),
                ),
                onPressed: _archive,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
