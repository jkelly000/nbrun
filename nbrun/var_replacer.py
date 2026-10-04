"""Replace selected variable assignments in Python source code."""

import ast
from typing import Any, TypeVar, cast

T = TypeVar("T", bound=ast.AST)


class VarReplacer(ast.NodeTransformer):
    """Replace variable assignment values in an AST."""

    def __init__(self, vars_to_replace: dict[str, Any]):
        """Initialize the transformer and validate all requested replacement values."""
        self.vars_to_replace = vars_to_replace
        self.scope_stack: list[str] = []  # Track current function/class scope
        # Validate all replacements upfront
        self._validate_replacements()

    def _get_full_path(self, name: str) -> str:
        """Return the variable name qualified by the currently visited scopes."""
        return ":".join(self.scope_stack + [name])

    def _is_constant(self, value: Any) -> bool:
        """Return whether a value is one of the supported constant types."""
        if value is None or isinstance(value, (bool, int, float, str, bytes)):
            return True
        if isinstance(value, (tuple, frozenset)):
            return all(self._is_constant(v) for v in value)
        return False

    def _validate_replacements(self) -> None:
        """Reject callable and non-constant replacement values."""
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
        """Replace the value of an assignment whose target matches a configured name."""
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
        """Replace the value of a matching annotated assignment."""
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
        """Visit a scope's contents while qualifying names with its scope label."""
        self.scope_stack.append(scope_name)
        node = cast(T, self.generic_visit(node))
        self.scope_stack.pop()
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit a function body using its name as the replacement scope."""
        # Visit the function body for variable replacements (e.g., "func:var": 123)
        # but don't replace the function definition itself
        node = self._visit_scope(node, node.name)
        return node

    def visit_For(self, node: ast.For) -> ast.For:
        """Visit a for-loop body using ``for`` as its replacement scope."""
        return self._visit_scope(node, "for")

    def visit_While(self, node: ast.While) -> ast.While:
        """Visit a while-loop body using ``while`` as its replacement scope."""
        return self._visit_scope(node, "while")

    def visit_If(self, node: ast.If) -> ast.If:
        """Visit an if statement's branches using ``if`` as their replacement scope."""
        return self._visit_scope(node, "if")

    def visit_With(self, node: ast.With) -> ast.With:
        """Visit a with statement's body using ``with`` as its replacement scope."""
        return self._visit_scope(node, "with")


def replace_vars(source: str, vars_to_replace: dict[str, Any]) -> str:
    """Return Python source with configured assignments replaced by constants.

    Replacement keys may be unqualified global names or colon-separated scope
    paths, such as ``"calculate:seed"``.
    """
    module = ast.parse(source)
    VarReplacer(vars_to_replace=vars_to_replace).visit(module)
    return ast.unparse(module)
