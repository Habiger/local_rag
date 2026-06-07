from docling_core.types.doc.document import DoclingDocument
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.doc_chunk import DocChunk

from app.domains.chunking.strategies.base import BaseChunker, BaseChunkerOptions, Chunk

class DoclingHybridChunkerOptions(BaseChunkerOptions):
    # docling specific options
    repeat_table_header: bool = True
    merge_peers: bool = True
    always_emit_headings: bool = True
    omit_header_on_overflow: bool = False

class DoclingHybridChunker(BaseChunker):
    def __init__(self, options: DoclingHybridChunkerOptions) -> None:
        self.options = options
        
    async def chunk(self, doc: DoclingDocument) -> list[Chunk]:
        chunker = HybridChunker(
            repeat_table_header=self.options.repeat_table_header,
            merge_peers=self.options.merge_peers,
            always_emit_headings=self.options.always_emit_headings,
            omit_header_on_overflow=self.options.omit_header_on_overflow,
            tokenizer=self.options.tokenizer
        )
        chunks = []
        for docling_chunk in chunker.chunk(dl_doc=doc):
            docling_chunk = DocChunk.model_validate(docling_chunk)
            # construct chunk string
            chunk_text = ""
            if docling_chunk.meta.headings:
                for level, heading in enumerate(docling_chunk.meta.headings):
                    chunk_text += f"{'#' * (level + 1)} {heading}\n\n"
            chunk_text += docling_chunk.text
            # create chunk object
            chunk = Chunk(
                doc_items=docling_chunk.meta.doc_items,
                text=chunk_text,
            )
            chunks.append(chunk)
        return chunks
    
    

    