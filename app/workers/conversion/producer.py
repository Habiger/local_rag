import asyncio

from app.config.logging import logger
from app.domains.conversion.page_splitting import PdfPage
from app.services.conversion_service import ConversionService

SLEEPING_TIME_PDF_PRODUCER_WORKER = 5

BACKPRESSURE_LIMIT = 20

async def docling_page_producer(
    service: ConversionService,
    queue: asyncio.Queue[PdfPage],
) -> None:

    while True:
        try:
            if queue.qsize() >= BACKPRESSURE_LIMIT:
                await asyncio.sleep(SLEEPING_TIME_PDF_PRODUCER_WORKER) 
                continue
            
            pages = await service.get_pdf_pages()

            if not pages:
                await asyncio.sleep(SLEEPING_TIME_PDF_PRODUCER_WORKER)
                continue

            async for page in pages:
                await queue.put(page)

        except asyncio.CancelledError:
            raise

        except Exception as e:
            logger.exception(
                "page producer failed",
                extra={"extra": {"exception": str(e)}},
            )
            await asyncio.sleep(5)