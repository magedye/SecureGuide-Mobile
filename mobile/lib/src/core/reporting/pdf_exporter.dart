import 'dart:typed_data';
import 'package:flutter/services.dart' show rootBundle;
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'report_generator.dart';

class PdfExporter {
  static Future<Uint8List> generatePdf(
    ProfileReportData data, {
    String languageCode = 'ar',
  }) async {
    final pdf = pw.Document();
    final labels = _PdfReportLabels.forLanguage(languageCode);

    final regularData = await rootBundle.load(
      'assets/fonts/Tajawal-Regular.ttf',
    );
    final boldData = await rootBundle.load('assets/fonts/Tajawal-Bold.ttf');
    final arabicFont = pw.Font.ttf(regularData);
    final arabicBoldFont = pw.Font.ttf(boldData);
    final theme = pw.ThemeData.withFont(base: arabicFont, bold: arabicBoldFont);

    pdf.addPage(
      pw.MultiPage(
        theme: theme,
        textDirection: labels.isArabic
            ? pw.TextDirection.rtl
            : pw.TextDirection.ltr,
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(32),
        header: (context) => pw.Container(
          alignment: labels.isArabic
              ? pw.Alignment.centerRight
              : pw.Alignment.centerLeft,
          margin: const pw.EdgeInsets.only(bottom: 20),
          child: pw.Text(
            'SecureGuide Enterprise Report',
            style: pw.TextStyle(color: PdfColors.grey, fontSize: 12),
          ),
        ),
        footer: (context) => pw.Container(
          alignment: pw.Alignment.center,
          margin: const pw.EdgeInsets.only(top: 20),
          child: pw.Text(
            labels.pageNumber(context.pageNumber, context.pagesCount),
            style: pw.TextStyle(color: PdfColors.grey, fontSize: 10),
          ),
        ),
        build: (context) => [
          _buildHeader(data, labels),
          pw.SizedBox(height: 24),
          _buildSummary(data, labels),
          pw.SizedBox(height: 24),
          _buildDomainBreakdown(data, labels),
          pw.SizedBox(height: 24),
          _buildArtifactList(data, labels),
        ],
      ),
    );

    return pdf.save();
  }

  static pw.Widget _buildHeader(
    ProfileReportData data,
    _PdfReportLabels labels,
  ) {
    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        pw.Text(
          labels.assessmentReport,
          style: pw.TextStyle(fontSize: 24, fontWeight: pw.FontWeight.bold),
        ),
        pw.SizedBox(height: 8),
        pw.Text(
          '${labels.profile}: ${data.profileName}',
          style: const pw.TextStyle(fontSize: 16),
        ),
        pw.Text(
          '${labels.date}: ${data.date}',
          style: const pw.TextStyle(fontSize: 14, color: PdfColors.grey700),
        ),
      ],
    );
  }

  static pw.Widget _buildSummary(
    ProfileReportData data,
    _PdfReportLabels labels,
  ) {
    return pw.Container(
      padding: const pw.EdgeInsets.all(12),
      decoration: pw.BoxDecoration(
        color: PdfColors.grey100,
        borderRadius: const pw.BorderRadius.all(pw.Radius.circular(8)),
      ),
      child: pw.Row(
        mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
        children: [
          _summaryItem(labels.total, data.totalArtifacts.toString()),
          _summaryItem(labels.implemented, data.implemented.toString()),
          _summaryItem(labels.remaining, data.pending.toString()),
          _summaryItem(labels.exceptions, data.exceptions.toString()),
        ],
      ),
    );
  }

  static pw.Widget _summaryItem(String label, String value) {
    return pw.Column(
      children: [
        pw.Text(
          value,
          style: pw.TextStyle(fontSize: 20, fontWeight: pw.FontWeight.bold),
        ),
        pw.SizedBox(height: 4),
        pw.Text(label, style: const pw.TextStyle(fontSize: 12)),
      ],
    );
  }

  static pw.Widget _buildDomainBreakdown(
    ProfileReportData data,
    _PdfReportLabels labels,
  ) {
    if (data.domainBreakdown.isEmpty) return pw.SizedBox();

    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        pw.Text(
          labels.domainBreakdown,
          style: pw.TextStyle(fontSize: 18, fontWeight: pw.FontWeight.bold),
        ),
        pw.SizedBox(height: 8),
        pw.TableHelper.fromTextArray(
          headers: [labels.domain, labels.implemented, labels.total],
          data: data.domainBreakdown
              .map(
                (r) => [
                  r['primary_domain']?.toString() ?? '-',
                  r['imp']?.toString() ?? '0',
                  r['total']?.toString() ?? '0',
                ],
              )
              .toList(),
          headerStyle: pw.TextStyle(
            fontWeight: pw.FontWeight.bold,
            color: PdfColors.white,
          ),
          headerDecoration: const pw.BoxDecoration(
            color: PdfColors.blueGrey800,
          ),
          cellAlignment: pw.Alignment.centerRight,
        ),
      ],
    );
  }

  static pw.Widget _buildArtifactList(
    ProfileReportData data,
    _PdfReportLabels labels,
  ) {
    if (data.artifactDetails.isEmpty) return pw.SizedBox();

    return pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        pw.Text(
          labels.artifactDetails,
          style: pw.TextStyle(fontSize: 18, fontWeight: pw.FontWeight.bold),
        ),
        pw.SizedBox(height: 8),
        pw.ListView.separated(
          itemCount: data.artifactDetails.length,
          separatorBuilder: (context, index) => pw.Divider(),
          itemBuilder: (context, index) {
            final a = data.artifactDetails[index];
            return pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Text(
                  '${a['artifact_id'] ?? ''} - '
                  '${labels.isArabic ? a['title_ar'] ?? a['title_en'] ?? '' : a['title_en'] ?? a['title_ar'] ?? ''}',
                  style: pw.TextStyle(
                    fontWeight: pw.FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
                pw.SizedBox(height: 4),
                pw.Row(
                  children: [
                    pw.Text(
                      '${labels.status}: '
                      '${a['implementation_status'] ?? labels.notSpecified}',
                      style: const pw.TextStyle(fontSize: 10),
                    ),
                    pw.SizedBox(width: 16),
                    pw.Text(
                      '${labels.priority}: '
                      '${a['effective_priority'] ?? labels.notSpecified}',
                      style: const pw.TextStyle(fontSize: 10),
                    ),
                  ],
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

final class _PdfReportLabels {
  const _PdfReportLabels({
    required this.isArabic,
    required this.assessmentReport,
    required this.profile,
    required this.date,
    required this.total,
    required this.implemented,
    required this.remaining,
    required this.exceptions,
    required this.domainBreakdown,
    required this.domain,
    required this.artifactDetails,
    required this.status,
    required this.priority,
    required this.notSpecified,
  });

  factory _PdfReportLabels.forLanguage(String languageCode) =>
      languageCode.toLowerCase().startsWith('ar')
      ? const _PdfReportLabels(
          isArabic: true,
          assessmentReport: 'تقرير التقييم',
          profile: 'الملف',
          date: 'التاريخ',
          total: 'الإجمالي',
          implemented: 'مكتمل',
          remaining: 'متبقي',
          exceptions: 'استثناءات',
          domainBreakdown: 'التوزيع حسب المجال',
          domain: 'المجال',
          artifactDetails: 'تفاصيل العناصر',
          status: 'الحالة',
          priority: 'الأولوية',
          notSpecified: 'غير محدد',
        )
      : const _PdfReportLabels(
          isArabic: false,
          assessmentReport: 'Assessment report',
          profile: 'Profile',
          date: 'Date',
          total: 'Total',
          implemented: 'Implemented',
          remaining: 'Remaining',
          exceptions: 'Exceptions',
          domainBreakdown: 'Domain breakdown',
          domain: 'Domain',
          artifactDetails: 'Artifact details',
          status: 'Status',
          priority: 'Priority',
          notSpecified: 'Not specified',
        );

  final bool isArabic;
  final String assessmentReport;
  final String profile;
  final String date;
  final String total;
  final String implemented;
  final String remaining;
  final String exceptions;
  final String domainBreakdown;
  final String domain;
  final String artifactDetails;
  final String status;
  final String priority;
  final String notSpecified;

  String pageNumber(int page, int pages) =>
      isArabic ? 'الصفحة $page من $pages' : 'Page $page of $pages';
}
