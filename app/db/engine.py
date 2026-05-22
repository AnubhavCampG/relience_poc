from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine() -> Engine:
    """
    Task:
        Initialize and return a SQLAlchemy connection Engine configured for the database.
        Maintains a singleton engine instance to manage connection pools.

    Input_Params:
        None

    Output_Params:
        Engine:
            SQLAlchemy Database connection Engine singleton.

    Returns:
        Engine:
            SQLAlchemy Engine.
    """
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
        )
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


def get_session_factory() -> sessionmaker:
    """
    Task:
        Return the SQLAlchemy thread-local Session Local factory class.

    Input_Params:
        None

    Output_Params:
        sessionmaker:
            Configured session factory.

    Returns:
        sessionmaker:
            SQLAlchemy session maker instance.
    """
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Task:
        Provide a transactional scope for database sessions as a context manager,
        guaranteeing transaction commits on success and automatic rollbacks on exception.

    Input_Params:
        None

    Output_Params:
        Generator[Session, None, None]:
            A yield generator for active SQLAlchemy database Session objects.

    Returns:
        Generator[Session, None, None]:
            Database session generator.

    Raises:
        Exception:
            If rollback or session close operation encounters structural database errors.
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connection() -> bool:
    """
    Task:
        Test and verify whether the database connection is active and responsive.

    Input_Params:
        None

    Output_Params:
        bool:
            True if connection test passes, False otherwise.

    Returns:
        bool:
            Connection responsiveness check outcome.
    """
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
