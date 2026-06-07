import shutil
import logging
import aiofiles

from pathlib import Path
from typing import Tuple
from pypdf import PdfReader

from app.config.paths import PDF_STORAGE_DIR
from app.services.pdf_service import PDFService

logger = logging.getLogger(__name__)


class PDFAcquisitionService:
    def __init__(self, pdf_service: PDFService):
        self.pdf_service = pdf_service

    async def _ensure_data_dir(self) -> None:
        PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    async def acquire_from_path(self, file_path: Path) -> Tuple[str, bool]:
        """
        Used for local dev / CLI ingestion.
        Stores the PDF under its original filename in the data/ directory.
        If a PDF with that name already exists, skips and logs.

        Returns:
            (pdf_name, is_new) — is_new is False if the file was skipped.
        """
        await self._ensure_data_dir()

        pdf_name = file_path.name

        if not pdf_name.lower().endswith(".pdf"):
            raise ValueError(f"File '{file_path.name}' is not a PDF")

        exists_in_db = await self.pdf_service.exists(pdf_name)
        if exists_in_db:
            logger.info("PDF '%s' already exists, skipping (treated as identical)", pdf_name)
            return pdf_name, False

        target_path = PDF_STORAGE_DIR / pdf_name
        shutil.copy(file_path, target_path)

        page_count = self._get_page_count(target_path)
        await self.pdf_service.register_pdf(
            pdf_name=pdf_name, 
            original_path=str(file_path), 
            page_count=page_count
        )

        return pdf_name, True

    async def acquire_from_bytes(
        self, file_bytes: bytes, original_filename: str, original_path: str
    ) -> Tuple[str, bool]:
        """
        Receives PDF bytes and stores under the original filename in data/.
        If a PDF with that name already exists, skips and logs.

        Args:
            file_bytes: raw PDF content
            original_filename: the basename (e.g. "report.pdf")
            original_path: the full user-facing path for tree reconstruction

        Returns:
            (pdf_name, is_new) — is_new is False if the file was skipped.
        """
        await self._ensure_data_dir()

        pdf_name = original_filename

        if not pdf_name.lower().endswith(".pdf"):
            raise ValueError(f"File '{original_filename}' is not a PDF")

        exists_in_db = await self.pdf_service.exists(pdf_name)
        if exists_in_db:
            logger.info("PDF '%s' already exists, skipping (treated as identical)", pdf_name)
            return pdf_name, False

        target_path = PDF_STORAGE_DIR / pdf_name

        async with aiofiles.open(target_path, "wb") as f:
            await f.write(file_bytes)

        page_count = self._get_page_count(target_path)

        await self.pdf_service.register_pdf(
            pdf_name=pdf_name,
            original_path=original_path,
            page_count=page_count,
        )

        return pdf_name, True

    def _get_page_count(self, path: Path) -> int:
        reader = PdfReader(str(path))
        return len(reader.pages)
