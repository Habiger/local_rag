# app/services/indexing_service.py
import asyncio
from docling_core.types.doc.document import DoclingDocument
from psycopg_pool import AsyncConnectionPool

from app.config.logging import logger

from app.schema.enums import PdfPipelineStatus, EmbeddingModel

from app.db.database import db
from app.db.unit_of_work import unit_of_work

from app.domains.chunking.strategies.base import (
    BaseChunkerOptions,
)
from app.domains.post_conversion_processing.base import BasePostProcessor, BasePostProcessorOptions
from app.domains.post_conversion_processing.factory import PostProcessorFactory, PostProcessorOptions
from app.domains.chunking.factory import ChunkerFactory


class PipelineService:

    def __init__(self, pool: AsyncConnectionPool):
        self.pool = pool

    async def schedule_indexing(
        self,
        pdf_name: str,
        post_conversion_options: PostProcessorOptions,
        chunking_options: BaseChunkerOptions,
        embedding_model: EmbeddingModel,
    ) -> int:
        async with unit_of_work(self.pool) as uow:

            post_processing_id = await uow.configs.get_or_create_post_processing_config_id(
                post_conversion_options
            )

            chunking_id = await uow.configs.get_or_create_chunking_config_id(
                chunking_options
            )

            pdf_indexing_config_id = await uow.configs.get_or_create_pdf_indexing_config_id(
                post_processing_id,
                chunking_id,
                embedding_model.value,
            )

            indexed_pdf_id = await uow.indexed_pdfs.create(
                pdf_name=pdf_name,
                pdf_indexing_config_id=pdf_indexing_config_id,
            )

        logger.info(
            "Scheduled PDF indexing",
            extra={
                "extra": {
                    "pdf_name": pdf_name,
                    "indexed_pdf_id": indexed_pdf_id,
                }
            },
        )

        return indexed_pdf_id


    async def process_next_post_processing_job(self) -> bool:
        try:
            # First Step: Claim a pdf to be post processed and fetch its pages
            async with unit_of_work(self.pool) as uow:
                task = await uow.indexed_pdfs.claim(
                    from_status=PdfPipelineStatus.PENDING,
                    to_status=PdfPipelineStatus.POST_PROCESSING_IN_PROGRESS,
                )

                if not task:
                    return False

                logger.info(
                    "Claimed post-processing job",
                    extra={
                        "extra": {
                            "pdf_name": task.pdf_name,
                            "indexed_pdf_id": task.indexed_pdf_id,
                        }
                    },
                )

                pdf_pages = await uow.pages.get_pages(task.pdf_name)

            # Seconc Step: 
            docling_page_documents = [
                DoclingDocument.model_validate(v.document.json_content)
                for _, v in sorted(pdf_pages.items())
            ]

            post_processor = PostProcessorFactory.create(
                task.post_processing_options
            )

            docling_document = await post_processor.post_process(
                docling_page_documents
            )

            async with unit_of_work(self.pool) as uow:
                post_processing_id = await uow.configs.get_or_create_post_processing_config_id(
                    post_processor.options
                )

                await uow.converted_pdfs.upsert(
                    task.pdf_name,
                    post_processing_id,
                    docling_document,
                )

                await uow.indexed_pdfs.update_status(
                    task.indexed_pdf_id,
                    PdfPipelineStatus.POST_PROCESSING_FINISHED,
                )

            logger.info(
                "Post-processing completed",
                extra={
                    "extra": {
                        "pdf_name": task.pdf_name,
                        "indexed_pdf_id": task.indexed_pdf_id,
                    }
                },
            )

            return True

        except asyncio.CancelledError:
            raise

        except Exception as e:
            logger.exception(
                "Post-processing job failed",
                extra={
                    "extra": {
                        "exception": str(e),
                        "exception_type": type(e).__name__,
                    }
                },
            )
            raise

    async def process_next_chunking_job(self) -> bool:
        try:
            async with unit_of_work(self.pool) as uow:
                task = await uow.indexed_pdfs.claim(
                    from_status=PdfPipelineStatus.POST_PROCESSING_FINISHED,
                    to_status=PdfPipelineStatus.CHUNKING_IN_PROGRESS,
                )

                if not task:
                    return False

                logger.info(
                    "Claimed chunking job",
                    extra={
                        "extra": {
                            "pdf_name": task.pdf_name,
                            "indexed_pdf_id": task.indexed_pdf_id,
                        }
                    },
                )

                docling_document = await uow.converted_pdfs.get(
                    task.pdf_name,
                    task.post_processing_config_id,
                )

            if not docling_document:
                logger.error(
                    "Missing post-processed document for chunking",
                    extra={
                        "extra": {
                            "pdf_name": task.pdf_name,
                            "indexed_pdf_id": task.indexed_pdf_id,
                        }
                    },
                )
                raise RuntimeError(
                    f"Could not find docling document for {task.pdf_name}"
                )

            chunker = ChunkerFactory.create(task.chunking_options)

            chunks = await chunker.chunk(docling_document)

            async with unit_of_work(self.pool) as uow:
                await uow.chunks.batch_insert(
                    indexed_pdf_id=task.indexed_pdf_id,
                    post_processing_config_id=task.post_processing_config_id,
                    pdf_name=task.pdf_name,
                    chunks=chunks,
                )

                await uow.indexed_pdfs.update_status(
                    task.indexed_pdf_id,
                    PdfPipelineStatus.CHUNKING_FINISHED,
                )

            logger.info(
                "Chunking job completed",
                extra={
                    "extra": {
                        "pdf_name": task.pdf_name,
                        "indexed_pdf_id": task.indexed_pdf_id,
                        "chunk_count": len(chunks),
                    }
                },
            )

            return True

        except asyncio.CancelledError:
            raise

        except Exception as e:
            logger.exception(
                "Chunking job failed",
                extra={
                    "extra": {
                        "exception": str(e),
                        "exception_type": type(e).__name__,
                    }
                },
            )
            raise

    async def mark_embedding_finished(
        self,
        indexed_pdf_id: int,
    ):
        async with unit_of_work(self.pool) as uow:
            await uow.indexed_pdfs.update_status(
                indexed_pdf_id,
                PdfPipelineStatus.EMBEDDING_FINISHED,
            )

        logger.info(
            "Embedding stage completed",
            extra={
                "extra": {
                    "indexed_pdf_id": indexed_pdf_id,
                }
            },
        )