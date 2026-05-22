"""LangGraph agent state definition."""

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    """
    Task:
        Define the state payload schemas managed and updated across all nodes
        in the LangGraph text-to-SQL copilot workflow.

    Input_Params:
        messages (Annotated[list, add_messages]):
            Chat message list with appending logic.
        user_query (str):
            The original natural language question from the user.
        intent (str):
            The parsed intent of the user (e.g., "query", "quote", "pdf").
        generated_sql (str):
            The PostgreSQL query drafted by the LLM agent.
        sql_result (dict[str, Any]):
            Results of executing the SQL query on the database.
        validation_error (str):
            Error details from validating the SQL.
        retry_count (int):
            Current number of query repair retries.
        final_answer (str):
            The final formatted conversational answer to show the user.
        quote_payload (dict[str, Any]):
            Parameters extracted to build a sales quote.
        quote_result (dict[str, Any]):
            The generated quote metadata output.
        schema_fragment (str):
            Relevant cached database schema text.
        pdf_path (str):
            Location to any PDF file referenced.
        use_ocr (bool):
            Whether to use system OCR for PDF extraction.
        pdf_result (dict[str, Any]):
            Results of extracting or summarizing the PDF.
    """
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
