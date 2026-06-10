"""Extract the framework of a Python file, keeping only class and function signatures."""

import ast


def extract_framework(file_path: str) -> str:
    """
    Extract the framework of a Python file, keeping only class and function signatures.

    Args:
        file_path (str): Path to the Python file

    Returns:
        str: The framework of the file as a string
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        tree = ast.parse(content)
        framework_lines = []

        # Keep file-level docstrings
        if (
            len(tree.body) > 0
            and isinstance(tree.body[0], ast.Expr)
            and isinstance(tree.body[0].value, ast.Constant)
            and isinstance(tree.body[0].value.value, str)
        ):
            docstring = tree.body[0].value.value
            framework_lines.append(f'"""{docstring}"""')

        for node in tree.body:
            # Keep imports and global variables
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                framework_lines.append(ast.unparse(node))
            elif isinstance(node, ast.Assign):
                # Extract global variable assignments
                var_def = _extract_global_variable(node)
                if var_def:
                    framework_lines.append(var_def)
            elif isinstance(node, ast.AnnAssign):
                # Extract annotated global variable assignments
                var_def = _extract_annotated_global_variable(node)
                if var_def:
                    framework_lines.append(var_def)
            elif isinstance(node, ast.ClassDef):
                # Extract class definition with its decorators
                class_def = _extract_class_framework(node)
                framework_lines.append(class_def)
            elif isinstance(node, ast.FunctionDef):
                # Extract function definition with its decorators
                func_def = _extract_function_framework(node)
                framework_lines.append(func_def)
            elif isinstance(node, ast.AsyncFunctionDef):
                # Extract async function definition with its decorators
                async_func_def = _extract_async_function_framework(node)
                framework_lines.append(async_func_def)

        return "\n".join(framework_lines)

    except Exception as e:
        return f"Error extracting framework: {str(e)}"


def _extract_global_variable(node):
    """Extract global variable assignments without their values"""
    try:
        # Handle multiple assignments in one statement (e.g., a = b = 1)
        target_names = []
        for target in node.targets:
            if isinstance(target, ast.Name):
                target_names.append(target.id)
            elif isinstance(target, ast.Tuple):
                for elt in target.elts:
                    if isinstance(elt, ast.Name):
                        target_names.append(elt.id)

        if target_names:
            return ", ".join(target_names)
        return None
    except:
        return None


def _extract_annotated_global_variable(node):
    """Extract annotated global variable assignments with type annotations but without values"""
    try:
        if isinstance(node.target, ast.Name):
            var_name = node.target.id
            if node.annotation:
                annotation = ast.unparse(node.annotation)
                return f"{var_name}: {annotation}"
            return var_name
        return None
    except:
        return None


def _extract_class_framework(class_node):
    """Extract a class definition with its methods but without implementations."""
    # Get class definition line with decorators
    decorators = [ast.unparse(decorator) for decorator in class_node.decorator_list]
    decorator_text = "\n".join(f"@{decorator}" for decorator in decorators)
    if decorator_text:
        decorator_text += "\n"

    # Class signature
    class_def = f"{decorator_text}class {class_node.name}"
    if class_node.bases:
        bases = ", ".join(ast.unparse(base) for base in class_node.bases)
        class_def += f"({bases})"
    else:
        class_def += "()"
    class_def += ":"

    # Class docstring
    class_body = []
    if (
        len(class_node.body) > 0
        and isinstance(class_node.body[0], ast.Expr)
        and isinstance(class_node.body[0].value, ast.Constant)
        and isinstance(class_node.body[0].value.value, str)
    ):
        docstring = class_node.body[0].value.value
        class_body.append(f'    """{docstring}"""')

    # Class methods and attributes
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef):
            method_def = _extract_function_framework(node, indent=4)
            class_body.append(method_def)
        elif isinstance(node, ast.AsyncFunctionDef):
            async_method_def = _extract_async_function_framework(node, indent=4)
            class_body.append(async_method_def)
        elif isinstance(node, ast.ClassDef):
            nested_class_def = _extract_class_framework(node)
            class_body.append("    " + nested_class_def.replace("\n", "\n    "))

    # If no body, add a pass statement
    if not class_body:
        class_body.append("    pass")

    return class_def + "\n" + "\n\n".join(class_body)


def _extract_function_framework(func_node, indent=0):
    """Extract a function definition without its implementation."""
    indent_str = " " * indent

    # Get function decorators
    decorators = [ast.unparse(decorator) for decorator in func_node.decorator_list]
    decorator_text = "\n".join(f"{indent_str}@{decorator}" for decorator in decorators)
    if decorator_text:
        decorator_text += "\n"

    # Function signature
    func_def = f"{decorator_text}{indent_str}def {func_node.name}("

    # Function arguments
    args = []
    for arg in func_node.args.args:
        if arg.annotation:
            args.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
        else:
            args.append(arg.arg)

    # Handle varargs
    if func_node.args.vararg:
        if func_node.args.vararg.annotation:
            args.append(
                f"*{func_node.args.vararg.arg}: {ast.unparse(func_node.args.vararg.annotation)}"
            )
        else:
            args.append(f"*{func_node.args.vararg.arg}")

    # Handle keyword-only args
    if func_node.args.kwonlyargs:
        if not func_node.args.vararg:
            args.append("*")
        for kwarg in func_node.args.kwonlyargs:
            if kwarg.annotation:
                args.append(f"{kwarg.arg}: {ast.unparse(kwarg.annotation)}")
            else:
                args.append(kwarg.arg)

    # Handle kwargs
    if func_node.args.kwarg:
        if func_node.args.kwarg.annotation:
            args.append(
                f"**{func_node.args.kwarg.arg}: {ast.unparse(func_node.args.kwarg.annotation)}"
            )
        else:
            args.append(f"**{func_node.args.kwarg.arg}")

    func_def += ", ".join(args) + ")"

    # Return type annotation
    if func_node.returns:
        func_def += f" -> {ast.unparse(func_node.returns)}"

    func_def += ":"

    # Function docstring
    if (
        len(func_node.body) > 0
        and isinstance(func_node.body[0], ast.Expr)
        and isinstance(func_node.body[0].value, ast.Constant)
        and isinstance(func_node.body[0].value.value, str)
    ):
        docstring = func_node.body[0].value.value
        func_def += f'\n{indent_str}    """' + docstring + '"""'

    # Add pass statement
    func_def += f"\n{indent_str}    pass"

    return func_def


def _extract_async_function_framework(func_node, indent=0):
    """Extract an async function definition without its implementation."""
    indent_str = " " * indent

    # Get function decorators
    decorators = [ast.unparse(decorator) for decorator in func_node.decorator_list]
    decorator_text = "\n".join(f"{indent_str}@{decorator}" for decorator in decorators)
    if decorator_text:
        decorator_text += "\n"

    # Function signature
    func_def = f"{decorator_text}{indent_str}async def {func_node.name}("

    # Function arguments (same as for regular functions)
    args = []
    for arg in func_node.args.args:
        if arg.annotation:
            args.append(f"{arg.arg}: {ast.unparse(arg.annotation)}")
        else:
            args.append(arg.arg)

    if func_node.args.vararg:
        if func_node.args.vararg.annotation:
            args.append(
                f"*{func_node.args.vararg.arg}: {ast.unparse(func_node.args.vararg.annotation)}"
            )
        else:
            args.append(f"*{func_node.args.vararg.arg}")

    if func_node.args.kwonlyargs:
        if not func_node.args.vararg:
            args.append("*")
        for kwarg in func_node.args.kwonlyargs:
            if kwarg.annotation:
                args.append(f"{kwarg.arg}: {ast.unparse(kwarg.annotation)}")
            else:
                args.append(kwarg.arg)

    if func_node.args.kwarg:
        if func_node.args.kwarg.annotation:
            args.append(
                f"**{func_node.args.kwarg.arg}: {ast.unparse(func_node.args.kwarg.annotation)}"
            )
        else:
            args.append(f"**{func_node.args.kwarg.arg}")

    func_def += ", ".join(args) + ")"

    # Return type annotation
    if func_node.returns:
        func_def += f" -> {ast.unparse(func_node.returns)}"

    func_def += ":"

    # Function docstring
    if (
        len(func_node.body) > 0
        and isinstance(func_node.body[0], ast.Expr)
        and isinstance(func_node.body[0].value, ast.Constant)
        and isinstance(func_node.body[0].value.value, str)
    ):
        docstring = func_node.body[0].value.value
        func_def += f'\n{indent_str}    """' + docstring + '"""'

    # Add pass statement
    func_def += f"\n{indent_str}    pass"

    return func_def
