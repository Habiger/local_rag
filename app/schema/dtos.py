from pydantic import BaseModel, Field, computed_field
from typing import List, Optional
from app.schema.enums import PDFConversionStatus, PdfPipelineStatus

class DoclingConversionProgressDTO(BaseModel):
    pdf_name: str
    conversion_status: PDFConversionStatus
    total_pages: int
    success_pages: int
    failed_pages: int

    @computed_field
    def conversion_percentage(self) -> float:
        if self.total_pages == 0: 
            return 0.0
        return round((self.success_pages / self.total_pages) * 100, 2)


class ConversionProgressAggregationResponse(BaseModel):
    documents: List[DoclingConversionProgressDTO]
    
class ProcessDocumentsRequest(BaseModel):
    pdf_names: List[str]
    pdf_indexing_config_id: int = 1  # Assuming a default config ID of 1 exists for now