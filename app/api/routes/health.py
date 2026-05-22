from fastapi import APIRouter

from app.api.schemas import HealthResponse, ReadyResponse
from app.db.engine import check_db_connection
from app.schema.introspect import get_schema_fragment

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """
    Task:
        Provide an instantaneous health check response indicating that the web service is running.

    Input_Params:
        None

    Output_Params:
        HealthResponse:
            A Pydantic model response with status set to "ok".

    Returns:
        HealthResponse:
            Health check status representation.
    """
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    """
    Task:
        Perform dependency checks on the database connectivity and the cached database schema state to verify if the service is ready to handle agent workflows.

    Input_Params:
        None

    Output_Params:
        ReadyResponse:
            Pydantic model summarizing readiness of backend systems.

    Returns:
        ReadyResponse:
            Readiness check status with status, database, and schema_cached indicators.
    """
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
