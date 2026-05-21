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
    """Chat with an uploaded PDF — routes through LangGraph pdf_extractor node."""
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
