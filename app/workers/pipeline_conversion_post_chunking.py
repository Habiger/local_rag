import asyncio

from app.config.settings import get_db_config, docling_config
from app.config.logging import logger
from app.config.docling_options import convert_options_json

from app.db.database import db

#from app.pipeline.pdf_async_websocket_processing import TaskSubscriptionManager, submit_worker, event_consumer
from app.workers.conversion.consumer import docling_page_consumer
from app.workers.conversion.producer import  docling_page_producer
from app.workers.conversion.completion import conversion_completion_worker
from app.workers.post_conversion_processing.worker import postprocessing_worker
from app.workers.chunking.worker import chunking_worker

from app.clients.docling_client_async import DoclingClient

from app.services.conversion_service import ConversionService
from app.services.pipeline_service import PipelineService


async def pipeline():
    await db.setup(get_db_config())
    # Initializing clients
    docling_client = DoclingClient(
        docling_config,
        convert_options_json,
    )
    conversion_service = ConversionService(db.pool, docling_client)
    indexing_service = PipelineService(db.pool)
    
    # PAGE CONVERSION
    page_queue = asyncio.Queue(maxsize=1000)
    NO_DOCLING_PAGE_PRODUCER = 2
    NO_DOCLING_PAGE_CONSUMER = 10
    NO_DOCLING_PAGE_COMPLETION = 1
    tasks = []
    for _ in range(NO_DOCLING_PAGE_PRODUCER):
        tasks.append(
            asyncio.create_task(
                docling_page_producer(conversion_service, page_queue)
            )
        )
    for _ in range(NO_DOCLING_PAGE_CONSUMER):
        tasks.append(
            asyncio.create_task(
                docling_page_consumer(conversion_service, page_queue)
            )
        )
    for _ in range(NO_DOCLING_PAGE_COMPLETION):
        tasks.append(
            asyncio.create_task(
                conversion_completion_worker(conversion_service)
            )
        )
        
    # Post Processing
    NO_POST_PROCESSING_WORKER = 1

    for _ in range(NO_POST_PROCESSING_WORKER):
        tasks.append(
            asyncio.create_task(
                postprocessing_worker(indexing_service)
            )
        )

    # Chunking
    NO_CHUNKING_WORKER = 1

    for _ in range(NO_CHUNKING_WORKER):
        tasks.append(
            asyncio.create_task(
                chunking_worker(indexing_service)
            )
        )
    
    try:
        await asyncio.gather(*tasks)
    finally:
        logger.info("Docling client closing ...")
        await docling_client.close()