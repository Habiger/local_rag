from enum import Enum

class EmbeddingModel(str, Enum):
    QWEN3_EMBEDDING_06B_Q8 = "Qwen3-Embedding-0.6B-Q8"
    
class PDFConversionStatus(str, Enum):
    UPLOADED = "uploaded"
    CLAIMED_FOR_PAGEWISE_CONVERSION = "claimed_for_pagewise_conversion"
    PAGEWISE_CONVERSION_FINISHED = "pagewise_conversion_finished"
    FAILED = "failed"

class PageConversionTaskStatus(str, Enum):
    RETRYING = "retrying"
    FAILED = "failed"
    SUCCESS = "success"

class EmbeddingTaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    RETRY = "retry"
    FAILED = "failed"


class PdfPipelineStatus(str, Enum):
    PENDING = "pending"
    PAGE_CONVERSION_IN_PROGRESS = "conversion_in_progress"
    PAGE_CONVERSION_FINISHED = "conversion_finished"
    POST_PROCESSING_IN_PROGRESS = "post_processing_in_progress"
    POST_PROCESSING_FINISHED = "post_processing_finished"
    CHUNKING_IN_PROGRESS = "chunking_in_progress"
    CHUNKING_FINISHED = "chunking_finished"
    EMBEDDING_IN_PROGRESS = "embedding_in_progress"
    EMBEDDING_FINISHED = "embedding_finished"
    FAILED = "failed"