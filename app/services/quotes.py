"""Sales quote persistence."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.config import get_settings
from app.db.engine import get_engine


def _quotes_dir() -> Path:
    settings = get_settings()
    path = settings.project_root / settings.quotes_dir
    path.mkdir(parents=True, exist_ok=True)
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    return path


def validate_customer_exists(customer_no: str) -> bool:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text('SELECT 1 FROM "PORTAL_CUSTOMER" WHERE "CUST_NO" = :cust LIMIT 1'),
            {"cust": customer_no},
        )
        return result.fetchone() is not None


def create_quote(customer_no: str, items: list[dict[str, Any]]) -> dict[str, Any]:
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
    quotes_dir = _quotes_dir()
    pattern = f"Sales_Quote_{customer_no}*.json"
    results = []
    for path in quotes_dir.glob(pattern):
        with open(path, "r", encoding="utf-8") as f:
            results.append(json.load(f))
    return results
