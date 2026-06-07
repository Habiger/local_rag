import asyncio
from app.config.logging import logger
from app.services.embedding_service import EmbeddingService

async def embedding_completion_worker(
    service: EmbeddingService,
    poll_interval_seconds: int = 5,
):
    while True:
        try:
            await service.check_and_update_completed_pdfs(limit=10)
            await asyncio.sleep(poll_interval_seconds)
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception(
                "Embedding completion worker crashed",
                extra={"extra": {"exception": str(e)}},
            )
            await asyncio.sleep(poll_interval_seconds)