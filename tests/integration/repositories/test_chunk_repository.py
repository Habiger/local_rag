import json
import pytest
from pydantic import BaseModel

# Tell pytest we are using asyncio for all tests in this file
pytestmark = pytest.mark.asyncio

# ====================================================================
# DUMMY MODELS FOR TESTING
# ====================================================================

class DummyDocItem(BaseModel):
    """Mock representing the Pydantic DocItem model."""
    self_ref: str
    content: str
    
    def model_dump_json(self, **kwargs) -> str:
        return json.dumps({"self_ref": self.self_ref, "content": self.content})

class DummyChunk:
    """Mock representing the Chunk domain model."""
    def __init__(self, text: str, doc_items: list[DummyDocItem]):
        self.text = text
        self.doc_items = doc_items
        self.contained_doc_item_strings = [di.self_ref for di in doc_items]

# ====================================================================
# HELPERS
# ====================================================================

async def _seed_dependencies(
    uow, 
    pdf_name: str, 
    post_processing_config_id: int, 
    indexed_pdf_id: int
):
    """
    Seeds the required foreign key references to avoid constraint violations.
    Using uow.chunks.conn.cursor() allows us to run this without knowing 
    the exact repository names for the other domains.
    """
    chunk_config_id = 999
    indexing_config_id = 999
    
    async with uow.chunks.conn.cursor() as cur:
        # 1. PDF
        await cur.execute(
            """INSERT INTO pdf (pdf_name, original_path, page_count, status) 
               VALUES (%s, 'dummy/path.pdf', 1, 'UPLOADED') 
               ON CONFLICT DO NOTHING""", 
            (pdf_name,)
        )
        
        # 2. Post Processing Config
        await cur.execute(
            """INSERT INTO post_processing_config (post_processing_config_id, parameter) 
               VALUES (%s, '{"test_param": 1}') 
               ON CONFLICT DO NOTHING""", 
            (post_processing_config_id,)
        )
        
        # 3. Chunking Config
        await cur.execute(
            """INSERT INTO chunking_config (chunking_config_id, parameters) 
               VALUES (%s, '{"chunk_size": 100}') 
               ON CONFLICT DO NOTHING""", 
            (chunk_config_id,)
        )
        
        # 4. Indexing Config
        await cur.execute(
            """INSERT INTO pdf_indexing_config 
                 (pdf_indexing_config_id, post_processing_config_id, chunking_config_id, embedding_model) 
               VALUES (%s, %s, %s, 'test-embedding-model') 
               ON CONFLICT DO NOTHING""", 
            (indexing_config_id, post_processing_config_id, chunk_config_id)
        )
        
        # 5. Indexed PDF
        await cur.execute(
            """INSERT INTO indexed_pdf (indexed_pdf_id, pdf_name, pdf_indexing_config_id, status) 
               VALUES (%s, %s, %s, 'PROCESSING') 
               ON CONFLICT DO NOTHING""", 
            (indexed_pdf_id, pdf_name, indexing_config_id)
        )

# ====================================================================
# TESTS
# ====================================================================

async def test_batch_insert_returns_empty_list_for_no_chunks(uow):
    # Act
    # Assuming the repository is attached to uow as `uow.chunks`
    chunk_ids = await uow.chunks.batch_insert(
        indexed_pdf_id=1,
        post_processing_config_id=1,
        pdf_name="doesnt_exist.pdf",
        chunks=[]
    )
    
    # Assert
    assert chunk_ids == []

async def test_batch_insert_success(uow):
    # Arrange
    pdf_name = "test_doc_chunks.pdf"
    pp_config_id = 1
    indexed_pdf_id = 1
    
    await _seed_dependencies(uow, pdf_name, pp_config_id, indexed_pdf_id)
    
    doc_item_1 = DummyDocItem(self_ref="ref_1", content="Title Header")
    doc_item_2 = DummyDocItem(self_ref="ref_2", content="Paragraph text")
    
    # Chunk 1 has one doc_item, Chunk 2 has both.
    chunk_1 = DummyChunk(text="Introduction text here.", doc_items=[doc_item_1])
    chunk_2 = DummyChunk(text="More detailed text following the header.", doc_items=[doc_item_1, doc_item_2])
    
    chunks = [chunk_1, chunk_2]
    
    # Act
    chunk_ids = await uow.chunks.batch_insert(
        indexed_pdf_id=indexed_pdf_id,
        post_processing_config_id=pp_config_id,
        pdf_name=pdf_name,
        chunks=chunks
    )
    
    # Assert returns
    assert len(chunk_ids) == 2
    assert all(isinstance(cid, int) for cid in chunk_ids)
    
    # Assert Database State
    async with uow.chunks.conn.cursor() as cur:
        # Check chunks
        await cur.execute("SELECT chunk_id, chunk_text FROM chunk ORDER BY chunk_id")
        db_chunks = await cur.fetchall()
        assert len(db_chunks) == 2
        assert db_chunks[0][1] == "Introduction text here."
        assert db_chunks[1][1] == "More detailed text following the header."
        
        # Check doc_items
        await cur.execute("SELECT doc_item_ref, doc_item FROM doc_item ORDER BY doc_item_ref")
        db_doc_items = await cur.fetchall()
        assert len(db_doc_items) == 2
        assert db_doc_items[0][0] == "ref_1"
        assert db_doc_items[1][0] == "ref_2"
        # Verify JSONB storage
        item_data = json.loads(db_doc_items[0][1]) if isinstance(db_doc_items[0][1], str) else db_doc_items[0][1]
        assert item_data["content"] == "Title Header"
        
        # Check mappings
        await cur.execute("SELECT chunk_id, doc_item_id FROM chunk_doc_item_mapping")
        db_mappings = await cur.fetchall()
        # chunk 1 -> ref 1
        # chunk 2 -> ref 1
        # chunk 2 -> ref 2
        assert len(db_mappings) == 3

async def test_batch_insert_idempotent_doc_items(uow):
    """
    Tests the ON CONFLICT DO UPDATE behavior for doc items and
    ON CONFLICT DO NOTHING for mapping intersections.
    """
    # Arrange
    pdf_name = "test_idempotent.pdf"
    pp_config_id = 2
    indexed_pdf_id = 2
    
    await _seed_dependencies(uow, pdf_name, pp_config_id, indexed_pdf_id)
    
    # First batch
    item_v1 = DummyDocItem(self_ref="shared_ref", content="Old Content")
    chunk_1 = DummyChunk(text="Chunk A", doc_items=[item_v1])
    
    await uow.chunks.batch_insert(
        indexed_pdf_id=indexed_pdf_id, post_processing_config_id=pp_config_id,
        pdf_name=pdf_name, chunks=[chunk_1]
    )
    
    # Second batch with updated content for the same ref
    item_v2 = DummyDocItem(self_ref="shared_ref", content="New Content")
    chunk_2 = DummyChunk(text="Chunk B", doc_items=[item_v2])
    
    # Act
    await uow.chunks.batch_insert(
        indexed_pdf_id=indexed_pdf_id, post_processing_config_id=pp_config_id,
        pdf_name=pdf_name, chunks=[chunk_2]
    )
    
    # Assert
    async with uow.chunks.conn.cursor() as cur:
        # Ensure we only have ONE doc_item and it was updated
        await cur.execute("SELECT doc_item_ref, doc_item FROM doc_item WHERE doc_item_ref = 'shared_ref'")
        items = await cur.fetchall()
        
        assert len(items) == 1
        item_data = json.loads(items[0][1]) if isinstance(items[0][1], str) else items[0][1] #TODO decide on ONE way to deal with jsonb data
        assert item_data["content"] == "New Content"  # The ON CONFLICT DO UPDATE worked
        
        # Ensure mappings exist for both chunks to this single doc_item
        await cur.execute("SELECT chunk_id FROM chunk_doc_item_mapping")
        mappings = await cur.fetchall()
        assert len(mappings) == 2