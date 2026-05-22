"""Bounded read-only SQL execution."""

import json
from typing import Any

from sqlalchemy import text

from app.config import get_settings
from app.db.engine import get_engine
from app.sql.validator import validate_sql


def _ensure_limit(query: str, max_rows: int) -> str:
    """
    Task:
        Ensure that the SELECT query contains a LIMIT clause to prevent fetching large results.
        If a LIMIT clause is not present, appends a LIMIT clause bounded to max_rows + 1.

    Input_Params:
        query (str):
            The verified SQL query string.
        max_rows (int):
            The maximum permitted rows allowed to be returned.
            Example: 50

    Output_Params:
        str:
            Query string modified with appropriate LIMIT bounding.

    Returns:
        str:
            SQL statement containing LIMIT.
    """
    upper = query.upper()
    if " LIMIT " in upper:
        return query
    return f"{query.rstrip(';')} LIMIT {max_rows + 1}"


def execute_query(query: str) -> dict[str, Any]:
    """
    Task:
        Validate, limit, and execute a SELECT statement on the database engine.
        Applies a statement-level timeout, fetches results, serializes types for JSON compatibility,
        and flags if results were truncated.

    Input_Params:
        query (str):
            The raw SQL query string to run.
            Example: "SELECT CUST_NAME FROM PORTAL_CUSTOMER"

    Output_Params:
        dict[str, Any]:
            A dictionary containing column keys, serialized rows, final row count, truncation status, and the exact query executed.

    Returns:
        dict[str, Any]:
            Structured query results dictionary.

    Raises:
        SQLValidationError:
            If validation checks fail.
        Exception:
            If database driver encounters operational execution failures.
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
    """
    Task:
        Execute a SQL SELECT statement and return results serialized as a raw JSON string.

    Input_Params:
        query (str):
            The target query string.

    Output_Params:
        str:
            JSON formatted results string.

    Returns:
        str:
            JSON results string.
    """
    return json.dumps(execute_query(query))
