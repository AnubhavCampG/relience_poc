"""PDF text extraction service (uses app.utils.pdf_extractor)."""

import re
import uuid
from pathlib import Path
from typing import Any

from app.config import get_settings

from app.utils.pdf_extractor import batch_extract_pdfs, extract_text_from_pdf


def get_uploads_dir() -> Path:
    """
    Task:
        Retrieve the resolved upload directory path configured in system settings, creating required directories on success.

    Input_Params:
        None

    Output_Params:
        Path:
            The upload directory path.

    Returns:
        Path:
            Upload directory path.
    """
    settings = get_settings()
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    path = settings.project_root / settings.uploads_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(filename: str, content: bytes) -> Path:
    """
    Task:
        Save raw uploaded file bytes to the local uploads directory with a safe, unique filename prefixed with a UUID.

    Input_Params:
        filename (str):
            The original name of the uploaded file.
            Example: "invoice.pdf"
        content (bytes):
            The raw binary content of the file.

    Output_Params:
        Path:
            The absolute or relative Path pointing to the written PDF on the system.

    Returns:
        Path:
            Path of the saved file.
    """
    uploads = get_uploads_dir()
    safe_name = re.sub(r"[^\w.\-]", "_", Path(filename).name)
    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"
    dest = uploads / f"{uuid.uuid4().hex}_{safe_name}"
    dest.write_bytes(content)
    return dest


def resolve_pdf_path(path_str: str) -> Path:
    """
    Task:
        Resolve a given PDF path string by checking absolute locations, project root configurations, and uploads directories.

    Input_Params:
        path_str (str):
            The file name or path string of the target PDF.
            Example: "invoice.pdf"

    Output_Params:
        Path:
            The resolved and validated Path instance.

    Returns:
        Path:
            The resolved system path.

    Raises:
        FileNotFoundError:
            Raised if the PDF document cannot be discovered in any of the search directories.
    """
    p = Path(path_str)
    if p.is_absolute() and p.exists():
        return p
    settings = get_settings()
    candidates = [
        settings.project_root / path_str,
        get_uploads_dir() / path_str,
        get_uploads_dir() / Path(path_str).name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"PDF not found: {path_str}")


def extract_pdf(
    pdf_path: str | Path,
    use_ocr: bool = False,
    output_file: str | None = None,
    max_chars: int | None = None,
) -> dict[str, Any]:
    """
    Task:
        Extract and clean textual data from a single PDF document, optionally invoking OCR, and enforcing character length constraints.

    Input_Params:
        pdf_path (str | Path):
            The path or file name targeting the PDF.
            Example: "uploads/invoice.pdf"
        use_ocr (bool):
            Whether to use OCR for parsing.
            Example: False
        output_file (str | None):
            Optional destination path to save extracted raw text.
            Example: "outputs/invoice.txt"
        max_chars (int | None):
            Optional maximum allowed characters in the returned text to avoid token limits.
            Example: 8000

    Output_Params:
        dict[str, Any]:
            Dictionary containing extracted details: file path, text content, char count, truncated flag, and OCR flag.

    Returns:
        dict[str, Any]:
            The extraction result metadata.
    """
    path = resolve_pdf_path(str(pdf_path)) if isinstance(pdf_path, str) else pdf_path
    text = extract_text_from_pdf(str(path), use_ocr=use_ocr, output_file=output_file)
    truncated = False
    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[Truncated — {len(text) - max_chars} more characters]"
        truncated = True
    return {
        "file": str(path),
        "text": text,
        "char_count": len(text),
        "truncated": truncated,
        "use_ocr": use_ocr,
    }


def batch_extract(
    directory: str,
    use_ocr: bool = False,
    output_directory: str | None = None,
) -> dict[str, Any]:
    """
    Task:
        Extract textual data in batch from all PDF documents found in a target directory.

    Input_Params:
        directory (str):
            The target source directory containing PDF documents.
            Example: "uploads/"
        use_ocr (bool):
            Whether to run OCR on the files.
            Example: False
        output_directory (str | None):
            Optional directory destination where extracted text files are saved.
            Example: "outputs/"

    Output_Params:
        dict[str, Any]:
            Dictionary containing directory path, count of processed files, and a dictionary of individual file extraction metadata.

    Returns:
        dict[str, Any]:
            Batch extraction results summary.
    """
    results = batch_extract_pdfs(directory, output_directory=output_directory, use_ocr=use_ocr)
    return {
        "directory": directory,
        "file_count": len(results),
        "results": {
            name: {
                "text": (text[:2000] + "..." if len(text) > 2000 else text),
                "char_count": len(text),
                "error": text.startswith("[Error:"),
            }
            for name, text in results.items()
        },
    }


def extract_path_from_query(user_query: str) -> str | None:
    """
    Task:
        Scan a natural language query for potential PDF filename or path patterns using regular expressions.

    Input_Params:
        user_query (str):
            The natural language prompt from the user.
            Example: "Extract content from invoice.pdf"

    Output_Params:
        str | None:
            Discovered PDF path or name on success, or None if no match is found.

    Returns:
        str | None:
            Extracted file path or None.
    """
    patterns = [
        r'["\']([^"\']+\.pdf)["\']',
        r"(\S+\.pdf)\b",
        r"(?:runtime/)?uploads[/\\](\S+\.pdf)",
    ]
    for pattern in patterns:
        match = re.search(pattern, user_query, re.IGNORECASE)
        if match:
            return match.group(1)
    return None
