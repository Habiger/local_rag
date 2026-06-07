from typing import List
from pathlib import Path
from contextlib import asynccontextmanager
from psycopg_pool import AsyncConnectionPool

from fastapi import FastAPI, Depends, File, UploadFile, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config.logging import logger
from app.db.database import db
from app.services.pdf_service import PDFService
from app.services.pdf_acquisition_service import PDFAcquisitionService
from app.utils.tree_builder import build_file_tree
from app.schema.dtos import ConversionProgressAggregationResponse
from app.schema.dtos import ProcessDocumentsRequest
from app.db.unit_of_work import unit_of_work

from app.clients.docling_client_async import DoclingClient
from app.clients.embedding_client import EmbeddingClient
from app.config.settings import get_db_config, get_docling_config, get_llamacpp_config
from app.config.paths import PDF_STORAGE_DIR

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    
    PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ensured data directory exists at: {PDF_STORAGE_DIR}")

    print("Initializing Database Pool...")
    await db.setup(get_db_config())
    #await db.drop_schema()
    await db.create_schema() #TODO: remove when moving towards stable version
    yield
    # --- Shutdown ---
    # Close the pool cleanly when Uvicorn stops
    print("Closing Database Pool...")
    await db.teardown()

def get_db_pool() -> AsyncConnectionPool:
    """Dependency that provides the active database pool."""
    return db.pool

def get_docling_client() -> DoclingClient:
    return DoclingClient(get_docling_config())

def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient(get_llamacpp_config())

def get_pdf_service(pool: AsyncConnectionPool = Depends(get_db_pool)) -> PDFService:
    """Inject the pool into the service."""
    return PDFService(pool=pool)

def get_pdf_acquisition_service(pdf_service: PDFService = Depends(get_pdf_service)) -> PDFAcquisitionService:
    return PDFAcquisitionService(pdf_service=pdf_service)

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return 'Health check: Success!'

@app.get("/api/v1/health")
async def get_health_status(
    docling_client: DoclingClient = Depends(get_docling_client),
    embedding_client: EmbeddingClient = Depends(get_embedding_client)
):
    docling_is_healthy = await docling_client.is_healthy()
    embedding_is_healthy = await embedding_client.is_healthy()
    return {
        "backend": "online",
        "docling": "online" if docling_is_healthy else "offline",
        "embedding": "online" if embedding_is_healthy else "offline"
    }

@app.post("/api/v1/documents/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    paths: List[str] = Form(...),
    pdf_acquisition_service: PDFAcquisitionService = Depends(get_pdf_acquisition_service)
):
    if len(files) != len(paths):
        raise HTTPException(status_code=400, detail="Mismatched files and paths length.")

    uploaded = []
    skipped = []

    for file, original_path in zip(files, paths):
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            continue

        try:
            file_bytes = await file.read()
            pdf_name, is_new = await pdf_acquisition_service.acquire_from_bytes(
                file_bytes,
                original_filename=Path(file.filename).name,
                original_path=original_path
            )

            if is_new:
                uploaded.append({
                    "pdf_name": pdf_name,
                    "original_path": original_path
                })
            else:
                skipped.append({
                    "pdf_name": pdf_name,
                    "original_path": original_path
                })
        except Exception as e:
            logger.exception(
                f"Failed to store {file.filename}", 
                extra={
                    "extra":  {
                        "exception": str(e),
                    }
                }
            )
            raise HTTPException(status_code=500, detail=f"Failed to acquire pdf from bytes:  {file.filename}")

    return {
        "uploaded_count": len(uploaded),
        "skipped_count": len(skipped),
        "uploaded": uploaded,
        "skipped": skipped
    }

@app.get("/api/v1/documents/tree")
async def get_document_tree(pdf_service: PDFService = Depends(get_pdf_service)):
    try:
        pdfs = await pdf_service.get_all_pdfs() 
        
        tree = build_file_tree(pdfs)
        return {"tree": tree} 
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch document tree: {str(e)}")
    
@app.get("/api/v1/documents/progress", response_model=ConversionProgressAggregationResponse)
async def get_document_progress(pdf_service: PDFService = Depends(get_pdf_service)):
    """
    Returns an aggregated view of pipeline progress for all uploaded documents,
    including pagination conversion rates and vector embedding rates.
    """
    try:
        progress_data = await pdf_service.get_all_conversion_progress()
        return ConversionProgressAggregationResponse(documents=progress_data)
    except Exception as e:
        logger.exception(
            "Failed to fetch progress data", 
            extra={"extra": {"exception": str(e)}}
        )
        raise HTTPException(status_code=500, detail="Failed to fetch progress data.")
    


@app.post("/api/v1/documents/process")
async def start_processing(
    request: ProcessDocumentsRequest,
    pool: AsyncConnectionPool = Depends(get_db_pool)
):
    """
    Receives a list of PDF names and initiates their processing pipelines.
    """
    if not request.pdf_names:
        raise HTTPException(status_code=400, detail="No PDFs provided for processing.")

    started_count = 0
    try:
        async with unit_of_work(pool) as uow:
            for pdf_name in request.pdf_names:
                # This matches the signature of your PdfPipelineRepository.create method
                await uow.indexed_pdfs.create(
                    pdf_name=pdf_name,
                    pdf_indexing_config_id=request.pdf_indexing_config_id
                )
                started_count += 1
                
        return {"message": f"Successfully queued {started_count} documents for processing."}
    except Exception as e:
        logger.exception("Failed to start processing", extra={"extra": {"exception": str(e)}})
        raise HTTPException(status_code=500, detail="Database transaction failed while queueing documents.")