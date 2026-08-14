import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../read_model_contract.dart';
import '../client/secure_guide_client.dart';

class TemplateDetailScreen extends StatefulWidget {
  const TemplateDetailScreen({
    super.key,
    required this.client,
    required this.profileId,
    required this.template,
  });

  final SecureGuideClient client;
  final String profileId;
  final TemplateSummary template;

  @override
  State<TemplateDetailScreen> createState() => _TemplateDetailScreenState();
}

class _TemplateDetailScreenState extends State<TemplateDetailScreen> {
  CatalogView? _view;
  Object? _error;
  bool _loading = true;
  bool _applying = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final templateId = widget.template.id;
      if (templateId == null) throw Exception('Invalid template ID');

      final view = await widget.client.templateItems(templateId);
      if (!mounted) return;
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

  Future<void> _applyTemplate() async {
    final templateId = widget.template.id;
    if (templateId == null) return;

    final actor = await _requestActor();
    if (actor == null || !mounted) return;

    setState(() => _applying = true);
    final l10n = AppLocalizations.of(context)!;
    try {
      await widget.client.applyTemplate(
        widget.profileId,
        templateId,
        appliedBy: actor,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.templateApplied)));
      Navigator.of(context).pop(); // Go back to template list
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l10n.templateApplyError(e))));
    } finally {
      if (mounted) setState(() => _applying = false);
    }
  }

  Future<String?> _requestActor() async {
    final l10n = AppLocalizations.of(context)!;
    final controller = TextEditingController();
    var showError = false;
    final actor = await showDialog<String>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text(l10n.applicationActorAudit),
          content: TextField(
            key: const Key('template-applied-by'),
            controller: controller,
            autofocus: true,
            decoration: InputDecoration(
              labelText: l10n.actorName,
              errorText: showError ? l10n.actorRequiredAudit : null,
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(l10n.cancel),
            ),
            FilledButton(
              onPressed: () {
                final value = controller.text.trim();
                if (value.isEmpty) {
                  setDialogState(() => showError = true);
                  return;
                }
                Navigator.pop(context, value);
              },
              child: Text(l10n.apply),
            ),
          ],
        ),
      ),
    );
    controller.dispose();
    return actor;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.template.name ?? l10n.templateDetails),
        centerTitle: true,
      ),
      body: Column(
        children: [
          _buildHeader(),
          const Divider(),
          Expanded(child: _buildBody()),
        ],
      ),
      bottomNavigationBar: _buildBottomBar(),
    );
  }

  Widget _buildHeader() {
    final l10n = AppLocalizations.of(context)!;
    final t = widget.template;
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(t.name ?? '', style: Theme.of(context).textTheme.titleLarge),
          if (t.description != null && t.description!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(t.description!),
          ],
          if (t.scopeNote != null && t.scopeNote!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              '${l10n.applicationScope}: ${t.scopeNote}',
              style: const TextStyle(color: Colors.grey),
            ),
          ],
          if (t.version != null) ...[
            const SizedBox(height: 4),
            Text(
              '${l10n.versionLabel}: ${t.version}',
              style: const TextStyle(color: Colors.grey),
            ),
          ],
        ],
      ),
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

    final items = _view?.items ?? [];
    if (items.isEmpty) {
      return Center(child: Text(l10n.noTemplateItems));
    }

    return ListView.separated(
      itemCount: items.length,
      separatorBuilder: (_, _) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final item = items[index];
        return ListTile(
          title: Text(item.title ?? item.id ?? ''),
          subtitle: item.definitionShort != null
              ? Text(
                  item.definitionShort!,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                )
              : null,
          trailing: Text(
            item.primaryDomain ?? '',
            style: const TextStyle(fontSize: 12, color: Colors.blueGrey),
          ),
        );
      },
    );
  }

  Widget _buildBottomBar() {
    final l10n = AppLocalizations.of(context)!;
    final count = _view?.items.length ?? 0;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: ElevatedButton.icon(
          onPressed: (_loading || _error != null || count == 0 || _applying)
              ? null
              : _applyTemplate,
          icon: _applying
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Icon(Icons.add_task),
          label: Text('${l10n.applyTemplate} ($count ${l10n.artifactCount})'),
          style: ElevatedButton.styleFrom(
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
        ),
      ),
    );
  }
}
