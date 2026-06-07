import pytest
from psycopg.rows import dict_row
from docling_core.types.doc.document import DoclingDocument
from app.db.unit_of_work import LazyWorkContext
from app.domains.post_conversion_processing.simple_concatenation import (
    SimpleConcatenatorOptions,
)
from app.domains.post_conversion_processing.base import PostProcessingStrategy

# --- Helper Functions ---

async def insert_parent_pdf(uow: LazyWorkContext, pdf_name: str) -> None:
    """Inserts a parent PDF record to satisfy foreign key constraints."""
    await uow.conn.execute(
        """
        INSERT INTO pdf (pdf_name, original_path, page_count, status)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (pdf_name) DO NOTHING;
        """,
        (pdf_name, f"/mock/path/{pdf_name}", 1, "PROCESSED")
    )


async def insert_post_processing_config(uow: LazyWorkContext, parameter_dict: dict) -> int:
    """
    Inserts a config record and returns the generated serial post_processing_config_id.
    """
    # Using fetchone to grab the SERIAL primary key via RETURNING clause
    options = SimpleConcatenatorOptions(
        strategy=PostProcessingStrategy.SIMPLE_CONCATENATION,
    )

    config_id = await uow.configs.get_or_create_post_processing_config_id(options)
    
    return config_id


def json_dump_helper(data: dict) -> str:
    """Helper to dump dict to string for explicit json insertion if needed."""
    import json
    return json.dumps(data)


def create_dummy_docling_document() -> DoclingDocument:
    """
    Generates a valid minimum structure for a DoclingDocument.
    Adjust the dictionary payloads if your specific docling_core version 
    demands stricter required baseline fields.
    """
    # Instantiating through valid dictionary schema ingestion
    minimal_doc_dict = {
        "schema_version": "1.0.0",
        "name": "dummy_doc",
        "elements": [],
        "pages": {}
    }
    return DoclingDocument.model_validate(minimal_doc_dict)


# --- Tests ---

async def test_upsert_and_get_docling_document_success(uow: LazyWorkContext):
    pdf_name = "sample_doc.pdf"
    await insert_parent_pdf(uow, pdf_name)
    
    config_id = await insert_post_processing_config(uow, {"chunk_size": 512, "overlap": 50})
    docling_doc = create_dummy_docling_document()

    # 1. Test clean Insert via repository
    await uow.converted_pdfs.upsert(
        pdf_name=pdf_name,
        post_processing_config_id=config_id,
        docling_document=docling_doc
    )

    # 2. Test Get via repository
    fetched_doc = await uow.converted_pdfs.get(pdf_name=pdf_name, post_processing_config_id=config_id)
    
    assert isinstance(fetched_doc, DoclingDocument)
    assert fetched_doc.name == docling_doc.name


async def test_upsert_handles_conflict_resolution_correctly(uow: LazyWorkContext):
    pdf_name = "upsert_conflict.pdf"
    await insert_parent_pdf(uow, pdf_name)
    
    config_id = await insert_post_processing_config(uow, {"strategy": "recursive"})
    
    doc1 = create_dummy_docling_document()
    doc1.name = "v1_document"
    
    doc2 = create_dummy_docling_document()
    doc2.name = "v2_updated_document"

    # 1. Primary insert
    await uow.converted_pdfs.upsert(pdf_name, config_id, doc1)
    
    # 2. Conflicting insert on same primary keys (pdf_name, post_processing_config_id)
    # This should trigger 'DO UPDATE SET docling_document=EXCLUDED.docling_document'
    await uow.converted_pdfs.upsert(pdf_name, config_id, doc2)

    # 3. Retrieve and confirm the updated data is present
    fetched_doc = await uow.converted_pdfs.get(pdf_name, config_id)
    assert fetched_doc.name == "v2_updated_document"


async def test_get_raises_runtime_error_when_not_found(uow: LazyWorkContext):
    invalid_pdf = "does_not_exist.pdf"
    fake_config_id = 99999
    
    # Asserting repository gracefully raises explicit business error handling
    with pytest.raises(RuntimeError) as exc_info:
        await uow.converted_pdfs.get(invalid_pdf, fake_config_id)
        
    assert f"Docling Document not found for pdf_name={invalid_pdf}" in str(exc_info.value)