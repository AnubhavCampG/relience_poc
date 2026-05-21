from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    pdf_path: str | None = Field(
        default=None,
        description="Path to a PDF under uploads/ or project root",
    )
    use_ocr: bool = False


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sql_used: str | None = None
    rows_preview: list[dict[str, Any]] | None = None
    intent: str | None = None
    pdf_preview: str | None = None
    pdf_file: str | None = None


class PdfExtractResponse(BaseModel):
    success: bool
    file: str
    char_count: int
    truncated: bool
    use_ocr: bool
    text: str | None = None
    summary: str | None = None
    error: str | None = None


class PdfBatchRequest(BaseModel):
    directory: str = Field(..., description="Directory path containing PDF files")
    use_ocr: bool = False
    output_directory: str | None = None


class PdfBatchResponse(BaseModel):
    directory: str
    file_count: int
    results: dict[str, Any]


class QuoteItem(BaseModel):
    product_id: str
    quantity: float
    price: float


class QuoteRequest(BaseModel):
    customer_no: str = Field(..., min_length=1)
    items: list[QuoteItem] = Field(..., min_length=1)


class QuoteResponse(BaseModel):
    success: bool
    file_created: str | None = None
    message: str | None = None
    quote: dict[str, Any] | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    database: bool
    schema_cached: bool
