from psycopg.types.json import Jsonb

from docling_serve.datamodel.responses import ConvertDocumentResponse
from app.db.base_repository import BaseRepository
from app.schema.enums import PageConversionTaskStatus


class ConvertedPageRepository(BaseRepository):

    async def insert(
        self,
        pdf_name: str,
        page_number: int,
        conversion_result: ConvertDocumentResponse,
    ):
        await self.execute(
            """
            INSERT INTO converted_page
            (
                pdf_name,
                page_number,
                conversion_result,
                retry_count,
                error_message,
                status
            )
            VALUES (%s, %s, %s, 0, NULL, %s)
            ON CONFLICT (pdf_name, page_number)
            DO UPDATE SET
                conversion_result = EXCLUDED.conversion_result,
                status = EXCLUDED.status,
                error_message = NULL
            """,
            (
                pdf_name,
                page_number,
                Jsonb(conversion_result.model_dump(mode="json")),
                PageConversionTaskStatus.SUCCESS.value,
            ),
        )

    async def get_pages(self, pdf_name: str) -> dict[int, ConvertDocumentResponse]:
        rows = await self.fetchall(
            """
            SELECT *
            FROM converted_page
            WHERE pdf_name = %s
                AND status = %s
            ORDER BY page_number
            """,
            (pdf_name, PageConversionTaskStatus.SUCCESS),
        )

        return {
            int(row["page_number"]): ConvertDocumentResponse(**row["conversion_result"])
            for row in rows
        }

    async def get_docling_conversion_progress(self) -> list[dict]:
        """
        Retrieves the page-wise Docling conversion progress for all documents,
        including successful and failed page counts.
        """
        rows = await self.fetchall(
            """
            SELECT
                p.pdf_name,
                p.status AS conversion_status,
                p.page_count AS total_pages,
                (
                    SELECT COUNT(*) 
                    FROM converted_page cp 
                    WHERE cp.pdf_name = p.pdf_name AND cp.status = %s
                ) AS converted_pages,
                (
                    SELECT COUNT(*) 
                    FROM converted_page cp 
                    WHERE cp.pdf_name = p.pdf_name AND cp.status = %s
                ) AS failed_pages
            FROM pdf p
            ORDER BY p.pdf_name ASC;
            """,
            (
                PageConversionTaskStatus.SUCCESS.value,
                PageConversionTaskStatus.FAILED.value
            ),
        )
        return rows

    async def count_pending(self, pdf_name: str) -> int:
        row = await self.fetchone(
            """
            SELECT
                COALESCE((SELECT page_count FROM pdf WHERE pdf_name = %s), 0)
                -
                (
                    SELECT COUNT(*)
                    FROM converted_page
                    WHERE pdf_name = %s
                      AND status = %s
                )
                AS pending
            """,
            (
                pdf_name,
                pdf_name,
                PageConversionTaskStatus.SUCCESS.value,
            ),
        )

        return max(row["pending"] or 0, 0) if row else 0

    async def mark_failed(
        self,
        pdf_name: str,
        page_number: int,
        error_message: str,
    ):
        await self.execute(
            """
            INSERT INTO converted_page
                (pdf_name, page_number, conversion_result, retry_count, error_message, status)
            VALUES
                (%s, %s, '{}'::jsonb, 1, %s, %s)
            ON CONFLICT (pdf_name, page_number)
            DO UPDATE SET
                retry_count = converted_page.retry_count + 1,
                error_message = EXCLUDED.error_message,
                status = EXCLUDED.status
            """,
            (
                pdf_name,
                page_number,
                error_message,
                PageConversionTaskStatus.FAILED.value,
            ),
        )
