from typing import Dict, List
from ..interface import AbsChecker
from .css_validator import is_valid_css
from .html_validator import is_valid_html
from .js_validator import is_valid_javascript


class WebChecker(AbsChecker):
    """
    WebChecker class for checking web-related code.
    """

    @property
    def name(self) -> str:
        return "Web Checker"

    def check(self, file_path: str) -> List[Dict[str, str]]:
        """
        Check the provided code for web-related issues.

        Args:
            file_path (str): The path to the file to check.

        Returns:
            out (List[Dict[str, str]]): A list of dictionaries containing information about issues found.
        """
        with open(file_path, "r") as file:
            code = file.read()

        is_valid = True
        ln, col, msg = None, None, None
        if file_path.endswith(".html"):
            is_valid, ln, col, msg = is_valid_html(code)
        elif file_path.endswith(".css"):
            is_valid, ln, col, msg = is_valid_css(code)
        elif file_path.endswith(".js"):
            is_valid, ln, col, msg = is_valid_javascript(code)
        else:
            return [{"error": "Unsupported file type"}]

        return (
            []
            if is_valid
            else [
                {
                    "line": ln if ln else "Unknown",
                    "column": col if col else "Unknown",
                    "problematic_code": code.splitlines()[ln - 1] if ln else "Unknown",
                    "message": msg if msg else "Invalid code for this file type",
                }
            ]
        )
