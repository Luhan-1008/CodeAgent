"""
Configuration module for the Executor class.
"""

import os
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional
from dataclasses import asdict, dataclass, field


@dataclass
class GenerationParams:
    """
    Dataclass to represent the generation parameters for the Executor class.
    None values represent parameters that are default to the API.
    """

    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    tools: Optional[List[Dict]] = None
    temperature: Optional[float] = None

    def __post_init__(self):
        if self.max_tokens is not None:
            self.max_completion_tokens = self.max_tokens
        if self.max_completion_tokens is not None:
            self.max_tokens = self.max_completion_tokens

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ExecutorConfig:
    """
    Dataclass to represent the configuration parameters for the Executor class.
    """

    api_key: str
    default_model: str
    base_url: Optional[str] = None
    generation_params: GenerationParams = field(default_factory=GenerationParams)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        result = {
            "api_key": "REDACTED" if self.api_key else None,
            "default_model": self.default_model,
            "base_url": self.base_url,
            "generation_params": self.generation_params.to_dict(),
        }
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutorConfig":
        """Create configuration from dictionary."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("API key is required, please set OPENAI_API_KEY")

        return cls(
            api_key=api_key,
            default_model=data["default_model"],
            base_url=data["base_url"],
            generation_params=GenerationParams(**data["generation_params"]),
        )

    @classmethod
    def from_env(cls) -> "ExecutorConfig":
        """Create configuration from environment variables."""
        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("API key is required, please set OPENAI_API_KEY")

        base_url = os.getenv("OPENAI_BASE_URL")
        default_model = os.getenv("AM_DEFAULT_MODEL")

        max_tokens = os.getenv("AM_MAX_TOKENS")
        top_p = os.getenv("AM_TOP_P")
        temperature = os.getenv("AM_DEFAULT_TEMPERATURE")

        generation_params = GenerationParams(
            max_tokens=int(max_tokens) if max_tokens else None,
            top_p=float(top_p) if top_p else None,
            temperature=float(temperature) if temperature else None,
        )

        return cls(
            api_key=api_key,
            default_model=default_model,
            base_url=base_url,
            generation_params=generation_params,
        )
