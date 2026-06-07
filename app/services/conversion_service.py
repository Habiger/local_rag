import asyncio

from typing import AsyncIterator
from psycopg_pool import AsyncConnectionPool

from app.config.paths import PDF_STORAGE_DIR
from app.config.logging import logger

from app.clients.docling_client_async import DoclingClient

from app.db.database import db
from app.db.unit_of_work import unit_of_work
from app.schema.enums import PDFConversionStatus

from app.domains.conversion.page_splitting import PdfPage, split_pdf_pages_in_memory_async


class ConversionService:
    MAX_RETRY_COUNT = 2
    
    def __init__(self, pool: AsyncConnectionPool, docling_client: DoclingClient):
        self.pool = pool
        self.pool = db.pool
        self.docling_client = docling_client

    async def _claim_pdf_for_page_conversion(self) -> str | None:
        async with unit_of_work(self.pool) as uow:
            pdf_name = await uow.pdfs.claim(
                PDFConversionStatus.UPLOADED,
                PDFConversionStatus.CLAIMED_FOR_PAGEWISE_CONVERSION,
            )

        if pdf_name:
            logger.info(
                "Claimed PDF for page conversion",
                extra={
                    "extra": {
                        "pdf_name": pdf_name,
                    }
                },
            )

        return pdf_name

    
    async def get_pdf_pages(self) -> AsyncIterator[PdfPage] | None:
        """
        Claims a PDF and returns a streaming iterator over its pages.
        """
        pdf_name = await self._claim_pdf_for_page_conversion()

        if not pdf_name:
            logger.debug("No PDFs available for page conversion")
            return None

        pdf_path = PDF_STORAGE_DIR / pdf_name #TODO Implement File/StorageHandler which is dependency injected

        logger.info(
            "Starting PDF page splitting",
            extra={
                "extra": {
                    "pdf_name": pdf_name,
                    "pdf_path": str(pdf_path),
                }
            },
        )

        return split_pdf_pages_in_memory_async(pdf_path)


    async def handle_page_conversion(self, pdf_page: PdfPage) -> None:
        """Orchestrates the page conversion process:
         - conversion via docling client
         - insertion of conversion result into db
         - if the conversion fails, the page is marked as failed in the db

        Args:
            pdf_page (PdfPage): the page to convert
        """
        try:
            logger.debug(
                "Starting page conversion",
                extra={
                    "extra": {
                        "pdf_name": pdf_page.pdf_name,
                        "page": pdf_page.page_number,
                    }
                },
            )
            # conversion
            conversion_result = await self.docling_client.sync_convert_pdf(
                pdf_page.page_bytes,
                pdf_page.pdf_name,
            )
            # store conversion result
            async with unit_of_work(self.pool) as uow:
                await uow.pages.insert(
                    pdf_page.pdf_name,
                    pdf_page.page_number,
                    conversion_result,
                )
            # logging
            logger.debug(
                "Stored converted page",
                extra={
                    "extra": {
                        "pdf_name": pdf_page.pdf_name,
                        "page": pdf_page.page_number,
                    }
                },
            )
        except asyncio.CancelledError:
            raise

        except Exception as e:
            # mark page conversion as failed
            logger.exception(
                f"Error processing page {pdf_page.pdf_name} {pdf_page.page_number}", 
                extra={
                    "extra": {
                        "pdf_name": pdf_page.pdf_name, 
                        "page": pdf_page.page_number, 
                        "exception": str(e)
                    }
                }
            )
            async with unit_of_work(self.pool) as uow:
                await uow.pages.mark_failed(pdf_page.pdf_name, pdf_page.page_number, str(e))
                

    async def check_if_whole_pdf_conversion_completed(self, pdf_name: str):
        """Checks if all pages of the pdf have been processed (success or failure), if yes: updates pdf status to `PDFStatus.PAGEWISE_CONVERSION_FINISHED`

        Args:
            pdf_name (str): the pdf to be checked
        """
        try:
            async with unit_of_work(self.pool) as uow:
                pending = await uow.pages.count_pending(pdf_name)

                logger.debug(
                    "Checked pending page count",
                    extra={
                        "extra": {
                            "pdf_name": pdf_name,
                            "pending_pages": pending,
                        }
                    },
                )

                if pending == 0:
                    await uow.pdfs.update_status(
                        pdf_name,
                        PDFConversionStatus.PAGEWISE_CONVERSION_FINISHED,
                    )

                    logger.info(
                        "PDF pagewise conversion completed",
                        extra={
                            "extra": {
                                "pdf_name": pdf_name,
                            }
                        },
                    )

        except asyncio.CancelledError:
            raise

        except Exception as e:
            logger.exception(
                "Failed checking PDF conversion completion",
                extra={
                    "extra": {
                        "pdf_name": pdf_name,
                        "exception": str(e),
                        "exception_type": type(e).__name__,
                    }
                },
            )
            raise
        
    async def load_converted_pages(self, pdf_name: str):
        async with unit_of_work(self.pool) as uow:
            pages = await uow.pages.get_pages(pdf_name)
        return pages

            
    async def get_pdfs_under_conversion(self) -> list[str]:
        async with unit_of_work(self.pool) as uow:
            pdfs = await uow.pdfs.get_by_status(
                PDFConversionStatus.CLAIMED_FOR_PAGEWISE_CONVERSION
            )
        return pdfs
