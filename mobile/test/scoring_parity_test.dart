import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:secureguide_mobile/src/core/scoring/scoring_engine.dart';

void main() {
  test('Scoring Engine Parity with Python', () async {
    final file = File('../tests/fixtures/golden/scoring/scenarios.json');
    final content = await file.readAsString();
    final List<dynamic> scenarios = jsonDecode(content);

    for (var scenario in scenarios) {
      final name = scenario['name'];
      final controls = (scenario['controls'] as List)
          .cast<Map<String, dynamic>>();
      final settings =
          (scenario['settings'] as Map?)?.cast<String, dynamic>() ??
          <String, dynamic>{};
      final policy = (scenario['policy'] as Map?)?.cast<String, dynamic>();

      final score = ScoringEngine.score(controls, settings, policy);

      final expectNode = scenario['expect'] as Map<String, dynamic>?;
      if (expectNode != null) {
        for (var key in expectNode.keys) {
          final expectedValue = expectNode[key];
          final actualValue = score[key];

          if (expectedValue is num && actualValue is num) {
            expect(
              (actualValue - expectedValue).abs(),
              lessThan(0.001),
              reason:
                  'Scenario $name failed for $key. Expected $expectedValue but got $actualValue',
            );
          } else {
            expect(
              actualValue,
              expectedValue,
              reason:
                  'Scenario $name failed for $key. Expected $expectedValue but got $actualValue',
            );
          }
        }
      }

      final expectRecommendations =
          scenario['expect_recommendations'] as List<dynamic>?;
      if (expectRecommendations != null) {
        final recs = ScoringEngine.recommend(controls, settings, policy);
        final actualIds = recs.map((r) => r['artifactId']).toList();
        expect(
          actualIds,
          expectRecommendations,
          reason: 'Scenario $name failed for recommendations.',
        );
      }
    }
  });
}
