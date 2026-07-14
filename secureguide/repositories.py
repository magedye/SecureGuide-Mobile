"""Data-access repositories. Business decisions belong in services, not SQL callers."""

from __future__ import annotations

import sqlite3
from typing import Any, Iterable


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def rows_dict(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


class CatalogRepository:
    """Read-only Master Catalog access with optional profile-state projection."""

    FILTER_COLUMNS = {
        "type": "a.type",
        "primary_domain": "a.primary_domain",
        "sub_domain": "a.sub_domain",
        "obligation_level": "a.obligation_level",
        "testability": "a.testability",
        "priority": "COALESCE(pa.priority_override,pa.template_priority_default,a.priority)",
        "ai_review_status": "a.ai_review_status",
        "implementation_status": "pa.implementation_status",
        "verification_status": "pa.verification_status",
        "effectiveness": "pa.effectiveness",
        "exception_status": "pa.exception_status",
    }

    def get(self, conn: sqlite3.Connection, artifact_id: str) -> dict[str, Any] | None:
        return row_dict(
            conn.execute(
                "SELECT * FROM security_artifacts WHERE id=?", (artifact_id,)
            ).fetchone()
        )

    def selectable_ids(
        self, conn: sqlite3.Connection, artifact_ids: Iterable[str]
    ) -> set[str]:
        ids = list(dict.fromkeys(artifact_ids))
        if not ids:
            return set()
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"""SELECT id FROM security_artifacts
                 WHERE id IN ({placeholders})
                   AND is_active=1 AND publication_status IN ('APPROVED','PUBLISHED')""",
            ids,
        ).fetchall()
        return {row[0] for row in rows}

    def search(
        self,
        conn: sqlite3.Connection,
        *,
        profile_id: str | None = None,
        locale: str = "en",
        query: str | None = None,
        filters: dict[str, Any] | None = None,
        selected_only: bool = False,
        publication_status: str | Iterable[str] | None = ("APPROVED", "PUBLISHED"),
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        filters = filters or {}
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))
        locale = locale or "en"
        preferred_title = (
            "COALESCE(loc.title,a.title_ar,a.title_en)"
            if locale.startswith("ar")
            else "COALESCE(loc.title,a.title_en,a.title_ar)"
        )
        preferred_short = (
            "COALESCE(loc.definition_short,a.definition_short_ar,a.definition_short_en)"
            if locale.startswith("ar")
            else "COALESCE(loc.definition_short,a.definition_short_en,a.definition_short_ar)"
        )
        sql = f"""
            SELECT a.id,a.type,{preferred_title} AS title,
                   {preferred_short} AS definition_short,
                   a.primary_domain,a.sub_domain,a.source,a.source_document,
                   a.obligation_level,a.testability,a.ai_review_status,
                   a.publication_status,
                   COALESCE(pa.priority_override,pa.template_priority_default,a.priority) AS effective_priority,
                   pa.id AS profile_artifact_id,pa.inclusion_status,
                   pa.implementation_status,pa.verification_status,
                   pa.effectiveness,pa.exception_status,pa.assigned_owner,pa.due_date,
                   (SELECT COUNT(*) FROM profile_evidence e
                     WHERE e.profile_artifact_id=pa.id) AS evidence_count
              FROM security_artifacts a
              LEFT JOIN artifact_localizations loc
                ON loc.artifact_id=a.id AND loc.locale=?
              LEFT JOIN profile_artifacts pa
                ON pa.artifact_id=a.id AND pa.profile_id=?
             WHERE a.is_active=1
        """
        params: list[Any] = [locale, profile_id]
        if publication_status is not None:
            statuses = (
                [publication_status]
                if isinstance(publication_status, str)
                else list(dict.fromkeys(publication_status))
            )
            if not statuses:
                sql += " AND 0=1"
            else:
                sql += f" AND a.publication_status IN ({','.join('?' for _ in statuses)})"
                params.extend(statuses)
        if selected_only:
            sql += " AND pa.id IS NOT NULL"
        if query and query.strip():
            needle = f"%{query.strip().lower()}%"
            sql += f""" AND (
                lower({preferred_title}) LIKE ?
                OR lower(COALESCE({preferred_short},'')) LIKE ?
                OR lower(COALESCE(a.source_document,'')) LIKE ?
                OR EXISTS (SELECT 1 FROM artifact_tags tq
                            WHERE tq.artifact_id=a.id
                              AND lower(tq.tag_value) LIKE ?)
            )"""
            params.extend([needle, needle, needle, needle])

        for key, column in self.FILTER_COLUMNS.items():
            value = filters.get(key)
            if value is not None:
                if key in {
                    "implementation_status",
                    "verification_status",
                    "effectiveness",
                    "exception_status",
                } and profile_id is None:
                    sql += " AND 0=1"
                else:
                    sql += f" AND {column}=?"
                    params.append(value)

        source = filters.get("source")
        if source:
            sql += " AND (a.source=? OR a.source_document=?)"
            params.extend([source, source])
        framework = filters.get("framework")
        if framework:
            sql += """ AND EXISTS (SELECT 1 FROM framework_mappings fm
                                      WHERE fm.artifact_id=a.id AND fm.framework=?)"""
            params.append(framework)
        tag_type = filters.get("tag_type")
        tag_value = filters.get("tag_value")
        if tag_type or tag_value:
            sql += " AND EXISTS (SELECT 1 FROM artifact_tags tf WHERE tf.artifact_id=a.id"
            if tag_type:
                sql += " AND tf.tag_type=?"
                params.append(tag_type)
            if tag_value:
                sql += " AND lower(tf.tag_value)=lower(?)"
                params.append(tag_value)
            sql += ")"
        scope_type = filters.get("applicability_scope_type")
        scope_value = filters.get("applicability_scope_value")
        if scope_type or scope_value:
            sql += " AND EXISTS (SELECT 1 FROM artifact_applicability_scope aps WHERE aps.artifact_id=a.id"
            if scope_type:
                sql += " AND aps.scope_type=?"
                params.append(scope_type)
            if scope_value:
                sql += " AND lower(aps.scope_value)=lower(?)"
                params.append(scope_value)
            sql += ")"

        sql += f" ORDER BY {preferred_title},a.id LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return rows_dict(conn.execute(sql, params).fetchall())


class TemplateRepository:
    def get(self, conn: sqlite3.Connection, template_id: str) -> dict[str, Any] | None:
        return row_dict(conn.execute("SELECT * FROM templates WHERE id=?", (template_id,)).fetchone())

    def items(
        self,
        conn: sqlite3.Connection,
        template_id: str,
        inclusion_statuses: Iterable[str],
    ) -> list[dict[str, Any]]:
        statuses = list(dict.fromkeys(inclusion_statuses))
        if not statuses:
            return []
        marks = ",".join("?" for _ in statuses)
        return rows_dict(
            conn.execute(
                f"""SELECT ti.*
                       FROM template_items ti
                       JOIN security_artifacts a ON a.id=ti.artifact_id
                      WHERE ti.template_id=?
                        AND ti.inclusion_status IN ({marks})
                        AND a.is_active=1 AND a.publication_status IN ('APPROVED','PUBLISHED')
                      ORDER BY ti.id""",
                [template_id, *statuses],
            ).fetchall()
        )


class ProfileRepository:
    OPERATIONAL_UPDATE_FIELDS = {
        "implementation_status",
        "verification_status",
        "effectiveness",
        "current_maturity_level",
        "assigned_owner",
        "due_date",
        "notes",
        "priority_override",
        "review_frequency_override",
    }

    def create(self, conn: sqlite3.Connection, values: dict[str, Any]) -> dict[str, Any]:
        columns = list(values)
        conn.execute(
            f"INSERT INTO enterprise_profiles({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            [values[column] for column in columns],
        )
        return self.get(conn, values["id"])

    def get(self, conn: sqlite3.Connection, profile_id: str) -> dict[str, Any] | None:
        return row_dict(conn.execute("SELECT * FROM enterprise_profiles WHERE id=?", (profile_id,)).fetchone())

    def list(self, conn: sqlite3.Connection) -> list[dict[str, Any]]:
        return rows_dict(conn.execute("SELECT * FROM enterprise_profiles ORDER BY name,id").fetchall())

    def set_active(self, conn: sqlite3.Connection, profile_id: str | None) -> None:
        conn.execute(
            "UPDATE application_state SET active_profile_id=?,updated_at=datetime('now') WHERE singleton_id=1",
            (profile_id,),
        )

    def active(self, conn: sqlite3.Connection) -> dict[str, Any] | None:
        return row_dict(
            conn.execute(
                """SELECT p.* FROM application_state s
                     JOIN enterprise_profiles p ON p.id=s.active_profile_id
                    WHERE s.singleton_id=1"""
            ).fetchone()
        )

    def profile_artifact(
        self,
        conn: sqlite3.Connection,
        profile_id: str,
        *,
        artifact_id: str | None = None,
        profile_artifact_id: str | None = None,
    ) -> dict[str, Any] | None:
        if profile_artifact_id:
            row = conn.execute(
                "SELECT * FROM profile_artifacts WHERE profile_id=? AND id=?",
                (profile_id, profile_artifact_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM profile_artifacts WHERE profile_id=? AND artifact_id=?",
                (profile_id, artifact_id),
            ).fetchone()
        return row_dict(row)

    def add_artifact(
        self,
        conn: sqlite3.Connection,
        *,
        row_id: str,
        profile_id: str,
        artifact_id: str,
        template_item_id: str | None = None,
        inclusion_status: str | None = None,
        template_priority_default: str | None = None,
        template_review_frequency_default: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        existing = self.profile_artifact(conn, profile_id, artifact_id=artifact_id)
        if existing:
            return existing, False
        conn.execute(
            """INSERT INTO profile_artifacts(
                   id,profile_id,artifact_id,template_item_id,inclusion_status,
                   template_priority_default,template_review_frequency_default)
               VALUES (?,?,?,?,?,?,?)""",
            (
                row_id,
                profile_id,
                artifact_id,
                template_item_id,
                inclusion_status,
                template_priority_default,
                template_review_frequency_default,
            ),
        )
        return self.profile_artifact(conn, profile_id, artifact_id=artifact_id), True

    def update_template_defaults(
        self,
        conn: sqlite3.Connection,
        profile_artifact_id: str,
        *,
        template_item_id: str,
        inclusion_status: str | None,
        priority: str | None,
        review_frequency: str | None,
    ) -> None:
        conn.execute(
            """UPDATE profile_artifacts
                  SET template_item_id=COALESCE(template_item_id,?),
                      inclusion_status=?,
                      template_priority_default=?,
                      template_review_frequency_default=?,
                      updated_at=datetime('now')
                WHERE id=?""",
            (template_item_id, inclusion_status, priority, review_frequency, profile_artifact_id),
        )

    def update_inclusion_status(
        self, conn: sqlite3.Connection, profile_artifact_id: str, inclusion_status: str | None
    ) -> None:
        conn.execute(
            """UPDATE profile_artifacts
                  SET inclusion_status=?,updated_at=datetime('now')
                WHERE id=?""",
            (inclusion_status, profile_artifact_id),
        )

    def add_origin(self, conn: sqlite3.Connection, values: dict[str, Any]) -> bool:
        columns = list(values)
        before = conn.total_changes
        conn.execute(
            f"INSERT OR IGNORE INTO profile_artifact_origins({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            [values[column] for column in columns],
        )
        return conn.total_changes > before

    def record_template_application(
        self, conn: sqlite3.Connection, values: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        existing = conn.execute(
            """SELECT * FROM profile_templates
                WHERE profile_id=? AND template_id=? AND template_version=?""",
            (values["profile_id"], values["template_id"], values["template_version"]),
        ).fetchone()
        if existing:
            return dict(existing), False
        columns = list(values)
        conn.execute(
            f"INSERT INTO profile_templates({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            [values[column] for column in columns],
        )
        return (
            dict(
                conn.execute(
                    "SELECT * FROM profile_templates WHERE id=?", (values["id"],)
                ).fetchone()
            ),
            True,
        )

    def set_primary_template_if_empty(
        self, conn: sqlite3.Connection, profile_id: str, template_id: str
    ) -> None:
        conn.execute(
            """UPDATE enterprise_profiles
                  SET source_template_id=COALESCE(source_template_id,?),updated_at=datetime('now')
                WHERE id=?""",
            (template_id, profile_id),
        )

    def update_operational_state(
        self, conn: sqlite3.Connection, profile_artifact_id: str, changes: dict[str, Any]
    ) -> None:
        invalid = set(changes) - self.OPERATIONAL_UPDATE_FIELDS
        if invalid:
            raise ValueError(f"unsupported operational fields: {sorted(invalid)}")
        if not changes:
            return
        columns = list(changes)
        assignments = ",".join(f"{column}=?" for column in columns)
        conn.execute(
            f"UPDATE profile_artifacts SET {assignments},updated_at=datetime('now') WHERE id=?",
            [*[changes[column] for column in columns], profile_artifact_id],
        )

    def add_assessment(self, conn: sqlite3.Connection, values: dict[str, Any]) -> dict[str, Any]:
        columns = list(values)
        conn.execute(
            f"INSERT INTO profile_assessments({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            [values[column] for column in columns],
        )
        return row_dict(conn.execute("SELECT * FROM profile_assessments WHERE id=?", (values["id"],)).fetchone())

    def add_evidence(self, conn: sqlite3.Connection, values: dict[str, Any]) -> dict[str, Any]:
        columns = list(values)
        conn.execute(
            f"INSERT INTO profile_evidence({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            [values[column] for column in columns],
        )
        return row_dict(conn.execute("SELECT * FROM profile_evidence WHERE id=?", (values["id"],)).fetchone())

    def add_exception(self, conn: sqlite3.Connection, values: dict[str, Any]) -> dict[str, Any]:
        columns = list(values)
        conn.execute(
            f"INSERT INTO profile_exceptions({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            [values[column] for column in columns],
        )
        return self.exception(conn, values["id"])

    def exception(self, conn: sqlite3.Connection, exception_id: str) -> dict[str, Any] | None:
        return row_dict(conn.execute("SELECT * FROM profile_exceptions WHERE id=?", (exception_id,)).fetchone())

    def exception_for_profile(
        self, conn: sqlite3.Connection, profile_id: str, exception_id: str
    ) -> dict[str, Any] | None:
        return row_dict(
            conn.execute(
                """SELECT pe.* FROM profile_exceptions pe
                     JOIN profile_artifacts pa ON pa.id=pe.profile_artifact_id
                    WHERE pe.id=? AND pa.profile_id=?""",
                (exception_id, profile_id),
            ).fetchone()
        )

    def transition_exception(
        self, conn: sqlite3.Connection, exception_id: str, changes: dict[str, Any]
    ) -> dict[str, Any]:
        columns = list(changes)
        assignments = ",".join(f"{column}=?" for column in columns)
        conn.execute(
            f"UPDATE profile_exceptions SET {assignments},updated_at=datetime('now') WHERE id=?",
            [*[changes[column] for column in columns], exception_id],
        )
        return self.exception(conn, exception_id)

    def dashboard_counts(self, conn: sqlite3.Connection, profile_id: str) -> dict[str, Any]:
        return row_dict(conn.execute("SELECT * FROM v_profile_dashboard WHERE profile_id=?", (profile_id,)).fetchone())

    def gaps(self, conn: sqlite3.Connection, profile_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return rows_dict(
            conn.execute(
                """SELECT * FROM v_gap_analysis WHERE profile_id=?
                    ORDER BY CASE priority
                      WHEN 'PRI-CRITICAL' THEN 1 WHEN 'PRI-HIGH' THEN 2
                      WHEN 'PRI-MEDIUM' THEN 3 ELSE 4 END,
                    due_date IS NULL,due_date,artifact_id LIMIT ?""",
                (profile_id, max(1, min(int(limit), 200))),
            ).fetchall()
        )

    def operational_items(self, conn: sqlite3.Connection, profile_id: str) -> list[dict[str, Any]]:
        return rows_dict(
            conn.execute(
                "SELECT * FROM v_profile_operational_items WHERE profile_id=? ORDER BY artifact_id",
                (profile_id,),
            ).fetchall()
        )


class BlueprintRepository:
    """Profile-scoped persistence for approved blueprint snapshots and tasks."""

    @staticmethod
    def _insert(conn: sqlite3.Connection, table: str, values: dict[str, Any]) -> None:
        columns = list(values)
        conn.execute(
            f"INSERT INTO {table}({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            [values[column] for column in columns],
        )

    def get(
        self, conn: sqlite3.Connection, profile_id: str, blueprint_id: str
    ) -> dict[str, Any] | None:
        return row_dict(
            conn.execute(
                "SELECT * FROM approved_blueprints WHERE id=? AND profile_id=?",
                (blueprint_id, profile_id),
            ).fetchone()
        )

    def latest_for_profile_artifact(
        self, conn: sqlite3.Connection, profile_artifact_id: str
    ) -> dict[str, Any] | None:
        return row_dict(
            conn.execute(
                """SELECT * FROM approved_blueprints
                    WHERE profile_artifact_id=? ORDER BY version DESC LIMIT 1""",
                (profile_artifact_id,),
            ).fetchone()
        )

    def candidate_for_profile_artifact(
        self, conn: sqlite3.Connection, profile_artifact_id: str
    ) -> dict[str, Any] | None:
        return row_dict(
            conn.execute(
                """SELECT * FROM approved_blueprints
                    WHERE profile_artifact_id=?
                      AND workflow_status IN ('DRAFT','UNDER_REVIEW')""",
                (profile_artifact_id,),
            ).fetchone()
        )

    def approved_for_profile_artifact(
        self, conn: sqlite3.Connection, profile_artifact_id: str
    ) -> dict[str, Any] | None:
        return row_dict(
            conn.execute(
                """SELECT * FROM approved_blueprints
                    WHERE profile_artifact_id=? AND workflow_status='APPROVED'""",
                (profile_artifact_id,),
            ).fetchone()
        )

    def create(self, conn: sqlite3.Connection, values: dict[str, Any]) -> dict[str, Any]:
        self._insert(conn, "approved_blueprints", values)
        return self.get(conn, values["profile_id"], values["id"])

    def add_rule(self, conn: sqlite3.Connection, values: dict[str, Any]) -> None:
        self._insert(conn, "approved_blueprint_rules", values)

    def add_action(self, conn: sqlite3.Connection, values: dict[str, Any]) -> None:
        self._insert(conn, "approved_blueprint_actions", values)

    def add_action_rule(self, conn: sqlite3.Connection, values: dict[str, Any]) -> None:
        self._insert(conn, "approved_blueprint_action_rules", values)

    def add_output(self, conn: sqlite3.Connection, values: dict[str, Any]) -> None:
        self._insert(conn, "approved_blueprint_outputs", values)

    def add_output_rule(self, conn: sqlite3.Connection, values: dict[str, Any]) -> None:
        self._insert(conn, "approved_blueprint_output_rules", values)

    def add_evidence(self, conn: sqlite3.Connection, values: dict[str, Any]) -> None:
        self._insert(conn, "approved_blueprint_evidence", values)

    def add_evidence_rule(self, conn: sqlite3.Connection, values: dict[str, Any]) -> None:
        self._insert(conn, "approved_blueprint_evidence_rules", values)

    def transition(
        self, conn: sqlite3.Connection, blueprint_id: str, changes: dict[str, Any]
    ) -> None:
        columns = list(changes)
        assignments = ",".join(f"{column}=?" for column in columns)
        conn.execute(
            f"""UPDATE approved_blueprints SET {assignments},
                       updated_at=datetime('now'),row_version=row_version+1
                 WHERE id=?""",
            [*[changes[column] for column in columns], blueprint_id],
        )

    def list(
        self,
        conn: sqlite3.Connection,
        profile_id: str,
        *,
        artifact_id: str | None = None,
        workflow_status: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM v_profile_blueprints WHERE profile_id=?"
        params: list[Any] = [profile_id]
        if artifact_id:
            sql += " AND artifact_id=?"
            params.append(artifact_id)
        if workflow_status:
            sql += " AND workflow_status=?"
            params.append(workflow_status)
        sql += " ORDER BY artifact_id,version DESC"
        return rows_dict(conn.execute(sql, params).fetchall())

    def detail(
        self, conn: sqlite3.Connection, profile_id: str, blueprint_id: str
    ) -> dict[str, Any] | None:
        blueprint = self.get(conn, profile_id, blueprint_id)
        if not blueprint:
            return None
        blueprint["applied_rules"] = rows_dict(
            conn.execute(
                """SELECT * FROM approved_blueprint_rules WHERE blueprint_id=?
                    ORDER BY CASE stage WHEN 'ARTIFACT_TYPE' THEN 1
                      WHEN 'CONTROL_NATURE' THEN 2 WHEN 'CONTROL_FUNCTION' THEN 3
                      WHEN 'SECURITY_DOMAIN' THEN 4 ELSE 5 END,priority,rule_id""",
                (blueprint_id,),
            ).fetchall()
        )
        actions = rows_dict(
            conn.execute(
                """SELECT * FROM approved_blueprint_actions WHERE blueprint_id=?
                    ORDER BY display_order,id""",
                (blueprint_id,),
            ).fetchall()
        )
        for action in actions:
            action["source_rules"] = rows_dict(
                conn.execute(
                    """SELECT rule_id,rule_version FROM approved_blueprint_action_rules
                        WHERE action_id=? ORDER BY rule_id,rule_version""",
                    (action["id"],),
                ).fetchall()
            )
        blueprint["actions"] = actions
        outputs = rows_dict(
            conn.execute(
                """SELECT * FROM approved_blueprint_outputs WHERE blueprint_id=?
                    ORDER BY id""",
                (blueprint_id,),
            ).fetchall()
        )
        for output in outputs:
            output["source_rules"] = rows_dict(
                conn.execute(
                    """SELECT rule_id,rule_version FROM approved_blueprint_output_rules
                        WHERE output_id=? ORDER BY rule_id,rule_version""",
                    (output["id"],),
                ).fetchall()
            )
        blueprint["expected_outputs"] = outputs
        evidence = rows_dict(
            conn.execute(
                """SELECT * FROM approved_blueprint_evidence WHERE blueprint_id=?
                    ORDER BY mandatory DESC,evidence_type,id""",
                (blueprint_id,),
            ).fetchall()
        )
        for item in evidence:
            item["source_rules"] = rows_dict(
                conn.execute(
                    """SELECT rule_id,rule_version FROM approved_blueprint_evidence_rules
                        WHERE evidence_id=? ORDER BY rule_id,rule_version""",
                    (item["id"],),
                ).fetchall()
            )
        blueprint["evidence"] = evidence
        blueprint["review_events"] = rows_dict(
            conn.execute(
                """SELECT * FROM blueprint_review_events WHERE blueprint_id=?
                    ORDER BY event_at,id""",
                (blueprint_id,),
            ).fetchall()
        )
        blueprint["review_findings"] = rows_dict(
            conn.execute(
                """SELECT * FROM approved_blueprint_review_findings
                    WHERE blueprint_id=? ORDER BY finding_type,finding_code,id""",
                (blueprint_id,),
            ).fetchall()
        )
        return blueprint

    def materialize_tasks(
        self,
        conn: sqlite3.Connection,
        *,
        blueprint: dict[str, Any],
        created_by: str,
        priority: str | None,
        assigned_to: str | None,
        due_date: str | None,
        id_factory: Any,
    ) -> tuple[int, int, list[str]]:
        actions = rows_dict(
            conn.execute(
                """SELECT * FROM approved_blueprint_actions
                    WHERE blueprint_id=? AND taskable=1 ORDER BY display_order,id""",
                (blueprint["id"],),
            ).fetchall()
        )
        created = existing = 0
        task_ids: list[str] = []
        for action in actions:
            current = conn.execute(
                "SELECT id FROM profile_tasks WHERE blueprint_action_id=?",
                (action["id"],),
            ).fetchone()
            if current:
                existing += 1
                task_ids.append(current["id"])
                continue
            task_id = id_factory("TSK")
            self._insert(conn, "profile_tasks", {
                "id": task_id,
                "profile_id": blueprint["profile_id"],
                "profile_artifact_id": blueprint["profile_artifact_id"],
                "blueprint_id": blueprint["id"],
                "blueprint_action_id": action["id"],
                "source_semantic_key": action["semantic_key"],
                "title": action["title"],
                "description": action["description"],
                "priority": priority,
                "assigned_to": assigned_to,
                "due_date": due_date,
                "created_by": created_by,
                "last_changed_by": created_by,
            })
            created += 1
            task_ids.append(task_id)
        return created, existing, task_ids

    def add_event(self, conn: sqlite3.Connection, values: dict[str, Any]) -> None:
        self._insert(conn, "blueprint_review_events", values)

    def add_review_finding(
        self, conn: sqlite3.Connection, values: dict[str, Any]
    ) -> None:
        self._insert(conn, "approved_blueprint_review_findings", values)

    def task(
        self, conn: sqlite3.Connection, profile_id: str, task_id: str
    ) -> dict[str, Any] | None:
        return row_dict(
            conn.execute(
                "SELECT * FROM profile_tasks WHERE id=? AND profile_id=?",
                (task_id, profile_id),
            ).fetchone()
        )

    def update_task(
        self, conn: sqlite3.Connection, task_id: str, changes: dict[str, Any]
    ) -> None:
        columns = list(changes)
        assignments = ",".join(f"{column}=?" for column in columns)
        conn.execute(
            f"UPDATE profile_tasks SET {assignments},updated_at=datetime('now') WHERE id=?",
            [*[changes[column] for column in columns], task_id],
        )

    def tasks(
        self, conn: sqlite3.Connection, profile_id: str, status: str | None = None
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM v_profile_task_queue WHERE profile_id=?"
        params: list[Any] = [profile_id]
        if status:
            sql += " AND status=?"
            params.append(status)
        sql += " ORDER BY due_date IS NULL,due_date,priority,id"
        return rows_dict(conn.execute(sql, params).fetchall())
