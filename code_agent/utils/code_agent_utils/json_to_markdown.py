"""
Utility functions for converting JSON data to markdown.
"""

import re
import json
from typing import Dict, Any, Union, List


def convert(
    *fields: str,
    data: Union[Dict[str, Any], str],
    title: str,
    code_languages: Dict[str, str] = None,
) -> str:
    """
    Convert JSON data to a markdown string.

    Args:
        *fields (str): Field names to extract from the JSON data
        data (Union[Dict[str, Any], str]): Either a JSON string or a dictionary containing the data
        title (str): The title to be used as the main heading
        code_languages (Dict[str, str]): Dictionary mapping field names to their respective code languages

    Returns:
        out: A markdown string formatted according to the specified fields
    """
    # Convert string to dict if needed
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON string provided")

    # Initialize code_languages if not provided
    if code_languages is None:
        code_languages = {}

    # Start with the title
    markdown = f"# {title}\n\n"

    # Add each requested field
    for field in fields:
        if field in data:
            # Get the value and handle different types appropriately
            value = data[field]

            # Capitalize each word in the field name
            field_title = field.replace("_", " ").title()

            # Format the field as a header
            markdown += f"## {field_title}\n"

            # Format the value based on its type and whether it's marked as code
            if field in code_languages:
                # Use specified language for code block
                language = code_languages[field]

                # Clean "``` LANGUAGE" and "```" from value
                value = re.sub(r"```[^\n]*\n", "", value)
                value = re.sub(r"```", "", value)

                markdown += f"```{language}\n{value}\n```\n\n"
            elif isinstance(value, (list, dict)):
                # For complex types, use JSON formatting
                markdown += f"```json\n{json.dumps(value, indent=2)}\n```\n\n"
            else:
                # For simple types, just add the value directly
                markdown += f"{value}\n\n"
        else:
            # If field doesn't exist, note that it's missing
            markdown += f"## {field}\nNot available\n\n"

    return markdown


def create_file_tree(files: List[str]) -> str:
    """
    Convert a list of file paths into a tree structure similar to the Linux 'tree' command.

    Args:
        files (List[str]): List of file paths (e.g., ["src/core/logic.py", "main.py"])

    Returns:
        out: A string representing the directory tree structure
    """
    if not files:
        return "Empty file structure"

    # Sort the files to ensure consistent output
    files.sort()

    # Build a directory structure
    tree_dict = {}
    for file_path in files:
        parts = file_path.split("/")
        current = tree_dict
        for part in parts[:-1]:  # Process directories
            if part not in current:
                current[part] = {}
            current = current[part]
        # Handle the file (last part)
        if parts[-1] not in current:
            current[parts[-1]] = None  # Files are leaf nodes

    # Convert tree dictionary to string representation
    lines = ["."]

    def _build_tree(node, prefix="", is_last=True):
        items = list(node.items())
        count = len(items)

        for i, (name, subtree) in enumerate(items):
            is_last_item = i == count - 1
            # Add line for current node
            if is_last:
                lines.append(f"{prefix}└── {name}")
                new_prefix = prefix + "    "
            else:
                lines.append(f"{prefix}├── {name}")
                new_prefix = prefix + "│   "

            # If it's a directory (has subtree), recurse
            if subtree is not None:
                _build_tree(subtree, new_prefix, is_last_item)

    _build_tree(tree_dict)
    return "\n".join(lines)
