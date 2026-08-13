class ScoringEngine {
  static const String implemented = 'implemented';
  static const String partial = 'partial';
  static const String notAssessed = 'not_assessed';

  static const Map<String, int> tierRank = {
    'essential': 0,
    'advanced': 1,
    'very_advanced': 2,
    'full': 3,
  };

  static const Set<String> sharedPlatforms = {
    'web',
    'router',
    'iot',
    'mobile',
    'desktop',
    'laptop',
  };

  static const Map<String, dynamic> defaultPolicy = {
    'critical_cap': 60.0,
    'dependency_clamp_ceiling': 0.5,
    'accepted_risk_lifts_cap': 0,
    'bands': [
      [0.0, 'At Risk'],
      [61.0, 'Fair'],
      [75.0, 'Strong'],
      [90.0, 'Excellent'],
    ],
  };

  static double statusValue(String s) {
    if (s == implemented) return 1.0;
    if (s == partial) return 0.5;
    return 0.0;
  }

  static String bandFor(double score, List bands) {
    String result = (bands[0] as List)[1] as String;
    for (var b in bands) {
      final List bandTuple = b as List;
      final double mn = (bandTuple[0] as num).toDouble();
      final String label = bandTuple[1] as String;
      if (score >= mn) {
        result = label;
      }
    }
    return result;
  }

  static bool platformApplies(Map<String, dynamic> c, List<String>? platforms) {
    final selected = platforms == null || platforms.isEmpty
        ? const ['android']
        : platforms;
    final pids = (c['platform_ids'] as List?)?.cast<String>() ?? <String>[];
    if (pids.isEmpty || pids.contains('all')) {
      return true;
    }
    if (pids.any((p) => sharedPlatforms.contains(p))) {
      return true;
    }
    return pids.any((p) => selected.contains(p));
  }

  static bool isIncluded(
    Map<String, dynamic> c,
    Map<String, dynamic> settings,
  ) {
    if (c['disabled'] == true) return false;

    final platforms = (settings['platforms'] as List?)?.cast<String>();
    if (!platformApplies(c, platforms)) return false;

    final view = settings['view_tier'] as String? ?? 'full';
    if (view == 'full') return true;

    final cTier = c['tier'] as String?;
    return (tierRank[cTier] ?? 0) <= (tierRank[view] ?? 0);
  }

  static Map<String, dynamic> score(
    List<Map<String, dynamic>> controls,
    Map<String, dynamic> settings,
    Map<String, dynamic>? policyOpt,
  ) {
    final policy = policyOpt ?? defaultPolicy;
    final ceiling = (policy['dependency_clamp_ceiling'] as num).toDouble();
    final cap = (policy['critical_cap'] as num).toDouble();
    final bands = policy['bands'] as List;

    final applicable = controls
        .where((c) => isIncluded(c, settings) && c['excluded'] != true)
        .toList();

    if (applicable.isEmpty) {
      return {
        'overall': 0.0,
        'band': bandFor(0.0, bands),
        'capped': false,
        'assessment_coverage': 0.0,
        'risk_reduction_pct': 0.0,
        'implementation_score_raw': 0.0,
        'verification_coverage': 0.0,
        'verification_assessment_coverage': 0.0,
        'effectiveness_known': 0.0,
        'assessed_controls': 0,
        'total_controls': 0,
        'remaining_critical_risk': 0,
        'critical_total': 0,
        'critical_compliant': 0,
        'critical_accepted': 0,
        'verified_pass': 0,
        'verified_fail': 0,
        'effectiveness_known_count': 0,
        'domain_scores': <String, double>{},
        'formula_version': 'profile-score-v1',
      };
    }

    final compliantIds = applicable
        .where(
          (c) =>
              c['user_status'] == implemented &&
              c['exception_type'] != 'deferred' &&
              c['exception_type'] != 'accepted_risk',
        )
        .map((c) => c['id'] as String)
        .toSet();

    double governedStatusValue(Map<String, dynamic> c) {
      if (c['exception_type'] == 'deferred' ||
          c['exception_type'] == 'accepted_risk') {
        return 0.0;
      }
      return statusValue(c['user_status'] as String? ?? notAssessed);
    }

    double vEff(Map<String, dynamic> c) {
      final v = governedStatusValue(c);
      final deps = (c['dependencies'] as List?)?.cast<String>() ?? [];
      bool ready = deps.every((d) => compliantIds.contains(d));
      if (ready) return v;
      return v < ceiling ? v : ceiling;
    }

    double wTotal = 0.0, wAch = 0.0, rrTotal = 0.0, rrAch = 0.0;
    int assessed = 0, critTotal = 0, critCompliant = 0, critAccepted = 0;
    int verifiedPass = 0, verifiedFail = 0, effectivenessKnownCount = 0;
    Map<String, double> domW = {};
    Map<String, double> domA = {};

    for (var c in applicable) {
      final cScoringWeight = c['scoring_weight'] as num?;
      final w = (cScoringWeight == null || cScoringWeight <= 0)
          ? 1.0
          : cScoringWeight.toDouble();

      final ve = vEff(c);
      wTotal += w;
      wAch += w * ve;

      final rrRaw = c['risk_reduction'] as num?;
      final rr = (rrRaw == null || rrRaw <= 0) ? 1.0 : rrRaw.toDouble();
      rrTotal += rr;
      rrAch += rr * ve;

      final userStatus = c['user_status'] as String? ?? notAssessed;
      if (userStatus != notAssessed ||
          c['exception_type'] == 'deferred' ||
          c['exception_type'] == 'accepted_risk') {
        assessed += 1;
      }

      final vStatus = c['verification_status'] as String?;
      if (vStatus == 'VER-PASS') {
        verifiedPass += 1;
      } else if (vStatus == 'VER-FAIL') {
        verifiedFail += 1;
      }

      final eff = c['effectiveness'] as String?;
      if (eff == 'EFF-LOW' || eff == 'EFF-MEDIUM' || eff == 'EFF-HIGH') {
        effectivenessKnownCount += 1;
      }

      final d = c['domain'] as String? ?? '';
      domW[d] = (domW[d] ?? 0.0) + w;
      domA[d] = (domA[d] ?? 0.0) + (w * ve);

      if (c['priority'] == 'critical') {
        critTotal += 1;
        if (userStatus == implemented &&
            c['exception_type'] != 'deferred' &&
            c['exception_type'] != 'accepted_risk') {
          critCompliant += 1;
        } else if (c['exception_type'] == 'accepted_risk') {
          critAccepted += 1;
        }
      }
    }

    final raw = wTotal == 0 ? 0.0 : (wAch / wTotal * 100);
    final acceptedLiftsCap = policy['accepted_risk_lifts_cap'] as int? ?? 0;
    final acceptedLifts = acceptedLiftsCap != 0;

    final critRemaining =
        critTotal - critCompliant - (acceptedLifts ? critAccepted : 0);
    final capped = critRemaining > 0;
    final overall = (capped && raw > cap) ? cap : raw;

    final domainScores = <String, double>{};
    for (var d in domW.keys) {
      domainScores[d] = domW[d] == 0 ? 0.0 : (domA[d]! / domW[d]! * 100);
    }

    final total = applicable.length;

    return {
      'overall': overall,
      'band': bandFor(overall, bands),
      'capped': capped,
      'assessment_coverage': total == 0 ? 0.0 : assessed / total * 100,
      'risk_reduction_pct': rrTotal == 0.0 ? 0.0 : rrAch / rrTotal * 100,
      'implementation_score_raw': raw,
      'verification_coverage': total == 0 ? 0.0 : verifiedPass / total * 100,
      'verification_assessment_coverage': total == 0
          ? 0.0
          : (verifiedPass + verifiedFail) / total * 100,
      'effectiveness_known': total == 0
          ? 0.0
          : effectivenessKnownCount / total * 100,
      'assessed_controls': assessed,
      'total_controls': total,
      'remaining_critical_risk': critRemaining,
      'critical_total': critTotal,
      'critical_compliant': critCompliant,
      'critical_accepted': critAccepted,
      'verified_pass': verifiedPass,
      'verified_fail': verifiedFail,
      'effectiveness_known_count': effectivenessKnownCount,
      'domain_scores': domainScores,
      'formula_version': 'profile-score-v1',
    };
  }

  static List<Map<String, dynamic>> recommend(
    List<Map<String, dynamic>> controls,
    Map<String, dynamic> settings,
    Map<String, dynamic>? policyOpt,
  ) {
    final compliantIds = controls
        .where((c) => c['user_status'] == implemented)
        .map((c) => c['id'] as String)
        .toSet();

    List<Map<String, dynamic>> items = [];

    for (var c in controls) {
      if (!isIncluded(c, settings)) continue;
      if (c['excluded'] == true || c['disabled'] == true) continue;
      if (c['user_status'] == implemented &&
          c['exception_type'] != 'accepted_risk' &&
          c['exception_type'] != 'deferred') {
        continue;
      }

      final deps = (c['dependencies'] as List?)?.cast<String>() ?? [];
      bool ready = deps.every((d) => compliantIds.contains(d));

      List<String> reasons = [];
      final prio = c['priority'] as String? ?? 'low';
      reasons.add('priority:$prio');
      reasons.add(ready ? 'dependencies:ready' : 'dependencies:blocked');
      if (c['exception_type'] == 'deferred' ||
          c['exception_type'] == 'accepted_risk') {
        reasons.add('exception:${c['exception_type']}');
      }

      items.add({
        'artifactId': c['id'],
        'priority': prio,
        'dependencyReady': ready,
        'reasonCodes': reasons,
        'effort': c['effort'] as String? ?? 'medium',
        'weight': (c['scoring_weight'] as num?)?.toDouble() ?? 0.0,
      });
    }

    final Map<String, int> prioMap = {
      'critical': 0,
      'high': 1,
      'medium': 2,
      'low': 3,
    };

    items.sort((a, b) {
      final aPrio = prioMap[a['priority']] ?? 2;
      final bPrio = prioMap[b['priority']] ?? 2;
      if (aPrio != bPrio) return aPrio.compareTo(bPrio);

      final aReady = a['dependencyReady'] as bool ? 0 : 1;
      final bReady = b['dependencyReady'] as bool ? 0 : 1;
      if (aReady != bReady) return aReady.compareTo(bReady);

      final effMap = const {'low': 0, 'medium': 1, 'high': 2};
      final aEffort = effMap[a['effort']] ?? 1;
      final bEffort = effMap[b['effort']] ?? 1;
      if (aEffort != bEffort) return aEffort.compareTo(bEffort);

      final aWeight = -(a['weight'] as num).toDouble();
      final bWeight = -(b['weight'] as num).toDouble();
      if (aWeight != bWeight) return aWeight.compareTo(bWeight);

      return (a['artifactId'] as String).compareTo(b['artifactId'] as String);
    });

    return items;
  }
}
