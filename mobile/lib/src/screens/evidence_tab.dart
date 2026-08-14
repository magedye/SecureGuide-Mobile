import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../client/evidence_manager.dart';
import 'add_evidence_sheet.dart';

class EvidenceTab extends StatefulWidget {
  const EvidenceTab({
    super.key,
    required this.profileArtifactId,
    required this.profileId,
  });

  final String profileArtifactId;
  final String profileId;

  @override
  State<EvidenceTab> createState() => _EvidenceTabState();
}

class _EvidenceTabState extends State<EvidenceTab> {
  final _manager = EvidenceManager();
  List<EvidenceRecord>? _evidenceList;
  Map<String, EvidenceIntegrity> _integrity = const {};
  Object? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final list = await _manager.getEvidenceForArtifact(
        widget.profileArtifactId,
        profileId: widget.profileId,
      );
      final integrity = <String, EvidenceIntegrity>{};
      for (final record in list) {
        integrity[record.id] = await _manager.verifyEvidence(
          record.id,
          profileId: widget.profileId,
        );
      }
      if (!mounted) return;
      setState(() {
        _evidenceList = list;
        _integrity = integrity;
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

  Future<void> _addEvidence() async {
    final result = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => Padding(
        padding: EdgeInsets.only(
          top: MediaQuery.of(context).padding.top + kToolbarHeight,
        ),
        child: AddEvidenceSheet(
          profileArtifactId: widget.profileArtifactId,
          profileId: widget.profileId,
          manager: _manager,
        ),
      ),
    );
    if (result == true) {
      setState(() => _loading = true);
      _load();
    }
  }

  Future<void> _deleteEvidence(EvidenceRecord record) async {
    final l10n = AppLocalizations.of(context)!;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.deleteEvidenceTitle),
        content: Text(l10n.deleteEvidenceConfirm),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(l10n.cancel),
          ),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: Text(l10n.delete, style: const TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      await _manager.deleteEvidence(record.id, profileId: widget.profileId);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.evidenceDeleted)));
      _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.evidenceDeleteError(e))));
    }
  }

  Future<void> _showEvidenceDetails(EvidenceRecord record) async {
    final messenger = ScaffoldMessenger.of(context);
    final l10n = AppLocalizations.of(context)!;
    try {
      final preview = await _manager.loadPreview(
        record.id,
        profileId: widget.profileId,
      );
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(l10n.evidenceDetails),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '${l10n.evidenceType}: ${record.evidenceType}',
                style: const TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              if (record.description != null) ...[
                Text(record.description!),
                const SizedBox(height: 16),
              ],
              if (record.collectedBy != null) ...[
                Text('${l10n.evidenceCollector}: ${record.collectedBy}'),
                const SizedBox(height: 8),
              ],
              Text(
                '${l10n.evidenceAddedAt}:\n${record.collectedAt}',
                style: const TextStyle(fontSize: 12),
              ),
              const SizedBox(height: 8),
              Text(
                '${l10n.fileSize}: ${record.fileSize ?? 0} bytes',
                style: const TextStyle(fontSize: 12),
              ),
              const SizedBox(height: 8),
              Text(
                '${l10n.sha256Fingerprint}:\n'
                '${record.contentHash ?? "N/A"}',
                style: const TextStyle(fontSize: 10, color: Colors.grey),
              ),
              if (preview.text != null) ...[
                const Divider(height: 24),
                SizedBox(
                  height: 240,
                  width: 420,
                  child: SingleChildScrollView(
                    child: SelectableText(preview.text!),
                  ),
                ),
              ] else if (preview.isImage) ...[
                const Divider(height: 24),
                SizedBox(
                  height: 320,
                  width: 420,
                  child: InteractiveViewer(
                    child: Image.memory(preview.bytes, fit: BoxFit.contain),
                  ),
                ),
              ] else ...[
                const Divider(height: 24),
                Text(l10n.unsupportedEvidencePreview),
              ],
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: Text(l10n.close),
            ),
          ],
        ),
      );
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.evidenceOpenError(error))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
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

    final list = _evidenceList ?? [];

    return Scaffold(
      body: list.isEmpty
          ? Center(child: Text(l10n.noEvidence))
          : ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
              itemCount: list.length,
              separatorBuilder: (_, _) => const Divider(),
              itemBuilder: (context, index) {
                final record = list[index];
                return ListTile(
                  leading: _integrityIcon(record.id),
                  title: Text(record.evidenceType),
                  subtitle: record.description != null
                      ? Text(
                          record.description!,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        )
                      : null,
                  trailing: IconButton(
                    icon: const Icon(Icons.delete, color: Colors.red),
                    onPressed: () => _deleteEvidence(record),
                  ),
                  onTap: _integrity[record.id] == EvidenceIntegrity.valid
                      ? () => _showEvidenceDetails(record)
                      : null,
                );
              },
            ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _addEvidence,
        icon: const Icon(Icons.add),
        label: Text(l10n.addEvidence),
      ),
    );
  }

  Widget _integrityIcon(String evidenceId) {
    final l10n = AppLocalizations.of(context)!;
    final status = _integrity[evidenceId];
    return Tooltip(
      message: switch (status) {
        EvidenceIntegrity.valid => l10n.integrityValid,
        EvidenceIntegrity.missing => l10n.integrityMissing,
        EvidenceIntegrity.corrupted => l10n.integrityCorrupted,
        EvidenceIntegrity.unsafePath => l10n.integrityUnsafePath,
        null => l10n.integrityVerifying,
      },
      child: Icon(
        status == EvidenceIntegrity.valid ? Icons.verified : Icons.gpp_bad,
        color: status == EvidenceIntegrity.valid ? Colors.green : Colors.red,
      ),
    );
  }
}
