import re
import ast
import inspect
import importlib
from ..interface import AbsChecker
from typing import List, Optional, Dict, Any, Set


class ClassType:
    """Represents a user-defined class in the analyzed code"""

    def __init__(self, name: str, class_info: Dict[str, Set[str]]):
        self.name = name
        self.attributes = class_info.get("attributes", set())
        self.methods = class_info.get("methods", set())

    @property
    def __name__(self):
        return self.name


class FunctionType:
    """Represents a user-defined function in the analyzed code"""

    def __init__(self, name: str, return_annotation=None):
        self.name = name
        self.return_annotation = return_annotation

    @property
    def __name__(self):
        return self.name

    def __call__(self, *args, **kwargs):
        return None


class AttributeAccessVisitor(ast.NodeVisitor):
    """
    AST visitor that finds all attribute accesses in the form 'instance.attribute'
    """

    def __init__(self):
        self.attribute_accesses = []
        self.variables = {}
        self.imports = {}
        self.current_scope = {}
        self.scopes = [self.current_scope]
        self.classes = {}  # Track class definitions
        self.current_class = None  # Track the current class being processed

    def visit_Attribute(self, node):
        """Visit attribute access nodes (instance.attribute)"""
        if isinstance(node.ctx, ast.Load):  # Only check attribute loading
            self.attribute_accesses.append(node)
        self.generic_visit(node)

    def visit_Import(self, node):
        """Track import statements"""
        for alias in node.names:
            module_name = alias.name
            asname = alias.asname or alias.name
            self.imports[asname] = module_name
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Track from-import statements"""
        module_name = node.module
        for alias in node.names:
            name = alias.name
            asname = alias.asname or alias.name
            self.imports[asname] = (module_name, name)
        self.generic_visit(node)

    def visit_Assign(self, node):
        """Track variable assignments to help determine types"""
        for target in node.targets:
            if isinstance(target, ast.Name) and isinstance(target.ctx, ast.Store):
                # Simple assignment like "x = value"
                self.current_scope[target.id] = node.value
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        """Track annotated assignments"""
        if isinstance(node.target, ast.Name):
            self.current_scope[node.target.id] = node.value
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """Handle function scope"""
        return_annotation = None
        if node.returns:
            # Extract return type annotation if available
            if isinstance(node.returns, ast.Name):
                return_annotation = node.returns.id
            elif isinstance(node.returns, ast.Constant):
                return_annotation = node.returns.value

        func_obj = FunctionType(node.name, return_annotation)
        self.current_scope[node.name] = func_obj

        old_scope = self.current_scope
        self.current_scope = {}
        self.scopes.append(self.current_scope)

        for arg in node.args.args:
            self.current_scope[arg.arg] = None

        self.generic_visit(node)
        self.current_scope = old_scope

    def visit_ClassDef(self, node):
        """Handle class scope and track class attributes"""
        old_scope = self.current_scope
        old_class = self.current_class

        self.current_scope = {}
        self.scopes.append(self.current_scope)
        self.current_class = node.name

        # Initialize class attributes
        class_attrs = {
            "methods": set(),
            "attributes": set(),
        }
        self.classes[node.name] = class_attrs

        # Visit all nodes in the class
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                # Add method name
                class_attrs["methods"].add(child.name)

                # Check if it's __init__ to find instance attributes
                if child.name == "__init__":
                    self._extract_init_attributes(child, class_attrs["attributes"])

            # Process other class-level assignments
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        class_attrs["attributes"].add(target.id)

        self.generic_visit(node)
        self.current_class = old_class
        self.current_scope = old_scope

    def _extract_init_attributes(self, init_node, attributes_set):
        """Extract instance attributes from __init__ method"""
        for stmt in init_node.body:
            # Look for self.attr = value assignments
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        attributes_set.add(target.attr)


class AttributeChecker(AbsChecker):
    """
    Checks if attribute accesses in Python code are valid.
    """

    def __init__(self):
        """
        Initialize with the Python code to check.

        Args:
            code_str (str): String containing Python code
        """
        self.tree = None
        self.visitor = None
        self.errors = []

    @property
    def name(self) -> str:
        return "Attribute Checker"

    def parse(self, code_str: str):
        """Parse the code string into an AST"""
        try:
            self.tree = ast.parse(code_str)
            self.visitor = AttributeAccessVisitor()
            self.visitor.visit(self.tree)
            return True
        except SyntaxError as e:
            self.errors.append(
                f'Syntax error: line {e.lineno}, offset {e.offset} ("{e.text}"): {e.msg}'
            )
            return False

    def _resolve_name_type(self, name_node: ast.Name, scope_idx=0) -> Optional[Any]:
        """
        Try to resolve the type of a name (variable).

        Args:
            name_node (ast.Name): AST node representing a name
            scope_idx (int): Index of the scope to check

        Returns:
            The type of the name, or None if it can't be determined
        """
        if scope_idx >= len(self.visitor.scopes) or not isinstance(name_node, ast.Name):
            return None

        var_name = name_node.id

        builtins_dict = (
            __builtins__.__dict__ if hasattr(__builtins__, "__dict__") else __builtins__
        )
        if var_name in builtins_dict:
            return type(builtins_dict[var_name])

        # Check if it's a class definition we've seen
        if var_name in self.visitor.classes:
            # Return a custom class type representation
            return ClassType(var_name, self.visitor.classes[var_name])

        # Check if it's an import
        if var_name in self.visitor.imports:
            import_info = self.visitor.imports[var_name]
            if isinstance(import_info, tuple):
                # from module import name
                module_name, attr_name = import_info
                try:
                    module = importlib.import_module(module_name)
                    if hasattr(module, attr_name):
                        attr_value = getattr(module, attr_name)
                        # Return the actual module/class, not just its type
                        return (
                            attr_value
                            if inspect.isclass(attr_value)
                            else type(attr_value)
                        )
                except (ImportError, AttributeError):
                    pass
            else:
                # import module
                try:
                    # Return the actual module, not its type
                    return importlib.import_module(import_info)
                except ImportError:
                    pass

        # Check in current scope
        curr_scope = self.visitor.scopes[scope_idx]

        if var_name in curr_scope:
            value_node = curr_scope[var_name]
            if value_node is None:
                # Try looking in parent scope
                return self._resolve_name_type(name_node, scope_idx + 1)

            # For simple cases like x = SomeClass()
            if isinstance(value_node, ast.Call):
                # Try to resolve the return type of the call
                call_return_type = self._resolve_call_return_type(value_node)
                if call_return_type:
                    return call_return_type

                func_node = value_node.func
                if isinstance(func_node, ast.Name):
                    # Try to get the type of the constructor
                    constructor_type = self._resolve_name_type(func_node, scope_idx)
                    if constructor_type:
                        if isinstance(constructor_type, ClassType):
                            # It's our custom class
                            return constructor_type
                        elif inspect.isclass(constructor_type):
                            # We're returning the class itself because we can't instantiate it without args
                            return constructor_type
                elif isinstance(func_node, ast.Attribute):
                    # Handle cases like datetime.now()
                    attr_type = self._resolve_attribute_type(func_node)
                    if attr_type:
                        return attr_type
            elif isinstance(value_node, FunctionType):
                basic_type = getattr(__builtins__, value_node.return_annotation, None)
                if basic_type:
                    return basic_type

        return self._resolve_name_type(name_node, scope_idx + 1)

    def _has_attribute(self, obj_type, attr_name):
        """
        Check if a type has a specific attribute.

        Args:
            obj_type: The type or object to check
            attr_name: The attribute name to look for

        Returns:
            True if the attribute exists, False otherwise
        """
        if obj_type is None:
            return False

        if isinstance(obj_type, ClassType):
            return attr_name in obj_type.attributes or attr_name in obj_type.methods

        if inspect.isclass(obj_type):
            # Check class attributes and instance attributes
            return hasattr(obj_type, attr_name) or any(
                hasattr(base, attr_name) for base in obj_type.__mro__
            )

        # Special case for modules
        if inspect.ismodule(obj_type):
            # For modules like os.path, directly check if attribute exists
            return hasattr(obj_type, attr_name)

        return hasattr(obj_type, attr_name)

    def check_attributes(self):
        """
        Check all attribute accesses in the code.

        Returns:
            List of errors found
        """
        if not self.tree or not self.visitor:
            return self.errors

        for attr_node in self.visitor.attribute_accesses:
            attr_name = attr_node.attr
            value_node = attr_node.value

            # Get source location for error reporting
            lineno = getattr(attr_node, "lineno", "?")
            col_offset = getattr(attr_node, "col_offset", "?")

            # Resolve the type of the object being accessed
            obj_type = None

            if isinstance(value_node, ast.Name):
                obj_type = self._resolve_name_type(value_node)
            elif isinstance(value_node, ast.Attribute):
                # Handle nested attributes like a.b.c
                obj_type = self._resolve_attribute_type(value_node)
            elif isinstance(value_node, ast.Call):
                # Handle method calls like func().attr
                func_type = None
                if isinstance(value_node.func, ast.Name):
                    func_type = self._resolve_name_type(value_node.func)
                elif isinstance(value_node.func, ast.Attribute):
                    func_type = self._resolve_attribute_type(value_node.func)

                if func_type and inspect.isclass(func_type):
                    obj_type = func_type

            # Check if the attribute exists
            if obj_type and not self._has_attribute(obj_type, attr_name):
                # Get a nice name for the object type
                type_name = (
                    obj_type.__name__
                    if hasattr(obj_type, "__name__")
                    else str(obj_type)
                )
                self.errors.append(
                    f"Line {lineno}, Col {col_offset}: '{attr_name}' is not a valid attribute for {type_name}"
                )

        return self.errors

    def _resolve_attribute_type(self, attr_node):
        """
        Resolve the type of an attribute access node.

        Args:
            attr_node: AST node representing an attribute access

        Returns:
            The type of the attribute, or None if it can't be determined
        """
        if isinstance(attr_node.value, ast.Name):
            obj = self._resolve_name_type(attr_node.value)
            if obj is not None:
                if hasattr(obj, attr_node.attr):
                    attr_value = getattr(obj, attr_node.attr)
                    # Handle case with module.attribute (like os.path)
                    if attr_value is not None:
                        return (
                            attr_value
                            if inspect.isclass(attr_value)
                            or inspect.ismodule(attr_value)
                            else type(attr_value)
                        )
        elif isinstance(attr_node.value, ast.Attribute):
            # Recursive case for nested attributes
            parent = self._resolve_attribute_type(attr_node.value)
            if parent is not None and hasattr(parent, attr_node.attr):
                attr_value = getattr(parent, attr_node.attr)
                # Return the actual module or class for further attribute resolution
                return (
                    attr_value
                    if inspect.isclass(attr_value) or inspect.ismodule(attr_value)
                    else type(attr_value)
                )
        elif isinstance(attr_node.value, ast.Call):
            # Handle method call return values like obj.method().attr
            return self._resolve_call_return_type(attr_node.value)

        return None

    def _resolve_call_return_type(self, call_node):
        """
        Try to determine the return type of a function/method call.

        Args:
            call_node (ast.Call): The AST call node

        Returns:
            The return type if determinable, None otherwise
        """
        if isinstance(call_node.func, ast.Name):
            # Direct function call like func()
            func_obj = self._resolve_name_type(call_node.func)
            if inspect.isclass(func_obj):
                return func_obj
            elif isinstance(func_obj, FunctionType) and func_obj.return_annotation:
                return_type = type(func_obj.return_annotation)
                if inspect.isclass(return_type):
                    return return_type

        elif isinstance(call_node.func, ast.Attribute):
            # Method call like obj.method()
            obj_node = call_node.func.value
            obj_type = None

            if isinstance(obj_node, ast.Name):
                obj_type = self._resolve_name_type(obj_node)
            elif isinstance(obj_node, ast.Attribute):
                obj_type = self._resolve_attribute_type(obj_node)

            if obj_type is not None:
                method_name = call_node.func.attr
                if hasattr(obj_type, method_name):
                    method = getattr(obj_type, method_name)
                    if callable(method) and hasattr(method, "__annotations__"):
                        return method.__annotations__.get("return")

        # If we can't determine the return type, just return None
        return None

    def check_attribute_access(self, code_str: str) -> List[str]:
        """
        Check a string of Python code for invalid attribute accesses.

        Args:
            code_str (str): String containing Python code

        Returns:
            List of error messages for invalid attribute accesses
        """
        if self.parse(code_str):
            return self.check_attributes()
        return self.errors

    def check(self, file_path: str) -> List[Dict[str, str]]:
        """
        Check the given code for invalid attribute accesses.

        Args:
            file_path (str): Path to the Python file to check

        Returns:
            out (List[Dict[str, Any]]): A list of dictionaries containing information about issues found.
                                 Each dictionary should typically contain information like:
                                 - 'line': line number of the issue
                                 - 'column': column number of the issue
                                 - 'problematic_code': code snippet that caused the issue
                                 - 'message': description of the issue
        """
        with open(file_path, "r") as file:
            code = file.read()

        self.errors = self.check_attribute_access(code)
        pattern = r"^Line (\d+), Col (\d+): (.*?)$"
        matches = [re.match(pattern, err) for err in self.errors]
        return [
            {
                "line": int(match.group(1)),
                "column": int(match.group(2)),
                "problematic_code": code.splitlines()[int(match.group(1)) - 1],
                "message": match.group(3),
            }
            for match in matches
            if match
        ]
