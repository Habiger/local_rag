from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typing import Generator
from app.services.pdf_acquisition_service import PDFAcquisitionService

@pytest.fixture
def mock_pdf_service():
    return AsyncMock()


@pytest.fixture
def acquisition_service(mock_pdf_service) -> Generator[PDFAcquisitionService, None, None]:
    with patch.object(PDFAcquisitionService, "_ensure_data_dir", new=AsyncMock()):
        yield PDFAcquisitionService(mock_pdf_service)


@pytest.fixture
def storage_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """
    Centralized fixture to handle the patching of PDF_STORAGE_DIR.
    Creates a 'data' directory in the temporary path and patches the 
    service to use it.
    """
    target_dir = tmp_path / "data"
    target_dir.mkdir()
    with patch("app.services.pdf_acquisition_service.PDF_STORAGE_DIR", new=target_dir):
        yield target_dir


# ---------------------------------------------------------------------------
# acquire_from_bytes — happy path
# ---------------------------------------------------------------------------

async def test_acquire_from_bytes_new_file(
    acquisition_service: PDFAcquisitionService, mock_pdf_service: AsyncMock, storage_dir: Path
):
    mock_pdf_service.exists.return_value = False

    fake_pdf_bytes = b"%PDF-1.4 fake content"
    filename = "report.pdf"
    original_path = "/home/user/Downloads/report.pdf"

    target_file = storage_dir / filename

    with patch.object(acquisition_service, "_get_page_count", return_value=5):
        pdf_name, is_new = await acquisition_service.acquire_from_bytes(
            fake_pdf_bytes, filename, original_path
        )

    assert pdf_name == filename
    assert is_new is True

    assert target_file.read_bytes() == fake_pdf_bytes

    mock_pdf_service.exists.assert_awaited_once_with(filename)
    mock_pdf_service.register_pdf.assert_awaited_once_with(
        pdf_name=filename, page_count=5, original_path=original_path
    )


# ---------------------------------------------------------------------------
# acquire_from_bytes — duplicate detected
# ---------------------------------------------------------------------------

async def test_acquire_from_bytes_duplicate(
    acquisition_service: PDFAcquisitionService, mock_pdf_service: AsyncMock
):
    mock_pdf_service.exists.return_value = True

    filename = "report.pdf"
    original_path = "/home/user/Downloads/report.pdf"

    # No patch needed here; the service returns before touching the storage directory
    pdf_name, is_new = await acquisition_service.acquire_from_bytes(
        b"%PDF-1.4", filename, original_path
    )

    assert pdf_name == filename
    assert is_new is False

    mock_pdf_service.exists.assert_awaited_once_with(filename)
    mock_pdf_service.register_pdf.assert_not_called()


# ---------------------------------------------------------------------------
# acquire_from_bytes — non-PDF extension raises
# ---------------------------------------------------------------------------

async def test_acquire_from_bytes_non_pdf_raises(
    acquisition_service: PDFAcquisitionService, mock_pdf_service: AsyncMock
):
    with pytest.raises(ValueError, match="is not a PDF"):
        await acquisition_service.acquire_from_bytes(
            b"content", "readme.txt", "/some/path/readme.txt"
        )

    mock_pdf_service.exists.assert_not_called()


# ---------------------------------------------------------------------------
# acquire_from_path — happy path
# ---------------------------------------------------------------------------

async def test_acquire_from_path_new_file(
    acquisition_service: PDFAcquisitionService, mock_pdf_service: AsyncMock, tmp_path: Path, storage_dir: Path
):
    mock_pdf_service.exists.return_value = False

    source_dir = tmp_path / "source"
    source_dir.mkdir()
    
    source_file = source_dir / "source.pdf"
    source_file.write_bytes(b"%PDF-1.4 fake")

    with patch.object(acquisition_service, "_get_page_count", return_value=3):
        pdf_name, is_new = await acquisition_service.acquire_from_path(source_file)

    assert pdf_name == "source.pdf"
    assert is_new is True

    target_file = storage_dir / "source.pdf"
    assert target_file.read_bytes() == b"%PDF-1.4 fake"

    mock_pdf_service.exists.assert_awaited_once_with("source.pdf")
    mock_pdf_service.register_pdf.assert_awaited_once_with(
        pdf_name="source.pdf", original_path=str(source_file), page_count=3,
    )


# ---------------------------------------------------------------------------
# acquire_from_path — duplicate detected
# ---------------------------------------------------------------------------

async def test_acquire_from_path_duplicate(
    acquisition_service: PDFAcquisitionService, mock_pdf_service: AsyncMock, tmp_path: Path
):
    mock_pdf_service.exists.return_value = True

    source_file = tmp_path / "existing.pdf"
    source_file.write_bytes(b"%PDF-1.4")

    # No patch needed here either due to the early return
    pdf_name, is_new = await acquisition_service.acquire_from_path(source_file)

    assert pdf_name == "existing.pdf"
    assert is_new is False

    mock_pdf_service.exists.assert_awaited_once_with("existing.pdf")
    mock_pdf_service.register_pdf.assert_not_called()


# ---------------------------------------------------------------------------
# acquire_from_path — non-PDF extension raises
# ---------------------------------------------------------------------------

async def test_acquire_from_path_non_pdf_raises(
    acquisition_service: PDFAcquisitionService, tmp_path: Path
):
    bad_file = tmp_path / "notes.txt"
    bad_file.write_bytes(b"not a pdf")

    with pytest.raises(ValueError, match="is not a PDF"):
        await acquisition_service.acquire_from_path(bad_file)