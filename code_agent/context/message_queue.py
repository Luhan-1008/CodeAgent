"""
Message queue module for agent communication.
"""

from typing import Dict, List, Optional, Any


class MessageQueue:
    """
    A message queue for inter-agent communication.

    Allows agents to send messages to each other asynchronously using
    'inform_' tools, and retrieve queued messages when ready to process them.
    """

    def __init__(self):
        """Initialize an empty message queue."""
        # Dictionary mapping agent names to list of messages
        self.queues: Dict[str, List[Dict[str, Any]]] = {}

    def enqueue(
        self, target_agent: str, message: Dict[str, Any], sender: Optional[str] = None
    ) -> None:
        """
        Add a message to a specific agent's queue.

        Args:
            target_agent: Name of the agent to receive the message
            message: The message content to enqueue
            sender: Optional name of the sending agent
        """
        if target_agent not in self.queues:
            self.queues[target_agent] = []

        # Add sender to message if provided
        if sender:
            message_with_sender = message.copy()
            message_with_sender["sender"] = sender
            self.queues[target_agent].append(message_with_sender)
        else:
            self.queues[target_agent].append(message)

    def get_messages(self, agent: str) -> List[Dict[str, Any]]:
        """
        Retrieve all messages for a specific agent without removing them.

        Args:
            agent: Name of the agent to retrieve messages for

        Returns:
            List of messages for the agent
        """
        return self.queues.get(agent, [])

    def dequeue_all(self, agent: str) -> List[Dict[str, Any]]:
        """
        Retrieve and remove all messages for a specific agent.

        Args:
            agent: Name of the agent to dequeue messages for

        Returns:
            List of messages for the agent
        """
        messages = self.queues.get(agent, [])
        if agent in self.queues:
            self.queues[agent] = []
        return messages

    def has_messages(self, agent: str) -> bool:
        """
        Check if a specific agent has any messages in the queue.

        Args:
            agent: Name of the agent to check

        Returns:
            True if agent has messages, False otherwise
        """
        return agent in self.queues and len(self.queues[agent]) > 0

    def clear(self, agent: Optional[str] = None) -> None:
        """
        Clear messages for a specific agent or all agents.

        Args:
            agent: Name of the agent to clear messages for, or None to clear all
        """
        if agent:
            self.queues[agent] = []
        else:
            self.queues = {}
