import 'dart:convert';
import 'dart:io';

import 'package:secureguide_mobile/read_model_contract.dart';
import 'package:secureguide_mobile/src/client/secure_guide_client.dart';

/// Load a shared golden fixture by surface name (resolves from the package dir
/// or the repo root). The same fixtures the Python + contract tests are pinned
/// to, so widget tests exercise the real wire shapes.
Map<String, dynamic> loadGolden(String name) {
  const candidates = [
    '../tests/fixtures/read_models/',
    'tests/fixtures/read_models/',
  ];
  for (final dir in candidates) {
    final file = File('$dir$name.json');
    if (file.existsSync()) {
      return jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
    }
  }
  throw StateError('golden fixture "$name" not found (cwd=${Directory.current.path})');
}

/// In-memory [SecureGuideClient] for widget tests: no sidecar, no network.
/// Reads return canned views; writes mutate local state and are recorded so a
/// test can assert the UI took the governed write path.
class FakeSecureGuideClient implements SecureGuideClient {
  FakeSecureGuideClient({
    required this.dashboardView,
    required List<ProfileSummary> profiles,
    List<Map<String, dynamic>> catalogItems = const [],
  })  : _profiles = List.of(profiles),
        _catalogItems =
            catalogItems.map((m) => Map<String, dynamic>.of(m)).toList(),
        _selected = {
          for (final m in catalogItems)
            if (m['isSelected'] == true) m['id'] as String,
        };

  final DashboardView dashboardView;
  List<ProfileSummary> _profiles;
  final List<Map<String, dynamic>> _catalogItems;
  final Set<String> _selected;

  ProfileSummary? lastCreated;
  String? lastActivated;
  List<String>? lastSelected;

  @override
  Future<ProfilesView> profiles() async => ProfilesView(profiles: List.of(_profiles));

  @override
  Future<DashboardView> dashboard({String? profileId}) async => dashboardView;

  @override
  Future<CatalogView> catalog({
    String? profileId,
    String? query,
    String locale = 'en',
    bool selectedOnly = false,
    int limit = 100,
    int offset = 0,
  }) async {
    var items = _catalogItems;
    if (query != null && query.trim().isNotEmpty) {
      final needle = query.toLowerCase();
      items = items
          .where((m) => (m['title'] as String? ?? '').toLowerCase().contains(needle))
          .toList();
    }
    final rendered = [
      for (final m in items) {...m, 'isSelected': _selected.contains(m['id'])},
    ];
    return CatalogView.fromJson({
      'contractVersion': kContractVersion,
      'locale': locale,
      'query': query,
      'limit': limit,
      'offset': offset,
      'count': rendered.length,
      'items': rendered,
    });
  }

  @override
  Future<SelectionResult> selectArtifacts(
    List<String> artifactIds, {
    String? profileId,
    String selectedBy = 'app-user',
    String? inclusionStatus,
    String? selectionReason,
  }) async {
    lastSelected = artifactIds;
    var created = 0;
    for (final id in artifactIds) {
      if (_selected.add(id)) created++;
    }
    return SelectionResult(
      profileId: profileId,
      requested: artifactIds.length,
      created: created,
      existing: artifactIds.length - created,
      originsAdded: created,
    );
  }

  @override
  Future<ProfileSummary> createProfile({
    required String name,
    String? profileKind,
    String? organizationSize,
    String? industry,
    String? country,
    String? targetMaturityLevel,
    String? description,
    bool activate = false,
  }) async {
    final created = ProfileSummary(id: 'PRF-$name', name: name, isActive: activate);
    _profiles = [..._profiles, created];
    lastCreated = created;
    return created;
  }

  @override
  Future<ProfileSummary> activateProfile(String profileId) async {
    lastActivated = profileId;
    return _profiles.firstWhere(
      (p) => p.id == profileId,
      orElse: () => ProfileSummary(id: profileId, isActive: true),
    );
  }
}
