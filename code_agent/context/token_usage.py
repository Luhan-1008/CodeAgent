"""
Classes for tracking token usage.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional


class TokenCount:
    """Class to track prompt, completion, and total tokens."""

    def __init__(self):
        """Initialize token counts."""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def update(self, prompt_tokens: int, completion_tokens: int) -> None:
        """
        Update token counts.

        Args:
            prompt_tokens: Number of prompt tokens to add
            completion_tokens: Number of completion tokens to add
        """
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens = self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary representation."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class TokenDetail:
    """Class to represent a single token usage record."""

    def __init__(
        self,
        agent_name: str,
        round_number: int,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
    ):
        """Initialize token detail record."""
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.agent = agent_name
        self.round = round_number
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "round": self.round,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class AgentTokenUsage:
    """Class to track token usage by agent."""

    def __init__(self):
        """Initialize agent token usage tracking."""
        self._agents: Dict[str, TokenCount] = {}

    def update(
        self, agent_name: str, prompt_tokens: int, completion_tokens: int
    ) -> None:
        """
        Update token usage for a specific agent.

        Args:
            agent_name: Name of the agent
            prompt_tokens: Number of prompt tokens to add
            completion_tokens: Number of completion tokens to add
        """
        if agent_name not in self._agents:
            self._agents[agent_name] = TokenCount()

        self._agents[agent_name].update(prompt_tokens, completion_tokens)

    def __getattr__(self, agent_name: str) -> TokenCount:
        """Access agent token usage via attribute."""
        if agent_name not in self._agents:
            self._agents[agent_name] = TokenCount()
        return self._agents[agent_name]

    def to_dict(self) -> Dict[str, Dict[str, int]]:
        """Convert to dictionary representation."""
        return {name: count.to_dict() for name, count in self._agents.items()}


class TokenUsage:
    """Main class for tracking all token usage."""

    def __init__(self):
        """Initialize token usage tracking."""
        self.total = TokenCount()
        self.agent = AgentTokenUsage()
        self.detailed: List[TokenDetail] = []

    def update(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        agent_name: str,
        round_number: int,
        model: Optional[str] = None,
    ) -> None:
        """
        Update all token usage statistics.

        Args:
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens used
            agent_name: Name of the agent making the call
            round_number: Round number within the agent's processing
            model: Optional model name used for the API call
        """
        # Update total counts
        self.total.update(prompt_tokens, completion_tokens)

        # Update per-agent counts
        self.agent.update(agent_name, prompt_tokens, completion_tokens)

        # Add detailed record
        detail = TokenDetail(
            agent_name=agent_name,
            round_number=round_number,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model,
        )
        self.detailed.append(detail)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total": self.total.to_dict(),
            "by_agent": self.agent.to_dict(),
            "detailed": [detail.to_dict() for detail in self.detailed],
        }
