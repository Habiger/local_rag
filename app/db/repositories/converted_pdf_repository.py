from psycopg.types.json import Jsonb

from docling_core.types.doc.document import DoclingDocument

from app.db.base_repository import BaseRepository


class ConvertedPDFRepository(BaseRepository):

    async def upsert(
        self,
        pdf_name: str,
        post_processing_config_id: int,
        docling_document: DoclingDocument,
    ) -> None:
        await self.execute(
            """
            INSERT INTO converted_pdf
            (
                pdf_name,
                post_processing_config_id,
                docling_document
            )
            VALUES (%s,%s,%s)
            ON CONFLICT
            (
                pdf_name,
                post_processing_config_id
            )
            DO UPDATE SET
                docling_document=EXCLUDED.docling_document
            """,
            (
                pdf_name,
                post_processing_config_id,
                Jsonb(docling_document.model_dump(mode="json")), #TODO maybe inefficient, compare with docling_document.model_dump_json
            ),
        )

    async def get(
            self,
            pdf_name: str,
            post_processing_config_id: int,
    ) -> DoclingDocument:
        row = await self.fetchone(
            """
            SELECT docling_document
            FROM converted_pdf
            WHERE pdf_name=%s
            AND post_processing_config_id=%s
            """,
            (
                pdf_name,
                post_processing_config_id,
            ),
        )
        if not row:
            raise RuntimeError(f"Docling Document not found for pdf_name={pdf_name} and post_processing_config_id={post_processing_config_id}")

        return DoclingDocument.model_validate(row["docling_document"])