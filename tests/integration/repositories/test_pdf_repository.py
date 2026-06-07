import pytest
from app.schema.enums import PDFConversionStatus
from app.db.unit_of_work import LazyWorkContext
# Tell pytest we are using asyncio for all tests in this file
pytestmark = pytest.mark.asyncio

async def test_insert_and_exists(uow):
    # Act
    await uow.pdfs.insert(pdf_name="test_doc.pdf", original_path="/uploads/test_doc.pdf", page_count=10)
    
    # Assert
    exists = await uow.pdfs.exists("test_doc.pdf")
    does_not_exist = await uow.pdfs.exists("ghost_doc.pdf")
    
    assert exists is True
    assert does_not_exist is False

async def test_get_status_and_update(uow):
    # Arrange
    doc_name = "status_doc.pdf"
    await uow.pdfs.insert(pdf_name=doc_name, original_path="/uploads/status_doc.pdf", page_count=5)
    
    # Act & Assert - Check default status
    initial_status = await uow.pdfs.get_status(doc_name)
    assert initial_status == PDFConversionStatus.UPLOADED
    
    # Act - Update status
    # Note: Replace PROCESSING with your actual enum value if different
    await uow.pdfs.update_status(doc_name, PDFConversionStatus.CLAIMED_FOR_PAGEWISE_CONVERSION)
    
    # Assert - Verify update
    updated_status = await uow.pdfs.get_status(doc_name)
    assert updated_status == PDFConversionStatus.CLAIMED_FOR_PAGEWISE_CONVERSION

async def test_claim_skips_locked_rows(uow: LazyWorkContext):
    # Arrange
    doc_1 = "doc_1.pdf"
    doc_2 = "doc_2.pdf"
    await uow.pdfs.insert(pdf_name=doc_1, original_path="/uploads/doc_1.pdf", page_count=2)
    await uow.pdfs.insert(pdf_name=doc_2, original_path="/uploads/doc_2.pdf", page_count=4)
    
    # Act - Claim the first available UPLOADED document
    claimed_doc = await uow.pdfs.claim(
        from_status=PDFConversionStatus.UPLOADED,
        to_status=PDFConversionStatus.CLAIMED_FOR_PAGEWISE_CONVERSION
    )
    
    # Assert
    assert claimed_doc in [doc_1, doc_2]
    
    # Verify the claimed doc is now marked as processing
    status = await uow.pdfs.get_status(claimed_doc)
    assert status == PDFConversionStatus.CLAIMED_FOR_PAGEWISE_CONVERSION

    # Act - Claim the second document
    second_claimed_doc = await uow.pdfs.claim(
        from_status=PDFConversionStatus.UPLOADED,
        to_status=PDFConversionStatus.CLAIMED_FOR_PAGEWISE_CONVERSION
    )
    
    # Assert - It should grab the other document
    assert second_claimed_doc != claimed_doc
    assert second_claimed_doc in [doc_1, doc_2]