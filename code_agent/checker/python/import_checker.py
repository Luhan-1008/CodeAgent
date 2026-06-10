import os
import sys
import ast
import importlib
from ..interface import AbsChecker
from typing import Dict, List, Tuple


def extract_imports(code: str) -> List[Tuple[str, str, List[str], int]]:
    """
    Extract all import statements from Python code string.

    Args:
        code (str): Python code as string

    Returns:
        out (list of tuples):
            - import type ('import' or 'from')
            - module name
            - list of names being imported (empty for simple imports)
            - line number in the source code
    """
    tree = ast.parse(code)
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.append(("import", name.name, [], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = [alias.name for alias in node.names]
            imports.append(("from", module, names, node.lineno))

    return imports


def check_imports(code: str, local_dir: str = None) -> Dict[Tuple[str, int], str]:
    """
    Check if all imports in the code can be successfully imported.

    Args:
        code: Python code as string
        local_dir: Directory to check for local modules (defaults to current working directory)

    Returns:
        Dictionary mapping (import statement, line number) to error messages (empty if successful)
    """
    imports = extract_imports(code)
    results = {}

    # If no local_dir specified, use current working directory
    if local_dir is None:
        local_dir = os.getcwd()

    # Temporarily add local_dir to sys.path to find local modules
    original_path = sys.path.copy()
    if local_dir not in sys.path:
        sys.path.insert(0, local_dir)

    try:
        for imp_type, module_name, names, lineno in imports:
            if imp_type == "import":
                import_stmt = f"import {module_name}"
                try:
                    importlib.import_module(module_name)
                except Exception as e:
                    results[(import_stmt, lineno)] = str(e)
            elif imp_type == "from":
                if not names:
                    continue

                import_stmt = f"from {module_name} import {', '.join(names)}"
                try:
                    if module_name:
                        mod = importlib.import_module(module_name)
                        for name in names:
                            try:
                                getattr(mod, name)
                            except AttributeError:
                                results[(import_stmt, lineno)] = (
                                    f"Cannot import name '{name}' from '{module_name}'"
                                )
                except Exception as e:
                    results[(import_stmt, lineno)] = str(e)
    finally:
        # Restore the original sys.path
        sys.path = original_path

    return results


def format_error_message(errors: Dict[Tuple[str, int], str]) -> str:
    """
    Format the error message for display including line numbers of invalid imports.

    Args:
        errors: Dictionary of (import statements, line number) to error messages

    Returns:
        Formatted error message
    """
    if not errors:
        return "All imports are successful!"

    error_msg = "Errors in imports:"
    for (stmt, lineno), error in errors.items():
        error_msg += f'\n  - Line {lineno}: "{stmt}": {error}'

    return error_msg


class ImportChecker(AbsChecker):
    """
    A checker that verifies if all imports in the code can be successfully imported.
    """

    @property
    def name(self) -> str:
        return "Import Checker"

    def check(self, file_path: str) -> List[Dict[str, str]]:
        """
        Check the imports in the given file.

        Args:
            file_path (str): Path to the Python file to check

        Returns:
            List of dictionaries containing line number, column, problematic code, and error message
        """
        with open(file_path, "r") as f:
            code = f.read()

        errors = check_imports(code)
        return [
            {"line": lineno, "column": 0, "problematic_code": stmt, "message": error}
            for (stmt, lineno), error in errors.items()
        ]
