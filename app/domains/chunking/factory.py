from app.domains.chunking.strategies.base import ChunkingStrategy, BaseChunker, BaseChunkerOptions
from app.domains.chunking.strategies.hybrid_chunker import (
    DoclingHybridChunker,
    DoclingHybridChunkerOptions,
)

CHUNKER_REGISTRY = {
    ChunkingStrategy.DOCLING_HYBRID: (
        DoclingHybridChunker,
        DoclingHybridChunkerOptions,
    ),
}

class ChunkerFactory:
    """Can be used to create Chunker instances during runtime as needed.
    """
    @staticmethod
    def create(data: dict | BaseChunkerOptions) -> BaseChunker:

        strategy_value = (
            data.strategy if isinstance(data, BaseChunkerOptions)
            else data["strategy"]
        )

        strategy = ChunkingStrategy(strategy_value)

        chunker_cls, chunker_options_cls = CHUNKER_REGISTRY[strategy]

        options = chunker_options_cls.model_validate(data)

        return chunker_cls(options)