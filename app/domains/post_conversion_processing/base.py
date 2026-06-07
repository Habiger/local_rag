from abc import ABC, abstractmethod
from pydantic import BaseModel, ConfigDict
from dataclasses import dataclass
from enum import Enum

from docling_core.types.doc.document import DoclingDocument


class PostProcessingStrategy(str, Enum):
    SIMPLE_CONCATENATION = "simple_concatenation"
    DUMMY_STRATEGY = "dummy_strategy"
    

class BasePostProcessorOptions(BaseModel, ABC):
    model_config = ConfigDict(extra='forbid')
    strategy: PostProcessingStrategy

class BasePostProcessor(ABC):
    """Base class for all post processors."""
    def __init__(self, options: BasePostProcessorOptions):
        self.options = options
    
    @abstractmethod
    async def post_process(self, pages: list[DoclingDocument]) -> DoclingDocument:
        raise NotImplementedError()

