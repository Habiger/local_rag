from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert

from docling_serve.datamodel.responses import ConvertDocumentResponse

from app.schema.enums import PageConversionTaskStatus
from app.db.base_repository import BaseRepository
from app.db.models import PdfModel, ConvertedPageModel

class ConvertedPageRepository(BaseRepository):

    async def _get_pdf_id_by_name(self, pdf_name: str) -> int:
        """Helper to resolve pdf_name to pdf_id since the schema uses surrogate keys."""
        stmt = select(PdfModel.pdf_id).where(PdfModel.pdf_name == pdf_name)
        pdf_id = await self.session.scalar(stmt)
        if not pdf_id:
            raise ValueError(f"PDF with name '{pdf_name}' not found.")
        return pdf_id

    async def insert(
        self,
        pdf_name: str,
        page_number: int,
        conversion_result: ConvertDocumentResponse,
    ):
        pdf_id = await self._get_pdf_id_by_name(pdf_name)

        stmt = insert(ConvertedPageModel).values(
            pdf_id=pdf_id,
            page_number=page_number,
            conversion_result=conversion_result.model_dump(mode="json"),
            retry_count=0,
            error_message=None,
            status=PageConversionTaskStatus.SUCCESS.value,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["pdf_id", "page_number"],
            set_={
                "conversion_result": stmt.excluded.conversion_result,
                "status": stmt.excluded.status,
                "error_message": None,
            },
        )

        await self.session.execute(stmt)

    async def get_pages(self, pdf_name: str) -> dict[int, ConvertDocumentResponse]:
        stmt = (
            select(ConvertedPageModel)
            .join(PdfModel, PdfModel.pdf_id == ConvertedPageModel.pdf_id)
            .where(
                PdfModel.pdf_name == pdf_name,
                ConvertedPageModel.status == PageConversionTaskStatus.SUCCESS.value,
            )
            .order_by(ConvertedPageModel.page_number)
        )

        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return {
            row.page_number: ConvertDocumentResponse.model_validate(row.conversion_result)
            for row in rows
        }

    async def get_docling_conversion_progress(self) -> list[dict]:
        """
        Retrieves the page-wise Docling conversion progress for all documents,
        including successful and failed page counts using PostgreSQL aggregate filters.
        """
        stmt = (
            select(
                PdfModel.pdf_name,
                PdfModel.status.label("conversion_status"),
                PdfModel.page_count.label("total_pages"),
                func.count(ConvertedPageModel.converted_page_id)
                .filter(ConvertedPageModel.status == PageConversionTaskStatus.SUCCESS.value)
                .label("converted_pages"),
                func.count(ConvertedPageModel.converted_page_id)
                .filter(ConvertedPageModel.status == PageConversionTaskStatus.FAILED.value)
                .label("failed_pages"),
            )
            .outerjoin(ConvertedPageModel, PdfModel.pdf_id == ConvertedPageModel.pdf_id)
            .group_by(PdfModel.pdf_id)
            .order_by(PdfModel.pdf_name.asc())
        )

        result = await self.session.execute(stmt)

        return [
            {
                "pdf_name": row.pdf_name,
                "conversion_status": row.conversion_status,
                "total_pages": row.total_pages,
                "converted_pages": row.converted_pages,
                "failed_pages": row.failed_pages,
            }
            for row in result.all()
        ]

    async def count_pending(self, pdf_name: str) -> int:
        stmt = (
            select(
                PdfModel.page_count,
                func.count(ConvertedPageModel.converted_page_id)
                .filter(ConvertedPageModel.status == PageConversionTaskStatus.SUCCESS.value)
            )
            .outerjoin(ConvertedPageModel, PdfModel.pdf_id == ConvertedPageModel.pdf_id)
            .where(PdfModel.pdf_name == pdf_name)
            .group_by(PdfModel.pdf_id)
        )

        result = await self.session.execute(stmt)
        row = result.one_or_none()

        if not row:
            return 0

        page_count, converted_count = row
        pending = (page_count or 0) - (converted_count or 0)
        return max(pending, 0)

    async def mark_failed(
        self,
        pdf_name: str,
        page_number: int,
        error_message: str,
    ):
        pdf_id = await self._get_pdf_id_by_name(pdf_name)

        stmt = insert(ConvertedPageModel).values(
            pdf_id=pdf_id,
            page_number=page_number,
            conversion_result={},
            retry_count=1,
            error_message=error_message,
            status=PageConversionTaskStatus.FAILED.value,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["pdf_id", "page_number"],
            set_={
                "retry_count": ConvertedPageModel.retry_count + 1,
                "error_message": stmt.excluded.error_message,
                "status": stmt.excluded.status,
            },
        )

        await self.session.execute(stmt)