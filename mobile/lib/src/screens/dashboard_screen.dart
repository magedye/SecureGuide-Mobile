import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../read_model_contract.dart';
import '../client/secure_guide_client.dart';
import 'report_preview_screen.dart';

/// Loads and renders one profile's governed dashboard. It binds strictly to
/// [DashboardView] — no scoring, exception, or approval logic runs here.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({
    super.key,
    required this.client,
    this.profileId,
    this.onAssess,
  });

  final SecureGuideClient client;
  final String? profileId;
  final Future<void> Function(String artifactId)? onAssess;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late Future<DashboardView> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.client.dashboard(profileId: widget.profileId);
  }

  Future<void> _assess(String artifactId) async {
    await widget.onAssess?.call(artifactId);
    if (!mounted) return;
    setState(() {
      _future = widget.client.dashboard(profileId: widget.profileId);
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<DashboardView>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                AppLocalizations.of(
                  context,
                )!.dashboardLoadError(snapshot.error!),
              ),
            ),
          );
        }
        return _DashboardBody(
          view: snapshot.data!,
          onAssess: _assess,
          profileId: widget.profileId ?? 'unknown',
        );
      },
    );
  }
}

class _DashboardBody extends StatelessWidget {
  const _DashboardBody({
    required this.view,
    required this.onAssess,
    required this.profileId,
  });

  final DashboardView view;
  final Future<void> Function(String artifactId) onAssess;
  final String profileId;

  String get _overall {
    final value = view.score.overall;
    return value == null ? '—' : '${value.toStringAsFixed(1)}%';
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final counts = view.counts;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        LayoutBuilder(
          builder: (context, constraints) {
            final scoreCard = _ScoreCard(
              overall: _overall,
              band: view.score.band ?? '—',
              label: l10n.totalScore,
            );
            final reportButton = ElevatedButton.icon(
              icon: const Icon(Icons.picture_as_pdf),
              label: Text(l10n.exportReport),
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (context) =>
                        ReportPreviewScreen(profileId: profileId),
                  ),
                );
              },
            );
            if (constraints.maxWidth < 560) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  scoreCard,
                  const SizedBox(height: 8),
                  Align(
                    alignment: AlignmentDirectional.centerEnd,
                    child: reportButton,
                  ),
                ],
              );
            }
            return Row(
              children: [
                Expanded(child: scoreCard),
                const SizedBox(width: 16),
                reportButton,
              ],
            );
          },
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            _StatTile(label: l10n.items, value: counts.totalItems),
            _StatTile(
              label: l10n.fullyImplemented,
              value: counts.implementedFull,
            ),
            _StatTile(label: l10n.openGaps, value: counts.openGaps),
            _StatTile(label: l10n.overdue, value: counts.overdueItems),
          ],
        ),
        const SizedBox(height: 24),
        _SectionTitle(l10n.openGaps, count: view.gaps.length),
        if (view.gaps.isEmpty)
          _EmptyRow(l10n.noOpenGaps)
        else
          ...view.gaps.map((gap) => _GapRow(gap: gap, onAssess: onAssess)),
        const SizedBox(height: 24),
        _SectionTitle(l10n.recommendations, count: view.recommendations.length),
        if (view.recommendations.isEmpty)
          _EmptyRow(l10n.noRecommendations)
        else
          ...view.recommendations.map((rec) => _RecommendationRow(rec: rec)),
      ],
    );
  }
}

class _ScoreCard extends StatelessWidget {
  const _ScoreCard({
    required this.overall,
    required this.band,
    required this.label,
  });

  final String overall;
  final String band;
  final String label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.labelLarge,
                  ),
                  const SizedBox(height: 4),
                  Text(overall, style: theme.textTheme.displaySmall),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Chip(label: Text(band)),
          ],
        ),
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({required this.label, required this.value});

  final String label;
  final num? value;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SizedBox(
      width: 150,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${value ?? '—'}', style: theme.textTheme.headlineMedium),
              const SizedBox(height: 4),
              Text(label, style: theme.textTheme.bodySmall),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.title, {required this.count});

  final String title;
  final int count;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(
        '$title ($count)',
        style: Theme.of(context).textTheme.titleMedium,
      ),
    );
  }
}

class _GapRow extends StatelessWidget {
  const _GapRow({required this.gap, required this.onAssess});

  final GapItem gap;
  final Future<void> Function(String artifactId) onAssess;

  @override
  Widget build(BuildContext context) {
    final isArabic = Localizations.localeOf(context).languageCode == 'ar';
    final title = isArabic
        ? gap.titleAr ?? gap.titleEn
        : gap.titleEn ?? gap.titleAr;
    return Card(
      child: ListTile(
        onTap: gap.artifactId == null ? null : () => onAssess(gap.artifactId!),
        title: Text(title ?? gap.artifactId ?? '—'),
        subtitle: Text(
          '${gap.primaryDomain ?? '—'} · ${gap.implementationStatus ?? '—'}',
        ),
        trailing: Text(gap.priority ?? '—'),
      ),
    );
  }
}

class _RecommendationRow extends StatelessWidget {
  const _RecommendationRow({required this.rec});

  final RecommendationItem rec;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        title: Text(rec.artifactId ?? '—'),
        subtitle: Text(rec.reasonCodes.join(' · ')),
        trailing: Text(rec.priority ?? '—'),
      ),
    );
  }
}

class _EmptyRow extends StatelessWidget {
  const _EmptyRow(this.message);

  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Text(message, style: Theme.of(context).textTheme.bodyMedium),
    );
  }
}
