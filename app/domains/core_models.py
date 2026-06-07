from dataclasses import dataclass, field
from typing import List
from enum import Enum
from pydantic import BaseModel

from app.schema.enums import EmbeddingModel

from app.schema.enums import PdfPipelineStatus

    
class ClaimedPdfTask(BaseModel):
    indexed_pdf_id: int
    pdf_name: str
    status: PdfPipelineStatus
    post_processing_config_id: int # ids are for making the db work easier
    chunking_config_id: int 
    post_processing_options: dict
    chunking_options: dict
    embedding_model: EmbeddingModel

@dataclass
class EmbeddedChunk:
    model: EmbeddingModel
    chunk_id: int 
    embedding_vectors: List[float] = field(default_factory=list)