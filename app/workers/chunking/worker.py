import asyncio

from app.services.pipeline_service import PipelineService

WAITING_TIME_CHUNKING_WORKER = 5

async def chunking_worker(
    service: PipelineService
    ) -> None:
    while True:
        # Claim Pdf
        a_job_has_been_found = await service.process_next_chunking_job()
        if not a_job_has_been_found:
            await asyncio.sleep(WAITING_TIME_CHUNKING_WORKER)
            continue
