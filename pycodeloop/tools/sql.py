"""SQL Tools — read-only query and schema introspection for any
SQLAlchemy-supported database via a connection URL (sqlite, postgresql,
mysql, ...). Only SELECT/WITH/EXPLAIN/PRAGMA/SHOW/DESCRIBE statements
are allowed — no writes, no DDL. Connections are opened read-only when
the dialect supports it."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from pycodeloop.abc.tool import Tool, ToolResult
from pycodeloop.tools._limits import truncate

_READ_ONLY = re.compile(
    r"^\s*(?:(?:--[^\n]*\n|/\*.*?\*/)\s*)*"
    r"(select|with|explain|pragma|show|describe|desc)\b",
    re.IGNORECASE | re.DOTALL,
)

_SAFE_PRAGMA = re.compile(
    r"^\s*(?:(?:--[^\n]*\n|/\*.*?\*/)\s*)*pragma\s+"
    r"(table_info|index_list|index_info|database_list|"
    r"foreign_key_list|table_list|compile_options|"
    r"integrity_check|quick_check|table_xinfo)\b",
    re.IGNORECASE | re.DOTALL,
)

_FORBIDDEN = re.compile(
    r"\b(into\s+outfile|into\s+dumpfile|for\s+update|load_file\s*\(|"
    r"pg_read_file\s*\(|copy\s+\w+\s+to\b|attach\s+database\b|"
    r"detach\s+database\b)",
    re.IGNORECASE,
)

_ALLOWED_SCHEMES = {
    "sqlite",
    "sqlite+pysqlite",
    "postgresql",
    "postgresql+psycopg",
    "postgresql+psycopg2",
    "postgres",
    "mysql",
    "mysql+pymysql",
    "mysql+mysqldb",
    "mariadb",
    "mariadb+pymysql",
}


def _is_read_only(query: str) -> bool:
    if not _READ_ONLY.match(query):
        return False
    if _FORBIDDEN.search(query):
        return False
    if re.match(
        r"^\s*(?:(?:--[^\n]*\n|/\*.*?\*/)\s*)*pragma\b",
        query,
        re.IGNORECASE | re.DOTALL,
    ):
        return bool(_SAFE_PRAGMA.match(query))
    return True


def _has_multiple_statements(query: str) -> bool:
    return ";" in query.strip().rstrip(";")


def _validate_url(url: str) -> str | None:
    """Return an error message if `url` is not an allowed SQLAlchemy URL,
    else None."""
    if not url or "://" not in url:
        return "URL must be a SQLAlchemy URL (e.g. sqlite:///path/to.db)."
    scheme = urlparse(url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        allowed = ", ".join(sorted(_ALLOWED_SCHEMES))
        return f"Unsupported database scheme {scheme!r}. Allowed: {allowed}."
    return None


def _create_engine(url: str, read_only: bool = False):
    engine = create_engine(url)

    if read_only:

        @event.listens_for(engine, "connect")
        def _set_read_only(dbapi_conn, _connection_record) -> None:
            dialect = engine.dialect.name
            try:
                if dialect == "sqlite":
                    dbapi_conn.execute("PRAGMA query_only = ON")
                elif dialect in {"postgresql", "postgres"}:
                    cursor = dbapi_conn.cursor()
                    try:
                        cursor.execute(
                            "SET SESSION CHARACTERISTICS AS "
                            "TRANSACTION READ ONLY"
                        )
                    finally:
                        cursor.close()
                elif dialect in {"mysql", "mariadb"}:
                    cursor = dbapi_conn.cursor()
                    try:
                        cursor.execute("SET SESSION TRANSACTION READ ONLY")
                    finally:
                        cursor.close()
            except Exception:
                pass

    return engine


class SqlSchemaTool(Tool):
    name = "sql_schema"
    description = (
        "List tables in a database, or the columns of one table. Pass a "
        "SQLAlchemy connection `url` (e.g. 'sqlite:///path/to.db', "
        "'postgresql://user:pass@host/db', 'mysql+pymysql://user:pass@"
        "host/db'). Use before sql_query to see what's there."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "table": {
                "type": "string",
                "description": (
                    "Omit to list every table instead of one table's columns."
                ),
            },
        },
        "required": ["url"],
    }
    dangerous = True

    def preview(self, url: str, table: str = "", **_) -> str:
        target = f"table {table}" if table else "all tables"
        return f"$ sql_schema {url} ({target})"

    def run(self, url: str, table: str = "") -> ToolResult:
        err = _validate_url(url)
        if err:
            return ToolResult(output=err, is_error=True)

        try:
            engine = _create_engine(url, read_only=True)
            inspector = inspect(engine)
        except SQLAlchemyError as exc:
            return ToolResult(output=f"Error connecting: {exc}", is_error=True)

        try:
            if table:
                columns = inspector.get_columns(table)
                if not columns:
                    return ToolResult(
                        output=f"No such table: {table}", is_error=True
                    )
                lines = [
                    f"{c['name']}\t{c['type']}"
                    + ("" if c.get("nullable", True) else "\tNOT NULL")
                    for c in columns
                ]
                return ToolResult(output=truncate("\n".join(lines)))

            tables = inspector.get_table_names()
            return ToolResult(
                output=(
                    truncate("\n".join(sorted(tables)))
                    if tables
                    else "(no tables)"
                )
            )
        except SQLAlchemyError as exc:
            return ToolResult(
                output=f"Error inspecting schema: {exc}", is_error=True
            )
        finally:
            engine.dispose()


class SqlQueryTool(Tool):
    name = "sql_query"
    description = (
        "Run a single read-only SQL statement (SELECT, WITH, EXPLAIN, "
        "safe PRAGMA, SHOW, or DESCRIBE — no INSERT/UPDATE/DELETE/DDL, "
        "no multiple statements) against a database and return the results "
        "as a tab-separated table. Pass a SQLAlchemy connection `url`. "
        "Use sql_schema first if you don't know the tables/columns yet."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "query": {"type": "string"},
            "max_rows": {"type": "integer", "default": 200},
        },
        "required": ["url", "query"],
    }
    dangerous = True

    def preview(self, url: str, query: str = "", **_) -> str:
        return f"$ sql_query {url}\n{query}"

    def run(self, url: str, query: str, max_rows: int = 200) -> ToolResult:
        err = _validate_url(url)
        if err:
            return ToolResult(output=err, is_error=True)

        if _has_multiple_statements(query):
            return ToolResult(
                output="Only a single SQL statement is allowed.", is_error=True
            )

        if not _is_read_only(query):
            return ToolResult(
                output=(
                    "Only read-only statements are allowed (SELECT, WITH, "
                    "EXPLAIN, safe PRAGMA, SHOW, DESCRIBE)."
                ),
                is_error=True,
            )

        try:
            engine = _create_engine(url, read_only=True)
        except SQLAlchemyError as exc:
            return ToolResult(output=f"Error connecting: {exc}", is_error=True)

        try:
            with engine.connect() as conn:
                result = conn.execute(text(query))
                if not result.returns_rows:
                    return ToolResult(output="(no rows returned)")
                columns = list(result.keys())
                rows = result.fetchmany(max_rows)
        except SQLAlchemyError as exc:
            return ToolResult(
                output=f"Error running query: {exc}", is_error=True
            )
        finally:
            engine.dispose()

        if not rows:
            return ToolResult(output="(no rows)")

        lines = ["\t".join(columns)]
        lines += [
            "\t".join("" if v is None else str(v) for v in row) for row in rows
        ]
        summary = "\n".join(lines)
        if len(rows) >= max_rows:
            summary += f"\n… (capped at {max_rows} rows)"

        return ToolResult(output=truncate(summary))
