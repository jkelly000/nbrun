import ast
from typing import Any, TypeVar
import inspect

T = TypeVar("T", bound=ast.AST)


class VarReplacer(ast.NodeTransformer):
    """Replace variable assignment values in an AST."""

    def __init__(self, vars_to_replace: dict[str, Any]):
        self.vars_to_replace = vars_to_replace
        self.scope_stack = []  # Track current function/class scope

    def _get_full_path(self, name: str) -> str:
        """Build hierarchical path: 'func:var' or 'class:func:var'"""
        return ":".join(self.scope_stack + [name])

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
        node = self.generic_visit(node)
        self.scope_stack.pop()
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if node.name in self.vars_to_replace:
            replacement = self.vars_to_replace[node.name]
            if callable(replacement):
                func_def: ast.FunctionDef = ast.parse(
                    inspect.getsource(replacement)
                ).body[0]
                # Rename the function so it can work as a drop-in replacement
                func_def.name = node.name
                return func_def
            raise ValueError

        else:
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
