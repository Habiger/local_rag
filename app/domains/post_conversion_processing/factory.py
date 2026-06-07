from typing import Union, Literal, List
from typing_extensions import Annotated
from pydantic import BaseModel, Field, ValidationError, TypeAdapter

from app.domains.post_conversion_processing.base import PostProcessingStrategy, BasePostProcessor, BasePostProcessorOptions
from app.domains.post_conversion_processing.simple_concatenation import SimpleConcatenator, SimpleConcatenatorOptions
from app.domains.post_conversion_processing.dummy import DummyOptions, DummyConcatenator

POST_PROCESSOR_REGISTRY = {
    PostProcessingStrategy.SIMPLE_CONCATENATION: (
        SimpleConcatenator
    ),
    PostProcessingStrategy.DUMMY_STRATEGY: (
        DummyConcatenator
    )
}

PostProcessorOptions = Annotated[
    Union[SimpleConcatenatorOptions, DummyOptions],
    Field(discriminator="strategy"),
]

class PostProcessorFactory:
    """Can be used to create PostProcessor instances during runtime as needed.
    """
    @staticmethod
    def create(config: dict | PostProcessorOptions) -> SimpleConcatenator | DummyConcatenator:
        
        options: PostProcessorOptions = TypeAdapter(PostProcessorOptions).validate_python(config)

        post_processor_cls = POST_PROCESSOR_REGISTRY[options.strategy]

        return post_processor_cls(options)