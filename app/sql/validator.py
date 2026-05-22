"""SQL validation layer using sqlglot."""

import re

import sqlglot
from sqlglot import exp

from app.config import get_settings

ALLOWED_TABLES = set(get_settings().allowed_tables)

DISALLOWED_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.TruncateTable,
    exp.Merge,
    exp.Command,
)


class SQLValidationError(Exception):
    """
    Task:
        Custom exception class raised when SQL query validation fails safety or syntax checks.
    """
    pass


def _normalize_query(query: str) -> str:
    """
    Task:
        Clean up SQL statements by stripping whitespace, removing markdown code blocks,
        and slicing trailing semicolons.

    Input_Params:
        query (str):
            The raw SQL string to normalize.
            Example: "```sql SELECT * FROM table; ```"

    Output_Params:
        str:
            Cleaned SQL statement without wrapping markers.

    Returns:
        str:
            Normalized SQL query string.
    """
    q = query.strip()
    # Remove markdown code fences if present
    q = re.sub(r"^```(?:sql)?\s*", "", q, flags=re.IGNORECASE)
    q = re.sub(r"\s*```$", "", q)
    return q.strip().rstrip(";")


def validate_sql(query: str) -> str:
    """
    Task:
        Perform comprehensive static safety checks on a SQL query using sqlglot.
        Ensures the query is a single SELECT statement, references only whitelisted tables,
        and optionally blocks SELECT * expressions.

    Input_Params:
        query (str):
            The drafted SQL query statement.
            Example: "SELECT * FROM PORTAL_CUSTOMER"

    Output_Params:
        str:
            The safe, normalized SQL statement.

    Returns:
        str:
            Verified normalized SQL query string.

    Raises:
        SQLValidationError:
            If query fails syntax checks, executes multiple statements, performs mutation actions (INSERT/DROP),
            references illegal tables, or breaks SELECT * rules.
    """
    settings = get_settings()
    normalized = _normalize_query(query)

    if not normalized:
        raise SQLValidationError("Empty SQL query")

    if ";" in normalized:
        raise SQLValidationError("Multiple statements are not allowed")

    try:
        expressions = sqlglot.parse(normalized, read="postgres")
    except Exception as e:
        raise SQLValidationError(f"SQL parse error: {e}") from e

    if len(expressions) != 1:
        raise SQLValidationError("Exactly one SQL statement is required")

    expression = expressions[0]

    if not isinstance(expression, exp.Select):
        raise SQLValidationError("Only SELECT statements are allowed")

    for node in expression.walk():
        if isinstance(node, DISALLOWED_EXPRESSIONS):
            raise SQLValidationError(
                f"Disallowed statement type: {type(node).__name__}"
            )

    if settings.sql_reject_select_star:
        for star in expression.find_all(exp.Star):
            if star.parent and not isinstance(star.parent, exp.Count):
                raise SQLValidationError("SELECT * is not allowed")

    referenced_tables: set[str] = set()
    for table in expression.find_all(exp.Table):
        name = table.name
        if name:
            referenced_tables.add(name.upper())

    if not referenced_tables:
        raise SQLValidationError("Query must reference at least one table")

    disallowed = referenced_tables - ALLOWED_TABLES
    if disallowed:
        raise SQLValidationError(
            f"Tables not allowed: {', '.join(sorted(disallowed))}. "
            f"Allowed: {', '.join(sorted(ALLOWED_TABLES))}"
        )

    return normalized
