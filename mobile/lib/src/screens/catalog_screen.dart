import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../read_model_contract.dart';
import '../client/secure_guide_client.dart';
import 'assessment_screen.dart';
import 'catalog_filter_sheet.dart';

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
  late CatalogFilter _filter;
  String? _locale;

  @override
  void initState() {
    super.initState();
    _filter = CatalogFilter(profileId: widget.profileId);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final locale = Localizations.localeOf(context).languageCode;
    if (_locale == locale) return;
    _locale = locale;
    _view = null;
    _loading = true;
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
        _filter,
        locale: _locale ?? 'ar',
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
      _filter = CatalogFilter.fromJson({
        ..._filter.toJson(),
        'searchQuery': value.trim().isEmpty ? null : value.trim(),
      });
      _view = null;
      _loading = true;
    });
    _load();
  }

  Future<void> _openFilter() async {
    final result = await showModalBottomSheet<CatalogFilter>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => Padding(
        padding: EdgeInsets.only(
          top: MediaQuery.of(context).padding.top + kToolbarHeight,
        ),
        child: CatalogFilterSheet(initialFilter: _filter),
      ),
    );
    if (result != null && mounted) {
      setState(() {
        _filter = result;
        _view = null;
        _loading = true;
      });
      _load();
    }
  }

  Future<void> _select(CatalogItem item) async {
    final id = item.id;
    if (id == null) return;
    final messenger = ScaffoldMessenger.of(context);
    final l10n = AppLocalizations.of(context)!;
    try {
      await widget.client.selectArtifacts([id], profileId: widget.profileId);
      await _load();
    } catch (error) {
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.addToProfileError(error))),
      );
    }
  }

  Future<void> _openAssessment(CatalogItem item) async {
    final id = item.id;
    if (id == null || item.isSelected != true) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => AssessmentScreen(
          client: widget.client,
          artifactId: id,
          profileId: widget.profileId,
        ),
      ),
    );
    if (mounted) await _load();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.catalog),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            tooltip: l10n.filter,
            onPressed: _openFilter,
          ),
        ],
      ),
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
                hintText: l10n.searchHint,
                border: const OutlineInputBorder(),
                suffixIcon:
                    (_filter.searchQuery == null ||
                        _filter.searchQuery!.isEmpty)
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
    final l10n = AppLocalizations.of(context)!;
    if (_loading && _view == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(l10n.catalogLoadError(_error!)),
        ),
      );
    }
    final items = _view?.items ?? const [];
    if (items.isEmpty) {
      return Center(child: Text(l10n.noMatchingArtifacts));
    }
    return ListView.builder(
      itemCount: items.length,
      itemBuilder: (context, index) => _CatalogRow(
        item: items[index],
        onSelect: _select,
        onOpen: _openAssessment,
      ),
    );
  }
}

class _CatalogRow extends StatelessWidget {
  const _CatalogRow({
    required this.item,
    required this.onSelect,
    required this.onOpen,
  });

  final CatalogItem item;
  final Future<void> Function(CatalogItem) onSelect;
  final Future<void> Function(CatalogItem) onOpen;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final selected = item.isSelected == true;
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: ListTile(
        key: ValueKey('catalog-item-${item.id}'),
        onTap: selected ? () => onOpen(item) : null,
        title: Text(item.title ?? item.id ?? '—'),
        subtitle: Text(
          '${item.primaryDomain ?? '—'} · ${item.effectivePriority ?? '—'}',
        ),
        trailing: selected
            ? Tooltip(
                message: l10n.openAssessment,
                child: const Icon(
                  Icons.assignment_outlined,
                  color: Colors.green,
                ),
              )
            : IconButton(
                key: ValueKey('catalog-add-${item.id}'),
                icon: const Icon(Icons.add_circle_outline),
                tooltip: l10n.addToProfile,
                onPressed: () => onSelect(item),
              ),
      ),
    );
  }
}
