"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, health, pdf, quotes
from app.db.engine import check_db_connection
from app.schema.introspect import get_schema_fragment

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Task:
        Manage FastAPI application lifespan events, primarily pre-warming the database schema cache if the database connection is active.

    Input_Params:
        app (FastAPI):
            The target FastAPI application instance.

    Output_Params:
        None

    Returns:
        None
    """
    # Warm schema cache on startup if DB is available
    if check_db_connection():
        try:
            get_schema_fragment(force_refresh=True)
        except Exception:
            pass
    yield


app = FastAPI(
    title="Reliance AI Copilot",
    description="LangGraph-powered text-to-SQL copilot with PostgreSQL",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router, prefix="/api/v1")
app.include_router(quotes.router, prefix="/api/v1")
app.include_router(pdf.router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Task:
        Catch and format all unhandled system exceptions globally, returning a uniform 500 JSON response.

    Input_Params:
        request (Request):
            The incoming HTTP Request instance that triggered the error.
        exc (Exception):
            The caught unhandled Exception.
            Example: ConnectionError("DB is down")

    Output_Params:
        JSONResponse:
            FastAPI JSONResponse containing error details and standard error code.

    Returns:
        JSONResponse:
            Formatted exception payload.
    """
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "error_code": "internal_error"},
    )
