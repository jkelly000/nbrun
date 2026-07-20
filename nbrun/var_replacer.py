import ast
from typing import Any, TypeVar, cast

T = TypeVar("T", bound=ast.AST)


class VarReplacer(ast.NodeTransformer):
    """Replace variable assignment values in an AST."""

    def __init__(self, vars_to_replace: dict[str, Any]):
        self.vars_to_replace = vars_to_replace
        self.scope_stack: list[str] = []  # Track current function/class scope
        # Validate all replacements upfront
        self._validate_replacements()

    def _get_full_path(self, name: str) -> str:
        """Build hierarchical path: 'func:var' or 'class:func:var'"""
        return ":".join(self.scope_stack + [name])

    def _is_constant(self, value: Any) -> bool:
        """Check if a value can be represented as an ast.Constant."""
        if value is None or isinstance(value, (bool, int, float, str, bytes)):
            return True
        if isinstance(value, (tuple, frozenset)):
            return all(self._is_constant(v) for v in value)
        return False

    def _validate_replacements(self) -> None:
        """Validate that all replacements are usable."""
        for key, value in self.vars_to_replace.items():
            if callable(value):
                raise ValueError(
                    f"Replacement for '{key}' is a callable. "
                    f"Only constant values are supported (int, str, bool, None, tuple, frozenset)."
                )
            if not self._is_constant(value):
                raise ValueError(
                    f"Replacement for '{key}' is not a constant. Got {type(value).__name__}. "
                    f"Only constant values are supported (int, str, bool, None, tuple, frozenset)."
                )

    def visit_Assign(self, node: ast.Assign) -> ast.Assign:
        # Check if any target matches our replacement dict
        for target in node.targets:
            if isinstance(target, ast.Name):
                full_path = self._get_full_path(target.id)
                if full_path in self.vars_to_replace:
                    # Replace the value with a constant
                    new_value = self.vars_to_replace[full_path]
                    node.value = ast.Constant(value=new_value)
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AnnAssign:
        # Handle annotated assignments: x: int = 5
        # Check if any target matches our replacement dict

        if isinstance(node.target, ast.Name):
            full_path = self._get_full_path(node.target.id)
            if full_path in self.vars_to_replace:
                # Replace the value with a constant
                new_value = self.vars_to_replace[full_path]
                node.value = ast.Constant(value=new_value)
        return node

    def _visit_scope(self, node: T, scope_name: str) -> T:
        self.scope_stack.append(scope_name)
        node = cast(T, self.generic_visit(node))
        self.scope_stack.pop()
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        # Visit the function body for variable replacements (e.g., "func:var": 123)
        # but don't replace the function definition itself
        node = self._visit_scope(node, node.name)
        return node

    def visit_For(self, node: ast.For) -> ast.For:
        return self._visit_scope(node, "for")

    def visit_While(self, node: ast.While) -> ast.While:
        return self._visit_scope(node, "while")

    def visit_If(self, node: ast.If) -> ast.If:
        return self._visit_scope(node, "if")

    def visit_With(self, node: ast.With) -> ast.With:
        return self._visit_scope(node, "with")


def replace_vars(source: str, vars_to_replace: dict[str, Any]) -> str:
    module = ast.parse(source)
    VarReplacer(vars_to_replace=vars_to_replace).visit(module)
    return ast.unparse(module)
