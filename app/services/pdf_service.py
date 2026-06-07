# app/services/pdf_service.py
from psycopg_pool import AsyncConnectionPool

from app.db.unit_of_work import unit_of_work

from app.schema.dtos import DoclingConversionProgressDTO
from app.schema.enums import PDFConversionStatus

class PDFService:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def register_pdf(self, pdf_name: str, original_path: str, page_count: int) -> None:
        async with unit_of_work(self.pool) as uow:
            await uow.pdfs.insert(pdf_name, original_path, page_count)

    async def get_all_pdfs(self) -> list[dict]:
        async with unit_of_work(self.pool) as uow:
            return await uow.pdfs.get_all_for_tree()

    async def exists(self, pdf_name: str) -> bool:
        async with unit_of_work(self.pool) as uow:
            return await uow.pdfs.exists(pdf_name)

    async def get_status(self, pdf_name: str):
        async with unit_of_work(self.pool) as uow:
            return await uow.pdfs.get_status(pdf_name)

    async def get_pdfs_by_status(self, pdf_status: PDFConversionStatus, limit: int):
        async with unit_of_work(self.pool) as uow:
            return await uow.pdfs.get_by_status(pdf_status, limit=limit)
        
    async def get_all_conversion_progress(self) -> list[DoclingConversionProgressDTO]:
        """
        Fetches system-wide Docling conversion progress and maps it to DTOs.
        """
        async with unit_of_work(self.pool) as uow:
            # Assuming you moved the query to the pdfs repository
            raw_progress = await uow.pages.get_docling_conversion_progress()
            
            return [
                DoclingConversionProgressDTO(
                    pdf_name=row["pdf_name"],
                    conversion_status=row["conversion_status"],
                    total_pages=row["total_pages"],
                    success_pages=row["converted_pages"],
                    failed_pages=row["failed_pages"]
                )
                for row in raw_progress
            ]