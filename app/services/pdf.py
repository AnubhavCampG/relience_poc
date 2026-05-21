"""PDF text extraction service (uses app.utils.pdf_extractor)."""

import re
import uuid
from pathlib import Path
from typing import Any

from app.config import get_settings

from app.utils.pdf_extractor import batch_extract_pdfs, extract_text_from_pdf


def get_uploads_dir() -> Path:
    settings = get_settings()
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    path = settings.project_root / settings.uploads_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(filename: str, content: bytes) -> Path:
    uploads = get_uploads_dir()
    safe_name = re.sub(r"[^\w.\-]", "_", Path(filename).name)
    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"
    dest = uploads / f"{uuid.uuid4().hex}_{safe_name}"
    dest.write_bytes(content)
    return dest


def resolve_pdf_path(path_str: str) -> Path:
    """Resolve a PDF path relative to project root or uploads dir."""
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
    """Try to find a .pdf path in the user message."""
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
