from typing import List, Dict
from abc import ABC, abstractmethod


class AbsChecker(ABC):
    """
    Abstract base class for code checkers.

    All code checkers should implement this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the checker.
        """
        pass

    @abstractmethod
    def check(self, file_path: str) -> List[Dict[str, str]]:
        """
        Check the given code and return a list of issues found.

        Args:
            file_path (str): Path to the code file to check

        Returns:
            out (List[Dict[str, Any]]): A list of dictionaries containing information about issues found.
                Each dictionary should typically contain information like:
                - 'line': line number of the issue
                - 'column': column number of the issue
                - 'problematic_code': code snippet that caused the issue
                - 'message': description of the issue
        """
        pass
