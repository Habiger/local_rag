from typing import Literal
from docling_core.types.doc.document import DoclingDocument, RefItem, DocItem

from app.domains.post_conversion_processing.base import BasePostProcessor, BasePostProcessorOptions, PostProcessingStrategy


class DummyOptions(BasePostProcessorOptions):
    strategy: Literal[PostProcessingStrategy.DUMMY_STRATEGY] = PostProcessingStrategy.DUMMY_STRATEGY # type: ignore

class DummyConcatenator(BasePostProcessor):
    def __init__(self, options: DummyOptions = DummyOptions(strategy=PostProcessingStrategy.DUMMY_STRATEGY)):
        self.options = options
        
    async def post_process(self, pages: list[DoclingDocument]) -> DoclingDocument:
        return DoclingDocument.concatenate(pages)