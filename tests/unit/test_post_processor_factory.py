import pytest
from pydantic import ValidationError

from app.domains.post_conversion_processing.base import PostProcessingStrategy
from app.domains.post_conversion_processing.simple_concatenation import (
    SimpleConcatenator,
    SimpleConcatenatorOptions,
)

from app.domains.post_conversion_processing.factory import PostProcessorFactory


# -------------------------
# Fixtures / helpers
# -------------------------

def simple_config_dict():
    return {
        "strategy": PostProcessingStrategy.SIMPLE_CONCATENATION,
    }


def simple_options_model():
    return SimpleConcatenatorOptions(
        strategy=PostProcessingStrategy.SIMPLE_CONCATENATION,
    )


# -------------------------
# Tests
# -------------------------

def test_create_from_dict_returns_correct_processor():
    processor = PostProcessorFactory.create(simple_config_dict())

    assert isinstance(processor, SimpleConcatenator)


def test_create_from_model_returns_correct_processor():
    processor = PostProcessorFactory.create(simple_options_model())

    assert isinstance(processor, SimpleConcatenator)


def test_create_passes_options_to_processor():
    processor = PostProcessorFactory.create(simple_config_dict())

    assert isinstance(processor.options, SimpleConcatenatorOptions)


def test_invalid_strategy_raises_key_error():
    with pytest.raises(ValidationError):
        PostProcessorFactory.create(
            {
                "strategy": "non_existent_strategy"
            }
        )


def test_invalid_config_raises_validation_error():
    # missing required fields inside SimpleConcatenatorOptions
    with pytest.raises(Exception):  # can be narrowed to ValidationError if desired
        PostProcessorFactory.create(
            {
                "strategy": PostProcessingStrategy.SIMPLE_CONCATENATION,
                "invalid_field": "xxx",
            }
        )


def test_model_instance_is_accepted_directly():
    model = simple_options_model()

    processor = PostProcessorFactory.create(model)

    assert isinstance(processor, SimpleConcatenator)


