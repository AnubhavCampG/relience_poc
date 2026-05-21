"""PostgreSQL DDL transpilation and CSV seed loader."""

import csv
import re

from sqlalchemy import text

from app.config import get_settings
from app.db.engine import get_engine

CSV_TABLES = (
    "MDM_DIM_PRODUCT_MASTER_MV",
    "FCT_INVENTORY_MV",
    "PORTAL_CUSTOMER",
)


def transpile_to_postgres(sql_content: str) -> list[str]:
    """Convert MS SQL / Snowflake DDL to PostgreSQL-compatible statements."""
    sql_content = re.sub(r"(?m)^\s*GO\s*$", ";", sql_content, flags=re.IGNORECASE)
    statements: list[str] = []

    for raw in sql_content.split(";"):
        stmt = raw.strip()
        if not stmt:
            continue

        if "PORTAL_CUSTOMER_CONTACT" in stmt.upper():
            continue

        stmt = re.sub(
            r"create\s+or\s+replace\s+TABLE",
            "CREATE TABLE IF NOT EXISTS",
            stmt,
            flags=re.IGNORECASE,
        )
        stmt = stmt.replace("CREATE TABLE [dbo].", "CREATE TABLE IF NOT EXISTS ")
        stmt = stmt.replace("[dbo].", "")
        stmt = re.sub(r"\[([^\]]+)\]", r"\1", stmt)

        stmt = re.sub(r"NUMBER\(\d+,\d+\)", "NUMERIC", stmt, flags=re.IGNORECASE)
        stmt = re.sub(r"NUMBER\(\d+\)", "NUMERIC", stmt, flags=re.IGNORECASE)
        stmt = re.sub(r"NUMBER\b", "NUMERIC", stmt, flags=re.IGNORECASE)
        stmt = re.sub(r"VARCHAR\(16777216\)", "TEXT", stmt, flags=re.IGNORECASE)
        stmt = re.sub(r"VARCHAR\(\d+\)", "VARCHAR", stmt, flags=re.IGNORECASE)
        stmt = re.sub(r"TIMESTAMP_NTZ\(\d+\)", "TIMESTAMPTZ", stmt, flags=re.IGNORECASE)
        stmt = re.sub(r"TIMESTAMP_NTZ", "TIMESTAMPTZ", stmt, flags=re.IGNORECASE)
        stmt = re.sub(r"\bdate\b", "DATE", stmt, flags=re.IGNORECASE)
        stmt = re.sub(r"\bbit\b", "BOOLEAN", stmt, flags=re.IGNORECASE)
        stmt = re.sub(r"decimal\(\d+,\s*\d+\)", "NUMERIC", stmt, flags=re.IGNORECASE)
        stmt = re.sub(r"\bint\b", "INTEGER", stmt, flags=re.IGNORECASE)
        stmt = re.sub(r"\bFLOAT\b", "DOUBLE PRECISION", stmt, flags=re.IGNORECASE)

        if "CONSTRAINT PK_PORTAL_CUSTOMER" in stmt:
            stmt = re.sub(
                r",?\s*CONSTRAINT\s+PK_PORTAL_CUSTOMER.*$",
                "",
                stmt,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if not stmt.strip().endswith(")"):
                stmt += ")"

        stmt = re.sub(r"\)\s*ON\s+PRIMARY.*$", ");", stmt, flags=re.IGNORECASE | re.DOTALL)
        stmt = re.sub(r"WITH\s*\(.*$", "", stmt, flags=re.IGNORECASE | re.DOTALL)
        stmt = re.sub(r"\)\s*ON\s+\[PRIMARY\].*$", ");", stmt, flags=re.IGNORECASE | re.DOTALL)

        if "CREATE TABLE" in stmt.upper() and "IF NOT EXISTS" not in stmt.upper():
            stmt = stmt.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS", 1)

        if "CREATE TABLE" in stmt.upper():
            match = re.search(
                r"CREATE TABLE IF NOT EXISTS\s+(\w+)",
                stmt,
                flags=re.IGNORECASE,
            )
            if match:
                table_name = match.group(1)
                stmt = stmt.replace(
                    f"CREATE TABLE IF NOT EXISTS {table_name}",
                    f'CREATE TABLE IF NOT EXISTS "{table_name}"',
                    1,
                )
            statements.append(stmt)

    return statements


def drop_tables(engine) -> None:
    tables = list(get_settings().allowed_tables)
    with engine.connect() as conn:
        for table in reversed(tables):
            conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
        conn.commit()


def import_csv(engine, table: str, csv_path) -> int:
    from pathlib import Path

    path = Path(csv_path)
    if not path.exists():
        print(f"File not found: {path}")
        return 0

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        if not headers:
            return 0
        rows = [tuple(row.get(h, "") for h in headers) for row in reader]

    if not rows:
        return 0

    cols = ", ".join(f'"{h}"' for h in headers)
    placeholders = ", ".join([f":{h}" for h in headers])
    insert_sql = f'INSERT INTO "{table}" ({cols}) VALUES ({placeholders})'

    with engine.connect() as conn:
        conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
        for row in rows:
            params = {h: row[i] for i, h in enumerate(headers)}
            conn.execute(text(insert_sql), params)
        conn.commit()

    return len(rows)


def setup_database(reset: bool = True) -> dict[str, int]:
    """Create tables from DDL and load CSV seed data."""
    settings = get_settings()
    engine = get_engine()

    if reset:
        drop_tables(engine)

    with open(settings.ddl_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    print("--- Creating Tables ---")
    for stmt in transpile_to_postgres(sql_content):
        try:
            with engine.connect() as conn:
                conn.execute(text(stmt))
                conn.commit()
            print(f"Success: {stmt[:60]}...")
        except Exception as e:
            print(f"Skipped/Failed: {stmt[:60]}... | Error: {e}")

    print("\n--- Importing Data ---")
    counts: dict[str, int] = {}
    for table in CSV_TABLES:
        csv_path = settings.seed_csv_path(table)
        try:
            count = import_csv(engine, table, csv_path)
            counts[table] = count
            print(f"Imported {count} rows into {table}")
        except Exception as e:
            print(f"Error importing {table}: {e}")
            counts[table] = 0

    print("\n--- Final Verification ---")
    with engine.connect() as conn:
        for table in settings.allowed_tables:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            count = result.scalar()
            print(f"Table {table}: {count} rows")
            counts[table] = count or 0

    return counts
