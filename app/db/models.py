from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    ForeignKey,
    Integer,
    Text,
    DateTime,
    UniqueConstraint,
    func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

class Base(DeclarativeBase):
    pass


class PdfModel(Base):
    __tablename__ = "pdf"

    # Added surrogate primary key
    pdf_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Kept pdf_name, but made it unique instead of the primary key
    pdf_name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    last_status_update: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )


class ConvertedPageModel(Base):
    __tablename__ = "converted_page"
    __table_args__ = (
        UniqueConstraint("pdf_id", "page_number", name="uq_converted_page"),
    )

    # Added surrogate primary key
    converted_page_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Updated FK to reference pdf_id
    pdf_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pdf.pdf_id", ondelete="CASCADE"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    conversion_result: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    last_retry: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )


class PostProcessingConfigModel(Base):
    __tablename__ = "post_processing_config"

    post_processing_config_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parameter: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, unique=True)


class ConvertedPdfModel(Base):
    __tablename__ = "converted_pdf"
    __table_args__ = (
        UniqueConstraint("pdf_id", "post_processing_config_id", name="uq_converted_pdf"),
    )

    # Added surrogate primary key
    converted_pdf_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Updated FK to reference pdf_id
    pdf_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pdf.pdf_id", ondelete="CASCADE"), nullable=False
    )
    post_processing_config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("post_processing_config.post_processing_config_id", ondelete="CASCADE"), nullable=False
    )
    docling_document: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)


class ChunkingConfigModel(Base):
    __tablename__ = "chunking_config"

    chunking_config_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, unique=True)


class PdfIndexingConfigModel(Base):
    __tablename__ = "pdf_indexing_config"
    __table_args__ = (
        UniqueConstraint(
            "post_processing_config_id", "chunking_config_id", "embedding_model",
            name="uq_pdf_indexing_config"
        ),
    )

    pdf_indexing_config_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_processing_config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("post_processing_config.post_processing_config_id", ondelete="CASCADE"), nullable=False
    )
    chunking_config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chunking_config.chunking_config_id", ondelete="CASCADE"), nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)


class IndexedPdfModel(Base):
    __tablename__ = "indexed_pdf"
    __table_args__ = (
        # Updated UniqueConstraint to use pdf_id
        UniqueConstraint("pdf_id", "pdf_indexing_config_id", name="uq_indexed_pdf"),
    )

    indexed_pdf_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Updated FK to reference pdf_id
    pdf_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pdf.pdf_id", ondelete="CASCADE"), nullable=False
    )
    pdf_indexing_config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pdf_indexing_config.pdf_indexing_config_id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ChunkModel(Base):
    __tablename__ = "chunk"

    chunk_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indexed_pdf_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("indexed_pdf.indexed_pdf_id", ondelete="CASCADE"), nullable=False
    )
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)


class ChunkEmbeddingModel(Base):
    __tablename__ = "chunk_embedding"
    __table_args__ = (
        UniqueConstraint("chunk_id", "embedding_model", name="uq_chunk_embedding"),
    )

    embedding_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chunk.chunk_id", ondelete="CASCADE"), nullable=False
    )
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector) 
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DocItemModel(Base):
    __tablename__ = "doc_item"
    __table_args__ = (
        # Updated UniqueConstraint to use pdf_id
        UniqueConstraint("pdf_id", "post_processing_config_id", "doc_item_ref", name="uq_doc_item"),
    )

    doc_item_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Updated FK to reference pdf_id
    pdf_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pdf.pdf_id", ondelete="CASCADE"), nullable=False
    )
    post_processing_config_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("post_processing_config.post_processing_config_id", ondelete="CASCADE"), nullable=False
    )
    doc_item_ref: Mapped[str] = mapped_column(Text, nullable=False)
    doc_item: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)


class ChunkDocItemMappingModel(Base):
    __tablename__ = "chunk_doc_item_mapping"

    chunk_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chunk.chunk_id", ondelete="CASCADE"), primary_key=True
    )
    doc_item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("doc_item.doc_item_id", ondelete="CASCADE"), primary_key=True
    )