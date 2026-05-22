"""LangGraph agent nodes."""

import json
from typing import Any

from app.config import get_settings
from app.schema.introspect import get_schema_fragment
from app.services import llm, pdf as pdf_service, quotes
from app.sql.executor import execute_query
from app.sql.validator import SQLValidationError, validate_sql


def route_intent(state: dict) -> dict:
    """
    Task:
        Analyze the incoming user request and determine the user's operational intent
        (either PDF extraction, sales quote creation, or raw SQL query search).

    Input_Params:
        state (dict):
            Current Graph AgentState dictionary.

    Output_Params:
        dict:
            Updated state dict containing parsed intent, loaded database schema, and retry count.

    Returns:
        dict:
            Substate update.
    """
    user_query = state.get("user_query", "")
    has_pdf = bool(state.get("pdf_path"))
    intent = llm.classify_intent(user_query, has_pdf_path=has_pdf)
    return {
        "intent": intent,
        "schema_fragment": get_schema_fragment(),
        "retry_count": state.get("retry_count", 0),
    }


def sql_writer(state: dict) -> dict:
    """
    Task:
        Draft a PostgreSQL query using the LLM agent based on the user's natural language request.

    Input_Params:
        state (dict):
            Current Graph AgentState dictionary.

    Output_Params:
        dict:
            Substate update containing the drafted 'generated_sql' and any compilation 'validation_error'.

    Returns:
        dict:
            Substate update.
    """
    user_query = state["user_query"]
    schema = state.get("schema_fragment") or get_schema_fragment()
    try:
        sql = llm.generate_sql(user_query, schema)
        return {"generated_sql": sql, "validation_error": ""}
    except Exception as e:
        return {"validation_error": str(e), "generated_sql": ""}


def validate_sql_node(state: dict) -> dict:
    """
    Task:
        Validate the generated SQL statement for syntax errors, safety restrictions, and access constraints.

    Input_Params:
        state (dict):
            Current Graph AgentState dictionary.

    Output_Params:
        dict:
            Substate update containing verified SQL or appropriate validation error.

    Returns:
        dict:
            Substate update.
    """
    sql = state.get("generated_sql", "")
    if not sql:
        return {"validation_error": state.get("validation_error", "No SQL generated")}
    try:
        validated = validate_sql(sql)
        return {"generated_sql": validated, "validation_error": ""}
    except SQLValidationError as e:
        return {"validation_error": str(e)}


def repair_sql_node(state: dict) -> dict:
    """
    Task:
        Attempt to automatically fix a failed SQL statement by sending it back to the LLM
        with error feedback.

    Input_Params:
        state (dict):
            Current Graph AgentState dictionary.

    Output_Params:
        dict:
            Substate update containing the corrected SQL statement, cleared validation error, and incremented retry count.

    Returns:
        dict:
            Substate update.
    """
    user_query = state["user_query"]
    failed_sql = state.get("generated_sql", "")
    error = state.get("validation_error", "Unknown error")
    schema = state.get("schema_fragment") or get_schema_fragment()
    retry_count = state.get("retry_count", 0) + 1

    try:
        sql = llm.repair_sql(user_query, failed_sql, error, schema)
        return {
            "generated_sql": sql,
            "validation_error": "",
            "retry_count": retry_count,
        }
    except Exception as e:
        return {
            "validation_error": str(e),
            "retry_count": retry_count,
        }


def execute_sql_node(state: dict) -> dict:
    """
    Task:
        Execute the fully validated PostgreSQL query against the target relational database.

    Input_Params:
        state (dict):
            Current Graph AgentState dictionary.

    Output_Params:
        dict:
            Substate update containing execution results under 'sql_result' or execution error in 'validation_error'.

    Returns:
        dict:
            Substate update.
    """
    sql = state.get("generated_sql", "")
    try:
        result = execute_query(sql)
        return {"sql_result": result, "validation_error": ""}
    except SQLValidationError as e:
        return {"validation_error": str(e), "sql_result": {}}
    except Exception as e:
        return {"validation_error": str(e), "sql_result": {"error": str(e)}}


def pdf_extractor(state: dict) -> dict:
    """
    Task:
        Extract and parse text content from a specified local PDF file.

    Input_Params:
        state (dict):
            Current Graph AgentState dictionary.

    Output_Params:
        dict:
            Substate update containing extracted text or errors in 'pdf_result' and resolved file path in 'pdf_path'.

    Returns:
        dict:
            Substate update.
    """
    user_query = state["user_query"]
    pdf_path = state.get("pdf_path") or pdf_service.extract_path_from_query(user_query)
    use_ocr = state.get("use_ocr", False)

    if not pdf_path:
        return {
            "pdf_result": {
                "error": "No PDF file provided. Upload a PDF or include a .pdf path in your message."
            },
            "validation_error": "Missing PDF path",
        }

    try:
        settings = get_settings()
        result = pdf_service.extract_pdf(
            pdf_path,
            use_ocr=use_ocr,
            max_chars=settings.pdf_max_chars_in_response,
        )
        return {"pdf_result": result, "pdf_path": result.get("file", pdf_path)}
    except Exception as e:
        return {"pdf_result": {"error": str(e), "file": pdf_path}}


def quote_builder(state: dict) -> dict:
    """
    Task:
        Parse, validate, and construct a new dynamic sales quote based on items
        and customer details parsed from user queries.

    Input_Params:
        state (dict):
            Current Graph AgentState dictionary.

    Output_Params:
        dict:
            Substate update containing quote output under 'quote_result' and original parameters under 'quote_payload'.

    Returns:
        dict:
            Substate update.
    """
    user_query = state["user_query"]
    payload = llm.parse_quote_from_query(user_query)

    if not payload or payload.get("error"):
        return {
            "quote_result": {"error": "Could not parse quote parameters from request"},
            "validation_error": "Quote parsing failed",
        }

    customer_no = str(payload.get("customer_no", ""))
    items = payload.get("items", [])

    if not customer_no or not items:
        return {
            "quote_result": {"error": "customer_no and items are required"},
            "validation_error": "Missing quote fields",
        }

    try:
        result = quotes.create_quote(customer_no, items)
        return {"quote_result": result, "quote_payload": payload}
    except Exception as e:
        return {"quote_result": {"error": str(e)}}


def respond(state: dict) -> dict:
    """
    Task:
        Synthesize the collected execution results (SQL results, PDF texts, or Quote logs)
        and draft a readable, descriptive conversational reply for the user.

    Input_Params:
        state (dict):
            Current Graph AgentState dictionary.

    Output_Params:
        dict:
            Substate update containing the conversational answer under 'final_answer'.

    Returns:
        dict:
            Substate update.
    """
    user_query = state["user_query"]
    intent = state.get("intent", "query")

    if intent == "pdf":
        pdf_result = state.get("pdf_result", {})
        if pdf_result.get("error"):
            answer = f"I could not extract text from the PDF: {pdf_result['error']}"
        else:
            text = pdf_result.get("text", "")
            answer = llm.summarize_pdf_text(user_query, text)
    elif intent == "quote":
        quote_result = state.get("quote_result", {})
        if quote_result.get("error"):
            answer = f"I could not create the quote: {quote_result['error']}"
        else:
            answer = quote_result.get("message", "Quote created successfully.")
    else:
        sql_result = state.get("sql_result", {})
        if state.get("validation_error") and not sql_result.get("rows"):
            answer = (
                f"I was unable to complete your query. Error: {state['validation_error']}"
            )
        else:
            context = json.dumps(sql_result, indent=2, default=str)
            if sql_result.get("sql_executed"):
                context = (
                    f"SQL executed: {sql_result['sql_executed']}\n\nResults:\n{context}"
                )
            answer = llm.generate_answer(user_query, context)

    return {"final_answer": answer}


def should_repair(state: dict) -> str:
    """
    Task:
        Conditional router node that determines whether a failed SQL statement
        should be sent to the auto-repair loop or aborted immediately based on retry limits.

    Input_Params:
        state (dict):
            Current Graph AgentState dictionary.

    Output_Params:
        str:
            The name of the next node to transition to ("repair", "execute", or "respond").

    Returns:
        str:
            Transition route name.
    """
    if state.get("validation_error"):
        if state.get("retry_count", 0) < 2:
            return "repair"
        return "respond"
    return "execute"


def route_by_intent(state: dict) -> str:
    """
    Task:
        Conditional router node that maps the parsed intent of the user
        to the appropriate starting action node.

    Input_Params:
        state (dict):
            Current Graph AgentState dictionary.

    Output_Params:
        str:
            The name of the starting action node to transition to ("pdf", "quote", or "sql_writer").

    Returns:
        str:
            Transition node name.
    """
    intent = state.get("intent", "query")
    if intent == "pdf":
        return "pdf"
    if intent == "quote":
        return "quote"
    return "sql_writer"
