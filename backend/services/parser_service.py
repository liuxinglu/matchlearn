import asyncio
from io import BytesIO

from PyPDF2 import PdfReader


def extract_text_from_pdf(file_content: bytes, max_pages: int = 50) -> str:
    """
    Extracts text from a PDF file byte stream with performance optimizations.

    Args:
        file_content: PDF file bytes
        max_pages: Maximum number of pages to process (for performance)

    Returns:
        Extracted text as string
    """
    # Check file size (limit to 10MB for performance)
    if len(file_content) > 10 * 1024 * 1024:  # 10MB
        raise ValueError("PDF file too large (max 10MB)")

    try:
        pdf_file = BytesIO(file_content)
        reader = PdfReader(pdf_file)

        # Check page count
        if len(reader.pages) > max_pages:
            print(
                f"Warning: PDF has {len(reader.pages)} pages, processing first {max_pages}"
            )

        # Extract text from pages (limit to max_pages for performance)
        text_parts = []
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                break
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        return "\n".join(text_parts)
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        raise


async def extract_text_from_pdf_async(file_content: bytes, max_pages: int = 50) -> str:
    """
    Asynchronous version of PDF text extraction.

    This runs the CPU-intensive PDF parsing in a thread pool to avoid
    blocking the event loop.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, extract_text_from_pdf, file_content, max_pages
    )
