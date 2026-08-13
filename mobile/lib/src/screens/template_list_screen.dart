import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../read_model_contract.dart';
import '../client/secure_guide_client.dart';
import 'template_detail_screen.dart';

class TemplateListScreen extends StatefulWidget {
  const TemplateListScreen({
    super.key,
    required this.client,
    required this.profileId,
  });

  final SecureGuideClient client;
  final String profileId;

  @override
  State<TemplateListScreen> createState() => _TemplateListScreenState();
}

class _TemplateListScreenState extends State<TemplateListScreen> {
  TemplateView? _view;
  Object? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final view = await widget.client.templates();
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

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.templates), centerTitle: true),
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

    final templates = _view?.templates ?? [];
    if (templates.isEmpty) {
      return Center(child: Text(l10n.noTemplates));
    }

    return ListView.builder(
      itemCount: templates.length,
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemBuilder: (context, index) {
        final t = templates[index];
        return ListTile(
          leading: const Icon(Icons.file_copy_outlined, color: Colors.blue),
          title: Text(t.name ?? t.id ?? l10n.unknownTemplate),
          subtitle: Text(
            t.description ?? t.scopeNote ?? '',
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          trailing: const Icon(Icons.chevron_right),
          onTap: () {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => TemplateDetailScreen(
                  client: widget.client,
                  profileId: widget.profileId,
                  template: t,
                ),
              ),
            );
          },
        );
      },
    );
  }
}
