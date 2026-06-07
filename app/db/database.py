from psycopg_pool import AsyncConnectionPool
from app.config.settings import DBConfig
from app.config.logging import logger


class Database:
    def __init__(self):
        self._pool = None

    @property
    def pool(self) -> AsyncConnectionPool:
        if self._pool is None:
            raise RuntimeError("Database pool is not initialized. Call .setup() first.")
        return self._pool  # type: ignore

    async def setup(self, config: DBConfig):
        self._pool = AsyncConnectionPool(
            conninfo=config.db_url,
            min_size=1,
            max_size=50,
            open=False,
        )
        await self.pool.open()

    async def teardown(self):
        if self._pool:
            await self._pool.close()

    async def is_reachable(self) -> bool:
        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1;")
                    await cur.fetchone()

            logger.info("DB is reachable :)")
            return True

        except Exception as e:
            logger.error("DB is not reachable", extra={"extra": {"exception": str(e)}})
            return False

    async def create_schema(self):
        """
        Creates full DB schema.
        Intended for:
        - integration tests
        - local dev bootstrap
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:

                await cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                await cur.execute("""
                CREATE TABLE IF NOT EXISTS pdf (
                    pdf_name TEXT PRIMARY KEY,
                    original_path TEXT NOT NULL, 
                    page_count INT NOT NULL,
                    uploaded_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    last_status_update TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                """)

                await cur.execute("""
                CREATE TABLE IF NOT EXISTS converted_page (
                    pdf_name TEXT NOT NULL,
                    page_number INT NOT NULL,
                    conversion_result JSONB,
                    status TEXT NOT NULL,
                    retry_count INT NOT NULL DEFAULT 0,
                    error_message TEXT,
                    last_retry TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (pdf_name) REFERENCES pdf (pdf_name) ON DELETE CASCADE,
                    PRIMARY KEY (pdf_name, page_number)
                );
                """)

                await cur.execute("""
                CREATE TABLE IF NOT EXISTS post_processing_config (
                    post_processing_config_id SERIAL PRIMARY KEY,
                    parameter JSONB UNIQUE
                );
                """)

                await cur.execute("""
                CREATE TABLE IF NOT EXISTS converted_pdf (
                    pdf_name TEXT NOT NULL,
                    post_processing_config_id INT NOT NULL,
                    docling_document JSONB NOT NULL,
                    PRIMARY KEY (pdf_name, post_processing_config_id),
                    FOREIGN KEY (pdf_name) REFERENCES pdf (pdf_name) ON DELETE CASCADE,
                    FOREIGN KEY (post_processing_config_id) REFERENCES post_processing_config (post_processing_config_id) ON DELETE CASCADE
                );
                """)

                await cur.execute("""
                CREATE TABLE IF NOT EXISTS chunking_config (
                    chunking_config_id SERIAL PRIMARY KEY,
                    parameters JSONB UNIQUE
                );
                """)

                await cur.execute("""
                CREATE TABLE IF NOT EXISTS pdf_indexing_config (
                    pdf_indexing_config_id SERIAL PRIMARY KEY,
                    post_processing_config_id INT NOT NULL,
                    chunking_config_id INT NOT NULL,
                    embedding_model TEXT NOT NULL,
                    FOREIGN KEY (post_processing_config_id) REFERENCES post_processing_config(post_processing_config_id) ON DELETE CASCADE,
                    FOREIGN KEY (chunking_config_id) REFERENCES chunking_config(chunking_config_id) ON DELETE CASCADE,
                    UNIQUE (
                        post_processing_config_id,
                        chunking_config_id,
                        embedding_model
                    )
                );
                """)

                await cur.execute("""
                CREATE TABLE IF NOT EXISTS indexed_pdf (
                    indexed_pdf_id SERIAL PRIMARY KEY,
                    pdf_name TEXT NOT NULL,
                    pdf_indexing_config_id INT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    FOREIGN KEY (pdf_name) REFERENCES pdf (pdf_name) ON DELETE CASCADE,
                    FOREIGN KEY (pdf_indexing_config_id) REFERENCES pdf_indexing_config(pdf_indexing_config_id) ON DELETE CASCADE,
                    UNIQUE (
                        pdf_name,
                        pdf_indexing_config_id
                    )
                );
                """)

                await cur.execute("""
                CREATE TABLE IF NOT EXISTS chunk (
                    chunk_id SERIAL PRIMARY KEY,
                    indexed_pdf_id INT NOT NULL,
                    chunk_text TEXT NOT NULL,
                    FOREIGN KEY (indexed_pdf_id) REFERENCES indexed_pdf(indexed_pdf_id) ON DELETE CASCADE
                );
                """)

                await cur.execute("""
                CREATE TABLE IF NOT EXISTS chunk_embedding (
                    embedding_id SERIAL PRIMARY KEY,
                    chunk_id INT NOT NULL,
                    embedding_model TEXT NOT NULL,
                    embedding VECTOR,
                    status TEXT NOT NULL, 
                    error_message TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    FOREIGN KEY (chunk_id) REFERENCES chunk(chunk_id) ON DELETE CASCADE,
                    UNIQUE (chunk_id, embedding_model)
                );
                """)

                await cur.execute("""
                CREATE TABLE IF NOT EXISTS doc_item (
                    doc_item_id SERIAL PRIMARY KEY,
                    pdf_name TEXT NOT NULL,
                    post_processing_config_id INT NOT NULL,
                    doc_item_ref TEXT NOT NULL,
                    doc_item JSONB NOT NULL,
                    UNIQUE(pdf_name, post_processing_config_id, doc_item_ref),
                    FOREIGN KEY (pdf_name) REFERENCES pdf (pdf_name) ON DELETE CASCADE,
                    FOREIGN KEY (post_processing_config_id) REFERENCES post_processing_config (post_processing_config_id) ON DELETE CASCADE
                );
                """)

                await cur.execute("""
                CREATE TABLE IF NOT EXISTS chunk_doc_item_mapping (
                    chunk_id INT NOT NULL,
                    doc_item_id INT NOT NULL,
                    PRIMARY KEY (chunk_id, doc_item_id),
                    FOREIGN KEY (chunk_id) REFERENCES chunk(chunk_id) ON DELETE CASCADE,
                    FOREIGN KEY (doc_item_id) REFERENCES doc_item(doc_item_id) ON DELETE CASCADE
                );
                """)

            await conn.commit()

    async def drop_schema(self):
        """
        Drops all tables and extensions created by create_schema().
        Safe for integration test teardown.
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:

                await cur.execute("""
                    DROP TABLE IF EXISTS chunk_doc_item_mapping CASCADE;
                    DROP TABLE IF EXISTS chunk_embedding CASCADE;
                    DROP TABLE IF EXISTS doc_item CASCADE;
                    DROP TABLE IF EXISTS chunk CASCADE;
                    DROP TABLE IF EXISTS indexed_pdf CASCADE;
                    DROP TABLE IF EXISTS pdf_indexing_config CASCADE;
                    DROP TABLE IF EXISTS converted_pdf CASCADE;
                    DROP TABLE IF EXISTS converted_page CASCADE;
                    DROP TABLE IF EXISTS chunking_config CASCADE;
                    DROP TABLE IF EXISTS post_processing_config CASCADE;
                    DROP TABLE IF EXISTS pdf CASCADE;

                    DROP EXTENSION IF EXISTS vector CASCADE;
                """)

            await conn.commit()

db = Database()
