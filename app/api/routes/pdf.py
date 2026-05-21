from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.agent.graph import run_agent_turn
from app.api.schemas import PdfBatchRequest, PdfBatchResponse, PdfExtractResponse
from app.services import llm, pdf as pdf_service

router = APIRouter(prefix="/pdf", tags=["pdf"])


@router.post("/extract", response_model=PdfExtractResponse)
async def extract_pdf_upload(
    file: UploadFile = File(...),
    use_ocr: bool = Form(False),
    summarize: bool = Form(True),
    message: str = Form("Summarize this PDF document."),
) -> PdfExtractResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    try:
        saved = pdf_service.save_upload(file.filename, content)
        result = pdf_service.extract_pdf(saved, use_ocr=use_ocr)
        summary = None
        if summarize and result.get("text"):
            summary = llm.summarize_pdf_text(message, result["text"])

        return PdfExtractResponse(
            success=True,
            file=result["file"],
            char_count=result["char_count"],
            truncated=result.get("truncated", False),
            use_ocr=use_ocr,
            text=result.get("text"),
            summary=summary,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/extract/path", response_model=PdfExtractResponse)
def extract_pdf_by_path(
    pdf_path: str = Form(...),
    use_ocr: bool = Form(False),
    summarize: bool = Form(True),
    message: str = Form("Summarize this PDF document."),
) -> PdfExtractResponse:
    try:
        result = pdf_service.extract_pdf(pdf_path, use_ocr=use_ocr)
        summary = None
        if summarize and result.get("text"):
            summary = llm.summarize_pdf_text(message, result["text"])
        return PdfExtractResponse(
            success=True,
            file=result["file"],
            char_count=result["char_count"],
            truncated=result.get("truncated", False),
            use_ocr=use_ocr,
            text=result.get("text"),
            summary=summary,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/extract/agent", response_model=PdfExtractResponse)
async def extract_pdf_via_agent(
    file: UploadFile = File(...),
    message: str = Form("Extract and summarize the text from this PDF."),
    use_ocr: bool = Form(False),
    session_id: str | None = Form(None),
) -> PdfExtractResponse:
    """Extract PDF through the LangGraph agent (same path as /chat with upload)."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    content = await file.read()
    saved = pdf_service.save_upload(file.filename, content)

    try:
        result = run_agent_turn(
            message,
            pdf_path=str(saved),
            use_ocr=use_ocr,
        )
        pdf_result = result.get("pdf_result", {})
        if pdf_result.get("error"):
            return PdfExtractResponse(
                success=False,
                file=str(saved),
                char_count=0,
                truncated=False,
                use_ocr=use_ocr,
                error=pdf_result["error"],
                summary=result.get("final_answer"),
            )
        text = pdf_result.get("text", "")
        return PdfExtractResponse(
            success=True,
            file=pdf_result.get("file", str(saved)),
            char_count=pdf_result.get("char_count", len(text)),
            truncated=pdf_result.get("truncated", False),
            use_ocr=use_ocr,
            text=text,
            summary=result.get("final_answer"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/batch", response_model=PdfBatchResponse)
def batch_extract(request: PdfBatchRequest) -> PdfBatchResponse:
    directory = Path(request.directory)
    if not directory.is_dir():
        raise HTTPException(status_code=404, detail=f"Directory not found: {request.directory}")
    try:
        result = pdf_service.batch_extract(
            str(directory),
            use_ocr=request.use_ocr,
            output_directory=request.output_directory,
        )
        return PdfBatchResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
