import asyncio

from app.services.pipeline_service import PipelineService
from app.config.logging import logger

WAITING_TIME_POSTPROCESSING_WORKER = 5

async def postprocessing_worker(
    service: PipelineService
    ) -> None:
    while True:
        # Claim Pdf
        try:
            a_job_has_been_found = await service.process_next_post_processing_job()
            if not a_job_has_been_found:
                await asyncio.sleep(WAITING_TIME_POSTPROCESSING_WORKER)
                continue
        except Exception as e:
            logger.error(f"Error while processing post processing job: {e}")
