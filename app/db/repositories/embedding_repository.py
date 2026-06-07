from app.db.base_repository import BaseRepository
from app.schema.enums import EmbeddingTaskStatus
from app.domains.core_models import EmbeddingModel

class EmbeddingRepository(BaseRepository):

    async def claim_chunks(
        self,
        limit: int = 10,
    ) -> list[dict]:

        rows = await self.fetchall(
            """
            WITH cte AS (
                SELECT embedding_id
                FROM chunk_embedding
                WHERE status IN (%s, %s)
                ORDER BY embedding_id
                FOR UPDATE SKIP LOCKED
                LIMIT %s
            )
            UPDATE chunk_embedding ce
            SET status = %s
            FROM cte, chunk c
            WHERE ce.embedding_id = cte.embedding_id
            AND ce.chunk_id = c.chunk_id
            RETURNING
                ce.chunk_id,
                c.chunk_text,
                ce.embedding_model
            """,
            (
                EmbeddingTaskStatus.PENDING.value,
                EmbeddingTaskStatus.RETRY.value,
                limit,
                EmbeddingTaskStatus.IN_PROGRESS.value,
            ),
        )

        return list(rows)

    async def upsert_embedding_vector(
        self,
        chunk_id: int,
        embedding_model: EmbeddingModel,
        embedding: list[float],
    ) -> None:

        await self.execute(
            """
            INSERT INTO chunk_embedding (chunk_id, embedding_model, embedding, status)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (chunk_id, embedding_model)
            DO UPDATE SET
                embedding = EXCLUDED.embedding,
                status = EXCLUDED.status,
                error_message = 'Embedding for this chunk was already in db; embedding vector has been overwritten'
            """,
            (
                chunk_id,
                embedding_model.value,
                embedding,
                EmbeddingTaskStatus.SUCCESS.value,
            ),
        )

    async def update_status(
        self,
        chunk_id: int,
        embedding_model: EmbeddingModel,
        status: EmbeddingTaskStatus,
        error_message: str | None = None,
    ) -> None:

        await self.execute(
            """
            UPDATE chunk_embedding
            SET
                status = %s,
                error_message = %s
            WHERE chunk_id = %s AND embedding_model = %s
            """,
            (
                status.value,
                error_message,
                chunk_id,
                embedding_model.value,
            ),
        )

    async def get_status(
        self,
        chunk_id: int,
        embedding_model: EmbeddingModel,
    ) -> dict | None:
        """
        Fetches the current lifecycle details of an embedding task.
        Returns a dict with keys: status, error_message, retry_count, or None if not found.
        """
        row = await self.fetchone(
            """
            SELECT status, error_message
            FROM chunk_embedding 
            WHERE chunk_id = %s AND embedding_model = %s
            """,
            (chunk_id, embedding_model.value),
        )
        return row