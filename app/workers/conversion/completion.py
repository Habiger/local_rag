import asyncio

from app.config.logging import logger
from app.services.conversion_service import ConversionService

CONVERSION_COMPLETION_WORKER_SLEEP_TIME = 5

async def conversion_completion_worker(
    service: ConversionService,
) -> None:
    while True:
        try:
            pdfs = await service.get_pdfs_under_conversion()

            for pdf_name in pdfs:
                await service.check_if_whole_pdf_conversion_completed(
                    pdf_name
                )
            await asyncio.sleep(
                CONVERSION_COMPLETION_WORKER_SLEEP_TIME
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(
                "Error in conversion completion worker",
                extra={
                    "extra": {"exception": str(e)}
                }
            )

