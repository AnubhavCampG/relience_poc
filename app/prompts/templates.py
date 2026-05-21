"""Schema-aware prompt templates."""

from app.schema.introspect import get_schema_fragment


def build_system_prompt(schema_fragment: str | None = None) -> str:
    schema = schema_fragment or get_schema_fragment()
    return f"""You are an intelligent AI assistant for Reliance Data.
Your goal is to help users query the PostgreSQL database for customers, products, and inventory,
and generate Sales Quotes when requested.

{schema}

When asked to search or analyze data, formulate a PostgreSQL SELECT query.
Use CUSTOMER_NO (not CUST_NO) on FCT_INVENTORY_MV when joining to customers.
When asked to create a quote, gather customer number, product IDs, quantities, and prices.
When asked to extract or summarize PDF documents, use the PDF extraction capability.
"""


def build_sql_writer_prompt(user_query: str, schema_fragment: str | None = None) -> str:
    schema = schema_fragment or get_schema_fragment()
    return f"""Generate a single PostgreSQL SELECT statement to answer the user question.
Return ONLY the SQL query, no markdown fences, no explanation.

Schema:
{schema}

User question: {user_query}
"""


def build_repair_prompt(
    user_query: str,
    failed_sql: str,
    error: str,
    schema_fragment: str | None = None,
) -> str:
    schema = schema_fragment or get_schema_fragment()
    return f"""The following SQL query failed validation or execution. Fix it.

Schema:
{schema}

User question: {user_query}

Failed SQL:
{failed_sql}

Error:
{error}

Return ONLY the corrected PostgreSQL SELECT statement.
"""


def build_respond_prompt(user_query: str, context: str) -> str:
    return f"""Based on the query results below, provide a clear, concise natural language answer.

User question: {user_query}

Context (SQL results or quote status):
{context}
"""
