#!/usr/bin/env python
"""
Task:
    CLI executable utility script to initialize the PostgreSQL schema
    and load seed data from Customer, Product, and Inventory CSV datasets.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.db.seed import setup_database  # noqa: E402


def main() -> None:
    """
    Task:
        Main entry point for resetting the PostgreSQL database,
        creating all target schemas dynamically, and populating tables with CSV records.

    Input_Params:
        None

    Output_Params:
        None

    Returns:
        None

    Raises:
        Exception:
            If connection fails or CSV seed file parser crashes.
    """
    print("Initializing Reliance PostgreSQL database...")
    counts = setup_database(reset=True)
    print("\nDone. Row counts:", counts)


if __name__ == "__main__":
    main()
