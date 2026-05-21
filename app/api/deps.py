"""FastAPI dependencies and session store."""

import uuid
from typing import Any

from app.agent.graph import get_agent_graph, run_agent_turn

# In-memory session store for POC
_sessions: dict[str, list[dict[str, Any]]] = {}


def get_or_create_session(session_id: str | None) -> str:
    if session_id and session_id in _sessions:
        return session_id
    new_id = session_id or str(uuid.uuid4())
    _sessions.setdefault(new_id, [])
    return new_id


def get_session_messages(session_id: str) -> list:
    return _sessions.get(session_id, [])


def append_session_message(session_id: str, role: str, content: str) -> None:
    _sessions.setdefault(session_id, []).append({"role": role, "content": content})


def get_graph():
    return get_agent_graph()
