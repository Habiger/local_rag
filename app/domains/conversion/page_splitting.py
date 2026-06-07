import aiofiles

from dataclasses import dataclass
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from io import BytesIO
from typing import AsyncIterator, Tuple

@dataclass
class PdfPage:
    pdf_name: str
    page_number: int
    page_bytes: bytes
    retry_count: int = 0
    
    @property
    def has_reached_retry_max(self) -> bool:
        return self.retry_count >= 3


async def split_pdf_pages_in_memory_async(
    input_pdf_path: str | Path,
) -> AsyncIterator[PdfPage]:
    """
    Asynchronously reads a PDF and yields (page_number, page_bytes). The first page has page_number=1.

    Args:
        input_pdf_path: Path to the source PDF.

    Yields:
        PdfPage: A dataclass containing the page number, page bytes, and a boolean indicating if it's the last page.
    """
    # Async file read
    async with aiofiles.open(input_pdf_path, "rb") as f:
        pdf_bytes = await f.read()
    pdf_name = Path(input_pdf_path).name
    reader = PdfReader(BytesIO(pdf_bytes))
    num_pages = reader.get_num_pages()
    is_last_page = False
    for page_index, page in enumerate(reader.pages, start=1): # start=1 -> first page has page number 1
        writer = PdfWriter()
        writer.add_page(page)
        buffer = BytesIO()
        writer.write(buffer)
        buffer.seek(0)
        if page_index == num_pages:
            is_last_page = True
        
        yield PdfPage(pdf_name, page_index, buffer.read(), is_last_page)