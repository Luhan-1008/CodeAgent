from .interface import AbsChecker
from typing import Any, List, Dict


class CheckerPipeline:
    """
    A pipeline for running multiple checkers on code.
    """

    def __init__(self):
        """Initialize an empty pipeline."""
        self._checkers: List[AbsChecker] = []

    def add_checker(self, *checkers: AbsChecker) -> "CheckerPipeline":
        """
        Add one or more checkers to the pipeline.

        Args:
            *checkers (AbsChecker): One or more checker instances to add

        Returns:
            CheckerPipeline: The pipeline object for method chaining
        """
        self._checkers.extend(checkers)
        return self

    def run(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Run checkers in the pipeline on the given code until one returns errors.

        Args:
            file_path (str): Path to the Python file to check

        Returns:
            out (List[Dict[str, Any]]): Results from the first checker that finds issues,
                                  or an empty list if no issues are found
        """
        for checker in self._checkers:
            try:
                checker_results = checker.check(file_path)
                if checker_results:  # If the checker found any issues
                    return checker_results
            except Exception as e:
                return [{"error": f"Checker '{checker.name}' failed: {str(e)}"}]

        # If no checker found issues
        return []

    def remove_checker(self, checker_name: str) -> bool:
        """
        Remove a checker from the pipeline by name.

        Args:
            checker_name (str): Name of the checker to remove

        Returns:
            bool: True if a checker was removed, False otherwise
        """
        original_length = len(self._checkers)
        self._checkers = [c for c in self._checkers if c.name != checker_name]
        return len(self._checkers) < original_length
