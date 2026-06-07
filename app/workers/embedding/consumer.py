import asyncio
from app.config.logging import logger
from app.services.embedding_service import EmbeddingService
from app.clients.embedding_client import EmbeddingClient
from app.workers.embedding.producer import EmbeddingQueueItem

EMBEDDING_CHUNK_CONSUMER_SLEEP_TIME = 5

async def chunk_consumer(
    queue: asyncio.Queue,
    service: EmbeddingService,
    embedding_client: EmbeddingClient,
    semaphore: asyncio.Semaphore,
):
    while True:
        try:
            queue_item: EmbeddingQueueItem = await queue.get()

            try:
                # 1. Fetch Embedding
                async with semaphore:
                    embeddings = await embedding_client.embed(
                        queue_item.chunk_text,
                        queue_item.embedding_model,
                    )

                # 2. Save via Service Layer
                await service.save_successful_embedding(
                    chunk_id=queue_item.chunk_id,
                    model=queue_item.embedding_model,
                    vector=embeddings
                )
                
                logger.debug(f"Stored embedding for chunk_id={queue_item.chunk_id}")

            except Exception as e:
                logger.error(
                    f"Embedding failed for chunk_id={queue_item.chunk_id}",
                    extra={"extra": {"exception": str(e)}},
                )
                await service.handle_embedding_failure(
                    chunk_id=queue_item.chunk_id,
                    model=queue_item.embedding_model,
                    error_message=str(e)
                )
            finally:
                queue.task_done()

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Consumer loop crashed", extra={"extra": {"exception": str(e)}})
            await asyncio.sleep(EMBEDDING_CHUNK_CONSUMER_SLEEP_TIME)