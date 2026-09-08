from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from app.config.settings import DBConfig
from app.config.logging import logger
from app.db.models import Base

class Database:
    def __init__(self):
        self._engine = None
        self._session_factory = None

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("Database is not initialized. Call .setup() first.")
        return self._session_factory

    async def setup(self, config: DBConfig):
        # Assuming config.db_url is "postgresql+psycopg://user:pass@host/db"
        self._engine = create_async_engine(
            config.db_url,
            pool_size=10,
            max_overflow=40,
            echo=False, # Set to True to see SQL logs during dev
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine, 
            expire_on_commit=False,
            class_=AsyncSession
        )

    async def teardown(self):
        if self._engine:
            await self._engine.dispose()

    async def is_reachable(self) -> bool:
        try:
            async with self._engine.begin() as conn: # type: ignore
                await conn.execute(text("SELECT 1;"))
            logger.info("DB is reachable :)")
            return True
        except Exception as e:
            logger.error("DB is not reachable", extra={"extra": {"exception": str(e)}})
            return False

    async def create_schema(self):
        """Creates full DB schema based on ORM models."""
        async with self._engine.begin() as conn:  # type: ignore
            # Install vector extension first
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            # Auto-generate tables from your SQLAlchemy models
            await conn.run_sync(Base.metadata.create_all)

    async def drop_schema(self):
        async with self._engine.begin() as conn: # type: ignore
            await conn.run_sync(Base.metadata.drop_all)
            await conn.execute(text("DROP EXTENSION IF EXISTS vector CASCADE;"))

db = Database()