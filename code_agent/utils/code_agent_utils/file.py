import os
import shutil


def copy_to_directory(src_path: str, dst_directory: str) -> str:
    """
    Copy a file to a directory.

    Args:
        src_path (str): The path to the source file.
        dst_directory (str): The path to the destination directory.

    Returns:
        str: The path to the copied file in the destination directory.
    """
    os.makedirs(dst_directory, exist_ok=True)

    base_name = os.path.basename(src_path)
    dst_path = os.path.join(dst_directory, base_name)

    shutil.copy2(src_path, dst_path)

    return dst_path
