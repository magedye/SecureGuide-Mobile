import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../read_model_contract.dart';

/// Raised when the sidecar returns a non-200 response.
class SecureGuideClientException implements Exception {
  SecureGuideClientException(this.statusCode, this.body);

  final int statusCode;
  final String body;

  @override
  String toString() => 'SecureGuideClientException($statusCode): $body';
}

/// The read boundary the UI binds to. Transport-agnostic on purpose: screens
/// depend only on `read-model-v1` view objects, never on SQL, HTTP, or business
/// rules. Swapping the transport (sidecar today, embedded core later on mobile)
/// changes only the implementation, not a single widget.
abstract interface class SecureGuideClient {
  Future<ProfilesView> profiles();

  Future<DashboardView> dashboard({String? profileId});

  /// Create an enterprise profile; returns the created profile.
  Future<ProfileSummary> createProfile({
    required String name,
    String? profileKind,
    String? organizationSize,
    String? industry,
    String? country,
    String? targetMaturityLevel,
    String? description,
    bool activate,
  });

  /// Make [profileId] the active profile; returns it.
  Future<ProfileSummary> activateProfile(String profileId);

  /// One page of the master catalog with the profile's selection overlay.
  Future<CatalogView> catalog({
    String? profileId,
    String? query,
    String locale,
    bool selectedOnly,
    int limit,
    int offset,
  });

  /// Select catalog artifacts into a profile; returns a selection summary.
  Future<SelectionResult> selectArtifacts(
    List<String> artifactIds, {
    String? profileId,
    String selectedBy,
    String? inclusionStatus,
    String? selectionReason,
  });
}

/// Reaches the Python core through the local sidecar over loopback HTTP.
class HttpSecureGuideClient implements SecureGuideClient {
  HttpSecureGuideClient({Uri? baseUri, http.Client? httpClient})
      : baseUri = baseUri ?? Uri.parse('http://127.0.0.1:8765'),
        _http = httpClient ?? http.Client();

  final Uri baseUri;
  final http.Client _http;

  Future<Map<String, dynamic>> _getJson(
    String path, [
    Map<String, String>? query,
  ]) async {
    final uri = baseUri.replace(path: path, queryParameters: query);
    final response = await _http.get(uri);
    return _decode(response);
  }

  Future<Map<String, dynamic>> _postJson(
    String path,
    Map<String, dynamic> body,
  ) async {
    final response = await _http.post(
      baseUri.replace(path: path),
      headers: {'Content-Type': 'application/json; charset=utf-8'},
      body: utf8.encode(jsonEncode(body)),
    );
    return _decode(response);
  }

  Map<String, dynamic> _decode(http.Response response) {
    if (response.statusCode != 200) {
      throw SecureGuideClientException(response.statusCode, response.body);
    }
    return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
  }

  @override
  Future<ProfilesView> profiles() async =>
      ProfilesView.fromJson(await _getJson('/read/profiles'));

  @override
  Future<DashboardView> dashboard({String? profileId}) async =>
      DashboardView.fromJson(
        await _getJson('/read/dashboard', {
          if (profileId != null) 'profileId': profileId,
        }),
      );

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
    final json = await _postJson('/write/profiles', {
      'name': name,
      if (profileKind != null) 'profileKind': profileKind,
      if (organizationSize != null) 'organizationSize': organizationSize,
      if (industry != null) 'industry': industry,
      if (country != null) 'country': country,
      if (targetMaturityLevel != null) 'targetMaturityLevel': targetMaturityLevel,
      if (description != null) 'description': description,
      'activate': activate,
    });
    return ProfileSummary.fromJson(json['profile'] as Map<String, dynamic>);
  }

  @override
  Future<ProfileSummary> activateProfile(String profileId) async {
    final json = await _postJson('/write/active-profile', {'profileId': profileId});
    return ProfileSummary.fromJson(json['profile'] as Map<String, dynamic>);
  }

  @override
  Future<CatalogView> catalog({
    String? profileId,
    String? query,
    String locale = 'en',
    bool selectedOnly = false,
    int limit = 100,
    int offset = 0,
  }) async {
    final params = <String, String>{
      if (profileId != null) 'profileId': profileId,
      'locale': locale,
      if (query != null && query.isNotEmpty) 'query': query,
      if (selectedOnly) 'selectedOnly': 'true',
      'limit': '$limit',
      'offset': '$offset',
    };
    return CatalogView.fromJson(await _getJson('/read/catalog', params));
  }

  @override
  Future<SelectionResult> selectArtifacts(
    List<String> artifactIds, {
    String? profileId,
    String selectedBy = 'app-user',
    String? inclusionStatus,
    String? selectionReason,
  }) async {
    final json = await _postJson('/write/select-artifacts', {
      'artifactIds': artifactIds,
      'selectedBy': selectedBy,
      if (profileId != null) 'profileId': profileId,
      if (inclusionStatus != null) 'inclusionStatus': inclusionStatus,
      if (selectionReason != null) 'selectionReason': selectionReason,
    });
    return SelectionResult.fromJson(json['selection'] as Map<String, dynamic>);
  }

  void close() => _http.close();
}
