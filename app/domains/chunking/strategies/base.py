from abc import ABC, abstractmethod
from dataclasses import dataclass
from pydantic import BaseModel, model_validator
from pathlib import Path
from enum import Enum

from docling_core.types.doc.document import DoclingDocument, RefItem, DocItem
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer

from app.schema.enums import EmbeddingModel

@dataclass
class Chunk:
    """
    Represents a chunk of text extracted from a document.

    Attributes:
        doc_items: List of string representations of RefItem references associated with this chunk.
        pages: List of page numbers where the chunk's content appears in the source document.
        text: The actual text content of the chunk.
    """
    doc_items: list[DocItem] # shall use RefItem str representation
    text: str
    
    @property
    def contained_doc_item_strings(self) -> list[str]:
        return [doc_item.self_ref for doc_item in self.doc_items]
    
MODELS_PATH = Path(__file__).parent.parent.parent.parent / "model_files" 

EMBEDDING_MODEL_PATH_MAPPING = {
    EmbeddingModel.QWEN3_EMBEDDING_06B_Q8: MODELS_PATH / "Qwen--Qwen3-Embedding-0.6B",
}
class ChunkingStrategy(str, Enum):
    DOCLING_HYBRID = "docling_hybrid"
    PAGEWISE = "pagewise"

class BaseChunkerOptions(BaseModel):
    max_tokens: int
    embedding_model: EmbeddingModel
    strategy: ChunkingStrategy

    @model_validator(mode="after")
    def validate_embedding_model_mapping(self) -> "BaseChunkerOptions":
        if self.embedding_model not in EMBEDDING_MODEL_PATH_MAPPING:
            available_models = ", ".join(
                model.value for model in EMBEDDING_MODEL_PATH_MAPPING
            )

            raise ValueError(
                f"No tokenizer path configured for embedding model "
                f"'{self.embedding_model.value}'. "
                f"Available models: [{available_models}]"
            )

        return self

    @property
    def tokenizer(self) -> HuggingFaceTokenizer:
        return HuggingFaceTokenizer.from_pretrained(
            EMBEDDING_MODEL_PATH_MAPPING[self.embedding_model],
            max_tokens=self.max_tokens
            )
        
class BaseChunker(ABC):
    """Base class for all chunkers."""
    def __init__(self, options: BaseChunkerOptions):
        self.options = options
    
    @abstractmethod
    async def chunk(self, doc: DoclingDocument) -> list[Chunk]:
        raise NotImplementedError()
    
    def count_tokens(self, text: str) -> int:
        return self.options.tokenizer.count_tokens(text)


