from sqlalchemy import text # <-- Add this import
import pytest

from app.db.unit_of_work import unit_of_work, LazyWorkContext
from app.schema.enums import PageConversionTaskStatus
from docling_serve.datamodel.responses import ConvertDocumentResponse
from docling_jobkit.datamodel.result import ExportDocumentResponse
from docling.datamodel.base_models import ConversionStatus

# --- Helper Functions ---

async def insert_parent_pdf(uow: LazyWorkContext, pdf_name: str, page_count: int = 5):
    """
    Helper to satisfy the FOREIGN KEY constraint in converted_page.
    Inserts a dummy PDF record into the DB.
    """
    # Replaced uow.conn.execute with uow.session.execute and added text() wrapper
    await uow.session.execute(
        text("""
        INSERT INTO pdf (pdf_name, original_path, page_count, status)
        VALUES (:pdf_name, :original_path, :page_count, :status)
        ON CONFLICT (pdf_name) DO NOTHING;
        """),
        {
            "pdf_name": pdf_name,
            "original_path": f"/mock/path/to/{pdf_name}",
            "page_count": page_count,
            "status": "PROCESSING"
        }
    )

def create_dummy_conversion_response() -> ConvertDocumentResponse:
    """
    Creates a valid mock ConvertDocumentResponse based on its Pydantic schema.
    """
    # 1. Create the required document payload
    dummy_export = ExportDocumentResponse(
        filename="dummy_page.pdf",
        md_content="# Dummy Header\nThis is placeholder text for the test.",
        text_content="Dummy Header\nThis is placeholder text for the test."
        # json_content, html_content, and doctags_content are Optional
    )
    
    # 2. Build and return the main response
    return ConvertDocumentResponse(
        document=dummy_export,
        status=ConversionStatus.SUCCESS,
        processing_time=0.45,
        # errors and timings default to [] and {} respectively, so we can omit them
    )


# --- Tests ---

async def test_insert_and_get_pages(uow: LazyWorkContext):
    pdf_name = "test_insert.pdf"
    await insert_parent_pdf(uow, pdf_name)
    
    dummy_response = create_dummy_conversion_response()
    
    # 1. Test Insert
    await uow.pages.insert(pdf_name, page_number=1, conversion_result=dummy_response)
    
    # 2. Test Get
    pages = await uow.pages.get_pages(pdf_name)
    
    assert len(pages) == 1
    assert 1 in pages
    assert isinstance(pages[1], ConvertDocumentResponse)
    
    # 3. Test Upsert (Conflict Resolution)
    # Re-inserting the same page shouldn't throw an IntegrityError
    await uow.pages.insert(pdf_name, page_number=1, conversion_result=dummy_response)
    
    pages_after_upsert = await uow.pages.get_pages(pdf_name)
    assert len(pages_after_upsert) == 1  # Should still be 1


async def test_mark_failed_increments_retry_count_and_updates_status(uow: LazyWorkContext):
    pdf_name = "test_failed.pdf"
    await insert_parent_pdf(uow, pdf_name)
    
    # 1. First failure insert
    error_msg_1 = "Timeout occurred"
    await uow.pages.mark_failed(pdf_name, page_number=2, error_message=error_msg_1)
    
    # Assert state via direct DB query to bypass repository filters
    # Replaced uow.conn.cursor with uow.session.execute + mapping
    # Note: Added JOIN since converted_page now uses pdf_id instead of pdf_name
    result1 = await uow.session.execute(
        text("""
        SELECT cp.retry_count, cp.error_message, cp.status 
        FROM converted_page cp
        JOIN pdf p ON cp.pdf_id = p.pdf_id
        WHERE p.pdf_name = :pdf_name AND cp.page_number = 2
        """),
        {"pdf_name": pdf_name}
    )
    row = result1.mappings().one_or_none()
    
    assert row is not None
    assert row["retry_count"] == 1
    assert row["error_message"] == error_msg_1
    assert row["status"] == PageConversionTaskStatus.FAILED.value

    # 2. Second failure (Upsert/Retry logic)
    error_msg_2 = "OOM Exception"
    await uow.pages.mark_failed(pdf_name, page_number=2, error_message=error_msg_2)
    
    result2 = await uow.session.execute(
        text("""
        SELECT cp.retry_count, cp.error_message 
        FROM converted_page cp
        JOIN pdf p ON cp.pdf_id = p.pdf_id
        WHERE p.pdf_name = :pdf_name AND cp.page_number = 2
        """),
        {"pdf_name": pdf_name}
    )
    row2 = result2.mappings().one_or_none()

    assert row2 is not None
    assert row2["retry_count"] == 2
    assert row2["error_message"] == error_msg_2


async def test_count_pending_calculates_correctly(uow: LazyWorkContext):
    pdf_name = "test_pending.pdf"
    # PDF has 5 total pages
    await insert_parent_pdf(uow, pdf_name, page_count=5)
    
    # 1. Initial state (0 converted, 5 total)
    pending_initial = await uow.pages.count_pending(pdf_name)
    assert pending_initial == 5
    
    # 2. Add 2 SUCCESS pages
    dummy_response = create_dummy_conversion_response()
    await uow.pages.insert(pdf_name, page_number=1, conversion_result=dummy_response)
    await uow.pages.insert(pdf_name, page_number=2, conversion_result=dummy_response)
    
    pending_after_success = await uow.pages.count_pending(pdf_name)
    assert pending_after_success == 3  # (5 total - 2 success)
    
    # 3. Add 1 FAILED page (Failed pages shouldn't reduce the pending count)
    await uow.pages.mark_failed(pdf_name, page_number=3, error_message="Failed")
    
    pending_after_failure = await uow.pages.count_pending(pdf_name)
    assert pending_after_failure == 3
    
    # 4. Unknown PDF should gracefully return 0 pending pages
    assert await uow.pages.count_pending("non_existent.pdf") == 0


async def test_get_docling_conversion_progress(uow: LazyWorkContext):
    pdf1 = "progress_1.pdf"
    pdf2 = "progress_2.pdf"
    
    await insert_parent_pdf(uow, pdf1, page_count=3)
    await insert_parent_pdf(uow, pdf2, page_count=2)
    
    dummy_response = create_dummy_conversion_response()
    
    # Setup PDF 1: 2 Success, 1 Failed
    await uow.pages.insert(pdf1, page_number=1, conversion_result=dummy_response)
    await uow.pages.insert(pdf1, page_number=2, conversion_result=dummy_response)
    await uow.pages.mark_failed(pdf1, page_number=3, error_message="Failed")
    
    # Setup PDF 2: 0 Success, 2 Failed
    await uow.pages.mark_failed(pdf2, page_number=1, error_message="Failed")
    await uow.pages.mark_failed(pdf2, page_number=2, error_message="Failed")
    
    progress_rows = await uow.pages.get_docling_conversion_progress()
    
    # Ensure our inserted PDFs exist in the query response
    assert len(progress_rows) >= 2
    
    p1_stats = next(row for row in progress_rows if row["pdf_name"] == pdf1)
    assert p1_stats["total_pages"] == 3
    assert p1_stats["converted_pages"] == 2
    assert p1_stats["failed_pages"] == 1
    
    p2_stats = next(row for row in progress_rows if row["pdf_name"] == pdf2)
    assert p2_stats["total_pages"] == 2
    assert p2_stats["converted_pages"] == 0
    assert p2_stats["failed_pages"] == 2