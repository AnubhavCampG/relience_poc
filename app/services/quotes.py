"""Sales quote persistence."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.config import get_settings
from app.db.engine import get_engine


def _quotes_dir() -> Path:
    """
    Task:
        Retrieve the local system path to the sales quotes folder, creating folders dynamically if required.

    Input_Params:
        None

    Output_Params:
        Path:
            The resolved quotes folder path.

    Returns:
        Path:
            Resolved quotes directory.
    """
    settings = get_settings()
    path = settings.project_root / settings.quotes_dir
    path.mkdir(parents=True, exist_ok=True)
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    return path


def validate_customer_exists(customer_no: str) -> bool:
    """
    Task:
        Check database records using the customer reference identifier to verify if they exist in the PORTAL_CUSTOMER table.

    Input_Params:
        customer_no (str):
            The unique customer reference ID.
            Example: "CUST-998"

    Output_Params:
        bool:
            True if customer is verified and exists in database, otherwise False.

    Returns:
        bool:
            Boolean representation of customer existence status.
    """
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text('SELECT 1 FROM "PORTAL_CUSTOMER" WHERE "CUST_NO" = :cust LIMIT 1'),
            {"cust": customer_no},
        )
        return result.fetchone() is not None


def create_quote(customer_no: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Task:
        Draft a new sales quote for a verified customer, calculate basic metrics, persist it to a local JSON file in quotes directory, and return metadata.

    Input_Params:
        customer_no (str):
            The target customer identification number.
            Example: "CUST-998"
        items (list[dict[str, Any]]):
            Line items list, each describing a product, quantity, and price.
            Example: [{"product_id": "P1", "quantity": 5.0, "price": 10.0}]

    Output_Params:
        dict[str, Any]:
            A summary dictionary containing quote details, creation message, and path to generated document.

    Returns:
        dict[str, Any]:
            Generated quote summary.

    Raises:
        ValueError:
            Raised if customer does not exist in the system database records.
    """
    if not validate_customer_exists(customer_no):
        raise ValueError(f"Customer {customer_no} not found")

    quote = {
        "customer_no": customer_no,
        "items": items,
        "total_items": len(items),
        "status": "Draft",
        "generated_by": "Reliance AI Copilot",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    filename = f"Sales_Quote_{customer_no}.json"
    filepath = _quotes_dir() / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(quote, f, indent=2)

    return {
        "success": True,
        "file_created": str(filepath),
        "message": f"Successfully created {filename}",
        "quote": quote,
    }


def list_quotes_for_customer(customer_no: str) -> list[dict[str, Any]]:
    """
    Task:
        Scan the quotes directory for JSON sales quote documents matching the specified customer, parse their contents, and return a list of records.

    Input_Params:
        customer_no (str):
            The unique customer reference ID.
            Example: "CUST-998"

    Output_Params:
        list[dict[str, Any]]:
            A list of dictionary records containing parsed details of matches.

    Returns:
        list[dict[str, Any]]:
            List of parsed quotes.
    """
    quotes_dir = _quotes_dir()
    pattern = f"Sales_Quote_{customer_no}*.json"
    results = []
    for path in quotes_dir.glob(pattern):
        with open(path, "r", encoding="utf-8") as f:
            results.append(json.load(f))
    return results
