"""Tests fuer `_ensure_schema()`: keine ueberfluessigen DDL-Aufrufe wenn
Schema und Tabellen bereits existieren (verhindert PostgreSQL-ERROR-Spam
im DB-Log durch CREATE-Versuche ohne Owner-Rechte).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.db_schema import ensure_schema as _ensure_schema


class FakeConn:
    """Sammelt alle execute()-Aufrufe und beantwortet fetchval/fetch
    nach einem konfigurierbaren Plan."""

    def __init__(
        self,
        *,
        schema_exists: bool,
        existing_tables: list[str],
    ) -> None:
        self.schema_exists = schema_exists
        self.existing_tables = existing_tables
        self.executed: list[str] = []

    async def fetchval(self, sql: str, *args: Any) -> bool:
        # Schema-Existenz-Check
        if "information_schema.schemata" in sql:
            return self.schema_exists
        return False

    async def fetch(self, sql: str, *args: Any) -> list[dict[str, str]]:
        if "information_schema.tables" in sql:
            return [{"table_name": t} for t in self.existing_tables]
        return []

    async def execute(self, sql: str, *args: Any) -> str:
        self.executed.append(sql.strip())
        return "OK"


class FakePool:
    def __init__(self, conn: FakeConn) -> None:
        self._conn = conn

    def acquire(self) -> "FakePoolAcquire":
        return FakePoolAcquire(self._conn)


class FakePoolAcquire:
    def __init__(self, conn: FakeConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> FakeConn:
        return self._conn

    async def __aexit__(self, *args: Any) -> None:
        pass


def _count_create_statements(executed: list[str]) -> dict[str, int]:
    """Zaehlt, wie oft welche Art von CREATE im Log auftaucht."""
    return {
        "schema": sum(1 for s in executed if s.upper().startswith("CREATE SCHEMA")),
        "table": sum(1 for s in executed if s.upper().startswith("CREATE TABLE")),
        "index": sum(1 for s in executed if s.upper().startswith("CREATE INDEX")),
    }


@pytest.mark.asyncio
async def test_alles_existiert_keine_ddl() -> None:
    """Production-Normalfall: Schema + beide Tabellen existieren bereits
    aus 002_schema.sql. Es darf NULL CREATE-Statements geben — sonst
    spammt PostgreSQL den Log mit "must be owner" / "permission denied"."""
    conn = FakeConn(
        schema_exists=True,
        existing_tables=["analysis_cache", "export_log"],
    )
    pool = FakePool(conn)

    await _ensure_schema(pool)  # type: ignore[arg-type]

    counts = _count_create_statements(conn.executed)
    assert counts["schema"] == 0, "CREATE SCHEMA darf nicht abgesetzt werden, wenn schon existiert"
    assert counts["table"] == 0, "CREATE TABLE darf nicht abgesetzt werden, wenn schon existiert"
    assert counts["index"] == 0, "CREATE INDEX darf nicht abgesetzt werden, wenn Tabelle schon existiert"


@pytest.mark.asyncio
async def test_schema_fehlt_legt_alles_an() -> None:
    """Fresh-DB-Fall: Nichts existiert. Service muss Schema + 2 Tabellen + 2 Indizes anlegen."""
    conn = FakeConn(schema_exists=False, existing_tables=[])
    pool = FakePool(conn)

    await _ensure_schema(pool)  # type: ignore[arg-type]

    counts = _count_create_statements(conn.executed)
    assert counts["schema"] == 1
    # Hinweis: Nach erfolgreichem CREATE SCHEMA kommt der zweite Existenz-Check
    # (information_schema.tables) — dort ist die Antwort weiterhin []
    # (FakeConn aktualisiert sich nicht). Also CREATE TABLE x2 + CREATE INDEX x2.
    assert counts["table"] == 2
    assert counts["index"] == 2


@pytest.mark.asyncio
async def test_nur_export_log_fehlt_kein_index_neu_angelegt() -> None:
    """Mischfall: Schema + analysis_cache existieren (mit eigenen Indizes vom
    DB-Init), nur export_log fehlt. Es darf NUR CREATE TABLE export_log
    abgesetzt werden — keine Indizes auf der bestehenden analysis_cache."""
    conn = FakeConn(schema_exists=True, existing_tables=["analysis_cache"])
    pool = FakePool(conn)

    await _ensure_schema(pool)  # type: ignore[arg-type]

    counts = _count_create_statements(conn.executed)
    assert counts["schema"] == 0
    assert counts["table"] == 1, "Nur export_log soll angelegt werden"
    assert counts["index"] == 0, "Keine Indizes auf vorhandener analysis_cache!"
    # Verifikation, dass es wirklich export_log ist (nicht analysis_cache):
    create_table_sql = next(s for s in conn.executed if s.upper().startswith("CREATE TABLE"))
    assert "export_log" in create_table_sql.lower()
    assert "analysis_cache" not in create_table_sql.lower()


@pytest.mark.asyncio
async def test_schema_create_fehler_beendet_sauber_kein_crash() -> None:
    """Wenn svc_export auch CREATE SCHEMA verweigert, soll der Service trotzdem
    sauber starten (Best-Effort). Keine Exception ans lifespan-aufrufende Framework."""
    conn = FakeConn(schema_exists=False, existing_tables=[])

    async def raising_execute(sql: str, *args: Any) -> str:
        if "CREATE SCHEMA" in sql.upper():
            raise PermissionError("permission denied for database ti_radar")
        conn.executed.append(sql.strip())
        return "OK"

    conn.execute = raising_execute  # type: ignore[assignment]
    pool = FakePool(conn)

    # Darf NICHT propagieren
    await _ensure_schema(pool)  # type: ignore[arg-type]
    # Wenn wir hier sind, ist alles gut.
