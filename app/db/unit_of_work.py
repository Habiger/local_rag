from functools import cached_property
from contextlib import asynccontextmanager
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.db.repositories.pdf_repository import PDFRepository
from app.db.repositories.converted_page_repository import ConvertedPageRepository
from app.db.repositories.converted_pdf_repository import ConvertedPDFRepository
from app.db.repositories.config_repository import ConfigRepository
from app.db.repositories.indexed_pdf_repository import PdfPipelineRepository
from app.db.repositories.chunk_repository import ChunkRepository
from app.db.repositories.embedding_repository import EmbeddingRepository
from app.db.repositories.retrieval_repository import RetrievalRepository


class LazyWorkContext:
    """
    Registry for database repositories.
    
    Uses Just-In-Time (JIT) instantiation via @cached_property to ensure
    high-concurrency workers only allocate memory/CPU for the specific 
    repositories they require during a transaction.
    """

    def __init__(self, conn: AsyncConnection) -> None:
        self.conn = conn

    @cached_property
    def pdfs(self) -> PDFRepository:
        return PDFRepository(self.conn)

    @cached_property
    def pages(self) -> ConvertedPageRepository:
        return ConvertedPageRepository(self.conn)

    @cached_property
    def converted_pdfs(self) -> ConvertedPDFRepository:
        return ConvertedPDFRepository(self.conn)

    @cached_property
    def configs(self) -> ConfigRepository:
        return ConfigRepository(self.conn)

    @cached_property
    def indexed_pdfs(self) -> PdfPipelineRepository:
        return PdfPipelineRepository(self.conn)

    @cached_property
    def chunks(self) -> ChunkRepository:
        return ChunkRepository(self.conn)

    @cached_property
    def embeddings(self) -> EmbeddingRepository:
        return EmbeddingRepository(self.conn)

    @cached_property
    def retrieval(self) -> RetrievalRepository:
        return RetrievalRepository(self.conn)


@asynccontextmanager
async def unit_of_work(pool: AsyncConnectionPool):
    """
    Manages connection lifecycle and transaction scope.
    Guarantees the connection is returned to the pool regardless of errors.
    """
    # 1. Use the pool's native context manager for guaranteed safety -> it has a `finally: self.putconn(conn)`
    async with pool.connection() as conn:
        try:
            # 2. Yield the registry with the injected connection
            yield LazyWorkContext(conn)
            
            # 3. If no exceptions occur in the caller's block, commit
            await conn.commit()
            
        except Exception:
            # 4. If any error happens, rollback to ensure atomicity
            await conn.rollback()
            raise