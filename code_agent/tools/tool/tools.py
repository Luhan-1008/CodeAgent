import os
import json
import time
import shutil
import signal
import platform
import subprocess
from pathlib import Path
from .tool_decorator import tool
from typing import Any, Dict, Optional
from agilemind.utils import extract_framework, extract_json
from agilemind.checker import python_checkers, web_checkers


class Tools:
    @staticmethod
    @tool("run_application", description="Run the application")
    def run_application(
        app_path: str = "main.py", cmd: str = "python", args: str = None
    ) -> Dict[str, Any]:
        """
        Run the application

        Args:
            app_path: The path to the application to run (defaults to 'main.py')
            cmd: The command to run the application (optional, defaults to 'python')
            args: The arguments to pass to the application (optional, defaults to None)

        Returns:
            Dict containing success status, message, and output
        """
        try:
            if not os.path.isfile(app_path):
                return {
                    "success": False,
                    "message": f"Application file not found: {app_path}",
                }

            command = f"{cmd} {app_path}"
            if args:
                command += f" {args}"

            is_windows = platform.system() == "Windows"
            subp = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if not is_windows else None,
            )

            timeout = 3
            start_time = time.time()
            while subp.poll() is None and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            retcode = subp.returncode

            if subp.poll() is None:
                try:
                    if is_windows:
                        os.kill(subp.pid, signal.SIGTERM)
                    else:
                        os.killpg(os.getpgid(subp.pid), signal.SIGTERM)
                    time.sleep(0.5)
                    if subp.poll() is None:
                        os.kill(subp.pid, signal.SIGKILL)
                except (ProcessLookupError, OSError, subprocess.SubprocessError):
                    pass

            stderr_output = subp.stderr.read().decode("utf-8")
            if (
                retcode == 0
                or not stderr_output
                or "traceback" not in stderr_output.lower()
            ):
                return {
                    "success": True,
                    "message": "Script test passed: Execution completed successfully",
                }

            current_dir = os.getcwd()
            stderr_output = stderr_output.replace(current_dir, ".")
            return {
                "success": False,
                "message": "Script test failed: Execution completed with errors",
                "traceback": stderr_output,
            }

        except Exception as e:
            return {"success": False, "message": f"App startup failed: {str(e)}"}

    @staticmethod
    @tool("work_done", description="Mark the task as done")
    def work_done() -> Dict[str, Any]:
        """
        Mark the task as done

        Returns:
            Dict containing success status and message
        """
        return {"success": True, "message": "Task marked as done"}

    @staticmethod
    @tool(
        "write_file",
        description="Write content to the file at the specified path. If the file already exists, it will be overwritten. Otherwise, a new file (and any necessary directories) will be created.",
        group="file_system",
    )
    def write_file(path: str, content: str) -> Dict[str, Any]:
        """
        Write content to a file. If the file already exists, it will be overwritten. Otherwise, a new file will be created.

        Args:
            path: The path to the file to write. You are currently in the root directory of the project. Use relative path.
            content: The content to write to the file. When creating a code file, make sure it is a valid code.

        Returns:
            Dict containing success status and message
        """
        cwd = Path(os.getcwd()).resolve()
        file_path = Path(path).resolve()
        if not file_path.is_relative_to(cwd):
            return {
                "success": False,
                "message": f"Cannot write to files outside the current directory: {path}",
            }

        overwritten = True if os.path.isfile(path) else False

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

            with open(path, "w") as f:
                if path.endswith(".json"):
                    json_content = extract_json(content)
                    f.write(json.dumps(json_content, indent=4))
                else:
                    f.write(content)
                f.flush()
            return {
                "success": True,
                "message": (
                    f"File created at {path}"
                    if not overwritten
                    else f"File overwritten at {path}"
                ),
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to create file: {str(e)}"}

    @staticmethod
    @tool(
        "read_file",
        description="Read the content of a file",
        group="file_system",
    )
    def read_file(path: str) -> Dict[str, Any]:
        """
        Read and return the content of a file.

        Args:
            path: The path to the file to read. **MUST use relative path.**

        Returns:
            Dict containing success status, message, and file content
        """
        cwd = Path(os.getcwd()).resolve()
        file_path = Path(path).resolve()
        if not file_path.is_relative_to(cwd):
            return {
                "success": False,
                "message": f"Cannot read files outside the current directory: {path}",
            }

        try:
            if not os.path.exists(path):
                return {"success": False, "message": f"File not found: {path}"}

            # Use the correct encoding for reading Chinese characters
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return {
                "success": True,
                "message": f"File read successfully",
                "content": content,
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to read file: {str(e)}"}

    @staticmethod
    @tool(
        "execute_command",
        description="Execute a shell command",
        confirmation_required=True,
    )
    def execute_command(command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a shell command. Related path **MUST be relative path.**

        Args:
            command: The command to execute
            cwd: Current working directory (optional)

        Returns:
            Dict containing success status, message, stdout and stderr
        """
        try:
            result = subprocess.run(
                command, shell=True, cwd=cwd, capture_output=True, text=True
            )

            return {
                "success": result.returncode == 0,
                "message": f"Command executed with return code {result.returncode}",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to execute command: {str(e)}"}

    @staticmethod
    @tool(
        "list_project_structure",
        description="List the structure of the project",
        group="file_system",
    )
    def list_directory() -> Dict[str, Any]:
        """
        List the structure of the project.

        Returns:
            Dict containing success status, message, and project structure
        """
        try:
            cwd = os.getcwd()
            items = []
            for root, dirs, files in os.walk(cwd):
                for name in dirs + files:
                    items.append(os.path.relpath(os.path.join(root, name)))

            return {
                "success": True,
                "message": "Project structure listed",
                "items": items,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to list project structure: {str(e)}",
            }

    @staticmethod
    @tool(
        "delete_file",
        description="Delete a file or directory",
    )
    def delete_file(path: str) -> Dict[str, Any]:
        """
        Delete a file or directory.

        Args:
            path: The path of file to delete. **MUST use relative path.**

        Returns:
            Dict containing success status and message
        """
        cwd = Path(os.getcwd()).resolve()
        file_path = Path(path).resolve()
        if not file_path.is_relative_to(cwd):
            return {
                "success": False,
                "message": f"Cannot delete files outside the current directory: {path}",
            }

        try:
            if not os.path.exists(path):
                return {"success": False, "message": f"Path not found: {path}"}

            if os.path.isdir(path):
                shutil.rmtree(path)
                return {"success": True, "message": f"Directory deleted: {path}"}
            else:
                os.remove(path)
                return {"success": True, "message": f"File deleted: {path}"}
        except Exception as e:
            return {"success": False, "message": f"Failed to delete: {str(e)}"}

    @staticmethod
    @tool(
        "add_to_requirements",
        description="Add a package to the requirements file",
        group="development",
    )
    def add_to_requirements(
        language: str, package_name: str, version: str = None
    ) -> Dict[str, Any]:
        """
        Add a package to the requirements file based on the language

        Args:
            language: The language for which to add the package
            package_name: The name of the package to add
            version: The version of the package to add (optional)

        Returns:
            Dict containing success status and message
        """
        if language.lower() == "python":
            if os.path.exists("requirements.txt"):
                with open("requirements.txt", "r") as f:
                    requirements = [
                        line.split("==")[0].split("<=")[0].split(">=")[0].strip()
                        for line in f.readlines()
                    ]
                if package_name in requirements:
                    return {
                        "success": True,
                        "message": f"{package_name} already exists in requirements.txt",
                    }

            with open("requirements.txt", "a") as f:
                if version:
                    f.write(f"{package_name}=={version}\n")
                else:
                    f.write(f"{package_name}\n")

            print(f'Info: Running "pip install {package_name}"')
            subp = subprocess.Popen(
                f"pip install {package_name}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            ret = subp.wait()
            print(
                f"Info: pip install {package_name} successfully"
                if ret == 0
                else "Error: " + subp.stdout.read().decode("utf-8")
            )

            return {
                "success": True,
                "message": f"Added {package_name} to requirements.txt",
            }
        elif language.lower() == "javascript":
            if not os.path.exists("package.json"):
                with open("package.json", "w") as f:
                    data = {"dependencies": {}}
                    json.dump(data, f, indent=2)
            else:
                with open("package.json", "r") as f:
                    data = json.load(f)
            if "dependencies" not in data:
                data["dependencies"] = {}
            data["dependencies"][package_name] = version or "*"
            with open("package.json", "w") as f:
                json.dump(data, f, indent=2)
            return {"success": True, "message": f"Added {package_name} to package.json"}

        return {
            "success": False,
            "message": f"Unsupported language: {language}",
        }

    @staticmethod
    @tool(
        "get_code_structure",
        description="Get the code structure of one file",
        group="development",
    )
    def get_code_structure(file: str) -> Dict[str, Any]:
        """
        Get the code structure of a module or all modules

        Args:
            file: file path to get the code structure for

        Returns:
            Dict containing success status and message
        """
        try:
            # If the file is not a subfile of cwd, return False
            cwd = Path(os.getcwd()).resolve()
            file_path = Path(file).resolve()
            if not file_path.is_relative_to(cwd):
                return {
                    "success": False,
                    "message": f"Cannot get code structure of files outside the current directory: {file}",
                }

            if not os.path.isfile(file_path):
                return {
                    "success": False,
                    "message": f"Path not found or not a file: {file}",
                }

            return {
                "success": True,
                "message": f"Code structure retrieved successfully",
                "code_structure": extract_framework(file_path),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get code structure: {str(e)}",
            }

    @staticmethod
    @tool(
        "run_static_analysis",
        description="Run static analysis on file",
        group="development",
    )
    def run_static_analysis(file_path: str) -> Dict[str, Any]:
        """
        Run static analysis on a file

        Args:
            file_path: The path of the file to run static analysis on.

        Returns:
            Dict containing success status and message
        """
        try:
            cwd = Path(os.getcwd()).resolve()
            file_path = Path(file_path).resolve()
            if not file_path.is_relative_to(cwd):
                return {
                    "success": False,
                    "message": f"Cannot run static analysis on files outside the current directory: {file_path}",
                }

            if not os.path.isfile(file_path):
                return {
                    "success": False,
                    "message": f"Path not found or not a file: {file_path}",
                }

            suffix = Path(file_path).suffix
            if suffix == ".py":
                results = python_checkers.run(file_path)
            elif suffix in [".html", ".css", ".js"]:
                results = web_checkers.run(file_path)
            else:
                results = [{"message": "Unsupported file type for static analysis."}]

            return {
                "success": True,
                "message": f"Static analysis completed",
                "analysis_results": results,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to run static analysis: {str(e)}",
            }
