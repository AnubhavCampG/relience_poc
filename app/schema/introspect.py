"""Dynamic schema introspection from PostgreSQL information_schema."""

import time
from dataclasses import dataclass, field

from sqlalchemy import text

from app.config import get_settings
from app.db.engine import get_engine

JOIN_PATHS = """
Join paths:
- FCT_INVENTORY_MV.CUSTOMER_NO -> PORTAL_CUSTOMER.CUST_NO
- FCT_INVENTORY_MV.PRODUCT_ID -> MDM_DIM_PRODUCT_MASTER_MV.PRODUCT_ID
"""


@dataclass
class SchemaCache:
    fragment: str = ""
    fetched_at: float = 0.0


_cache = SchemaCache()


def _fetch_schema_fragment() -> str:
    settings = get_settings()
    tables = settings.allowed_tables
    placeholders = ", ".join(f"'{t}'" for t in tables)

    query = text(f"""
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name IN ({placeholders})
        ORDER BY table_name, ordinal_position
    """)

    engine = get_engine()
    lines: list[str] = ["Database schema (PostgreSQL):", ""]

    with engine.connect() as conn:
        result = conn.execute(query)
        current_table = None
        for row in result:
            table_name, col_name, data_type, nullable = row
            if table_name != current_table:
                if current_table is not None:
                    lines.append("")
                current_table = table_name
                lines.append(f"Table: {table_name}")
            null_str = "NULL" if nullable == "YES" else "NOT NULL"
            lines.append(f"  - {col_name} ({data_type}, {null_str})")

    lines.append("")
    lines.append(JOIN_PATHS.strip())
    lines.append("")
    lines.append("Important: FCT_INVENTORY_MV uses CUSTOMER_NO (not CUST_NO) for customer linkage.")
    return "\n".join(lines)


def get_schema_fragment(force_refresh: bool = False) -> str:
    settings = get_settings()
    global _cache
    now = time.time()
    if (
        not force_refresh
        and _cache.fragment
        and (now - _cache.fetched_at) < settings.schema_cache_ttl_seconds
    ):
        return _cache.fragment

    _cache.fragment = _fetch_schema_fragment()
    _cache.fetched_at = now
    return _cache.fragment


def invalidate_schema_cache() -> None:
    global _cache
    _cache = SchemaCache()
