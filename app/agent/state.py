"""LangGraph agent state definition."""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    messages: Annotated[list, add_messages]
    user_query: str
    intent: str
    generated_sql: str
    sql_result: dict[str, Any]
    validation_error: str
    retry_count: int
    final_answer: str
    quote_payload: dict[str, Any]
    quote_result: dict[str, Any]
    schema_fragment: str
    pdf_path: str
    use_ocr: bool
    pdf_result: dict[str, Any]
