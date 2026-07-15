import 'package:flutter/material.dart';

import '../../read_model_contract.dart';
import '../client/secure_guide_client.dart';

/// Browse the master catalog for the active profile and select artifacts into
/// it. Binds to [CatalogView]/[CatalogItem]; selection is a governed write via
/// [SecureGuideClient.selectArtifacts] — no rules run here. Loaded state is held
/// explicitly (not via FutureBuilder) so a post-write reload deterministically
/// re-renders the affected row.
class CatalogScreen extends StatefulWidget {
  const CatalogScreen({super.key, required this.client, this.profileId});

  final SecureGuideClient client;
  final String? profileId;

  @override
  State<CatalogScreen> createState() => _CatalogScreenState();
}

class _CatalogScreenState extends State<CatalogScreen> {
  final _searchController = TextEditingController();
  CatalogView? _view;
  Object? _error;
  bool _loading = true;
  String _query = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final view = await widget.client.catalog(
        profileId: widget.profileId,
        query: _query.isEmpty ? null : _query,
        limit: 100,
      );
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

  void _search(String value) {
    setState(() {
      _query = value.trim();
      _view = null;
      _loading = true;
    });
    _load();
  }

  Future<void> _select(CatalogItem item) async {
    final id = item.id;
    if (id == null) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await widget.client.selectArtifacts([id], profileId: widget.profileId);
      await _load();
    } catch (error) {
      messenger.showSnackBar(SnackBar(content: Text('تعذّرت الإضافة: $error')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الكتالوج')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: TextField(
              controller: _searchController,
              textInputAction: TextInputAction.search,
              onSubmitted: _search,
              decoration: InputDecoration(
                prefixIcon: const Icon(Icons.search),
                hintText: 'بحث في الكتالوج',
                border: const OutlineInputBorder(),
                suffixIcon: _query.isEmpty
                    ? null
                    : IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          _search('');
                        },
                      ),
              ),
            ),
          ),
          Expanded(child: _body()),
        ],
      ),
    );
  }

  Widget _body() {
    if (_loading && _view == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text('تعذّر تحميل الكتالوج: $_error'),
        ),
      );
    }
    final items = _view?.items ?? const [];
    if (items.isEmpty) {
      return const Center(child: Text('لا توجد عناصر مطابقة.'));
    }
    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (context, index) =>
          _CatalogRow(item: items[index], onSelect: _select),
    );
  }
}

class _CatalogRow extends StatelessWidget {
  const _CatalogRow({required this.item, required this.onSelect});

  final CatalogItem item;
  final Future<void> Function(CatalogItem) onSelect;

  @override
  Widget build(BuildContext context) {
    final selected = item.isSelected == true;
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: ListTile(
        title: Text(item.title ?? item.id ?? '—'),
        subtitle: Text(
          '${item.primaryDomain ?? '—'} · ${item.effectivePriority ?? '—'}',
        ),
        trailing: selected
            ? const Icon(Icons.check_circle, color: Colors.green)
            : IconButton(
                icon: const Icon(Icons.add_circle_outline),
                tooltip: 'إضافة إلى الملف',
                onPressed: () => onSelect(item),
              ),
      ),
    );
  }
}
