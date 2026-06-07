import asyncio

from app.config.logging import logger
from app.domains.conversion.page_splitting import PdfPage
from app.services.conversion_service import ConversionService


SLEEPING_TIME_PDF_CONSUMER_WORKER = 5


async def docling_page_consumer(
    service: ConversionService,
    queue: asyncio.Queue[PdfPage],
) -> None:

    while True:
        pdf_page = await queue.get()

        await service.handle_page_conversion(pdf_page)
        #await service.check_if_whole_pdf_conversion_completed(pdf_page.pdf_name)
