import 'dart:convert';

import 'report_generator.dart';

final class ReportExporter {
  const ReportExporter._();

  static String toJson(ProfileReportData data) =>
      const JsonEncoder.withIndent('  ').convert(data.toJson());

  static String toHtml(ProfileReportData data, {String languageCode = 'ar'}) {
    const escape = HtmlEscape(HtmlEscapeMode.element);
    String value(Object? input) => escape.convert(input?.toString() ?? '');
    final labels = _HtmlReportLabels.forLanguage(languageCode);

    final domains = data.domainBreakdown
        .map(
          (domain) =>
              '<tr><td>${value(domain['primary_domain'])}</td>'
              '<td>${value(domain['imp'] ?? 0)}</td>'
              '<td>${value(domain['total'] ?? 0)}</td></tr>',
        )
        .join();
    final artifacts = data.artifactDetails
        .map(
          (artifact) =>
              '<tr><td>${value(artifact['artifact_id'])}</td>'
              '<td>${value(labels.isArabic ? artifact['title_ar'] ?? artifact['title_en'] : artifact['title_en'] ?? artifact['title_ar'])}</td>'
              '<td>${value(artifact['implementation_status'])}</td>'
              '<td>${value(artifact['verification_status'])}</td>'
              '<td>${value(artifact['effective_priority'])}</td></tr>',
        )
        .join();

    return '''<!doctype html>
<html lang="${labels.languageCode}" dir="${labels.direction}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SecureGuide - ${value(data.profileName)}</title>
  <style>
    body{font-family:Arial,sans-serif;margin:2rem;color:#17212b}
    table{border-collapse:collapse;width:100%;margin:1rem 0}
    th,td{border:1px solid #cbd5e1;padding:.5rem;text-align:${labels.textAlign}}
    th{background:#e2e8f0}.summary{display:flex;gap:1rem;flex-wrap:wrap}
    .summary span{background:#f1f5f9;padding:.75rem;border-radius:.5rem}
  </style>
</head>
<body>
  <h1>${labels.reportTitle}</h1>
  <p>${value(data.profileName)} — ${value(data.date)}</p>
  <div class="summary">
    <span>${labels.total}: ${data.totalArtifacts}</span>
    <span>${labels.implemented}: ${data.implemented}</span>
    <span>${labels.openGaps}: ${data.pending}</span>
    <span>${labels.exceptions}: ${data.exceptions}</span>
  </div>
  <h2>${labels.domainBreakdown}</h2>
  <table><thead><tr><th>${labels.domain}</th><th>${labels.implemented}</th><th>${labels.total}</th></tr></thead>
    <tbody>$domains</tbody></table>
  <h2>${labels.artifactDetails}</h2>
  <table><thead><tr><th>${labels.identifier}</th><th>${labels.title}</th><th>${labels.implementation}</th><th>${labels.verification}</th><th>${labels.priority}</th></tr></thead>
    <tbody>$artifacts</tbody></table>
</body>
</html>''';
  }
}

final class _HtmlReportLabels {
  const _HtmlReportLabels({
    required this.isArabic,
    required this.reportTitle,
    required this.total,
    required this.implemented,
    required this.openGaps,
    required this.exceptions,
    required this.domainBreakdown,
    required this.domain,
    required this.artifactDetails,
    required this.identifier,
    required this.title,
    required this.implementation,
    required this.verification,
    required this.priority,
  });

  factory _HtmlReportLabels.forLanguage(String languageCode) =>
      languageCode.toLowerCase().startsWith('ar')
      ? const _HtmlReportLabels(
          isArabic: true,
          reportTitle: 'تقرير SecureGuide',
          total: 'الإجمالي',
          implemented: 'مكتمل',
          openGaps: 'فجوات مفتوحة',
          exceptions: 'استثناءات',
          domainBreakdown: 'التوزيع حسب المجال',
          domain: 'المجال',
          artifactDetails: 'تفاصيل العناصر',
          identifier: 'المعرف',
          title: 'العنوان',
          implementation: 'التطبيق',
          verification: 'التحقق',
          priority: 'الأولوية',
        )
      : const _HtmlReportLabels(
          isArabic: false,
          reportTitle: 'SecureGuide report',
          total: 'Total',
          implemented: 'Implemented',
          openGaps: 'Open gaps',
          exceptions: 'Exceptions',
          domainBreakdown: 'Domain breakdown',
          domain: 'Domain',
          artifactDetails: 'Artifact details',
          identifier: 'Identifier',
          title: 'Title',
          implementation: 'Implementation',
          verification: 'Verification',
          priority: 'Priority',
        );

  final bool isArabic;
  final String reportTitle;
  final String total;
  final String implemented;
  final String openGaps;
  final String exceptions;
  final String domainBreakdown;
  final String domain;
  final String artifactDetails;
  final String identifier;
  final String title;
  final String implementation;
  final String verification;
  final String priority;

  String get languageCode => isArabic ? 'ar' : 'en';
  String get direction => isArabic ? 'rtl' : 'ltr';
  String get textAlign => isArabic ? 'right' : 'left';
}
