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
    """
    Task:
        Accept a PDF upload directly, extract the textual data (using OCR if requested), optionally invoke the LLM summarizing engine, and return the metadata and contents.

    Input_Params:
        file (UploadFile):
            The uploaded PDF document.
        use_ocr (bool):
            Whether to use OCR for PDF extraction.
            Example: False
        summarize (bool):
            Indicates whether to generate an LLM summary of the text.
            Example: True
        message (str):
            The instruction prompt directed to the LLM summarizing engine.
            Example: "Summarize this PDF document."

    Output_Params:
        PdfExtractResponse:
            A Pydantic model summarizing the text extraction success, path, char counts, text preview, and LLM summary.

    Returns:
        PdfExtractResponse:
            Detailed PDF extraction payload.

    Raises:
        HTTPException:
            Raised if an invalid file type is uploaded, an empty file is processed, or the extraction/summary encounters an exception.
    """
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
    """
    Task:
        Accept a local system file path pointing to a PDF, extract textual data from it, optionally summarize it using LLM services, and return the details.

    Input_Params:
        pdf_path (str):
            The local absolute or relative system path to the PDF file.
            Example: "uploads/invoice.pdf"
        use_ocr (bool):
            Whether to run OCR processing.
            Example: False
        summarize (bool):
            Whether to trigger an LLM summary.
            Example: True
        message (str):
            The prompt template directed to the LLM.
            Example: "Summarize this PDF document."

    Output_Params:
        PdfExtractResponse:
            Detailed success indicator, text content, character length, and LLM summary.

    Returns:
        PdfExtractResponse:
            The structured extraction response.

    Raises:
        HTTPException:
            Raised with 404 status code if the target PDF file is not found, or 500 status code for internal exceptions.
    """
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
    """
    Task:
        Upload a PDF file and route it directly through the multi-agent LangGraph execution graph for comprehensive routing, parsing, validation, or responding.

    Input_Params:
        file (UploadFile):
            The uploaded PDF document.
        message (str):
            The agent prompt directed to the LangGraph execution turn.
            Example: "Extract and summarize the text from this PDF."
        use_ocr (bool):
            Whether OCR is enabled for the agent's internal tool nodes.
            Example: False
        session_id (str | None):
            Optional session key to track dialogue.
            Example: "session-12345"

    Output_Params:
        PdfExtractResponse:
            A detailed response model containing extracted text and final agent answer.

    Returns:
        PdfExtractResponse:
            The compiled PDF extract response from the agent.

    Raises:
        HTTPException:
            Raised if the file type is invalid or if the agent graph execution fails.
    """
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
    """
    Task:
        Scan an entire local system directory for PDF files, extract text from each discovered file in batch, save results to an output directory if supplied, and return aggregate metrics.

    Input_Params:
        request (PdfBatchRequest):
            Pydantic model containing the source directory, OCR flag, and optional output directory destination.
            Example: PdfBatchRequest(directory="uploads/")

    Output_Params:
        PdfBatchResponse:
            Summary response outlining directory paths, processed count, and detailed success mapping.

    Returns:
        PdfBatchResponse:
            The batch process execution metrics.

    Raises:
        HTTPException:
            Raised with status 404 if the directory is missing, or status 500 if internal processing fails.
    """
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
