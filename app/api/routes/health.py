from fastapi import APIRouter

from app.api.schemas import HealthResponse, ReadyResponse
from app.db.engine import check_db_connection
from app.schema.introspect import get_schema_fragment

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    db_ok = check_db_connection()
    schema_ok = False
    if db_ok:
        try:
            fragment = get_schema_fragment(force_refresh=True)
            schema_ok = bool(fragment)
        except Exception:
            schema_ok = False

    status = "ready" if db_ok and schema_ok else "degraded"
    return ReadyResponse(status=status, database=db_ok, schema_cached=schema_ok)
