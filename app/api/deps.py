"""FastAPI dependencies and session store."""

import uuid
from typing import Any

from app.agent.graph import get_agent_graph, run_agent_turn

# In-memory session store for POC
_sessions: dict[str, list[dict[str, Any]]] = {}


def get_or_create_session(session_id: str | None) -> str:
    """
    Task:
        Check if a session ID exists, returning it on success or creating a fresh UUID session ID otherwise.

    Input_Params:
        session_id (str | None):
            Optional identifier for the session.
            Example: "session-12345"

    Output_Params:
        str:
            The confirmed or newly instantiated session ID.

    Returns:
        str:
            Resolved session ID.
    """
    if session_id and session_id in _sessions:
        return session_id
    new_id = session_id or str(uuid.uuid4())
    _sessions.setdefault(new_id, [])
    return new_id


def get_session_messages(session_id: str) -> list:
    """
    Task:
        Retrieve the list of historical chat messages stored for a specific session ID.

    Input_Params:
        session_id (str):
            The target session key.
            Example: "session-12345"

    Output_Params:
        list:
            List of message dictionaries (with 'role' and 'content' fields).

    Returns:
        list:
            List containing chat history.
    """
    return _sessions.get(session_id, [])


def append_session_message(session_id: str, role: str, content: str) -> None:
    """
    Task:
        Add a new chat message to the in-memory log history of a specific session.

    Input_Params:
        session_id (str):
            The target session key.
            Example: "session-12345"
        role (str):
            The sender of the message (e.g. "user", "assistant").
            Example: "user"
        content (str):
            The body content of the message.
            Example: "Hello AI!"

    Output_Params:
        None

    Returns:
        None
    """
    _sessions.setdefault(session_id, []).append({"role": role, "content": content})


def get_graph():
    """
    Task:
        FastAPI dependency provider that retrieves the compiled agent StateGraph.

    Input_Params:
        None

    Output_Params:
        CompiledStateGraph:
            The compiled StateGraph.

    Returns:
        CompiledStateGraph:
            Compiled agent graph.
    """
    return get_agent_graph()
