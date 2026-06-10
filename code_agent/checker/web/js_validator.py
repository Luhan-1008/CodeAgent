"""Validate JavaScript files."""

import esprima
from esprima.error_handler import Error as EsprimaError


def is_valid_javascript(content: str) -> bool:
    """
    Validates whether the content of a file at the given path is valid JavaScript.

    Args:
        content (str): Content of the file to validate

    Returns:
        bool: True if the content is valid JavaScript, False otherwise
    """
    return is_valid_javascript_esprima(content)


def is_valid_javascript_esprima(content: str) -> tuple[bool, int, int, str]:
    """
    Validates whether the content of a file at the given path is valid JavaScript
    using the esprima parser if available.

    Args:
        content (str): Content of the file to validate

    Returns:
        tuple: A tuple containing:
            - bool: True if the content is valid JavaScript, False otherwise
            - int: The line number of the error (if any)
            - int: The column number of the error (if any)
            - str: The error message (if any)
    """
    try:
        esprima.parseScript(content)
        return True, None, None, None
    except EsprimaError as e:
        return False, e.lineNumber, e.column, e.message
