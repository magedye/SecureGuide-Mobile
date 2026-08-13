import 'dart:convert';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:printing/printing.dart';

import '../../l10n/app_localizations.dart';
import '../core/reporting/pdf_exporter.dart';
import '../core/reporting/report_exporter.dart';
import '../core/reporting/report_generator.dart';

class ReportPreviewScreen extends StatefulWidget {
  const ReportPreviewScreen({super.key, required this.profileId, this.report});

  final String profileId;
  final Future<ProfileReportData>? report;

  @override
  State<ReportPreviewScreen> createState() => _ReportPreviewScreenState();
}

class _ReportPreviewScreenState extends State<ReportPreviewScreen> {
  final ReportGenerator _generator = ReportGenerator();
  late final Future<ProfileReportData> _report;

  @override
  void initState() {
    super.initState();
    _report = widget.report ?? _generator.generateReport(widget.profileId);
  }

  Future<void> _saveTextExport({required bool html}) async {
    final messenger = ScaffoldMessenger.of(context);
    final l10n = AppLocalizations.of(context)!;
    final languageCode = Localizations.localeOf(context).languageCode;
    try {
      final report = await _report;
      final extension = html ? 'html' : 'json';
      final contents = html
          ? ReportExporter.toHtml(report, languageCode: languageCode)
          : ReportExporter.toJson(report);
      final path = await FilePicker.saveFile(
        dialogTitle: html ? l10n.saveHtmlReport : l10n.saveJsonReport,
        fileName: 'secureguide_report_${widget.profileId}.$extension',
        type: FileType.custom,
        allowedExtensions: [extension],
        bytes: Uint8List.fromList(utf8.encode(contents)),
      );
      if (!mounted || path == null) return;
      messenger.showSnackBar(SnackBar(content: Text(l10n.reportSaved(path))));
    } catch (error) {
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(content: Text(l10n.reportSaveError(error))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final languageCode = Localizations.localeOf(context).languageCode;
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.reportPreview),
        actions: [
          IconButton(
            key: const Key('exportReportJson'),
            tooltip: l10n.exportJson,
            onPressed: () => _saveTextExport(html: false),
            icon: const Icon(Icons.data_object),
          ),
          IconButton(
            key: const Key('exportReportHtml'),
            tooltip: l10n.exportHtml,
            onPressed: () => _saveTextExport(html: true),
            icon: const Icon(Icons.html),
          ),
        ],
      ),
      body: PdfPreview(
        key: const Key('exportReportPdf'),
        build: (format) async {
          final data = await _report;
          return PdfExporter.generatePdf(data, languageCode: languageCode);
        },
        useActions: true,
        allowPrinting: true,
        allowSharing: true,
        canChangeOrientation: false,
        canChangePageFormat: false,
        canDebug: false,
        pdfFileName: 'secureguide_report_${widget.profileId}.pdf',
        loadingWidget: const Center(child: CircularProgressIndicator()),
      ),
    );
  }
}
