from typing import List, Optional
from psycopg_pool import AsyncConnectionPool

from app.config.logging import logger

from app.db.database import db
from app.db.unit_of_work import unit_of_work

from app.schema.enums import EmbeddingTaskStatus, EmbeddingModel

class EmbeddingService:
    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def claim_chunks_for_embedding(
        self, limit: int = 10
    ) -> List[dict]:
        """
        Finds chunks that need embeddings, locks them (or creates a PENDING embedding record),
        and returns them.
        """
        async with unit_of_work(self.pool) as uow:
            # You will need to implement this in your EmbeddingRepository
            # It should ideally INSERT into chunk_embedding with status='CLAIMED' 
            # for chunks that don't have an embedding for the required model yet.
            return await uow.embeddings.claim_chunks(limit=limit)

    async def save_successful_embedding(
        self, chunk_id: int, model: EmbeddingModel, vector: list[float]
    ) -> None:
        """Saves the generated vector and marks status as SUCCESS."""
        async with unit_of_work(self.pool) as uow:
            await uow.embeddings.upsert_embedding_vector(
                chunk_id=chunk_id,
                embedding_model=model,
                embedding=vector
            )

    async def handle_embedding_failure(
        self, chunk_id: int, model: EmbeddingModel, error_message: str
    ) -> None:
        """Logs the error and increments retry count/updates status."""
        async with unit_of_work(self.pool) as uow:
            await uow.embeddings.update_status(
                chunk_id=chunk_id,
                status=EmbeddingTaskStatus.FAILED,
                embedding_model=model,
                error_message=error_message
            )

    async def check_and_update_completed_pdfs(self, limit: int = 10) -> None:
        """
        Finds indexed_pdfs where all associated chunks have finished processing
        and atomically updates the PDF status to EMBEDDING_FINISHED.
        """
        async with unit_of_work(self.pool) as uow:
            completed_ids = await uow.indexed_pdfs.mark_completed_embeddings(
                limit=limit
            )
            
            if completed_ids:
                logger.info(f"Successfully marked PDFs as EMBEDDING_FINISHED: {completed_ids}")