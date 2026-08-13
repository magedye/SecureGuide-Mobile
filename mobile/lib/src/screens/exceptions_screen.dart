import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../client/exception_manager.dart';
import '../client/secure_guide_client.dart';
import 'assessment_screen.dart';

class ExceptionsScreen extends StatefulWidget {
  const ExceptionsScreen({
    super.key,
    required this.client,
    required this.profileId,
  });

  final SecureGuideClient client;
  final String profileId;

  @override
  State<ExceptionsScreen> createState() => _ExceptionsScreenState();
}

class _ExceptionsScreenState extends State<ExceptionsScreen> {
  final _manager = ExceptionManager();
  List<Map<String, dynamic>>? _exceptions;
  Object? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final rows = await _manager.listForProfile(widget.profileId);

      if (!mounted) return;
      setState(() {
        _exceptions = rows;
        _error = null;
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

  Future<void> _submit(String exceptionId) async {
    final l10n = AppLocalizations.of(context)!;
    try {
      await _manager.submit(exceptionId);
      await _load();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.exceptionSubmitError(error))));
    }
  }

  Future<void> _approve(String exceptionId) async {
    final l10n = AppLocalizations.of(context)!;
    final controller = TextEditingController();
    final approver = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(l10n.approveExceptionTitle),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: InputDecoration(labelText: l10n.approverName),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () =>
                Navigator.of(dialogContext).pop(controller.text.trim()),
            child: Text(l10n.approve),
          ),
        ],
      ),
    );
    controller.dispose();
    if (approver == null || approver.isEmpty) return;

    try {
      await _manager.approve(exceptionId, approvedBy: approver);
      await _load();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.exceptionApproveError(error))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.exceptionLog)),
      body: _buildBody(),
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

    final items = _exceptions ?? [];
    if (items.isEmpty) {
      return Center(child: Text(l10n.noExceptions));
    }

    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        final artifactTitle = item['artifact_title'] as String?;
        final artifactId = item['artifact_id'] as String?;
        final status = item['exception_status'] as String;
        final workflowStatus = item['workflow_status'] as String;
        final justification = item['justification'] as String;
        final expiry = item['expiry_date'] as String?;
        final exceptionId = item['exception_id'] as String;

        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Column(
            children: [
              ListTile(
                title: Text(artifactTitle ?? artifactId ?? l10n.unknownItem),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 4),
                    Text(
                      '${l10n.workflowLabel}: $workflowStatus — '
                      '${l10n.typeLabel}: $status',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    Text(
                      '${l10n.justificationLabel}: $justification',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (expiry != null)
                      Text(
                        '${l10n.expiryLabel}: $expiry',
                        style: const TextStyle(color: Colors.red),
                      ),
                  ],
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: artifactId == null
                    ? null
                    : () {
                        Navigator.of(context)
                            .push(
                              MaterialPageRoute(
                                builder: (_) => AssessmentScreen(
                                  client: widget.client,
                                  artifactId: artifactId,
                                  profileId: widget.profileId,
                                ),
                              ),
                            )
                            .then((_) => _load());
                      },
              ),
              if (workflowStatus == 'DRAFT' || workflowStatus == 'SUBMITTED')
                Padding(
                  padding: const EdgeInsets.only(
                    left: 16,
                    right: 16,
                    bottom: 12,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      if (workflowStatus == 'DRAFT')
                        FilledButton.tonal(
                          onPressed: () => _submit(exceptionId),
                          child: Text(l10n.submitForReview),
                        ),
                      if (workflowStatus == 'SUBMITTED')
                        FilledButton(
                          onPressed: () => _approve(exceptionId),
                          child: Text(l10n.approve),
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
}
