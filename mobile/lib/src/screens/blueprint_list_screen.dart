import 'package:flutter/material.dart';
import '../../l10n/app_localizations.dart';
import '../../read_model_contract.dart';
import '../client/secure_guide_client.dart';
import 'blueprint_detail_screen.dart';

class BlueprintListScreen extends StatefulWidget {
  const BlueprintListScreen({
    super.key,
    required this.client,
    required this.profileId,
  });

  final SecureGuideClient client;
  final String profileId;

  @override
  State<BlueprintListScreen> createState() => _BlueprintListScreenState();
}

class _BlueprintListScreenState extends State<BlueprintListScreen> {
  BlueprintsView? _view;
  Object? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final view = await widget.client.blueprints(widget.profileId);
      if (!mounted) return;
      setState(() {
        _view = view;
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

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(title: Text(l10n.blueprintsTitle)),
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

    final blueprints = _view?.blueprints ?? [];
    if (blueprints.isEmpty) {
      return Center(child: Text(l10n.noBlueprints));
    }

    return ListView.builder(
      itemCount: blueprints.length,
      itemBuilder: (context, index) {
        final b = blueprints[index];
        final id = b.id;
        if (id == null) return const SizedBox.shrink();

        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: ListTile(
            title: Text(b.title ?? l10n.unnamedBlueprint),
            subtitle: Text(
              '${l10n.statusLabel}: ${b.workflowStatus} - '
              '${l10n.versionLabel}: ${b.version}',
            ),
            trailing: const Icon(Icons.chevron_right),
            onTap: () {
              Navigator.of(context)
                  .push(
                    MaterialPageRoute(
                      builder: (_) => BlueprintDetailScreen(
                        client: widget.client,
                        blueprintId: id,
                      ),
                    ),
                  )
                  .then((_) => _load());
            },
          ),
        );
      },
    );
  }
}
