/// End-to-end proof that the Dart mirror matches the Python `read-model-v1`
/// contract. The test reads the *same* golden fixtures the Python suite guards
/// (`tests/fixtures/read_models/`), so a drift on either side fails here.
///
/// The core assertion is a canonical round-trip: `fromJson(golden)` then
/// `toJson()` must reproduce the golden exactly. That single check proves no
/// key was dropped or added, and that every value (and its JSON number type)
/// survives — the acceptance bar for the mirror.
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:secureguide_mobile/read_model_contract.dart';

/// Load a shared golden by surface name, resolving the path whether the test
/// runs from the package dir or the repo root.
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
  throw StateError(
    'golden fixture "$name" not found (cwd=${Directory.current.path})',
  );
}

/// Recursively sort map keys so two structurally-equal payloads encode to the
/// same string regardless of key order.
Object? _canon(Object? value) {
  if (value is Map) {
    final keys = value.keys.map((k) => k as String).toList()..sort();
    return {for (final k in keys) k: _canon(value[k])};
  }
  if (value is List) {
    return value.map(_canon).toList();
  }
  return value;
}

String canonical(Object? value) => jsonEncode(_canon(value));

void main() {
  test('profiles surface round-trips its golden without dropping a key', () {
    final golden = loadGolden('profiles');
    final view = ProfilesView.fromJson(golden);

    expect(view.contractVersion, kContractVersion);
    expect(canonical(view.toJson()), canonical(golden));

    // Meaningful end-to-end content: two seeded profiles decoded correctly.
    expect(view.profiles, hasLength(2));
    expect(view.profiles.map((p) => p.id), containsAll(['P-HQ', 'P-AUDIT']));
  });

  test('dashboard surface round-trips its golden without dropping a key', () {
    final golden = loadGolden('dashboard');
    final view = DashboardView.fromJson(golden);

    expect(view.contractVersion, kContractVersion);
    expect(canonical(view.toJson()), canonical(golden));

    // Spot-check nested decoding across every collection the surface carries.
    expect(view.profile.id, 'P-HQ');
    expect(view.counts.totalItems, 3);
    expect(view.score.formulaVersion, 'profile-score-v1');
    expect(view.score.domainScores['SD-03'], 100.0);
    expect(view.gaps, hasLength(2));
    expect(view.gaps.first.artifactId, isNotNull);
    expect(view.recommendations, isNotEmpty);
    expect(view.reviewQueue, isEmpty);
  });

  test('catalog surface round-trips its golden without dropping a key', () {
    final golden = loadGolden('catalog');
    final view = CatalogView.fromJson(golden);

    expect(view.contractVersion, kContractVersion);
    expect(canonical(view.toJson()), canonical(golden));

    // Pagination echo and the selection overlay decode correctly.
    expect(view.locale, 'en');
    expect(view.count, view.items.length);
    final selected = {for (final item in view.items) item.id: item.isSelected};
    expect(selected['A-IDENTITY'], isTrue); // selected in the workflow
    expect(selected['A-POLICY'], isFalse); // never selected
  });

  test('tasks surface round-trips its golden without dropping a key', () {
    final golden = loadGolden('tasks');
    final view = TasksView.fromJson(golden);

    expect(view.contractVersion, kContractVersion);
    expect(canonical(view.toJson()), canonical(golden));

    // Every materialized task traces to its blueprint; one was started.
    expect(view.tasks, isNotEmpty);
    expect(view.tasks.every((t) => t.blueprintId != null), isTrue);
    expect(view.tasks.map((t) => t.status), contains('IN_PROGRESS'));
  });

  test('blueprints surface round-trips its golden without dropping a key', () {
    final golden = loadGolden('blueprints');
    final view = BlueprintsView.fromJson(golden);

    expect(view.contractVersion, kContractVersion);
    expect(canonical(view.toJson()), canonical(golden));

    // The list carries the artifact title and rollup counts the detail omits.
    expect(view.blueprints, hasLength(1));
    final bp = view.blueprints.single;
    expect(bp.workflowStatus, 'APPROVED');
    expect(bp.artifactTitleEn, 'Identity governance');
    expect(bp.actionCount, 6);
    expect(bp.taskCount, 6);
  });

  test('blueprint detail surface round-trips its golden without dropping a key',
      () {
    final golden = loadGolden('blueprint_detail');
    final view = BlueprintDetailView.fromJson(golden);

    expect(view.contractVersion, kContractVersion);
    expect(canonical(view.toJson()), canonical(golden));

    // Every nested collection decodes, including the source-rule child objects.
    final bp = view.blueprint;
    expect(bp.appliedRules, hasLength(5));
    expect(bp.actions, hasLength(6));
    expect(bp.actions.every((a) => a.sourceRules.isNotEmpty), isTrue);
    expect(bp.expectedOutputs, hasLength(1));
    expect(bp.evidence, hasLength(4));
    expect(bp.evidence.first.mandatory, isNotNull);
    expect(bp.patternEnrichments, isEmpty);
    expect(bp.reviewFindings, isEmpty);
  });

  // The golden's patternEnrichments/reviewFindings are empty (this workflow has
  // no enrichment and a clean generation), so these self-consistency guards
  // exercise those two mappers directly against their documented key sets.
  test('empty-in-golden collection mappers round-trip their key sets', () {
    final enrichment = <String, dynamic>{
      'id': '<id>',
      'sourcePatternId': 'OP-EXAMPLE',
      'recommendedArtifactType': 'ART-CTR',
      'primaryDomain': 'SD-03',
      'subDomain': 'SD-03.03',
      'patternPriority': 'PRI-HIGH',
      'copiedTitleAr': 'عنوان',
      'copiedTextAr': 'نص',
      'safetyReviewRequired': true,
      'safetyAcknowledged': true,
      'safetyNoteAr': 'ملاحظة سلامة',
      'libraryVersion': '1.0.0',
      'selectedBy': 'author',
      'selectionReason': 'سبب الاختيار',
      'selectedAt': '<ts>',
    };
    expect(
      canonical(PatternEnrichment.fromJson(enrichment).toJson()),
      canonical(enrichment),
    );

    final finding = <String, dynamic>{
      'findingType': 'REVIEW_REASON',
      'findingCode': 'REVIEW-001',
      'fieldName': null,
      'inputValue': null,
      'canonicalValue': null,
      'detail': 'classification confidence below threshold',
      'quality': null,
    };
    expect(
      canonical(ReviewFinding.fromJson(finding).toJson()),
      canonical(finding),
    );
  });
}
