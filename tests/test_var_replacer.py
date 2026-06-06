import pytest
from nbrun.var_replacer import replace_vars
from typing import Any

def new_foo():
    return 999


@pytest.mark.parametrize(
    ("source", "vars_to_replace", "output"),
    [
        pytest.param("x = 5", {"x": 100}, "x = 100", id="global_var"),
        pytest.param("x: int = 5", {"x": 100}, "x: int = 100", id="annotated_global_var"),
        pytest.param("x = y = z = 5", {"x": 10, "y": 20, "z": 30}, "x = y = z = 30", id="chained_assignment"),
        pytest.param("def foo():\n    x = 5", {"foo:x": 100}, "def foo():\n    x = 100", id="var_in_function"),
        pytest.param("x = 1\ny = 2", {"x": 10, "y": 20}, "x = 10\ny = 20", id="multiple_vars"),
        pytest.param("def foo():\n    return 1", {"foo": new_foo}, "def foo():\n    return 999", id="replace_entire_func"),
        pytest.param("for i in range(10):\n    x = 5", {"for:x": 100}, "for i in range(10):\n    x = 100", id="var_in_for_loop"),
        pytest.param("while True:\n    y = 10", {"while:y": 200}, "while True:\n    y = 200", id="var_in_while_loop"),
        pytest.param("if True:\n    z = 15", {"if:z": 300}, "if True:\n    z = 300", id="var_in_if_block"),
        pytest.param("with open('f') as f:\n    data = 42", {"with:data": 999}, "with open('f') as f:\n    data = 999", id="var_in_with_block"),
        pytest.param("def foo():\n    for i in range(5):\n        x = 1", {"foo:for:x": 50}, "def foo():\n    for i in range(5):\n        x = 50", id="nested_scopes_func_for"),
    ],
)
def test_replace_vars(source: str, vars_to_replace: dict[str, Any], output: str):
    assert replace_vars(source, vars_to_replace) == output


