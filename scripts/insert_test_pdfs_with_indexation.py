import asyncio
import sys
from pathlib import Path

from app.db.database import Database
from app.config.settings import get_db_config
from app.schema.enums import PDFConversionStatus
from app.domains.chunking.strategies.hybrid_chunker import DoclingHybridChunkerOptions
from app.domains.post_conversion_processing.simple_concatenation import (
    SimpleConcatenatorOptions
)
from app.domains.core_models import EmbeddingModel
from app.domains.chunking.strategies.base import ChunkingStrategy
from app.domains.post_conversion_processing.base import PostProcessingStrategy

from app.services.pdf_acquisition_service import PDFAcquisitionService
from app.services.pdf_service import PDFService
from app.services.pipeline_service import PipelineService
# ============================================================
# SEED PDFs
# ============================================================

async def seed_test_pdfs(
    pdf_aquisition_service: PDFAcquisitionService,
    pdf_folder: str,
    reset: bool = False,
):
    """
    Seeds the database with PDFs from a folder for pipeline testing.
    """

    folder = Path(pdf_folder)

    if not folder.exists():
        raise ValueError(f"Folder does not exist: {pdf_folder}")

    pdf_files = list(folder.glob("*.pdf"))

    if not pdf_files:
        raise ValueError(f"No PDFs found in {pdf_folder}")

    print(f"Found {len(pdf_files)} PDFs")

    for pdf_path in pdf_files:
        pdf_name = pdf_path.name

        try:
            if reset:
                pdf_name_result, is_new = await pdf_aquisition_service.acquire_from_path(pdf_path)
                if is_new:
                    print(f"Seeded PDF: {pdf_name}")
                else:
                    print(f"Skipped (exists): {pdf_name}")
            else:
                raise RuntimeError("not implemented yet")

        except Exception as e:
            print(f"Failed to seed {pdf_name}: {e}")


# ============================================================
# SEED INDEXED PDFs (NEW)
# ============================================================

async def seed_indexed_pdfs(
    pdf_service: PDFService,
    indexing_service: PipelineService
):
    """
    Creates indexed_pdf entries for all PDFs in DB.
    """

    pdf_names = await pdf_service.get_pdfs_by_status(PDFConversionStatus.UPLOADED, limit=100)

    # default configs (safe fallbacks for testing)
    embedding_model = EmbeddingModel.QWEN3_EMBEDDING_06B_Q8
    chunking_options = DoclingHybridChunkerOptions(
        max_tokens=8192, 
        embedding_model=embedding_model, 
        strategy=ChunkingStrategy.DOCLING_HYBRID)
    post_conversion_options = SimpleConcatenatorOptions(strategy=PostProcessingStrategy.SIMPLE_CONCATENATION)

    for pdf_name in pdf_names:
        try:
            indexed_pdf_id = await indexing_service.schedule_indexing(
                pdf_name=pdf_name,
                post_conversion_options=post_conversion_options,
                chunking_options=chunking_options,
                embedding_model=embedding_model,
            )

            print(f"Indexed PDF created: {pdf_name} -> {indexed_pdf_id}")

        except Exception as e:
            print(f"Failed to index {pdf_name}: {e}")


# ============================================================
# FULL RESET (DROP + RECREATE)
# ============================================================

async def complete_reset(pdf_folder):
    db = Database()
    await db.setup(get_db_config())
    pdf_service = PDFService(db.pool)
    pdf_aquisition_service = PDFAcquisitionService(pdf_service)
    indexing_service = PipelineService(db.pool)

    await db.is_reachable()

    print("Dropping schema...")
    await db.drop_schema()

    print("Creating schema...")
    await db.create_schema()

    print("Seeding PDFs...")

    await seed_test_pdfs(
        pdf_aquisition_service=pdf_aquisition_service,
        pdf_folder=pdf_folder,
        reset=True,
    )

    print("Seeding indexed PDFs...")

    await seed_indexed_pdfs(pdf_service, indexing_service)

    print("Done.")


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    pdf_folder_to_be_inserted = r"C:\Users\HydraJ\Desktop\test_folder_short"
    asyncio.run(complete_reset(pdf_folder_to_be_inserted))