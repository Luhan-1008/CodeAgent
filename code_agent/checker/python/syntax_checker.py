import re
import ast
from ..interface import AbsChecker
from typing import Dict, List, Union, Tuple, Optional


def check_syntax(code: str) -> Dict[str, Union[bool, str]]:
    """
    Checks if a given Python code string contains syntax errors by attempting to build an AST.

    Args:
        code (str): The Python code string to check

    Returns:
        out (Dict[str, Union[bool, str]]):
            - 'valid' (bool): True if no syntax errors, False otherwise
            - 'error' (str, optional): Error message if syntax is invalid
    """
    result = {
        "valid": False,
        "error": None,
    }

    try:
        # Attempt to parse the code into an AST
        ast.parse(code)
        result["valid"] = True
        return result
    except SyntaxError as e:
        # Capture syntax error details
        error_line = code.splitlines()[e.lineno - 1]
        result["error"] = (
            f'Syntax error at line {e.lineno} column {e.offset}, "{error_line}": {e.msg}'
        )
        return result
    except Exception as e:
        # Catch any other parsing errors
        result["error"] = f"Error parsing code: {str(e)}"
        return result


def get_syntax_error_location(code: str) -> Optional[Tuple[int, int, str]]:
    """
    Returns the location and message of a syntax error in the provided code.

    Args:
        code (str): The Python code string to check

    Returns:
        out (Optional[Tuple[int, int, str]]): A tuple of (line, column, error_message) if there's a syntax error, None if the code is valid.
    """
    try:
        ast.parse(code)
        return None  # No syntax error
    except SyntaxError as e:
        return (e.lineno, e.offset, e.msg)
    except Exception as e:
        # For non-syntax errors, return position as 1,0
        return (1, 0, str(e))


def has_syntax_error(code: str) -> bool:
    """
    A simple check to determine if the code has any syntax errors.

    Args:
        code (str): The Python code string to check

    Returns:
        out (bool): True if there are syntax errors, False otherwise
    """
    try:
        ast.parse(code)
        return False
    except:
        return True


class SyntaxChecker(AbsChecker):
    """
    A checker that verifies if the given Python code string contains syntax errors.
    """

    @property
    def name(self) -> str:
        return "Syntax Checker"

    def check(self, file_path: str) -> List[Dict[str, str]]:
        """
        Check the syntax of the Python code in the given file.

        Args:
            file_path (str): Path to the Python file to check

        Returns:
            out (List[Dict[str, str]]): A list of dictionaries containing line number, column, problematic code, and error message
        """
        with open(file_path, "r") as f:
            code = f.read()

        error = check_syntax(code)
        if error["valid"]:
            return []
        pattern = r"Syntax error at line (\d+) column (\d+), \"(.+)\": (.+)"
        return [
            {
                "line": int(match.group(1)),
                "column": int(match.group(2)),
                "problematic_code": match.group(3),
                "message": match.group(4),
            }
            for match in re.finditer(pattern, error["error"])
        ]
