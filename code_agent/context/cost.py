"""
Classes for tracking API costs.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional


class CostAmount:
    """Class to track costs for prompts, completions, and total."""

    def __init__(self):
        """Initialize cost amounts."""
        self.prompt_cost = 0.0
        self.completion_cost = 0.0
        self.total_cost = 0.0

    def update(self, prompt_cost: float, completion_cost: float) -> None:
        """
        Update cost amounts.

        Args:
            prompt_cost: Cost for prompts to add
            completion_cost: Cost for completions to add
        """
        self.prompt_cost += prompt_cost
        self.completion_cost += completion_cost
        self.total_cost = self.prompt_cost + self.completion_cost

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary representation."""
        return {
            "prompt_cost": self.prompt_cost,
            "completion_cost": self.completion_cost,
            "total_cost": self.total_cost,
        }


class CostDetail:
    """Class to represent a single cost record."""

    def __init__(
        self,
        agent_name: str,
        round_number: int,
        prompt_cost: float,
        completion_cost: float,
        model: Optional[str] = None,
    ):
        """Initialize cost detail record."""
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.agent = agent_name
        self.round = round_number
        self.model = model
        self.prompt_cost = prompt_cost
        self.completion_cost = completion_cost
        self.total_cost = prompt_cost + completion_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "round": self.round,
            "model": self.model,
            "prompt_cost": self.prompt_cost,
            "completion_cost": self.completion_cost,
            "total_cost": self.total_cost,
        }


class AgentCost:
    """Class to track costs by agent."""

    def __init__(self):
        """Initialize agent cost tracking."""
        self._agents: Dict[str, CostAmount] = {}

    def update(
        self, agent_name: str, prompt_cost: float, completion_cost: float
    ) -> None:
        """
        Update cost for a specific agent.

        Args:
            agent_name: Name of the agent
            prompt_cost: Cost for prompts to add
            completion_cost: Cost for completions to add
        """
        if agent_name not in self._agents:
            self._agents[agent_name] = CostAmount()

        self._agents[agent_name].update(prompt_cost, completion_cost)

    def __getattr__(self, agent_name: str) -> CostAmount:
        """Access agent cost via attribute."""
        if agent_name not in self._agents:
            self._agents[agent_name] = CostAmount()
        return self._agents[agent_name]

    def to_dict(self) -> Dict[str, Dict[str, float]]:
        """Convert to dictionary representation."""
        return {name: amount.to_dict() for name, amount in self._agents.items()}


class Cost:
    """Main class for tracking all API costs."""

    def __init__(self):
        """Initialize cost tracking."""
        self.total = CostAmount()
        self.agent = AgentCost()
        self.detailed: List[CostDetail] = []

    def update(
        self,
        prompt_cost: float,
        completion_cost: float,
        agent_name: str,
        round_number: int,
        model: Optional[str] = None,
    ) -> None:
        """
        Update all cost statistics.

        Args:
            prompt_cost: Cost for prompts
            completion_cost: Cost for completions
            agent_name: Name of the agent making the call
            round_number: Round number within the agent's processing
            model: Optional model name used for the API call
        """
        # Update total costs
        self.total.update(prompt_cost, completion_cost)

        # Update per-agent costs
        self.agent.update(agent_name, prompt_cost, completion_cost)

        # Add detailed record
        detail = CostDetail(
            agent_name=agent_name,
            round_number=round_number,
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
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
