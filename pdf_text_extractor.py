"""
PDF Text Extraction Module
This module provides robust PDF text extraction with proper handling of:
- Multi-page PDFs
- Various text encodings
- Complex layouts
- Image-based text (OCR support)
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_text_from_pdf(
    pdf_file_path: str,
    use_ocr: bool = False,
    output_file: Optional[str] = None
) -> str:
    """
    Extract text from a PDF file with proper error handling.
    
    Args:
        pdf_file_path (str): Path to the PDF file
        use_ocr (bool): Whether to use OCR for scanned PDFs (requires pytesseract)
        output_file (str, optional): Path to save extracted text to a file
    
    Returns:
        str: Extracted text from the PDF
    
    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If file is not a valid PDF
        ImportError: If required libraries are not installed
    """
    
    try:
        import PyPDF2
    except ImportError:
        logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
        raise ImportError("PyPDF2 is required. Install with: pip install PyPDF2")
    
    if use_ocr:
        try:
            import pytesseract
            from PIL import Image
            from pdf2image import convert_from_path
        except ImportError:
            logger.error("OCR libraries not installed. Install with: pip install pytesseract pdf2image pillow")
            raise ImportError("Required OCR libraries not installed")
    
    # Validate file path
    pdf_path = Path(pdf_file_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_file_path}")
    
    if not pdf_path.suffix.lower() == '.pdf':
        raise ValueError(f"File is not a PDF: {pdf_file_path}")
    
    extracted_text = ""
    
    try:
        logger.info(f"Processing PDF: {pdf_file_path}")
        
        # Try standard text extraction first
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            logger.info(f"Total pages in PDF: {num_pages}")
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text:
                        extracted_text += f"\n--- Page {page_num} ---\n{text}\n"
                        logger.debug(f"Extracted text from page {page_num}")
                    else:
                        logger.warning(f"Page {page_num} appears to be empty or scanned image")
                except Exception as e:
                    logger.error(f"Error extracting text from page {page_num}: {str(e)}")
                    extracted_text += f"\n--- Page {page_num} ---\n[Error extracting text]\n"
        
        # If OCR is enabled and text extraction yielded minimal results, use OCR
        if use_ocr and len(extracted_text.strip()) < 50:
            logger.info("Text extraction returned minimal results. Attempting OCR...")
            extracted_text = _extract_text_with_ocr(pdf_path)
        
        if not extracted_text.strip():
            logger.warning("No text could be extracted from the PDF")
            extracted_text = "[No extractable text found in PDF]"
        
        # Save to file if output_file is specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            logger.info(f"Extracted text saved to: {output_file}")
        
        logger.info("PDF text extraction completed successfully")
        return extracted_text
    
    except Exception as e:
        logger.error(f"Unexpected error during PDF processing: {str(e)}")
        raise


def _extract_text_with_ocr(pdf_path: Path) -> str:
    """
    Extract text from PDF using OCR (Tesseract).
    
    Args:
        pdf_path (Path): Path to the PDF file
    
    Returns:
        str: Extracted text using OCR
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
    except ImportError:
        raise ImportError("OCR requires: pip install pytesseract pdf2image")
    
    extracted_text = ""
    
    try:
        logger.info("Converting PDF to images for OCR...")
        images = convert_from_path(str(pdf_path))
        
        for page_num, image in enumerate(images, 1):
            logger.info(f"Processing page {page_num} with OCR...")
            text = pytesseract.image_to_string(image)
            extracted_text += f"\n--- Page {page_num} (OCR) ---\n{text}\n"
        
        return extracted_text
    except Exception as e:
        logger.error(f"OCR extraction failed: {str(e)}")
        raise


def batch_extract_pdfs(
    pdf_directory: str,
    output_directory: Optional[str] = None,
    use_ocr: bool = False
) -> dict:
    """
    Extract text from multiple PDF files in a directory.
    
    Args:
        pdf_directory (str): Directory containing PDF files
        output_directory (str, optional): Directory to save extracted texts
        use_ocr (bool): Whether to use OCR for scanned PDFs
    
    Returns:
        dict: Dictionary with PDF filenames as keys and extracted text as values
    """
    
    pdf_dir = Path(pdf_directory)
    if not pdf_dir.is_dir():
        raise ValueError(f"Directory not found: {pdf_directory}")
    
    pdf_files = list(pdf_dir.glob('*.pdf')) + list(pdf_dir.glob('*.PDF'))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in: {pdf_directory}")
        return {}
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    results = {}
    for pdf_file in pdf_files:
        try:
            logger.info(f"Processing: {pdf_file.name}")
            text = extract_text_from_pdf(
                str(pdf_file),
                use_ocr=use_ocr,
                output_file=str(Path(output_directory) / f"{pdf_file.stem}.txt") if output_directory else None
            )
            results[pdf_file.name] = text
        except Exception as e:
            logger.error(f"Failed to process {pdf_file.name}: {str(e)}")
            results[pdf_file.name] = f"[Error: {str(e)}]"
    
    return results


def main():
    """
    Main function for command-line usage.
    Usage: python pdf_text_extractor.py <pdf_file_path> [--output OUTPUT_FILE] [--ocr]
    """
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract text from PDF files with proper error handling'
    )
    parser.add_argument(
        'pdf_file',
        help='Path to the PDF file or directory containing PDFs'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Output file to save extracted text (optional)',
        default=None
    )
    parser.add_argument(
        '--ocr',
        action='store_true',
        help='Use OCR for scanned PDFs (requires pytesseract)'
    )
    parser.add_argument(
        '--batch',
        '-b',
        action='store_true',
        help='Process all PDFs in a directory'
    )
    
    args = parser.parse_args()
    
    try:
        if args.batch:
            results = batch_extract_pdfs(
                args.pdf_file,
                output_directory=args.output,
                use_ocr=args.ocr
            )
            logger.info(f"Batch processing completed. Processed {len(results)} files")
            for filename, text_preview in results.items():
                preview = text_preview[:100] + "..." if len(text_preview) > 100 else text_preview
                print(f"\n{filename}:\n{preview}")
        else:
            text = extract_text_from_pdf(
                args.pdf_file,
                use_ocr=args.ocr,
                output_file=args.output
            )
            print("\n" + "="*80)
            print("EXTRACTED TEXT:")
            print("="*80)
            print(text)
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
