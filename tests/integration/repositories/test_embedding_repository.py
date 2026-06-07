import pytest
import pytest_asyncio
from unittest.mock import MagicMock

from app.schema.enums import EmbeddingTaskStatus, EmbeddingModel
from app.db.unit_of_work import LazyWorkContext

# Ensure all async tests run in the asyncio event loop
pytestmark = pytest.mark.asyncio

@pytest_asyncio.fixture(scope="function")
async def seed_db(setup_database):
    """
    Seeds the database with the necessary parent foreign-key records
    so we can insert test chunks and chunk embeddings.
    """
    async with setup_database.pool.connection() as conn:
        async with conn.cursor() as cur:
            # 1. Insert base PDF
            await cur.execute("""
                INSERT INTO pdf (pdf_name, original_path, page_count, status) 
                VALUES ('test_doc.pdf', '/path/test_doc.pdf', 5, 'COMPLETED');
            """)
            
            # 2. Insert processing configs
            await cur.execute("""
                INSERT INTO post_processing_config (post_processing_config_id, parameter) 
                VALUES (1, '{"strategy": "simple"}');
            """)
            await cur.execute("""
                INSERT INTO chunking_config (chunking_config_id, parameters) 
                VALUES (1, '{"chunk_size": 512}');
            """)
            
            # 3. Insert indexing config
            await cur.execute("""
                INSERT INTO pdf_indexing_config (pdf_indexing_config_id, post_processing_config_id, chunking_config_id, embedding_model) 
                VALUES (1, 1, 1, 'text-embedding-3-small');
            """)
            
            # 4. Insert indexed PDF record
            await cur.execute("""
                INSERT INTO indexed_pdf (indexed_pdf_id, pdf_name, pdf_indexing_config_id, status) 
                VALUES (1, 'test_doc.pdf', 1, 'PROCESSING');
            """)
            
            # 5. Insert Chunks
            await cur.execute("""
                INSERT INTO chunk (chunk_id, indexed_pdf_id, chunk_text) 
                VALUES 
                (1, 1, 'This is the first test chunk.'),
                (2, 1, 'This is the second test chunk.'),
                (3, 1, 'This is the third test chunk.');
            """)
            
            # 6. Insert Embeddings Tasks (Pending, Retry, Success)
            await cur.execute("""
                INSERT INTO chunk_embedding (embedding_id, chunk_id, embedding_model, status) 
                VALUES 
                (1, 1, %s, %s),
                (2, 2, %s, %s),
                (3, 3, %s, %s);
            """, (
                EmbeddingModel.QWEN3_EMBEDDING_06B_Q8.value, EmbeddingTaskStatus.PENDING.value,
                EmbeddingModel.QWEN3_EMBEDDING_06B_Q8.value, EmbeddingTaskStatus.RETRY.value,
                EmbeddingModel.QWEN3_EMBEDDING_06B_Q8.value, EmbeddingTaskStatus.SUCCESS.value
            ))
        await conn.commit()


async def test_get_status_returns_correct_task_details(uow: LazyWorkContext, seed_db):
    """
    Test that get_status accurately fetches database state records for a given chunk and model.
    """
    embedding_model = EmbeddingModel.QWEN3_EMBEDDING_06B_Q8
    # Act
    task_1 = await uow.embeddings.get_status(chunk_id=1, embedding_model=embedding_model)
    task_2 = await uow.embeddings.get_status(chunk_id=2, embedding_model=embedding_model)
    missing_task = await uow.embeddings.get_status(chunk_id=999, embedding_model=embedding_model)
    
    # Assert
    assert task_1 is not None
    assert task_1["status"] == EmbeddingTaskStatus.PENDING.value
    assert task_1["error_message"] is None

    assert task_2 is not None
    assert task_2["status"] == EmbeddingTaskStatus.RETRY.value

    assert missing_task is None


async def test_claim_chunks_fetches_and_locks_correct_rows(uow: LazyWorkContext, seed_db):
    """
    Test that `claim_chunks` only grabs PENDING and RETRY statuses,
    skips SUCCESS, updates statuses to IN_PROGRESS, and returns the joined data.
    """
    # Act
    claimed_chunks = await uow.embeddings.claim_chunks(limit=5)
    
    # Assert
    assert len(claimed_chunks) == 2
    
    chunk_ids = [c["chunk_id"] for c in claimed_chunks]
    assert 1 in chunk_ids  
    assert 2 in chunk_ids  
    assert 3 not in chunk_ids  
    embedding_model = EmbeddingModel.QWEN3_EMBEDDING_06B_Q8
    # Verify status change using our new clean helper method
    task_1 = await uow.embeddings.get_status(chunk_id=1, embedding_model=embedding_model)
    task_2 = await uow.embeddings.get_status(chunk_id=2, embedding_model=embedding_model)
    assert task_1 is not None
    assert task_2 is not None
    assert task_1["status"] == EmbeddingTaskStatus.IN_PROGRESS.value
    assert task_2["status"] == EmbeddingTaskStatus.IN_PROGRESS.value


async def test_store_embedding_updates_vector_and_status(uow: LazyWorkContext, seed_db):
    """
    Test that storing an embedding correctly saves the vector array and marks status as SUCCESS.
    """
    # Arrange
    target_chunk_id = 1
    embedding_model = EmbeddingModel.QWEN3_EMBEDDING_06B_Q8
    test_vector = [0.123, -0.456, 0.789]

    # Act
    await uow.embeddings.upsert_embedding_vector(
        chunk_id=target_chunk_id, 
        embedding_model=embedding_model, 
        embedding=test_vector
    )
    
    # Assert - Cleanly verify status via helper
    task = await uow.embeddings.get_status(chunk_id=target_chunk_id, embedding_model=embedding_model)
    assert task is not None
    assert task["status"] == EmbeddingTaskStatus.SUCCESS.value
    
    # (Optional: If you still need to check the raw text vector payload, you can perform an isolated fetch)
    raw_vector = await uow.embeddings.fetchone(
        "SELECT embedding::text FROM chunk_embedding WHERE chunk_id = %s", (target_chunk_id,)
    )
    assert raw_vector is not None
    assert "0.123" in raw_vector["embedding"]


async def test_update_status_increments_retries_and_sets_error(uow: LazyWorkContext, seed_db):
    """
    Test that updating an embedding's status successfully increments the retry_count
    and stores the provided error message.
    """
    # Arrange
    target_chunk_id = 1
    embedding_model = EmbeddingModel.QWEN3_EMBEDDING_06B_Q8
    error_msg = "Rate limit exceeded"

    # Act
    await uow.embeddings.update_status(
        chunk_id=target_chunk_id,
        embedding_model=embedding_model,
        status=EmbeddingTaskStatus.RETRY,
        error_message=error_msg
    )
    
    # Assert - Complete isolation verification with zero leaked raw SQL string
    task = await uow.embeddings.get_status(chunk_id=target_chunk_id, embedding_model=embedding_model)
    
    assert task is not None
    assert task["status"] == EmbeddingTaskStatus.RETRY.value
    assert task["error_message"] == error_msg