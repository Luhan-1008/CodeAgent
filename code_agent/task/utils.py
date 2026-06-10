import os
import pathlib
from .definition import Task
from agilemind.context import Context


def save_result_to_file(task: Task, context: Context) -> None:
    """
    Save text content to a file at the given relative path.

    Args:
        file_path (str): The relative path to save the file to.
        content (str): The text content to save.

    Raises:
        ValueError: If the path is not relative or contains ".."
        FileExistsError: If the file already exists.
    """
    file_path = task.artifact_path
    if not file_path:
        raise ValueError("File path not set in task")

    # Check if path is relative and doesn't contain ".."
    if os.path.isabs(file_path):
        raise ValueError("File path must be relative, not absolute")

    if ".." in pathlib.Path(file_path).parts:
        raise ValueError("File path must not contain parent directory references (..)")

    if not context.is_root_dir_set():
        raise ValueError("Root directory not set in context")

    # Get the full path to the file
    file_path = os.path.join(context.root_dir, file_path)

    # Check if file already exists
    if os.path.exists(file_path):
        raise FileExistsError(f"File already exists at {file_path}")

    # Create parent directories if they don't exist
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    # Write content to file
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(task.result.output)
