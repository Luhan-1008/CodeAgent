from . import fixed as fixed_prompt
from . import agile as agile_prompt
from . import waterfall as waterfall_prompt

DEFAULT_SYSTEM_MESSAGE = """You are a helpful assistant."""

__all__ = ["DEFAULT_SYSTEM_MESSAGE", "fixed_prompt", "agile_prompt", "waterfall_prompt"]
