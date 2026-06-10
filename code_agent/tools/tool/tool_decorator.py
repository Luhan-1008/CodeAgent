import inspect
import functools
from dataclasses import dataclass
from typing import Any, Callable, Optional, Type, Union, get_type_hints


@dataclass
class ParameterSpec:
    """Specification for a parameter in a tool function"""

    name: str
    type: Type
    description: str
    required: bool = True
    default: Any = None


def tool(
    name_or_func: Optional[Union[str, Callable]] = None,
    description: Optional[str] = None,
    confirmation_required: bool = False,
    group: str = "general",
):
    """
    Decorator to mark a function as a tool and provide OpenAI API tools format metadata.

    Args:
        name_or_func: Function or custom name for the tool
        description: Optional description (defaults to function docstring)
        confirmation_required: Whether user confirmation is required before execution
        group: Group/category this tool belongs to (default: "general")

    Returns:
        Decorated function with OpenAI tools metadata
    """
    # Handle case when decorator is used without parentheses @tool
    if callable(name_or_func):
        return _tool_impl(name_or_func)

    # Handle case when decorator is used with parentheses @tool(...) or @tool()
    name = name_or_func

    def decorator(func: Callable):
        return _tool_impl(
            func,
            name=name,
            description=description,
            confirmation_required=confirmation_required,
            group=group,
        )

    return decorator


def _tool_impl(
    func: Callable,
    name: Optional[str] = None,
    description: Optional[str] = None,
    confirmation_required: bool = False,
    group: str = "general",
):
    """
    Actual implementation of the tool decorator

    Args:
        func: The function to decorate
        name: Optional custom name for the tool
        description: Optional description
        confirmation_required: Whether user confirmation is required before execution
        group: Group/category this tool belongs to
    """
    func_name = name or func.__name__
    signature = inspect.signature(func)
    doc = inspect.getdoc(func) or ""
    func_description = description or (
        doc.split("\n\n")[0] if doc else f"Function {func_name}"
    )

    # Extract parameter specifications
    params = []
    for param_name, param in signature.parameters.items():
        if param_name == "self":
            continue

        is_required = param.default is inspect.Parameter.empty
        default_value = None if is_required else param.default

        # Try to find parameter description in docstring
        param_desc = ""
        if doc:
            doc_lines = doc.split("\n")
            for i, line in enumerate(doc_lines):
                if line.strip().startswith(f"{param_name}:"):
                    param_desc = line.split(":", 1)[1].strip()
                # Look for Args section format
                elif "Args:" in doc and line.strip().startswith(f"{param_name}:"):
                    param_desc = line.split(":", 1)[1].strip()
                # Look for parameters documented in the format param_name (type): description
                elif f"{param_name} (" in line:
                    param_desc = line.split(":", 1)[1].strip() if ":" in line else ""

        param_type = get_type_hints(func).get(param_name, str)

        params.append(
            ParameterSpec(
                name=param_name,
                type=param_type,
                description=param_desc,
                required=is_required,
                default=default_value,
            )
        )

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    # Attach OpenAI tools metadata
    wrapper.is_tool = True
    wrapper.tool_name = func_name
    wrapper.tool_description = func_description
    wrapper.tool_parameters = params
    wrapper.confirmation_required = confirmation_required
    wrapper.tool_group = group

    # Add a method to get OpenAI format
    def get_openai_schema():
        properties = {}
        required_params = []

        for param in params:
            # Skip the context parameter when generating schema for OpenAI API
            if param.name == "context":
                continue

            param_schema = {
                "type": _get_openai_type(param.type),
                "description": param.description,
            }

            if not param.required:
                param_schema["default"] = param.default
            else:
                required_params.append(param.name)

            properties[param.name] = param_schema

        schema = {
            "type": "function",
            "function": {
                "name": func_name,
                "description": func_description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required_params,
                },
            },
        }

        # Add confirmation metadata if required
        if confirmation_required:
            schema["function"]["confirmation_required"] = True

        return schema

    wrapper.get_openai_schema = get_openai_schema
    return wrapper


def _get_openai_type(python_type):
    """Convert Python types to OpenAI schema types"""
    if python_type == str:
        return "string"
    elif python_type == int:
        return "integer"
    elif python_type == float:
        return "number"
    elif python_type == bool:
        return "boolean"
    elif hasattr(python_type, "__origin__") and python_type.__origin__ == list:
        return "array"
    elif hasattr(python_type, "__origin__") and python_type.__origin__ == dict:
        return "object"
    else:
        return "string"  # Default fallback
