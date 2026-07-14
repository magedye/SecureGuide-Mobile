"""SQLite connection and migration infrastructure for SecureGuide."""

from __future__ import annotations

import contextlib
import sqlite3
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parent.parent


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a configured SQLite connection with integrity features enabled."""
    conn = sqlite3.connect(str(path), timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _has_migration_table(conn: sqlite3.Connection) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone() is not None


def apply_migrations(
    path: str | Path, migrations_dir: str | Path | None = None
) -> list[str]:
    """Apply missing ordered SQL migrations and run post-apply integrity checks.

    Migrations 001-003 predate the bookkeeping table; migration 004 records all
    four. On a new database they are therefore applied in order before normal
    version checks take over.
    """
    directory = Path(migrations_dir) if migrations_dir else ROOT / "migrations"
    files = sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))
    applied: list[str] = []
    conn = connect(path)
    try:
        for migration in files:
            version = migration.name[:3]
            if _has_migration_table(conn):
                exists = conn.execute(
                    "SELECT 1 FROM schema_migrations WHERE version=?", (version,)
                ).fetchone()
                if exists:
                    continue
            conn.executescript(migration.read_text(encoding="utf-8"))
            applied.append(version)

        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise sqlite3.DatabaseError(f"integrity_check failed: {integrity}")
        foreign_key_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if foreign_key_errors:
            raise sqlite3.IntegrityError(
                f"foreign_key_check found {len(foreign_key_errors)} issue(s)"
            )
        return applied
    finally:
        conn.close()


class Database:
    """Small unit-of-work boundary shared by repositories and services."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    @contextlib.contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        conn = connect(self.path)
        try:
            yield conn
        finally:
            conn.close()

    @contextlib.contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = connect(self.path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def migrate(self) -> list[str]:
        return apply_migrations(self.path)
