"""
DEPRECATED: Use scripts/init_db.py with PostgreSQL instead.

Legacy SQLite bootstrap for the original POC.
"""
import csv
import os
import re
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_FILE = PROJECT_ROOT / "runtime" / "reliance_data.db"
SQL_SCRIPT_PATH = DATA_DIR / "ddl" / "Table-Script.sql"

CSV_MAPPING = {
    "MDM_DIM_PRODUCT_MASTER_MV": DATA_DIR / "seed" / "Product.csv",
    "FCT_INVENTORY_MV": DATA_DIR / "seed" / "Inventory.csv",
    "PORTAL_CUSTOMER": DATA_DIR / "seed" / "Customer-Data.csv",
}


def setup_database():
    """
    Task:
        Bootstrap the legacy SQLite database by parsing custom DDL statements and seeding tables from CSV files (deprecated in favor of PostgreSQL).

    Input_Params:
        None

    Output_Params:
        None

    Returns:
        None
    """
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    if DB_FILE.exists():
        DB_FILE.unlink()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        with open(SQL_SCRIPT_PATH, "r") as f:
            sql_content = f.read()

        sql_content = re.sub(r"(?m)^\s*GO\s*$", ";", sql_content, flags=re.IGNORECASE)
        statements = sql_content.split(";")

        print("--- Creating Tables ---")
        for statement in statements:
            stmt = statement.strip()
            if not stmt:
                continue

            stmt = stmt.replace("create or replace TABLE", "CREATE TABLE IF NOT EXISTS")
            stmt = stmt.replace("NUMBER(18,5)", "REAL").replace("NUMBER(38,12)", "REAL")
            stmt = stmt.replace("NUMBER(32,5)", "REAL").replace("NUMBER(20,5)", "REAL")
            stmt = stmt.replace("TIMESTAMP_NTZ(9)", "TEXT").replace("TIMESTAMP_NTZ", "TEXT")
            stmt = stmt.replace("date", "TEXT").replace("bit", "INTEGER")
            stmt = stmt.replace("decimal(12, 4)", "REAL")
            stmt = stmt.replace("VARCHAR(16777216)", "TEXT")
            stmt = re.sub(r"VARCHAR\(\d+\)", "TEXT", stmt, flags=re.IGNORECASE)
            stmt = stmt.replace("[dbo].", "").replace("[", "").replace("]", "")
            stmt = re.sub(r"\)\s*ON\s+PRIMARY.*$", ");", stmt, flags=re.IGNORECASE | re.DOTALL)

            if "CONSTRAINT PK_PORTAL_CUSTOMER" in stmt:
                stmt = re.sub(
                    r",?\s*CONSTRAINT\s+PK_PORTAL_CUSTOMER.*$",
                    "",
                    stmt,
                    flags=re.IGNORECASE | re.DOTALL,
                )
                if not stmt.strip().endswith(")"):
                    stmt += ")"

            try:
                cursor.execute(stmt)
                print(f"Success: {stmt[:40]}...")
            except Exception as e:
                print(f"Skipped/Failed: {stmt[:40]}... | Error: {e}")

        print("\n--- Importing Data ---")
        for table, csv_path in CSV_MAPPING.items():
            if csv_path.exists():
                try:
                    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
                        reader = csv.DictReader(f)
                        headers = reader.fieldnames
                        if not headers:
                            continue
                        placeholders = ", ".join(["?"] * len(headers))
                        cols = ", ".join(headers)
                        insert_sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
                        rows = [tuple(row[h] for h in headers) for row in reader]
                        cursor.executemany(insert_sql, rows)
                        print(f"Imported {len(rows)} rows into {table}")
                except Exception as e:
                    print(f"Error importing {table}: {e}")
            else:
                print(f"File not found: {csv_path}")

        conn.commit()

        print("\n--- Final Verification ---")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        for table in cursor.fetchall():
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            print(f"Table {table[0]}: {cursor.fetchone()[0]} rows")

    finally:
        conn.close()


if __name__ == "__main__":
    setup_database()
