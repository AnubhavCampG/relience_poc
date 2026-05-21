"""Bounded read-only SQL execution."""

import json
from typing import Any

from sqlalchemy import text

from app.config import get_settings
from app.db.engine import get_engine
from app.sql.validator import validate_sql


def _ensure_limit(query: str, max_rows: int) -> str:
    upper = query.upper()
    if " LIMIT " in upper:
        return query
    return f"{query.rstrip(';')} LIMIT {max_rows + 1}"


def execute_query(query: str) -> dict[str, Any]:
    """
    Validate and execute a SELECT query.
    Returns structured result dict.
    """
    settings = get_settings()
    validated = validate_sql(query)
    limited_query = _ensure_limit(validated, settings.sql_max_rows)

    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            text(f"SET statement_timeout = {settings.sql_statement_timeout_ms}")
        )
        result = conn.execute(text(limited_query))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]

    truncated = len(rows) > settings.sql_max_rows
    if truncated:
        rows = rows[: settings.sql_max_rows]

    # Serialize for JSON compatibility
    serializable_rows = []
    for row in rows:
        serializable_rows.append(
            {k: (str(v) if v is not None else None) for k, v in row.items()}
        )

    return {
        "columns": columns,
        "rows": serializable_rows,
        "row_count": len(serializable_rows),
        "truncated": truncated,
        "sql_executed": limited_query,
    }


def execute_query_json(query: str) -> str:
    return json.dumps(execute_query(query))
