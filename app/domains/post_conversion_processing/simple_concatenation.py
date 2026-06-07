from typing import Literal
from docling_core.types.doc.document import DoclingDocument, RefItem, DocItem

from app.domains.post_conversion_processing.base import BasePostProcessor, BasePostProcessorOptions, PostProcessingStrategy


class SimpleConcatenatorOptions(BasePostProcessorOptions):
    strategy: Literal[PostProcessingStrategy.SIMPLE_CONCATENATION] = PostProcessingStrategy.SIMPLE_CONCATENATION # type: ignore

class SimpleConcatenator(BasePostProcessor):
    def __init__(self, options: SimpleConcatenatorOptions = SimpleConcatenatorOptions(strategy=PostProcessingStrategy.SIMPLE_CONCATENATION)):
        self.options = options
        
    async def post_process(self, pages: list[DoclingDocument]) -> DoclingDocument:
        return DoclingDocument.concatenate(pages)