from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agent.graph import run_agent_turn
from app.api.deps import (
    append_session_message,
    get_or_create_session,
    get_session_messages,
)
from app.api.schemas import ChatRequest, ChatResponse
from app.services import pdf as pdf_service

router = APIRouter(prefix="/chat", tags=["chat"])


def _build_chat_response(result: dict, session_id: str) -> ChatResponse:
    """
    Task:
        Helper to construct a standard ChatResponse instance from the raw dictionary returned by the agent turn execution.

    Input_Params:
        result (dict):
            The dictionary of state data returned from the agent run turn.
            Example: {"final_answer": "Done", "intent": "sql_query"}
        session_id (str):
            The session identifier associated with the request.
            Example: "session-12345"

    Output_Params:
        ChatResponse:
            Constructed ChatResponse schema containing formatted answers, database rows, SQL details, and PDF previews.

    Returns:
        ChatResponse:
            Formatted chat response object.
    """
    sql_result = result.get("sql_result") or {}
    rows_preview = sql_result.get("rows", [])[:10] if sql_result else None
    pdf_result = result.get("pdf_result") or {}
    pdf_preview = None
    if pdf_result.get("text"):
        text = pdf_result["text"]
        pdf_preview = text[:500] + "..." if len(text) > 500 else text

    return ChatResponse(
        answer=result.get("final_answer", "I could not process your request."),
        session_id=session_id,
        sql_used=sql_result.get("sql_executed") or result.get("generated_sql"),
        rows_preview=rows_preview,
        intent=result.get("intent"),
        pdf_preview=pdf_preview,
        pdf_file=pdf_result.get("file"),
    )


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Task:
        Handle structured POST requests to interact with the LLM/SQL/PDF LangGraph Agent. Manages chat history retrieval, saving user requests, executing the state graph turn, saving response messages, and generating the response payload.

    Input_Params:
        request (ChatRequest):
            ChatRequest containing the message prompt, session_id, and optional PDF path/configurations.
            Example: ChatRequest(message="Retrieve all accounts")

    Output_Params:
        ChatResponse:
            A ChatResponse containing the agent's response details.

    Returns:
        ChatResponse:
            Formatted chat response.

    Raises:
        HTTPException:
            Raised if the LangGraph turn execution encounters an exception.
    """
    session_id = get_or_create_session(request.session_id)
    messages = get_session_messages(session_id)

    append_session_message(session_id, "user", request.message)

    try:
        result = run_agent_turn(
            request.message,
            session_messages=messages,
            pdf_path=request.pdf_path,
            use_ocr=request.use_ocr,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    answer = result.get("final_answer", "I could not process your request.")
    append_session_message(session_id, "assistant", answer)

    return _build_chat_response(result, session_id)


@router.post("/upload", response_model=ChatResponse)
async def chat_with_pdf(
    message: str = Form(...),
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
    use_ocr: bool = Form(False),
) -> ChatResponse:
    """
    Task:
        Receive an uploaded PDF file and a prompt message, save the file to local uploads, and execute a state graph turn with the uploaded PDF as target context.

    Input_Params:
        message (str):
            The user prompt or query.
            Example: "Summarize this invoice"
        file (UploadFile):
            The uploaded PDF document to analyze.
        session_id (str | None):
            Optional session key to track dialogue.
            Example: "session-12345"
        use_ocr (bool):
            Indicates whether OCR parsing is required.
            Example: False

    Output_Params:
        ChatResponse:
            The compiled ChatResponse detailing the agent's analysis of the PDF.

    Returns:
        ChatResponse:
            Chat response representing findings.

    Raises:
        HTTPException:
            Raised if an invalid file type is uploaded, an empty file is processed, or the agent execution fails.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    sid = get_or_create_session(session_id)
    messages = get_session_messages(sid)
    append_session_message(sid, "user", message)

    try:
        saved = pdf_service.save_upload(file.filename, content)
        result = run_agent_turn(
            message,
            session_messages=messages,
            pdf_path=str(saved),
            use_ocr=use_ocr,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    append_session_message(sid, "assistant", result.get("final_answer", ""))
    return _build_chat_response(result, sid)
