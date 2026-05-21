#!/usr/bin/env python
"""Initialize PostgreSQL schema and load CSV seed data."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.db.seed import setup_database  # noqa: E402


def main() -> None:
    print("Initializing Reliance PostgreSQL database...")
    counts = setup_database(reset=True)
    print("\nDone. Row counts:", counts)


if __name__ == "__main__":
    main()
