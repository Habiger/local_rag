import pytest
from app.db.unit_of_work import LazyWorkContext
from app.schema.enums import EmbeddingModel
from app.domains.chunking.strategies.base import BaseChunkerOptions, ChunkingStrategy
from app.domains.post_conversion_processing.simple_concatenation import (
    SimpleConcatenatorOptions,
)
from app.domains.post_conversion_processing.base import PostProcessingStrategy

pytestmark = pytest.mark.asyncio


async def test_get_or_create_post_processing_config_id_creates_new(uow: LazyWorkContext):
    options = SimpleConcatenatorOptions(
        strategy=PostProcessingStrategy.SIMPLE_CONCATENATION,
    )

    config_id = await uow.configs.get_or_create_post_processing_config_id(options)

    assert isinstance(config_id, int)
    assert config_id > 0


async def test_get_or_create_post_processing_config_id_is_idempotent(uow: LazyWorkContext):
    options = SimpleConcatenatorOptions(
        strategy=PostProcessingStrategy.SIMPLE_CONCATENATION,
    )

    id_1 = await uow.configs.get_or_create_post_processing_config_id(options)
    id_2 = await uow.configs.get_or_create_post_processing_config_id(options)

    assert id_1 == id_2


async def test_get_or_create_chunking_config_id_creates_new(uow: LazyWorkContext):
    options = BaseChunkerOptions(
        max_tokens=8192,
        embedding_model=EmbeddingModel.QWEN3_EMBEDDING_06B_Q8,
        strategy=ChunkingStrategy.DOCLING_HYBRID,
    )

    config_id = await uow.configs.get_or_create_chunking_config_id(options)

    assert isinstance(config_id, int)
    assert config_id > 0


async def test_get_or_create_chunking_config_id_is_idempotent(uow: LazyWorkContext):
    options = BaseChunkerOptions(
        max_tokens=4096,
        embedding_model=EmbeddingModel.QWEN3_EMBEDDING_06B_Q8,
        strategy=ChunkingStrategy.PAGEWISE,
    )

    id_1 = await uow.configs.get_or_create_chunking_config_id(options)
    id_2 = await uow.configs.get_or_create_chunking_config_id(options)

    assert id_1 == id_2


async def test_get_or_create_chunking_config_id_different_options_returns_different_id(
    uow: LazyWorkContext,
):
    options_a = BaseChunkerOptions(
        max_tokens=512,
        embedding_model=EmbeddingModel.QWEN3_EMBEDDING_06B_Q8,
        strategy=ChunkingStrategy.DOCLING_HYBRID,
    )

    options_b = BaseChunkerOptions(
        max_tokens=1024,
        embedding_model=EmbeddingModel.QWEN3_EMBEDDING_06B_Q8,
        strategy=ChunkingStrategy.PAGEWISE,
    )

    id_a = await uow.configs.get_or_create_chunking_config_id(options_a)
    id_b = await uow.configs.get_or_create_chunking_config_id(options_b)

    assert id_a != id_b


async def test_get_or_create_pdf_indexing_config_id_creates_new(uow: LazyWorkContext):
    post_proc_options = SimpleConcatenatorOptions(
        strategy=PostProcessingStrategy.SIMPLE_CONCATENATION,
    )
    chunking_options = BaseChunkerOptions(
        max_tokens=8192,
        embedding_model=EmbeddingModel.QWEN3_EMBEDDING_06B_Q8,
        strategy=ChunkingStrategy.DOCLING_HYBRID,
    )

    post_proc_id = await uow.configs.get_or_create_post_processing_config_id(post_proc_options)
    chunking_id = await uow.configs.get_or_create_chunking_config_id(chunking_options)

    indexing_id = await uow.configs.get_or_create_pdf_indexing_config_id(
        post_processing_config_id=post_proc_id,
        chunking_config_id=chunking_id,
        embedding_model=EmbeddingModel.QWEN3_EMBEDDING_06B_Q8.value,
    )

    assert isinstance(indexing_id, int)
    assert indexing_id > 0


async def test_get_or_create_pdf_indexing_config_id_is_idempotent(uow: LazyWorkContext):
    post_proc_options = SimpleConcatenatorOptions(
        strategy=PostProcessingStrategy.SIMPLE_CONCATENATION,
    )
    chunking_options = BaseChunkerOptions(
        max_tokens=512,
        embedding_model=EmbeddingModel.QWEN3_EMBEDDING_06B_Q8,
        strategy=ChunkingStrategy.PAGEWISE,
    )

    post_proc_id = await uow.configs.get_or_create_post_processing_config_id(post_proc_options)
    chunking_id = await uow.configs.get_or_create_chunking_config_id(chunking_options)

    id_1 = await uow.configs.get_or_create_pdf_indexing_config_id(
        post_processing_config_id=post_proc_id,
        chunking_config_id=chunking_id,
        embedding_model=EmbeddingModel.QWEN3_EMBEDDING_06B_Q8.value,
    )
    id_2 = await uow.configs.get_or_create_pdf_indexing_config_id(
        post_processing_config_id=post_proc_id,
        chunking_config_id=chunking_id,
        embedding_model=EmbeddingModel.QWEN3_EMBEDDING_06B_Q8.value,
    )

    assert id_1 == id_2


async def test_full_pipeline_configs_are_created_and_linkable(uow: LazyWorkContext):
  post_proc_options = SimpleConcatenatorOptions(
      strategy=PostProcessingStrategy.SIMPLE_CONCATENATION,
  )
  chunking_options = BaseChunkerOptions(
      max_tokens=4096,
      embedding_model=EmbeddingModel.QWEN3_EMBEDDING_06B_Q8,
      strategy=ChunkingStrategy.DOCLING_HYBRID,
  )

  post_proc_id = await uow.configs.get_or_create_post_processing_config_id(post_proc_options)
  chunking_id = await uow.configs.get_or_create_chunking_config_id(chunking_options)
  indexing_id = await uow.configs.get_or_create_pdf_indexing_config_id(
      post_processing_config_id=post_proc_id,
      chunking_config_id=chunking_id,
      embedding_model=EmbeddingModel.QWEN3_EMBEDDING_06B_Q8.value,
  )

  assert isinstance(post_proc_id, int) and post_proc_id > 0
  assert isinstance(chunking_id, int) and chunking_id > 0
  assert isinstance(indexing_id, int) and indexing_id > 0
