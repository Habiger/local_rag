from functools import cached_property
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
    
    Uses (fancy) Just-In-Time (JIT) instantiation via @cached_property to ensure
    high-concurrency workers only allocate memory/CPU for the specific 
    repositories they require during a transaction. (ChatGPT likes this)
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @cached_property
    def pdfs(self) -> PDFRepository:
        return PDFRepository(self.session)

    @cached_property
    def pages(self) -> ConvertedPageRepository:
        return ConvertedPageRepository(self.session)

    @cached_property
    def converted_pdfs(self) -> ConvertedPDFRepository:
        return ConvertedPDFRepository(self.session)

    @cached_property
    def configs(self) -> ConfigRepository:
        return ConfigRepository(self.session)

    @cached_property
    def indexed_pdfs(self) -> PdfPipelineRepository:
        return PdfPipelineRepository(self.session)

    @cached_property
    def chunks(self) -> ChunkRepository:
        return ChunkRepository(self.session)

    @cached_property
    def embeddings(self) -> EmbeddingRepository:
        return EmbeddingRepository(self.session)

    @cached_property
    def retrieval(self) -> RetrievalRepository:
        return RetrievalRepository(self.session)


@asynccontextmanager
async def unit_of_work(session_factory: async_sessionmaker[AsyncSession]):
    """
    Yields a LazyWorkContext wrapped in an SQLAlchemy transaction.
    """
    async with session_factory() as session:
        async with session.begin(): # This automatically handles commit/rollback
            yield LazyWorkContext(session)