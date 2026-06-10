import re
import tempfile
import subprocess
from ..interface import AbsChecker
from typing import Any, List, Dict


class PylintError(Exception):
    """Exception raised for errors in the Pylint execution."""

    pass


def run_pylint_on_file(file_path: str) -> str:
    """
    Run pylint on the given file and return the raw output.

    Args:
        file_path (str): The Python file to check

    Returns:
        str: Raw output from pylint

    Raises:
        PylintError: If pylint execution fails
    """
    try:
        pylint = subprocess.run(
            ["which", "pylint"], text=True, capture_output=True, check=True
        )
        pylint = pylint.stdout.strip()
        result = subprocess.run(
            [pylint, file_path, "-E", "--disable=E0401,E1101"],
            text=True,
            capture_output=True,
        )
        return result.stdout + result.stderr
    except Exception as e:
        raise PylintError(f"Failed to execute pylint: {str(e)}")


def run_pylint_on_code(code_str: str) -> str:
    """
    Run pylint on the given code string and return the raw output.

    Args:
        code_str (str): The Python code to check

    Returns:
        str: Raw output from pylint

    Raises:
        PylintError: If pylint execution fails
    """
    # Save code to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".py") as temp_file:
        temp_file_path = temp_file.name
        temp_file.write(code_str.encode("utf-8"))
        temp_file.flush()

        return run_pylint_on_file(temp_file_path)


def parse_pylint_errors(pylint_output: str) -> List[Dict[str, Any]]:
    """
    Parse pylint output and extract error information.

    Args:
        pylint_output (str): Raw output from pylint

    Returns:
        out (List[Dict[str, Any]]): List of error dictionaries
    """
    # Regular expression to extract error information
    # Format typically: filename:line:column: error_code: message
    error_pattern = r"(.*?):(\d+):(\d+): (\w+): (.+)"

    errors = []
    for line in pylint_output.split("\n"):
        if not line.strip():
            continue

        match = re.search(error_pattern, line)
        if match and match.group(4).startswith("E"):  # Ensure it's an error (E)
            errors.append(
                {
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "column": int(match.group(3)),
                    "code": match.group(4),
                    "message": match.group(5),
                }
            )

    return errors


def check_code_with_pylint(code_str: str) -> List[Dict[str, Any]]:
    """
    Check the given Python code string with PyLint and return errors (Exxxx).

    Args:
        code_str (str): A string representation of Python code to be checked.

    Returns:
        out (List[Dict[str, Any]]): A list of dictionaries containing error details:
            - code: The error code (e.g., E0001)
            - line: Line number where the error occurred
            - column: Column number where the error occurred
            - message: Description of the error
    """
    try:
        pylint_output = run_pylint_on_code(code_str)
        return parse_pylint_errors(pylint_output)
    except PylintError as e:
        return [
            {
                "file": "",
                "code": "Unknown",
                "line": 0,
                "column": 0,
                "message": f"Error running PyLint: {str(e)}",
            }
        ]


def check_file_with_pylint(file_path: str) -> List[Dict[str, Any]]:
    """
    Check the given Python file with PyLint and return errors (Exxxx).

    Args:
        file_path (str): A string representation of Python file to be checked.

    Returns:
        out (List[Dict[str, Any]]): A list of dictionaries containing error details:
            - code: The error code (e.g., E0001)
            - line: Line number where the error occurred
            - column: Column number where the error occurred
            - message: Description of the error
    """
    try:
        pylint_output = run_pylint_on_file(file_path)
        return parse_pylint_errors(pylint_output)
    except PylintError as e:
        return [
            {
                "file": file_path,
                "code": "Unknown",
                "line": 0,
                "column": 0,
                "message": f"Error running PyLint: {str(e)}",
            }
        ]


class PylintChecker(AbsChecker):
    """
    A checker that verifies Python code using PyLint.
    """

    @property
    def name(self) -> str:
        return "PyLint Checker"

    def check(self, file_path: str) -> List[Dict[str, str]]:
        """
        Check the Python code in the given file using PyLint.

        Args:
            file_path (str): Path to the Python file to check

        Returns:
            out (List[Dict[str, str]]): List of dictionaries containing line number, column, problematic code, and error message
        """
        with open(file_path, "r") as f:
            code = f.read()

        errors = check_code_with_pylint(code)
        return [
            {
                "line": error["line"],
                "column": error["column"],
                "problematic_code": code.splitlines()[error["line"] - 1],
                "message": error["message"],
            }
            for error in errors
        ]
