"""LangGraph agent graph compilation."""

from functools import lru_cache

from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    execute_sql_node,
    pdf_extractor,
    quote_builder,
    repair_sql_node,
    respond,
    route_by_intent,
    route_intent,
    should_repair,
    sql_writer,
    validate_sql_node,
)
from app.agent.state import AgentState


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("route_intent", route_intent)
    graph.add_node("sql_writer", sql_writer)
    graph.add_node("validate_sql", validate_sql_node)
    graph.add_node("repair_sql", repair_sql_node)
    graph.add_node("execute_sql", execute_sql_node)
    graph.add_node("quote_builder", quote_builder)
    graph.add_node("pdf_extractor", pdf_extractor)
    graph.add_node("respond", respond)

    graph.set_entry_point("route_intent")

    graph.add_conditional_edges(
        "route_intent",
        route_by_intent,
        {
            "sql_writer": "sql_writer",
            "quote": "quote_builder",
            "pdf": "pdf_extractor",
        },
    )

    graph.add_edge("sql_writer", "validate_sql")

    graph.add_conditional_edges(
        "validate_sql",
        should_repair,
        {"repair": "repair_sql", "execute": "execute_sql", "respond": "respond"},
    )

    graph.add_edge("repair_sql", "validate_sql")
    graph.add_edge("execute_sql", "respond")
    graph.add_edge("quote_builder", "respond")
    graph.add_edge("pdf_extractor", "respond")
    graph.add_edge("respond", END)

    return graph.compile()


@lru_cache
def get_agent_graph():
    return build_graph()


def run_agent_turn(
    user_query: str,
    session_messages: list | None = None,
    pdf_path: str | None = None,
    use_ocr: bool = False,
) -> dict:
    """Run one agent turn and return final state."""
    graph = get_agent_graph()
    initial_state: dict = {
        "user_query": user_query,
        "retry_count": 0,
        "use_ocr": use_ocr,
    }
    if pdf_path:
        initial_state["pdf_path"] = pdf_path
    if session_messages:
        initial_state["messages"] = session_messages

    result = graph.invoke(initial_state)
    return result
