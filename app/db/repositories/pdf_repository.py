from app.db.base_repository import BaseRepository
from app.schema.enums import PDFConversionStatus

class PDFRepository(BaseRepository):

    async def insert(self, pdf_name: str, original_path: str, page_count: int) -> None:
        await self.execute(
            """
            INSERT INTO pdf
            (
                pdf_name,
                original_path,
                page_count,
                status
            )
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (pdf_name)
            DO NOTHING
            """,
            (
                pdf_name,
                original_path, # New column mapped here
                page_count,
                PDFConversionStatus.UPLOADED.value,
            ),
        )

    # NEW: Fetch all records to build the frontend FileTree
    async def get_all_for_tree(self) -> list[dict]:
        rows = await self.fetchall(
            """
            SELECT pdf_name, original_path
            FROM pdf
            """
        )
        return [{"pdf_name": r["pdf_name"], "original_path": r["original_path"]} for r in rows]


    async def exists(self, pdf_name: str) -> bool:
        row = await self.fetchone(
            """
            SELECT 1
            FROM pdf
            WHERE pdf_name=%s
            """,
            (pdf_name,),
        )
        return row is not None

    async def get_status(self, pdf_name: str) -> PDFConversionStatus | None:
        row = await self.fetchone(
            """
            SELECT status
            FROM pdf
            WHERE pdf_name=%s
            """,
            (pdf_name,),
        )

        if not row:
            return None

        return PDFConversionStatus(row["status"])

    async def update_status(
        self,
        pdf_name: str,
        status: PDFConversionStatus,
    ) -> None:
        await self.execute(
            """
            UPDATE pdf
            SET
                status=%s,
                last_status_update=NOW()
            WHERE pdf_name=%s
            """,
            (
                status.value,
                pdf_name,
            ),
        )

    async def get_by_status(
        self,
        status: PDFConversionStatus,
        limit: int = 100,
    ) -> list[str]:
        rows = await self.fetchall(
            """
            SELECT pdf_name
            FROM pdf
            WHERE status=%s
            LIMIT %s
            """,
            (
                status.value,
                limit,
            ),
        )
        return [r["pdf_name"] for r in rows]

    async def claim(
        self,
        from_status: PDFConversionStatus,
        to_status: PDFConversionStatus,
    ) -> str | None:
        row = await self.fetchone(
            """
            WITH cte AS (
                SELECT pdf_name
                FROM pdf
                WHERE status=%s
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            UPDATE pdf
            SET status=%s
            FROM cte
            WHERE pdf.pdf_name=cte.pdf_name
            RETURNING pdf.pdf_name
            """,
            (
                from_status.value,
                to_status.value,
            ),
        )
        return (row["pdf_name"] if row else None)