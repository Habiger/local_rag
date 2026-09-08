import asyncio

from app.config.settings import llamacpp_config
from app.config.logging import logger

from app.clients.embedding_client import EmbeddingClient
from app.workers.embedding.producer import chunk_producer
from app.workers.embedding.consumer import chunk_consumer
from app.workers.embedding.completion import embedding_completion_worker

from app.services.embedding_service import EmbeddingService

async def pipeline():
    # Initializing clients
    embedding_service = EmbeddingService()
    embedding_client = EmbeddingClient(llamacpp_config)#
    
    # PAGE CONVERSION
    page_queue = asyncio.Queue(maxsize=1000)
    NO_EMBEDDING_CHUNK_PRODUCER = 2
    NO_EMBEDDING_CHUNK_CONSUMER = 10
    NO_EMBEDDING_CHUNK_COMPLETION = 1
    tasks = []
    for _ in range(NO_EMBEDDING_CHUNK_PRODUCER):
        tasks.append(
            asyncio.create_task(
                chunk_producer(page_queue, embedding_service)
            )
        )
    semaphore = asyncio.Semaphore(5)
    for _ in range(NO_EMBEDDING_CHUNK_CONSUMER):
        tasks.append(
            asyncio.create_task(
                chunk_consumer(
                    page_queue, 
                    embedding_service,
                    embedding_client,
                    semaphore
                    
                )
            )
        )
    for _ in range(NO_EMBEDDING_CHUNK_COMPLETION):
        tasks.append(
            asyncio.create_task(
                embedding_completion_worker(
                    embedding_service,
                    poll_interval_seconds=5
                    )
            )
        )
        
    try:
        await asyncio.gather(*tasks)
    finally:
        logger.info("Docling client closing ...")
        await embedding_client.close()