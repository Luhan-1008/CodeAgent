"""Validates CSS files."""

import tinycss2
import tinycss2.ast


def is_valid_css(content: str) -> tuple[bool, int, int, str]:
    """
    Validates whether the content of a file at the given path is valid CSS.

    Args:
        content (str): Content of the file to validate.

    Returns:
        tuple: A tuple containing:
            - bool: True if the content is valid CSS, False otherwise
            - int: The line number of the error (if any)
            - int: The column number of the error (if any)
            - str: The error message (if any)
    """
    # Parse the CSS content
    stylesheet = tinycss2.parse_stylesheet(content)

    # Check for parse errors
    for node in stylesheet:
        if isinstance(node, tinycss2.ast.ParseError):
            return False, node.source_line, node.source_column, node.message

    return True, None, None, None
