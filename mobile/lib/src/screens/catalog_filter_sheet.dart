import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../read_model_contract.dart';

class CatalogFilterSheet extends StatefulWidget {
  const CatalogFilterSheet({super.key, required this.initialFilter});

  final CatalogFilter initialFilter;

  @override
  State<CatalogFilterSheet> createState() => _CatalogFilterSheetState();
}

class _CatalogFilterSheetState extends State<CatalogFilterSheet> {
  static const _subDomains = <String>[
    'SD-01.01',
    'SD-01.02',
    'SD-01.03',
    'SD-01.04',
    'SD-01.05',
    'SD-02.01',
    'SD-02.02',
    'SD-02.03',
    'SD-02.04',
    'SD-02.05',
    'SD-03.01',
    'SD-03.02',
    'SD-03.03',
    'SD-03.04',
    'SD-03.05',
    'SD-04.01',
    'SD-04.02',
    'SD-04.03',
    'SD-04.04',
    'SD-04.05',
    'SD-05.01',
    'SD-05.02',
    'SD-05.03',
    'SD-05.04',
    'SD-05.05',
    'SD-06.01',
    'SD-06.02',
    'SD-06.03',
    'SD-06.04',
    'SD-06.05',
    'SD-07.01',
    'SD-07.02',
    'SD-07.03',
    'SD-07.04',
    'SD-07.05',
    'SD-08.01',
    'SD-08.02',
    'SD-08.03',
    'SD-08.04',
    'SD-08.05',
  ];

  late CatalogFilter _filter;

  @override
  void initState() {
    super.initState();
    _filter = widget.initialFilter;
  }

  void _toggleListItem(
    List<String>? current,
    String value,
    void Function(List<String>?) update,
  ) {
    final list = List<String>.from(current ?? []);
    if (list.contains(value)) {
      list.remove(value);
    } else {
      list.add(value);
    }
    update(list.isEmpty ? null : list);
  }

  Widget _buildFilterChips(
    String title,
    List<String> options,
    List<String>? currentSelection,
    void Function(List<String>?) onChanged,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: options.map((option) {
            final isSelected = currentSelection?.contains(option) ?? false;
            return FilterChip(
              label: Text(option),
              selected: isSelected,
              onSelected: (_) {
                setState(() {
                  _toggleListItem(currentSelection, option, onChanged);
                });
              },
            );
          }).toList(),
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final selectedDomains = _filter.primaryDomains;
    final visibleSubDomains = selectedDomains == null
        ? _subDomains
        : _subDomains
              .where(
                (subDomain) => selectedDomains.any(
                  (domain) => subDomain.startsWith('$domain.'),
                ),
              )
              .toList(growable: false);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                l10n.catalogFiltersTitle,
                style: const TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const Divider(),
          Expanded(
            child: ListView(
              children: [
                _buildFilterChips(
                  l10n.artifactTypeFilter,
                  [
                    'ART-REQ',
                    'ART-OBJ',
                    'ART-PRI',
                    'ART-POL',
                    'ART-STD',
                    'ART-CTR',
                    'ART-CTE',
                    'ART-PRO',
                    'ART-PRC',
                    'ART-PRG',
                    'ART-PLN',
                    'ART-TSK',
                    'ART-CFG',
                    'ART-RUL',
                    'ART-EVD',
                    'ART-MET',
                    'ART-EXC',
                    'ART-RSK',
                    'ART-AST',
                    'ART-THR',
                    'ART-VUL',
                    'ART-OWN',
                  ],
                  _filter.types,
                  (v) => _filter = CatalogFilter.fromJson({
                    ..._filter.toJson(),
                    'types': v,
                  }),
                ),
                _buildFilterChips(
                  l10n.primaryDomainFilter,
                  [
                    'SD-01',
                    'SD-02',
                    'SD-03',
                    'SD-04',
                    'SD-05',
                    'SD-06',
                    'SD-07',
                    'SD-08',
                  ],
                  _filter.primaryDomains,
                  (v) {
                    final retainedSubDomains = _filter.subDomains
                        ?.where(
                          (subDomain) =>
                              v == null ||
                              v.any(
                                (domain) => subDomain.startsWith('$domain.'),
                              ),
                        )
                        .toList(growable: false);
                    _filter = CatalogFilter.fromJson({
                      ..._filter.toJson(),
                      'primaryDomains': v,
                      'subDomains': retainedSubDomains?.isEmpty == true
                          ? null
                          : retainedSubDomains,
                    });
                  },
                ),
                _buildFilterChips(
                  l10n.subDomainFilter,
                  visibleSubDomains,
                  _filter.subDomains,
                  (v) => _filter = CatalogFilter.fromJson({
                    ..._filter.toJson(),
                    'subDomains': v,
                  }),
                ),
                _buildFilterChips(
                  l10n.priorityFilter,
                  ['PRI-CRITICAL', 'PRI-HIGH', 'PRI-MEDIUM', 'PRI-LOW'],
                  _filter.priorities,
                  (v) => _filter = CatalogFilter.fromJson({
                    ..._filter.toJson(),
                    'priorities': v,
                  }),
                ),
                _buildFilterChips(
                  l10n.testabilityFilter,
                  ['TST-AUTO', 'TST-MAN', 'TST-DOC', 'TST-INT', 'TST-NA'],
                  _filter.testability != null ? [_filter.testability!] : null,
                  (v) => _filter = CatalogFilter.fromJson({
                    ..._filter.toJson(),
                    'testability': v?.firstOrNull,
                  }),
                ),
                _buildFilterChips(
                  l10n.implementationStatus,
                  [
                    'STS-NOT-APPLIED',
                    'STS-PARTIAL',
                    'STS-FULL',
                    'STS-PLANNED',
                    'STS-NEEDS-IMPROVEMENT',
                  ],
                  _filter.implementationStatus != null
                      ? [_filter.implementationStatus!]
                      : null,
                  (v) => _filter = CatalogFilter.fromJson({
                    ..._filter.toJson(),
                    'implementationStatus': v?.firstOrNull,
                  }),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () {
                    setState(() {
                      _filter = CatalogFilter(
                        profileId: _filter.profileId,
                        searchQuery: _filter.searchQuery,
                      );
                    });
                  },
                  child: Text(l10n.clearFilters),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: FilledButton(
                  onPressed: () => Navigator.of(context).pop(_filter),
                  child: Text(l10n.applyFilters),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
