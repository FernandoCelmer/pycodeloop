"""SQL Tools — read-only query and schema introspection for any
SQLAlchemy-supported database via a connection URL (sqlite, postgresql,
mysql, ...). Only SELECT/WITH/EXPLAIN/PRAGMA/SHOW/DESCRIBE statements
are allowed — no writes, no DDL."""

from __future__ import annotations

import re

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from pycodeloop.abc.tool import Tool, ToolResult
from pycodeloop.tools._limits import truncate

_READ_ONLY = re.compile(
    r"^\s*(--[^\n]*\n\s*)*(select|with|explain|pragma|show|describe|desc)\b",
    re.IGNORECASE,
)


def _is_read_only(query: str) -> bool:
    return bool(_READ_ONLY.match(query))


def _has_multiple_statements(query: str) -> bool:
    return ";" in query.strip().rstrip(";")


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
                "description": "Omit to list every table instead of one table's columns.",
            },
        },
        "required": ["url"],
    }

    def run(self, url: str, table: str = "") -> ToolResult:
        try:
            engine = create_engine(url)
            inspector = inspect(engine)
        except SQLAlchemyError as exc:
            return ToolResult(output=f"Error connecting: {exc}", is_error=True)

        try:
            if table:
                columns = inspector.get_columns(table)
                if not columns:
                    return ToolResult(output=f"No such table: {table}", is_error=True)
                lines = [
                    f"{c['name']}\t{c['type']}"
                    + ("" if c.get("nullable", True) else "\tNOT NULL")
                    for c in columns
                ]
                return ToolResult(output=truncate("\n".join(lines)))

            tables = inspector.get_table_names()
            return ToolResult(
                output=truncate("\n".join(sorted(tables))) if tables else "(no tables)"
            )
        except SQLAlchemyError as exc:
            return ToolResult(output=f"Error inspecting schema: {exc}", is_error=True)
        finally:
            engine.dispose()


class SqlQueryTool(Tool):
    name = "sql_query"
    description = (
        "Run a single read-only SQL statement (SELECT, WITH, EXPLAIN, "
        "PRAGMA, SHOW, or DESCRIBE — no INSERT/UPDATE/DELETE/DDL, no "
        "multiple statements) against a database and return the results "
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

    def run(self, url: str, query: str, max_rows: int = 200) -> ToolResult:
        if _has_multiple_statements(query):
            return ToolResult(
                output="Only a single SQL statement is allowed.", is_error=True
            )

        if not _is_read_only(query):
            return ToolResult(
                output=(
                    "Only read-only statements are allowed (SELECT, WITH, "
                    "EXPLAIN, PRAGMA, SHOW, DESCRIBE)."
                ),
                is_error=True,
            )

        try:
            engine = create_engine(url)
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
            return ToolResult(output=f"Error running query: {exc}", is_error=True)
        finally:
            engine.dispose()

        if not rows:
            return ToolResult(output="(no rows)")

        lines = ["\t".join(columns)]
        lines += ["\t".join("" if v is None else str(v) for v in row) for row in rows]
        summary = "\n".join(lines)
        if len(rows) >= max_rows:
            summary += f"\n… (capped at {max_rows} rows)"

        return ToolResult(output=truncate(summary))
