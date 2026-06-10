"""
Module to store and manage LLM model information including pricing and capabilities.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional

# Set to track models that have already been warned about
_warned_models = set()


@dataclass
class ModelInfo:
    """Class for storing comprehensive model information."""

    # Human-readable model name
    name: str

    # Input price in USD per 1000 tokens
    input_price: float

    # Output price in USD per 1000 tokens
    output_price: float

    # Whether the model supports multimodal inputs (images, etc.)
    is_multimodal: bool = False

    # Maximum context length in tokens
    context_length: int = 8192


class ModelLibrary(Enum):
    """Enum for common LLM models and their information."""

    # OpenAI models
    GPT_4O_MINI = ModelInfo(
        "gpt-4o-mini",
        0.00015,
        0.0006,
        is_multimodal=True,
        context_length=128000,
    )
    GPT_4O = ModelInfo(
        "gpt-4o",
        0.0025,
        0.01,
        is_multimodal=True,
        context_length=128000,
    )

    # Anthropic models
    CLAUDE_3_7_SONNET_20250219 = ModelInfo(
        "claude-3-7-sonnet-20250219",
        0.0033,
        0.0165,
        is_multimodal=True,
        context_length=200000,
    )
    CLAUDE_3_5_SONNET_20241022 = ModelInfo(
        "claude-3-5-sonnet-20241022",
        0.0033,
        0.0165,
        is_multimodal=True,
        context_length=200000,
    )
    CLAUDE_3_5_HAIKU_20241022 = ModelInfo(
        "claude-3-5-haiku-20241022",
        0.0011,
        0.0055,
        is_multimodal=True,
        context_length=200000,
    )

    # Deepseek models
    DEEPSEEK_V3 = ModelInfo(
        "DeepSeek V3",
        0.000272,
        0.001088,
        is_multimodal=False,
        context_length=64000,
    )
    DEEPSEEK_R1 = ModelInfo(
        "DeepSeek R1",
        0.000546,
        0.002184,
        is_multimodal=False,
        context_length=64000,
    )
    DEEPSEEK_CHAT = ModelInfo(
        "DeepSeek-chat",
        0.000546,
        0.002184,
        is_multimodal=False,
        context_length=64000,
    )

    @classmethod
    def get_known_model_ids(cls) -> List[str]:
        """Return a list of known model IDs"""
        return [member.name for member in cls]

    @classmethod
    def get_known_model_names(cls) -> List[str]:
        """Return a list of human-readable model names"""
        return [member.value.name for member in cls]

    @classmethod
    def get_multimodal_models(cls) -> List[str]:
        """Return a list of multimodal model IDs"""
        return [member.name for member in cls if member.value.is_multimodal]

    @classmethod
    def get_model_by_name(cls, name: str) -> Optional["ModelLibrary"]:
        """Find a model by its human-readable name"""
        for model in cls:
            if model.value.name.lower() == name.lower():
                return model
        return None

    @classmethod
    def get_default_model(cls) -> "ModelInfo":
        """Return the default model to use when model is unknown"""
        return cls.GPT_4O.value


def calculate_cost(
    model: str, prompt_tokens: int, completion_tokens: int
) -> Dict[str, float]:
    """
    Calculate the cost for a given model and token usage.

    Args:
        model: The model to calculate pricing for
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens

    Returns:
        Dictionary with prompt_cost, completion_cost, and total_cost
    """
    # Format model name for comparison
    model_id = model.upper().replace("-", "_").replace(" ", "_")

    try:
        # Try to get the model directly by ID
        model_info = ModelLibrary[model_id].value
    except KeyError:
        # Try to find by display name
        found_model = ModelLibrary.get_model_by_name(model)
        if found_model:
            model_info = found_model.value
        else:
            # Use default if not found
            if model_id not in _warned_models:
                print(
                    f"Unknown price for model: {model}, "
                    f"using {ModelLibrary.get_default_model().name}'s "
                    "price for reference."
                )
                _warned_models.add(model_id)
            model_info = ModelLibrary.get_default_model()

    prompt_cost = model_info.input_price * (prompt_tokens / 1000)
    completion_cost = model_info.output_price * (completion_tokens / 1000)
    total_cost = prompt_cost + completion_cost

    return {
        "prompt_cost": prompt_cost,
        "completion_cost": completion_cost,
        "total_cost": total_cost,
    }


def get_model_info(model: str) -> ModelInfo:
    """
    Get comprehensive information about a model.

    Args:
        model: The model name or ID

    Returns:
        ModelInfo object with model details
    """
    model_id = model.upper().replace("-", "_").replace(" ", "_")

    try:
        return ModelLibrary[model_id].value
    except KeyError:
        found_model = ModelLibrary.get_model_by_name(model)
        if found_model:
            return found_model.value

        if model_id not in _warned_models:
            print(f"Unknown model: {model}, returning default model information.")
            _warned_models.add(model_id)
        return ModelLibrary.get_default_model()
