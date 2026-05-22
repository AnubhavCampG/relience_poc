"""Azure OpenAI LLM service."""

import json
import re
from functools import lru_cache
from typing import Any

from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import get_settings
from app.prompts.templates import build_system_prompt


@lru_cache
def get_chat_model() -> AzureChatOpenAI:
    """
    Task:
        Initialize and cache the AzureChatOpenAI client utilizing settings from configuration.

    Input_Params:
        None

    Output_Params:
        AzureChatOpenAI:
            Cached AzureChatOpenAI instance.

    Returns:
        AzureChatOpenAI:
            The configured chat model.
    """
    settings = get_settings()
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.openai_api_version,
        azure_deployment=settings.deployment_name,
        temperature=0,
    )


def invoke_text(system: str, user: str) -> str:
    """
    Task:
        Submit system and user prompts to the Azure OpenAI chat model and return the textual response content.

    Input_Params:
        system (str):
            The system context or behavioral guidelines instruction.
            Example: "You are a helpful assistant."
        user (str):
            The user prompt or query details.
            Example: "Hello AI!"

    Output_Params:
        str:
            The raw text content returned by the Azure OpenAI chat completion.

    Returns:
        str:
            Response content.
    """
    model = get_chat_model()
    response = model.invoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )
    return response.content or ""


def extract_sql_from_response(text: str) -> str | None:
    """
    Task:
        Extract and clean a raw SQL query string from an LLM response, parsing markdown code blocks if present.

    Input_Params:
        text (str):
            The raw chat response string containing SQL (often enclosed in markdown fences).
            Example: "```sql SELECT * FROM accounts; ```"

    Output_Params:
        str | None:
            Extracted, stripped, and cleaned SQL string, or None if no SQL pattern matches.

    Returns:
        str | None:
            Extracted SQL query or None.
    """
    text = text.strip()
    fence_match = re.search(r"```(?:sql)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()

    # If response looks like SQL
    upper = text.upper()
    if upper.startswith("SELECT") or upper.startswith("WITH"):
        return text.strip().rstrip(";")

    return None


def classify_intent(user_query: str, has_pdf_path: bool = False) -> str:
    """
    Task:
        Classify a natural language user query intent into one of the known categories: 'pdf', 'quote', or 'query'.

    Input_Params:
        user_query (str):
            The input textual message from the user.
            Example: "Create a sales quote for customer 123"
        has_pdf_path (bool):
            Flag indicating whether a PDF path was explicitly provided.
            Example: False

    Output_Params:
        str:
            Categorized intent string ('pdf', 'quote', or 'query').

    Returns:
        str:
            Classified intent label.
    """
    lower = user_query.lower()
    if has_pdf_path:
        return "pdf"
    pdf_keywords = (
        "extract text from pdf",
        "extract pdf",
        "read pdf",
        "parse pdf",
        "ocr pdf",
        "scanned pdf",
        "pdf document",
        "from the pdf",
        "from this pdf",
        "uploaded pdf",
    )
    if any(kw in lower for kw in pdf_keywords) or ".pdf" in lower:
        return "pdf"
    quote_keywords = ("quote", "sales quote", "create a quote", "draft quote", "generate quote")
    if any(kw in lower for kw in quote_keywords):
        return "quote"
    return "query"


def summarize_pdf_text(user_query: str, extracted_text: str) -> str:
    """
    Task:
        Generate a summary or answer user questions based on the provided PDF text using the Azure OpenAI LLM.

    Input_Params:
        user_query (str):
            The user's direct request or query.
            Example: "Summarize this PDF"
        extracted_text (str):
            Extracted text content from the PDF document.
            Example: "Reliance Q3 report..."

    Output_Params:
        str:
            The generated summary response text.

    Returns:
        str:
            Answer or summary response text.
    """
    settings = get_settings()
    max_chars = settings.pdf_max_chars_in_response
    text_for_prompt = extracted_text
    if len(text_for_prompt) > max_chars:
        text_for_prompt = text_for_prompt[:max_chars] + "\n[Text truncated for summarization]"

    system = (
        "You are a document assistant for Reliance. Summarize or answer questions "
        "based only on the extracted PDF text provided."
    )
    user = f"""User request: {user_query}

Extracted PDF text:
{text_for_prompt}

Provide a clear, helpful response. If summarizing, use bullet points for key findings."""
    return invoke_text(system, user)


def generate_sql(user_query: str, schema_fragment: str) -> str:
    """
    Task:
        Generate a database-compliant SQL query based on a user's natural language question and database schema fragment.

    Input_Params:
        user_query (str):
            The user prompt or query.
            Example: "Find total sales in 2025"
        schema_fragment (str):
            The structural database DDL or catalog fragment context.
            Example: "CREATE TABLE sales (...)"

    Output_Params:
        str:
            The generated and extracted SQL query string.

    Returns:
        str:
            Valid SQL query string.

    Raises:
        ValueError:
            Raised if SQL extraction fails or LLM output doesn't contain a valid SQL structure.
    """
    from app.prompts.templates import build_sql_writer_prompt

    system = build_system_prompt(schema_fragment)
    user = build_sql_writer_prompt(user_query, schema_fragment)
    response = invoke_text(system, user)
    sql = extract_sql_from_response(response)
    if not sql:
        raise ValueError(f"Could not extract SQL from model response: {response[:200]}")
    return sql


def repair_sql(
    user_query: str,
    failed_sql: str,
    error: str,
    schema_fragment: str,
) -> str:
    """
    Task:
        Synthesize a repaired SQL query based on a failed query attempt, database schema context, and the engine-specific error message.

    Input_Params:
        user_query (str):
            The original natural language question from the user.
            Example: "Show all products"
        failed_sql (str):
            The incorrect SQL query that failed execution.
            Example: "SELECT name FROM products"
        error (str):
            The database engine error message returned during execution.
            Example: "column 'name' does not exist"
        schema_fragment (str):
            The DDL structural database details.
            Example: "CREATE TABLE products (product_id VARCHAR, description VARCHAR)"

    Output_Params:
        str:
            The newly corrected and repaired SQL query string.

    Returns:
        str:
            Corrected SQL query.

    Raises:
        ValueError:
            Raised if the repaired SQL cannot be extracted from the LLM response.
    """
    from app.prompts.templates import build_repair_prompt

    system = build_system_prompt(schema_fragment)
    user = build_repair_prompt(user_query, failed_sql, error, schema_fragment)
    response = invoke_text(system, user)
    sql = extract_sql_from_response(response)
    if not sql:
        raise ValueError(f"Could not extract repaired SQL: {response[:200]}")
    return sql


def generate_answer(user_query: str, context: str) -> str:
    """
    Task:
        Synthesize a final reader-friendly natural language response summarizing database or tool output context for the user query.

    Input_Params:
        user_query (str):
            The user prompt or query.
            Example: "What was the total amount?"
        context (str):
            Database result rows, status, or raw details represented as context text.
            Example: "[{'sum': 10500}]"

    Output_Params:
        str:
            The detailed natural language summary or answer.

    Returns:
        str:
            Synthesized answer.
    """
    from app.prompts.templates import build_respond_prompt

    system = "You are a helpful data assistant for Reliance. Summarize results clearly."
    user = build_respond_prompt(user_query, context)
    return invoke_text(system, user)


def parse_quote_from_query(user_query: str) -> dict[str, Any] | None:
    """
    Task:
        Parse sales quote details (customer_no, items, product_id, quantity, price) from natural language instructions.

    Input_Params:
        user_query (str):
            The raw text request to draft a sales quote.
            Example: "Quote customer C1 with product P1 qty 10 price 5"

    Output_Params:
        dict[str, Any] | None:
            Parsed JSON dict representation containing customer info and product quote items, or None if parsing fails.

    Returns:
        dict[str, Any] | None:
            Extracted JSON dictionary or None.
    """
    system = """Extract sales quote parameters from the user message.
Return JSON only: {"customer_no": "...", "items": [{"product_id": "...", "quantity": N, "price": N}]}
If not a quote request, return {"error": "not a quote"}"""
    response = invoke_text(system, user_query)
    try:
        match = re.search(r"\{[\s\S]*\}", response)
        if match:
            return json.loads(match.group(0))
    except json.JSONDecodeError:
        pass
    return None
