"""
Tool group management and utilities for organizing tools into categories.
"""

import inspect
from tools import Tools
from typing import Dict, List, Set


# Standard tool groups
class ToolGroups:
    """Standard tool group names for consistency across the application."""

    GENERAL = "general"
    FILE_SYSTEM = "file_system"
    SYSTEM = "system"
    DEVELOPMENT = "development"

    @classmethod
    def get_all_groups(cls) -> List[str]:
        """Get a list of all standard tool groups."""
        return [
            value
            for name, value in vars(cls).items()
            if not name.startswith("_") and isinstance(value, str)
        ]

    @classmethod
    def get_group_description(cls, group: str) -> str:
        """Get a description for a tool group."""
        descriptions = {
            cls.GENERAL: "General purpose tools",
            cls.FILE_SYSTEM: "File and directory operations",
            cls.SYSTEM: "System commands and operations",
            cls.DEVELOPMENT: "Development tools and utilities",
        }
        return descriptions.get(group, f"Tools in the {group} category")


def get_available_groups() -> Set[str]:
    """
    Get all groups that have at least one tool registered.

    Returns:
        Set of group names that have tools registered
    """
    available_groups = set()

    for name, method in inspect.getmembers(Tools):
        if hasattr(method, "is_tool") and method.is_tool:
            available_groups.add(method.tool_group)

    return available_groups


def get_tools_by_group() -> Dict[str, List[Dict]]:
    """
    Organize all tools by their group.

    Returns:
        Dictionary mapping group names to lists of tool schemas
    """
    tools_by_group = {}

    for name, method in inspect.getmembers(Tools):
        if hasattr(method, "is_tool") and method.is_tool:
            group = method.tool_group
            if group not in tools_by_group:
                tools_by_group[group] = []

            tools_by_group[group].append(method.get_openai_schema())

    return tools_by_group
