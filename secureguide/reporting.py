"""Pure presentation layer: render the official profile report as printable HTML.

This module contains no business rules and no database access. It formats the
dict returned by ``SecureGuideService.report`` — which already exposes approved
blueprints only — into a self-contained, right-to-left, print-friendly document.
Keeping rendering separate from the service preserves the rule that presentation
code never recomputes scoring, exception, or approval logic.
"""

from __future__ import annotations

import html
from typing import Any

__all__ = ["render_report_html"]

STATUS_LABELS_AR = {
    "STS-FULL": "مطبَّق كليًا",
    "STS-PARTIAL": "مطبَّق جزئيًا",
    "STS-NOT-APPLIED": "غير مطبَّق",
    "STS-PLANNED": "مخطَّط",
    "STS-NEEDS-IMPROVEMENT": "يحتاج تحسينًا",
    "VER-PASS": "تحقّق ناجح",
    "VER-FAIL": "تحقّق فاشل",
    "VER-NOT-VERIFIED": "غير محقَّق",
    "TODO": "قيد الانتظار",
    "IN_PROGRESS": "قيد التنفيذ",
    "BLOCKED": "معطَّل",
    "DONE": "منجز",
    "CANCELLED": "ملغى",
    "PRI-CRITICAL": "حرجة",
    "PRI-HIGH": "عالية",
    "PRI-MEDIUM": "متوسطة",
    "PRI-LOW": "منخفضة",
}


def _esc(value: Any) -> str:
    if value is None:
        return "—"
    text = str(value)
    return html.escape(text) if text.strip() else "—"


def _label(value: Any) -> str:
    if value is None:
        return "—"
    return _esc(STATUS_LABELS_AR.get(str(value), value))


def _pct(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "—"


def _num(value: Any) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return _esc(value)


def _rows(items: list[dict[str, Any]], columns: list[tuple[str, Any]], empty: str) -> str:
    """Build a table body from ``columns`` = list of (header, cell-callable)."""
    head = "".join(f"<th>{html.escape(header)}</th>" for header, _ in columns)
    if not items:
        return (
            f"<table><thead><tr>{head}</tr></thead>"
            f"<tbody><tr><td class='empty' colspan='{len(columns)}'>{html.escape(empty)}</td>"
            f"</tr></tbody></table>"
        )
    body = []
    for item in items:
        cells = "".join(f"<td>{render(item)}</td>" for _, render in columns)
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def _kpi(label: str, value: str) -> str:
    return (
        f"<div class='kpi'><span class='kpi-value'>{value}</span>"
        f"<span class='kpi-label'>{html.escape(label)}</span></div>"
    )


def render_report_html(report: dict[str, Any]) -> str:
    profile = report.get("profile") or {}
    summary = report.get("summary") or {}
    counts = summary.get("counts") or {}
    score = summary.get("score") or {}

    enrichments_by_bp: dict[str, list[dict[str, Any]]] = {}
    for enrichment in report.get("approved_blueprint_enrichments") or []:
        enrichments_by_bp.setdefault(enrichment.get("blueprint_id"), []).append(enrichment)

    kpis = "".join([
        _kpi("النتيجة الكلية", _pct(score.get("overall"))),
        _kpi("العناصر المطبَّقة", _num(counts.get("implemented_full"))),
        _kpi("الفجوات المفتوحة", _num(summary.get("gap_count"))),
        _kpi("خطط معتمدة", _num(summary.get("approved_blueprint_count"))),
        _kpi("مهام مفتوحة", _num(summary.get("open_task_count"))),
        _kpi("قائمة المراجعة", _num(summary.get("review_queue_count"))),
    ])

    profile_meta = "".join(
        f"<div><dt>{html.escape(label)}</dt><dd>{_esc(profile.get(key))}</dd></div>"
        for label, key in [
            ("المعرّف", "id"),
            ("النوع", "profile_kind"),
            ("القطاع", "industry"),
            ("الدولة", "country"),
        ]
    )

    gaps_table = _rows(
        report.get("gaps") or [],
        [
            ("العنصر", lambda i: _esc(i.get("title_en") or i.get("artifact_id"))),
            ("المجال", lambda i: _esc(i.get("primary_domain"))),
            ("الأولوية", lambda i: _label(i.get("priority"))),
            ("حالة التطبيق", lambda i: _label(i.get("implementation_status"))),
            ("التحقق", lambda i: _label(i.get("verification_status"))),
            ("المالك", lambda i: _esc(i.get("assigned_owner"))),
            ("الاستحقاق", lambda i: _esc(i.get("due_date"))),
        ],
        "لا توجد فجوات مفتوحة.",
    )

    def _blueprint_cell(item: dict[str, Any]) -> str:
        title = _esc(item.get("artifact_title_ar") or item.get("artifact_title_en") or item.get("artifact_id"))
        rows = enrichments_by_bp.get(item.get("id")) or []
        if not rows:
            return title
        chips = "".join(
            "<li>{pattern}{safety} — <span class='muted'>{reason}</span></li>".format(
                pattern=_esc(e.get("source_pattern_id")),
                safety=" ⚠" if e.get("safety_review_required") else "",
                reason=_esc(e.get("selection_reason")),
            )
            for e in rows
        )
        return (
            f"{title}<ul class='enrich'>"
            f"<li class='enrich-head'>إثراء من الأنماط (اقتراحات معيارية بناءً على التصنيف):</li>"
            f"{chips}</ul>"
        )

    blueprints_table = _rows(
        report.get("approved_blueprints") or [],
        [
            ("الخطة المعتمدة", _blueprint_cell),
            ("الإصدار", lambda i: _num(i.get("version"))),
            ("الإجراءات", lambda i: _num(i.get("action_count"))),
            ("الأدلة", lambda i: _num(i.get("evidence_count"))),
            ("المهام", lambda i: _num(i.get("task_count"))),
            ("المعتمِد", lambda i: _esc(i.get("approved_by"))),
            ("تاريخ الاعتماد", lambda i: _esc(i.get("approved_at"))),
        ],
        "لا توجد خطط معتمدة بعد.",
    )

    tasks_table = _rows(
        report.get("tasks") or [],
        [
            ("المهمة", lambda i: _esc(i.get("title"))),
            ("العنصر", lambda i: _esc(i.get("artifact_title_en") or i.get("artifact_id"))),
            ("الحالة", lambda i: _label(i.get("status"))),
            ("الأولوية", lambda i: _label(i.get("priority"))),
            ("مُسندة إلى", lambda i: _esc(i.get("assigned_to"))),
            ("الاستحقاق", lambda i: _esc(i.get("due_date"))),
        ],
        "لا توجد مهام.",
    )

    templates_table = _rows(
        report.get("templates") or [],
        [
            ("القالب", lambda i: _esc(i.get("template_name") or i.get("template_id"))),
            ("تاريخ التطبيق", lambda i: _esc(i.get("applied_at"))),
        ],
        "لم يُطبَّق أي قالب.",
    )

    band = _esc(score.get("band"))
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>تقرير الامتثال — {_esc(profile.get('name'))}</title>
<style>
:root {{ color-scheme: light; }}
* {{ box-sizing: border-box; }}
body {{ font-family: "Segoe UI", Tahoma, "Noto Naskh Arabic", sans-serif; margin: 0;
  background: #f4f5f7; color: #1c2430; line-height: 1.5; }}
.page {{ max-width: 1000px; margin: 0 auto; padding: 32px; background: #fff; }}
header.doc {{ border-bottom: 3px solid #1f4e79; padding-bottom: 16px; margin-bottom: 8px; }}
header.doc h1 {{ margin: 0 0 4px; font-size: 24px; color: #1f4e79; }}
.meta-line {{ color: #55627a; font-size: 13px; }}
h2 {{ font-size: 17px; color: #1f4e79; margin: 28px 0 10px; border-right: 4px solid #1f4e79;
  padding-right: 8px; }}
dl.profile {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px 16px; margin: 12px 0; }}
dl.profile dt {{ font-size: 12px; color: #55627a; }}
dl.profile dd {{ margin: 0; font-weight: 600; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px; margin: 12px 0; }}
.kpi {{ background: #f0f4f9; border: 1px solid #d7e0ec; border-radius: 10px; padding: 14px;
  text-align: center; }}
.kpi-value {{ display: block; font-size: 22px; font-weight: 700; color: #1f4e79; }}
.kpi-label {{ display: block; font-size: 12px; color: #55627a; margin-top: 4px; }}
.band {{ display: inline-block; background: #1f4e79; color: #fff; border-radius: 999px;
  padding: 2px 14px; font-size: 13px; font-weight: 600; }}
table {{ width: 100%; border-collapse: collapse; margin: 8px 0 4px; font-size: 13px; }}
th, td {{ border: 1px solid #dce3ec; padding: 7px 9px; text-align: right; vertical-align: top; }}
thead th {{ background: #1f4e79; color: #fff; font-weight: 600; }}
tbody tr:nth-child(even) {{ background: #f7f9fc; }}
td.empty {{ text-align: center; color: #8892a4; font-style: italic; }}
.muted {{ color: #6b7688; }}
ul.enrich {{ margin: 6px 0 0; padding-inline-start: 16px; font-size: 12px; color: #3a4a63; }}
ul.enrich .enrich-head {{ list-style: none; margin-inline-start: -16px; color: #55627a;
  font-weight: 600; }}
footer.doc {{ margin-top: 32px; border-top: 1px solid #dce3ec; padding-top: 12px;
  font-size: 12px; color: #6b7688; }}
@media print {{ body {{ background: #fff; }} .page {{ max-width: none; padding: 0; }}
  h2 {{ break-after: avoid; }} table {{ break-inside: auto; }} tr {{ break-inside: avoid; }} }}
</style>
</head>
<body>
<div class="page">
<header class="doc">
  <h1>تقرير الامتثال التشغيلي — {_esc(profile.get('name'))}</h1>
  <div class="meta-line">
    صيغة الاحتساب: {_esc(report.get('formula_version'))} ·
    تاريخ الإصدار: {_esc(report.get('generated_at'))} ·
    التصنيف: {band}
  </div>
</header>
<dl class="profile">{profile_meta}</dl>

<h2>الملخص التنفيذي</h2>
<div class="kpis">{kpis}</div>

<h2>الفجوات المفتوحة</h2>
{gaps_table}

<h2>الخطط المعتمدة</h2>
{blueprints_table}

<h2>المهام التشغيلية</h2>
{tasks_table}

<h2>القوالب المطبَّقة</h2>
{templates_table}

<footer class="doc">
  هذا التقرير الرسمي يعرض الخطط المعتمدة فقط، ولا يتضمن المسودات أو المقترحات المؤقتة.
  إثراءات الأنماط هي «اقتراحات معيارية بناءً على التصنيف» غير سلطوية، محفوظة كنسب على اللقطة المعتمدة.
</footer>
</div>
</body>
</html>
"""
