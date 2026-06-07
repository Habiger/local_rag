from app.db.base_repository import BaseRepository
from app.schema.enums import PdfPipelineStatus, EmbeddingTaskStatus, PDFConversionStatus
from app.domains.core_models import ClaimedPdfTask

class PdfPipelineRepository(BaseRepository):

    async def create(
            self,
            pdf_name: str,
            pdf_indexing_config_id: int,
    ) -> int:
        row = await self.fetchone(
            """
            INSERT INTO indexed_pdf 
            (pdf_name, pdf_indexing_config_id, status)
            VALUES (%s, %s, %s)
            ON CONFLICT (pdf_name, pdf_indexing_config_id)
            DO UPDATE SET status=EXCLUDED.status
            RETURNING indexed_pdf_id
            """,
            (
                pdf_name,
                pdf_indexing_config_id,
                PdfPipelineStatus.PENDING.value,
            ),
        )
        if not row:
            raise RuntimeError("Failed to create indexed_pdf")
        return row["indexed_pdf_id"]

    async def update_status(
        self,
        indexed_pdf_id: int,
        status: PdfPipelineStatus,
    ) -> None:
        await self.execute(
            """
            UPDATE indexed_pdf
            SET status=%s
            WHERE indexed_pdf_id=%s
            """,
            (
                status.value,
                indexed_pdf_id,
            ),
        )

    async def claim(
            self,
            from_status: PdfPipelineStatus,
            to_status: PdfPipelineStatus,
    ) -> ClaimedPdfTask | None:
            
        row = await self.fetchone(
            """
            WITH cte AS (
                SELECT ip.indexed_pdf_id, ip.pdf_indexing_config_id
                FROM indexed_pdf ip
                JOIN pdf p ON p.pdf_name = ip.pdf_name
                WHERE ip.status = %s
                AND p.status = %s
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            ),
            updated AS (
                UPDATE indexed_pdf ip
                SET status = %s
                FROM cte
                WHERE ip.indexed_pdf_id = cte.indexed_pdf_id
                RETURNING
                    ip.indexed_pdf_id,
                    ip.pdf_name,
                    ip.status,
                    ip.pdf_indexing_config_id
            )
            SELECT
                u.indexed_pdf_id,
                u.pdf_name,
                u.status,
                pic.embedding_model,
                ppc.parameter AS post_processing_params,
                ppc.post_processing_config_id,
                cc.parameters AS chunking_params,
                cc.chunking_config_id
            FROM updated u
            JOIN pdf_indexing_config pic ON u.pdf_indexing_config_id = pic.pdf_indexing_config_id
            JOIN post_processing_config ppc ON pic.post_processing_config_id = ppc.post_processing_config_id
            JOIN chunking_config cc ON pic.chunking_config_id = cc.chunking_config_id;
            """,
            (from_status.value, PDFConversionStatus.PAGEWISE_CONVERSION_FINISHED.value, to_status.value),
        )

        if not row:
            return None

        return ClaimedPdfTask(
            indexed_pdf_id=row["indexed_pdf_id"],
            pdf_name=row["pdf_name"],
            status=PdfPipelineStatus(row["status"]),
            post_processing_config_id=row["post_processing_config_id"],
            chunking_config_id=row["chunking_config_id"],      
            post_processing_options=row["post_processing_params"],
            chunking_options=row["chunking_params"],
            embedding_model=row["embedding_model"]
        )

    async def mark_completed_embeddings(self, limit: int = 100) -> list[int]:
        """
        Atomically finds PDFs which are currently in the `IndexedPdfStatus.EMBEDDING_IN_PROGRESS`state and where ALL associated chunks have reached 
        a terminal embedding state (either EmbeddingTaskStatus.SUCCESS or EmbeddingTaskStatus.FAILED). The found PDF's Indexation status is then updated to `IndexedPdfStatus.EMBEDDING_FINISHED`.
        
        Args:
            limit (int): The maximum number of PDFs to update. Defaults to 100.
            
        Returns:
           list[int]: A list of the indexed_pdf_ids which were updated.
        """
        rows = await self.fetchall(
            """
            WITH completed_pdfs AS (
                SELECT ip.indexed_pdf_id
                FROM indexed_pdf ip
                JOIN pdf_indexing_config pic ON ip.pdf_indexing_config_id = pic.pdf_indexing_config_id
                WHERE ip.status = %s
                AND EXISTS (
                    SELECT 1 FROM chunk c WHERE c.indexed_pdf_id = ip.indexed_pdf_id
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM chunk c
                    LEFT JOIN chunk_embedding ce 
                      ON c.chunk_id = ce.chunk_id 
                     AND ce.embedding_model = pic.embedding_model
                    WHERE c.indexed_pdf_id = ip.indexed_pdf_id
                      AND (
                          ce.status IS NULL 
                          OR ce.status NOT IN %s
                      )
                )
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            )
            UPDATE indexed_pdf ip
            SET status = %s
            FROM completed_pdfs
            WHERE ip.indexed_pdf_id = completed_pdfs.indexed_pdf_id
            RETURNING ip.indexed_pdf_id;
            """,
            (
                PdfPipelineStatus.EMBEDDING_IN_PROGRESS.value,
                (EmbeddingTaskStatus.SUCCESS.value, EmbeddingTaskStatus.FAILED.value), 
                limit,
                PdfPipelineStatus.EMBEDDING_FINISHED.value,
            ),
        )

        return [r["indexed_pdf_id"] for r in rows]
    
    async def get_pipeline_progress(self) -> list[dict]:
        """
        Retrieves the aggregated progress of all documents in the pipeline.
        Uses correlated subqueries to avoid Cartesian fan-out from multiple 1-to-N relationships.
        """
        rows = await self.fetchall(
            """
            SELECT
                p.pdf_name,
                p.status AS conversion_status,
                ip.status AS pipeline_status,
                -- Page Level Progress
                (SELECT COUNT(*) FROM converted_page cp WHERE cp.pdf_name = p.pdf_name) AS total_pages,
                (
                    SELECT COUNT(*) 
                    FROM converted_page cp 
                    WHERE cp.pdf_name = p.pdf_name AND cp.status = 'success'
                ) AS converted_pages,
                -- Chunk / Embedding Level Progress (Requires an indexed_pdf context)
                COALESCE((SELECT COUNT(*) FROM chunk c WHERE c.indexed_pdf_id = ip.indexed_pdf_id), 0) AS total_chunks,
                COALESCE((
                    SELECT COUNT(*)
                    FROM chunk c
                    JOIN chunk_embedding ce ON c.chunk_id = ce.chunk_id
                    WHERE c.indexed_pdf_id = ip.indexed_pdf_id AND ce.status = 'success'
                ), 0) AS embedded_chunks
            FROM pdf p
            LEFT JOIN indexed_pdf ip ON p.pdf_name = ip.pdf_name
            ORDER BY p.pdf_name ASC;
            """
        )
        return rows