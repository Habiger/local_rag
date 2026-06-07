import asyncio
from app.config.logging import logger
from app.services.embedding_service import EmbeddingService
from app.domains.core_models import EmbeddingModel

from dataclasses import dataclass

@dataclass
class EmbeddingQueueItem:
    chunk_id: int
    chunk_text: str 
    embedding_model: EmbeddingModel

QUEUE_MIN_SIZE = 100
SLEEP_TIME = 2

async def chunk_producer(
    queue: asyncio.Queue[EmbeddingQueueItem],
    service: EmbeddingService,
):
    while True:
        try:
            if queue.qsize() >= QUEUE_MIN_SIZE:
                await asyncio.sleep(SLEEP_TIME)
                continue

            claimed_chunks = await service.claim_chunks_for_embedding(limit=20)
            
            if not claimed_chunks:
                await asyncio.sleep(SLEEP_TIME)
                continue
            
            for claimed_chunk in claimed_chunks:
                queue_item = EmbeddingQueueItem(
                    chunk_id=claimed_chunk["chunk_id"],
                    chunk_text=claimed_chunk["chunk_text"],
                    embedding_model=EmbeddingModel(claimed_chunk["embedding_model"]),
                )
                await queue.put(queue_item)
                
            logger.debug(f"Queued {len(claimed_chunks)} chunks for embedding.")
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Chunk producer failed", extra={"extra": {"exception": str(e)}})
            await asyncio.sleep(SLEEP_TIME)