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
    settings = get_settings()
    return AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.openai_api_version,
        azure_deployment=settings.deployment_name,
        temperature=0,
    )


def invoke_text(system: str, user: str) -> str:
    model = get_chat_model()
    response = model.invoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )
    return response.content or ""


def extract_sql_from_response(text: str) -> str | None:
    """Extract SQL from LLM response, handling markdown fences."""
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
    """Return 'pdf', 'quote', or 'query'."""
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
    """Summarize or answer questions about extracted PDF text."""
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
    from app.prompts.templates import build_repair_prompt

    system = build_system_prompt(schema_fragment)
    user = build_repair_prompt(user_query, failed_sql, error, schema_fragment)
    response = invoke_text(system, user)
    sql = extract_sql_from_response(response)
    if not sql:
        raise ValueError(f"Could not extract repaired SQL: {response[:200]}")
    return sql


def generate_answer(user_query: str, context: str) -> str:
    from app.prompts.templates import build_respond_prompt

    system = "You are a helpful data assistant for Reliance. Summarize results clearly."
    user = build_respond_prompt(user_query, context)
    return invoke_text(system, user)


def parse_quote_from_query(user_query: str) -> dict[str, Any] | None:
    """Use LLM to extract quote parameters from natural language."""
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
