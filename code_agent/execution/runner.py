"""
Runner module for managing the execution flow between agents.
"""

import json
from .agent import Agent
from typing import Dict, Any


class Runner:
    """
    Manages the execution flow between agents.

    The runner starts with an initial agent and input, then handles
    any handoffs between agents, tool usage, and final output generation.
    """

    @classmethod
    def run(
        cls, starting_agent: Agent, input: str, max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Run a conversation through agents, handling handoffs.

        Args:
            starting_agent: The agent to start with
            input: Initial user input
            max_iterations: Maximum number of agent handoffs to prevent infinite loops

        Returns:
            Dict containing the final response and execution trace
        """
        current_agent = starting_agent
        current_input = input
        iterations = 0
        execution_trace = []

        while iterations < max_iterations:
            iterations += 1

            # Process the input with the current agent
            result = current_agent.process(current_input)

            # Add to execution trace
            execution_trace.append(
                {"agent": current_agent.name, "input": current_input, "output": result}
            )

            # Check if there's a handoff (could be from direct handoff or forced via next_agent)
            if result["handoff"]:
                # Update the trace to indicate the handoff
                execution_trace[-1]["handoff_to"] = result["handoff"].name
                # Update current agent and use the previous agent's response as input for the new agent
                current_agent = result["handoff"]
                # Use previous agent's response as new input
                current_input = result["content"]
                # Reset the handoff to the new agent's name
                result["handoff"] = result["handoff"].name
                continue

            if result["tool_calls"]:
                # Add to the trace
                execution_trace[-1]["tool_calls"] = result["tool_calls"]

                # Format the tool results into a message to send back to the agent
                current_input = f'Here are the results of executed tools:\n{json.dumps(result["tool_calls"])}\n\nPlease continue based on these results.'
                continue

            # No handoffs or tool follow-ups needed, we're done
            return {
                "agent": current_agent.name,
                "response": result["content"],
                "execution_trace": execution_trace,
            }

        # If we reach here, we hit the max iterations
        return {
            "agent": current_agent.name,
            "response": "Maximum number of agent iterations reached without resolution.",
            "execution_trace": execution_trace,
        }
