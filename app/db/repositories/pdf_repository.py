from sqlalchemy import select, update, exists, func
from sqlalchemy.dialects.postgresql import insert
from app.schema.enums import PDFConversionStatus
from app.db.models import PdfModel
from app.db.base_repository import BaseRepository

class PDFRepository(BaseRepository):

    async def insert(self, pdf_name: str, original_path: str, page_count: int) -> None:
        stmt = insert(PdfModel).values(
            pdf_name=pdf_name,
            original_path=original_path,
            page_count=page_count,
            status=PDFConversionStatus.UPLOADED.value,
        ).on_conflict_do_nothing(index_elements=['pdf_name'])
        
        await self.session.execute(stmt)

    async def get_all_for_tree(self) -> list[dict]:
        stmt = select(PdfModel.pdf_name, PdfModel.original_path)
        result = await self.session.execute(stmt)
        # result.mappings().all() returns a list of row-like dicts
        return [{"pdf_name": row.pdf_name, "original_path": row.original_path} 
                for row in result.mappings().all()]

    async def exists(self, pdf_name: str) -> bool:
        stmt = select(exists().where(PdfModel.pdf_name == pdf_name))
        result = await self.session.execute(stmt)
        res_val = result.scalar()
        
        return res_val if res_val is not None else False

    async def get_status(self, pdf_name: str) -> PDFConversionStatus | None:
        stmt = select(PdfModel.status).where(PdfModel.pdf_name == pdf_name)
        result = await self.session.execute(stmt)
        status_value = result.scalar_one_or_none()
        
        if status_value is None:
            return None
        return PDFConversionStatus(status_value)

    async def update_status(self, pdf_name: str, status: PDFConversionStatus) -> None:
        stmt = update(PdfModel).where(
            PdfModel.pdf_name == pdf_name
        ).values(
            status=status.value
        )
        await self.session.execute(stmt)

    async def get_by_status(self, status: PDFConversionStatus, limit: int = 100) -> list[str]:
        stmt = select(PdfModel.pdf_name).where(
            PdfModel.status == status.value
        ).limit(limit)
        
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def claim(
        self,
        from_status: PDFConversionStatus,
        to_status: PDFConversionStatus,
    ) -> str | None:
        # 1. Create the SKIP LOCKED subquery to ensure that multiple workers don't claim the same pdf twice
        subq = (
            select(PdfModel.pdf_name)
            .where(PdfModel.status == from_status.value)
            .with_for_update(skip_locked=True)
            .limit(1)
            .scalar_subquery()
        )
        
        # 2. Feed it into the UPDATE statement
        stmt = (
            update(PdfModel)
            .where(PdfModel.pdf_name == subq)
            .values(status=to_status.value)
            .returning(PdfModel.pdf_name)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()