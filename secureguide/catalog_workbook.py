"""Audited nine-sheet Excel round-trip for SecureGuide catalog curation."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter, quote_sheetname
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.defined_name import DefinedName

from secureguide.catalog_validation import (
    canonical_hash,
    file_hash,
    load_contract,
    minimum_result,
)
from secureguide.database import connect


ROOT = Path(__file__).resolve().parent.parent
RELEASE_ASSET = (ROOT / "mobile" / "assets" / "catalog.db").resolve()
SHEETS = (
    "00_Manifest", "01_Artifacts", "02_Source_Lineage",
    "03_Framework_Mappings", "04_Relationships", "05_Tags",
    "06_Type_Specific", "07_Reference_Lists", "08_Validation_Errors",
)
ACTION_VALUES = ("NO_CHANGE", "UPSERT", "DEPRECATE")
TABLE_SHEETS = {
    "01_Artifacts": "security_artifacts",
    "02_Source_Lineage": "artifact_source_lineage",
    "03_Framework_Mappings": "framework_mappings",
    "04_Relationships": "artifact_relationships",
    "05_Tags": "artifact_tags",
}
PRIMARY_KEYS = {
    "01_Artifacts": ("id",),
    "02_Source_Lineage": ("artifact_id", "raw_artifact_id"),
    "03_Framework_Mappings": ("id",),
    "04_Relationships": ("id",),
    "05_Tags": ("artifact_id", "tag_type", "tag_value"),
    "06_Type_Specific": ("artifact_id",),
}
TYPE_FIELDS = (
    "artifact_id", "type", "requirement_type", "control_nature",
    "control_function", "testability", "asset_type", "asset_criticality",
    "exception_approval_date", "exception_expiry_date", "effective_date",
)
LOOKUPS = {
    "type": "lk_artifact_type", "primary_domain": "lk_sdt_domain",
    "sub_domain": "lk_sdt_subdomain", "abstraction_level": "lk_abstraction_level",
    "source": "lk_obligation_source", "source_type": "lk_source_type",
    "obligation_level": "lk_obligation_level", "requirement_type": "lk_requirement_type",
    "granularity_level": "lk_granularity_level", "control_nature": "lk_control_nature",
    "control_function": "lk_control_function", "testability": "lk_testability",
    "priority": "lk_priority", "review_frequency": "lk_review_frequency",
    "publication_status": "lk_publication_status", "ai_review_status": "lk_ai_review_status",
}
STATIC_LISTS = {
    "action": ACTION_VALUES,
    "mapping_strength": ("DIRECT", "INDIRECT", "PARTIAL", "INFORMATIVE"),
    "lineage_role": ("SUPPORTS_CANONICAL", "SPLIT"),
    "relation_type": (
        "REL-DER", "REL-SAT", "REL-SUP", "REL-SPL", "REL-IMP", "REL-VER",
        "REL-MEA", "REL-MIT", "REL-AFF", "REL-EXC", "REL-DEP", "REL-CNF",
    ),
    "tag_type": ("Technology", "Framework", "Concept", "Context", "Threat", "Data", "Party"),
}
META_COLUMNS = ("_action", "_baseline_key", "_baseline_hash")


class WorkbookError(ValueError):
    pass


class WorkbookConflict(WorkbookError):
    pass


def _portable_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _row_dict(row: sqlite3.Row, columns: Iterable[str] | None = None) -> dict[str, Any]:
    names = columns or row.keys()
    return {name: _json_value(row[name]) for name in names}


def row_hash(values: dict[str, Any]) -> str:
    # Excel stores integral floating-point values such as 0.0 as numeric 0.
    # Treat those JSON number spellings as the same semantic value while
    # retaining booleans and non-integral floats exactly.
    normalized = {
        key: (
            int(values[key])
            if isinstance(values[key], float) and values[key].is_integer()
            else values[key]
        )
        for key in sorted(values)
    }
    return canonical_hash(normalized)


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]


def _table_rows(conn: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    columns = _table_columns(conn, table)
    order = ",".join(
        row[1] for row in conn.execute(f"PRAGMA table_info({table})") if row[5]
    ) or ",".join(columns)
    return [_row_dict(row, columns) for row in conn.execute(f"SELECT * FROM {table} ORDER BY {order}")]


def catalog_state_hash(conn: sqlite3.Connection) -> str:
    """Logical hash excluding workbook audit rows and SQLite byte layout."""
    payload = {table: _table_rows(conn, table) for table in TABLE_SHEETS.values()}
    return canonical_hash(payload)


def _style_sheet(ws, *, freeze: str = "A2") -> None:
    ws.freeze_panes = freeze
    if ws.max_row and ws.max_column:
        ws.auto_filter.ref = ws.dimensions
    header_fill = PatternFill("solid", fgColor="1F4E78")
    for cell in ws[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = header_fill
    for column in range(1, ws.max_column + 1):
        header = str(ws.cell(1, column).value or "")
        width = min(52, max(12, len(header) + 2))
        for row in range(2, min(ws.max_row, 80) + 1):
            width = min(52, max(width, len(str(ws.cell(row, column).value or "")) + 2))
        ws.column_dimensions[get_column_letter(column)].width = width


def _append_table(ws, columns: list[str], rows: list[dict[str, Any]]) -> None:
    ws.append([*META_COLUMNS, *columns])
    for values in rows:
        key_columns = PRIMARY_KEYS[ws.title]
        baseline_key = canonical_hash({key: values.get(key) for key in key_columns})
        ws.append(["NO_CHANGE", baseline_key, row_hash(values), *[values.get(c) for c in columns]])


def _reference_lists(conn: sqlite3.Connection) -> dict[str, tuple[str, ...]]:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    result = dict(STATIC_LISTS)
    for field, table in LOOKUPS.items():
        if table in tables:
            result[field] = tuple(row[0] for row in conn.execute(f"SELECT code FROM {table} ORDER BY sort_order,code"))
    return result


def export_workbook(database: str | Path, output: str | Path, *, actor: str = "codex") -> dict[str, Any]:
    database = Path(database).resolve()
    output = Path(output).resolve()
    conn = connect(database)
    try:
        baseline = catalog_state_hash(conn)
        schema = conn.execute("SELECT MAX(CAST(version AS INTEGER)) FROM schema_migrations").fetchone()[0]
        wb = Workbook()
        wb.remove(wb.active)
        manifest_ws = wb.create_sheet(SHEETS[0])
        manifest_ws.append(["key", "value"])
        manifest = {
            "workbook_contract": "secureguide-catalog-workbook-v1",
            "schema_version": int(schema or 0),
            "baseline_db_sha256": baseline,
            "database_name": database.name,
            "row_omission_semantics": "NO_CHANGE",
            "allowed_actions": "|".join(ACTION_VALUES),
        }
        for key, value in manifest.items():
            manifest_ws.append([key, value])

        for sheet, table in TABLE_SHEETS.items():
            ws = wb.create_sheet(sheet)
            columns = _table_columns(conn, table)
            _append_table(ws, columns, _table_rows(conn, table))

        type_ws = wb.create_sheet("06_Type_Specific")
        type_rows = []
        for row in conn.execute(
            """SELECT id AS artifact_id,type,requirement_type,control_nature,
                      control_function,testability,asset_type,asset_criticality,
                      exception_approval_date,exception_expiry_date,effective_date
                 FROM security_artifacts ORDER BY id"""
        ):
            type_rows.append(_row_dict(row, TYPE_FIELDS))
        _append_table(type_ws, list(TYPE_FIELDS), type_rows)

        refs = _reference_lists(conn)
        ref_ws = wb.create_sheet("07_Reference_Lists")
        ref_ws.append(["list_name", "code"])
        ranges: dict[str, tuple[int, int]] = {}
        for name in sorted(refs):
            start = ref_ws.max_row + 1
            for code in refs[name]:
                ref_ws.append([name, code])
            ranges[name] = (start, ref_ws.max_row)

        errors_ws = wb.create_sheet("08_Validation_Errors")
        errors_ws.append(["sheet", "row", "field", "code", "message"])

        for ws in wb.worksheets:
            _style_sheet(ws)
        action_fill = PatternFill("solid", fgColor="FFF2CC")
        for sheet in SHEETS[1:7]:
            ws = wb[sheet]
            for cell in ws["A"][1:]:
                cell.fill = action_fill
            action_dv = DataValidation(type="list", formula1='"NO_CHANGE,UPSERT,DEPRECATE"')
            ws.add_data_validation(action_dv)
            action_dv.add(f"A2:A{max(ws.max_row + 500, 501)}")

        for name, (start, end) in ranges.items():
            safe = "REF_" + "".join(ch if ch.isalnum() else "_" for ch in name).upper()
            reference = f"{quote_sheetname('07_Reference_Lists')}!$B${start}:$B${end}"
            wb.defined_names.add(DefinedName(safe, attr_text=reference))
            for sheet in ("01_Artifacts", "02_Source_Lineage", "03_Framework_Mappings", "04_Relationships", "05_Tags", "06_Type_Specific"):
                ws = wb[sheet]
                headers = {cell.value: cell.column for cell in ws[1]}
                if name in headers:
                    col = get_column_letter(headers[name])
                    dv = DataValidation(type="list", formula1=f"={safe}", allow_blank=True)
                    ws.add_data_validation(dv)
                    dv.add(f"{col}2:{col}{max(ws.max_row + 500, 501)}")

        output.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output)
        return {
            "path": _portable_path(output), "sheetCount": len(wb.sheetnames),
            "sheets": wb.sheetnames, "baselineDbSha256": baseline,
            "workbookSha256": file_hash(output),
        }
    finally:
        conn.close()


def _manifest(wb) -> dict[str, Any]:
    ws = wb["00_Manifest"]
    return {str(row[0].value): row[1].value for row in ws.iter_rows(min_row=2) if row[0].value}


def _headers(ws) -> list[str]:
    return [str(cell.value) if cell.value is not None else "" for cell in ws[1]]


def _workbook_rows(ws) -> list[tuple[int, dict[str, Any]]]:
    headers = _headers(ws)
    rows: list[tuple[int, dict[str, Any]]] = []
    for number, cells in enumerate(ws.iter_rows(min_row=2), start=2):
        if all(cell.value is None for cell in cells):
            continue
        rows.append((number, {headers[index]: _json_value(cell.value) for index, cell in enumerate(cells)}))
    return rows


def _business_values(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key not in META_COLUMNS}


def _key(sheet: str, row: dict[str, Any]) -> str:
    return canonical_hash({key: row.get(key) for key in PRIMARY_KEYS[sheet]})


def annotate_validation_errors(
    workbook: str | Path,
    errors: Iterable[dict[str, Any]],
    output: str | Path,
) -> dict[str, Any]:
    """Write an actionable, ordered error sheet to a workbook copy."""
    workbook = Path(workbook).resolve()
    output = Path(output).resolve()
    wb = load_workbook(workbook, data_only=False)
    if "08_Validation_Errors" not in wb.sheetnames:
        raise WorkbookError("08_Validation_Errors sheet is missing")
    ws = wb["08_Validation_Errors"]
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)
    sheet_order = {name: index for index, name in enumerate(SHEETS)}
    ordered = sorted(
        errors,
        key=lambda error: (
            sheet_order.get(str(error.get("sheet")), len(SHEETS)),
            int(error.get("row") or 0),
            str(error.get("field") or ""),
            str(error.get("code") or ""),
            str(error.get("message") or ""),
        ),
    )
    for error in ordered:
        ws.append(
            [
                error.get("sheet"),
                error.get("row"),
                error.get("field"),
                error.get("code"),
                error.get("message"),
            ]
        )
    _style_sheet(ws)
    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)
    return {
        "path": _portable_path(output),
        "errorCount": len(ordered),
        "workbookSha256": file_hash(output),
    }


def validate_workbook(workbook: str | Path, database: str | Path) -> dict[str, Any]:
    workbook = Path(workbook).resolve()
    database = Path(database).resolve()
    wb = load_workbook(workbook, data_only=False)
    errors: list[dict[str, Any]] = []

    if wb.sheetnames != list(SHEETS):
        errors.append({"sheet": "WORKBOOK", "row": 0, "field": "sheetnames", "code": "SHEET_SET", "message": "Workbook must contain the exact nine sheets in contract order."})
        return {"valid": False, "errors": errors, "workbookSha256": file_hash(workbook)}

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.data_type == "f":
                    errors.append({"sheet": ws.title, "row": cell.row, "field": cell.coordinate, "code": "FORMULA", "message": "Formulas are forbidden in curation workbooks."})

    manifest = _manifest(wb)
    conn = connect(database)
    try:
        current_db_hash = catalog_state_hash(conn)
        refs = _reference_lists(conn)
        table_columns = {sheet: _table_columns(conn, table) for sheet, table in TABLE_SHEETS.items()}
        table_columns["06_Type_Specific"] = list(TYPE_FIELDS)
        for sheet in SHEETS[1:7]:
            ws = wb[sheet]
            expected_headers = [*META_COLUMNS, *table_columns[sheet]]
            if _headers(ws) != expected_headers:
                errors.append({"sheet": sheet, "row": 1, "field": "headers", "code": "HEADERS", "message": "Columns differ from the exported contract."})
                continue
            seen_keys: dict[str, int] = {}
            for row_number, row in _workbook_rows(ws):
                action = row.get("_action")
                if action not in ACTION_VALUES:
                    errors.append({"sheet": sheet, "row": row_number, "field": "_action", "code": "ACTION", "message": f"Invalid action {action}."})
                    continue
                values = _business_values(row)
                semantic_key = _key(sheet, values)
                if semantic_key in seen_keys:
                    errors.append({
                        "sheet": sheet,
                        "row": row_number,
                        "field": ",".join(PRIMARY_KEYS[sheet]),
                        "code": "DUPLICATE_ROW_KEY",
                        "message": (
                            "Editable row identity duplicates row "
                            f"{seen_keys[semantic_key]}."
                        ),
                    })
                else:
                    seen_keys[semantic_key] = row_number
                baseline_key = row.get("_baseline_key")
                if baseline_key and baseline_key != semantic_key:
                    errors.append({"sheet": sheet, "row": row_number, "field": PRIMARY_KEYS[sheet][0], "code": "IMMUTABLE_ID", "message": "Primary identity changed since export."})
                proposed_hash = row_hash(values)
                if action == "NO_CHANGE" and row.get("_baseline_hash") != proposed_hash:
                    errors.append({"sheet": sheet, "row": row_number, "field": "_action", "code": "ACTION_REQUIRED", "message": "Edited row must use UPSERT or DEPRECATE."})
                if action == "DEPRECATE" and sheet != "01_Artifacts":
                    errors.append({"sheet": sheet, "row": row_number, "field": "_action", "code": "DEPRECATE_SCOPE", "message": "Only catalog artifacts support logical deprecation."})
                for field, allowed in refs.items():
                    if field in values and values[field] not in (None, "") and values[field] not in allowed:
                        errors.append({"sheet": sheet, "row": row_number, "field": field, "code": "ENUM", "message": f"Value {values[field]} is not controlled."})
                if sheet == "01_Artifacts" and action == "UPSERT":
                    for field in load_contract()["core_required"]:
                        if values.get(field) in (None, ""):
                            errors.append({"sheet": sheet, "row": row_number, "field": field, "code": "MINIMUM", "message": "Required by the minimum catalog contract."})
                    confidence = values.get("classification_confidence")
                    if confidence is not None and float(confidence) <= 0.70 and not (
                        values.get("requires_human_review") in (1, True)
                        and values.get("ai_review_status") == "AIR-HUMAN-REVIEW"
                    ):
                        errors.append({"sheet": sheet, "row": row_number, "field": "classification_confidence", "code": "LOW_CONFIDENCE", "message": "Low confidence requires explicit human-review flags."})
    finally:
        conn.close()
    return {
        "valid": not errors, "errors": errors,
        "baselineDbSha256": manifest.get("baseline_db_sha256"),
        "currentDbSha256": current_db_hash,
        "workbookSha256": file_hash(workbook),
    }


def _current_row(conn: sqlite3.Connection, sheet: str, values: dict[str, Any]) -> dict[str, Any] | None:
    if sheet == "06_Type_Specific":
        row = conn.execute(
            "SELECT " + ",".join(f"{c if c != 'artifact_id' else 'id AS artifact_id'}" for c in TYPE_FIELDS)
            + " FROM security_artifacts WHERE id=?", (values.get("artifact_id"),)
        ).fetchone()
        return _row_dict(row, TYPE_FIELDS) if row else None
    table = TABLE_SHEETS[sheet]
    keys = PRIMARY_KEYS[sheet]
    if any(values.get(key) in (None, "") for key in keys):
        return None
    where = " AND ".join(f"{key}=?" for key in keys)
    row = conn.execute(
        f"SELECT * FROM {table} WHERE {where}", tuple(values[key] for key in keys)
    ).fetchone()
    return _row_dict(row) if row else None


def plan_workbook(
    workbook: str | Path, database: str | Path,
    resolutions: dict[str, str] | None = None,
) -> dict[str, Any]:
    validation = validate_workbook(workbook, database)
    resolutions = resolutions or {}
    if not validation["valid"]:
        raise WorkbookError(f"workbook validation failed with {len(validation['errors'])} error(s)")
    wb = load_workbook(workbook, data_only=False)
    conn = connect(database)
    try:
        entries: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        db_stale = validation["baselineDbSha256"] != validation["currentDbSha256"]
        for sheet in SHEETS[1:7]:
            for row_number, row in _workbook_rows(wb[sheet]):
                action = row["_action"]
                if action == "NO_CHANGE":
                    continue
                values = _business_values(row)
                key = _key(sheet, values)
                current = _current_row(conn, sheet, values)
                current_hash = row_hash(current) if current else None
                resolution = resolutions.get(f"{sheet}:{key}") or resolutions.get("__database__")
                stale = db_stale or (
                    row.get("_baseline_hash") is not None
                    and current_hash != row.get("_baseline_hash")
                )
                if stale and resolution not in ("USE_WORKBOOK", "USE_DATABASE", "MANUAL"):
                    conflicts.append({"sheet": sheet, "row": row_number, "rowKey": key, "reason": "STALE_BASELINE"})
                entries.append({
                    "sheet": sheet, "row": row_number, "rowKey": key,
                    "action": action, "baselineHash": row.get("_baseline_hash"),
                    "currentHash": current_hash, "proposedHash": row_hash(values),
                    "values": values, "resolution": resolution,
                })
        plan = {
            "contract": "secureguide-catalog-workbook-plan-v1",
            "database": _portable_path(database),
            "workbook": _portable_path(workbook),
            "baselineDbSha256": validation["baselineDbSha256"],
            "currentDbSha256": validation["currentDbSha256"],
            "workbookSha256": validation["workbookSha256"],
            "entries": entries, "conflicts": conflicts,
        }
        plan["planSha256"] = canonical_hash(plan)
        return plan
    finally:
        conn.close()


def _update_artifact(conn: sqlite3.Connection, values: dict[str, Any]) -> None:
    artifact_id = values["id"]
    columns = _table_columns(conn, "security_artifacts")
    existing = conn.execute("SELECT 1 FROM security_artifacts WHERE id=?", (artifact_id,)).fetchone()
    writable = [c for c in columns if c in values and c != "id"]
    if existing:
        conn.execute(
            "UPDATE security_artifacts SET " + ",".join(f"{c}=?" for c in writable) + " WHERE id=?",
            tuple(values[c] for c in writable) + (artifact_id,),
        )
    else:
        insert_columns = [c for c in columns if c in values and values[c] is not None]
        conn.execute(
            f"INSERT INTO security_artifacts({','.join(insert_columns)}) VALUES({','.join('?' for _ in insert_columns)})",
            tuple(values[c] for c in insert_columns),
        )


def _apply_entry(conn: sqlite3.Connection, entry: dict[str, Any]) -> None:
    sheet, action, values = entry["sheet"], entry["action"], entry["values"]
    if entry.get("resolution") == "USE_DATABASE":
        return
    if action == "DEPRECATE":
        conn.execute(
            "UPDATE security_artifacts SET publication_status='DEPRECATED',is_active=0,"
            "updated_at=datetime('now'),version=version+1 WHERE id=?", (values["id"],)
        )
        return
    if sheet == "01_Artifacts":
        _update_artifact(conn, values)
    elif sheet == "06_Type_Specific":
        writable = [field for field in TYPE_FIELDS[1:] if field in values]
        conn.execute(
            "UPDATE security_artifacts SET " + ",".join(f"{f}=?" for f in writable) + " WHERE id=?",
            tuple(values[field] for field in writable) + (values["artifact_id"],),
        )
    else:
        table = TABLE_SHEETS[sheet]
        columns = [c for c in _table_columns(conn, table) if c in values and values[c] is not None]
        keys = PRIMARY_KEYS[sheet]
        current = _current_row(conn, sheet, values)
        if current:
            writable = [c for c in columns if c not in keys]
            if writable:
                conn.execute(
                    f"UPDATE {table} SET " + ",".join(f"{c}=?" for c in writable)
                    + " WHERE " + " AND ".join(f"{k}=?" for k in keys),
                    tuple(values[c] for c in writable) + tuple(values[k] for k in keys),
                )
        else:
            conn.execute(
                f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
                tuple(values[c] for c in columns),
            )


def apply_workbook_plan(plan: dict[str, Any], *, actor: str = "codex") -> dict[str, Any]:
    database = Path(plan["database"]).resolve()
    if database == RELEASE_ASSET:
        raise WorkbookError("direct curation of mobile/assets/catalog.db is forbidden")
    if canonical_hash({k: v for k, v in plan.items() if k != "planSha256"}) != plan.get("planSha256"):
        raise WorkbookError("plan hash mismatch")
    unresolved = [c for c in plan["conflicts"] if not any(
        e["rowKey"] == c["rowKey"] and e.get("resolution") in ("USE_WORKBOOK", "USE_DATABASE", "MANUAL")
        for e in plan["entries"]
    )]
    if unresolved:
        raise WorkbookConflict(f"{len(unresolved)} unresolved workbook conflict(s)")
    if file_hash(plan["workbook"]) != plan["workbookSha256"]:
        raise WorkbookConflict("workbook changed after plan creation")

    conn = connect(database)
    run_id = f"WBR-{uuid.uuid4()}"
    try:
        conn.execute("BEGIN IMMEDIATE")
        current_state = catalog_state_hash(conn)
        if current_state != plan["currentDbSha256"]:
            raise WorkbookConflict("database changed after plan creation")
        conn.execute(
            """INSERT INTO catalog_workbook_runs(
                   id,operation,workbook_path,baseline_db_sha256,workbook_sha256,
                   status,actor,conflict_resolution_json
               ) VALUES(?,?,?,?,?,'STARTED',?,?)""",
            (run_id, "APPLY", plan["workbook"], plan["baselineDbSha256"],
             plan["workbookSha256"], actor,
             json.dumps({e["rowKey"]: e.get("resolution") for e in plan["entries"] if e.get("resolution")}, sort_keys=True)),
        )
        affected: set[str] = set()
        for entry in plan["entries"]:
            if entry.get("resolution") == "MANUAL":
                raise WorkbookConflict(f"manual resolution incomplete for {entry['rowKey']}")
            _apply_entry(conn, entry)
            artifact_id = entry["values"].get("id") or entry["values"].get("artifact_id")
            if artifact_id:
                affected.add(str(artifact_id))
            conn.execute(
                """INSERT INTO catalog_workbook_row_audit(
                       run_id,sheet_name,row_key,action,baseline_hash,current_hash,
                       proposed_hash,outcome,resolution
                   ) VALUES(?,?,?,?,?,?,?,'APPLIED',?)""",
                (run_id, entry["sheet"], entry["rowKey"], entry["action"],
                 entry["baselineHash"], entry["currentHash"], entry["proposedHash"],
                 entry.get("resolution")),
            )
        contract = load_contract()
        invalid: list[dict[str, Any]] = []
        for artifact_id in sorted(affected):
            row = conn.execute("SELECT * FROM security_artifacts WHERE id=?", (artifact_id,)).fetchone()
            if row and row["is_active"]:
                result = minimum_result(conn, row, contract)
                if not result["valid"]:
                    invalid.append({"id": artifact_id, **result})
        if invalid:
            raise WorkbookError(f"post-apply minimum validation failed: {invalid[:3]}")
        summary = {"entries": len(plan["entries"]), "affectedArtifacts": len(affected)}
        conn.execute(
            "UPDATE catalog_workbook_runs SET status='APPLIED',summary_json=?,completed_at=datetime('now') WHERE id=?",
            (json.dumps(summary, sort_keys=True), run_id),
        )
        conn.execute("COMMIT")
        return {"status": "APPLIED", "runId": run_id, **summary, "catalogStateSha256": catalog_state_hash(conn)}
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
