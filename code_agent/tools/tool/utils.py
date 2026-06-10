import inspect
import readchar
from .tools import Tools
from typing import Any, Dict, List
from agilemind.context import Context


def get_tool(tool_name: str) -> Dict[str, Any]:
    """
    Get a specific tool defined with the @tool decorator in OpenAI format.

    Args:
        tool_name: Name of the tool to retrieve.

    Returns:
        Tool definition for OpenAI API or None if not found.
    """
    for name, method in inspect.getmembers(Tools):
        if (
            hasattr(method, "is_tool")
            and method.is_tool
            and method.tool_name == tool_name
        ):
            return method.get_openai_schema()

    return None


def get_all_tools(*groups) -> List[Dict[str, Any]]:
    """
    Get all tools defined with the @tool decorator in OpenAI format,
    optionally filtered by one or more groups.

    Args:
        *groups: If provided, only return tools from these groups.
                Multiple group names can be passed as separate arguments.

    Returns:
        List of tool definitions for OpenAI API
    """
    tool_schemas = []
    for name, method in inspect.getmembers(Tools):
        if hasattr(method, "is_tool") and method.is_tool:
            # If no groups specified or tool belongs to one of the specified groups
            if not groups or method.tool_group in groups:
                tool_schemas.append(method.get_openai_schema())

    return tool_schemas


def execute_tool(
    context: Context, tool_name: str, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute a tool by name with the provided arguments

    Args:
        context: The context object
        tool_name: Name of the tool to execute
        arguments: Arguments to pass to the tool

    Returns:
        Result of tool execution
    """
    for name, method in inspect.getmembers(Tools):
        if (
            hasattr(method, "is_tool")
            and method.is_tool
            and method.tool_name == tool_name
        ):
            # Check if all required arguments are provided
            missing_args = []
            sig = inspect.signature(method)
            for param_name, param in sig.parameters.items():
                # Required params have no default and aren't variadic (*args, **kwargs)
                if param.default is param.empty and param.kind not in (
                    param.VAR_POSITIONAL,
                    param.VAR_KEYWORD,
                ):
                    if param_name not in arguments and param_name != "context":
                        missing_args.append(param_name)
            if missing_args:
                return {
                    "success": False,
                    "message": f"Missing required arguments: {', '.join(missing_args)}",
                }

            # Check if confirmation is required
            if (
                hasattr(method, "confirmation_required")
                and method.confirmation_required
            ):
                # Format arguments as a readable string
                args_str = "\n".join(f"{k}={repr(v)}" for k, v in arguments.items())

                print(f"Do you want to execute {tool_name}? (y/n)")
                confirmation = readchar.readchar()

                # Check if user confirmed
                if confirmation.lower() not in ["y", "yes"]:
                    return {
                        "success": False,
                        "message": "Tool execution cancelled by user",
                    }

            result = method(**arguments)

            context.add_used_tool(
                tool_name=tool_name,
                params=arguments,
                result=result,
            )

            return result

    return {"success": False, "message": f"Unknown tool: {tool_name}"}
