from .agent import Agent
from .runner import Runner
from .config import GenerationParams


creative_generation = GenerationParams(
    top_p=0.9,
    temperature=0.8,
)
deterministic_generation = GenerationParams(
    temperature=0.2,
)
neutral_generation = GenerationParams(
    top_p=0.5,
    temperature=0.5,
)

__all__ = [
    "Agent",
    "Runner",
    "GenerationParams",
    "creative_generation",
    "deterministic_generation",
    "neutral_generation",
]
