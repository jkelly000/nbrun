nbrun — run notebooks programmatically
====================================

While much easier for non-technical users to run, Jupyter notebooks can be tricky to test.
User requirements shift, external libraries change and, without tests, bugs can often surface.

nbrun helps developers write unit tests for notebooks which are easy to write and run.

# How is nbrun different?

Most approaches to unit-testing Jupyter notebooks involve either:
1) Writing unit tests within Jupyter notebooks themselves
2) Writing unit tests outside of Jupyter notebooks and using a Jupyter kernel to run the notebooks (e.g. [Testbook](https://pypi.org/project/testbook/))
3) Writing notebooks where the heavy lifting happens in .py files which get imported - the unit tests then cover these .py files.

## No Jupyter Kernel
nbrun doesn't use a Jupyter kernel - tests run in the active Python environment, meaning you can debug the exported notebook code line by line.

This also lets you make assertions on the final state of variables from the notebook, in addition to any files that may have been written.

## Variable replacement
Python notebooks are often structured with constants at the top of the file which are passed into functions or API calls further down the notebook. These can't be neatly overwritten for testing using patching.

Instead of creating multiple copies of a notebook to do testing, having to keep them in sync, nbrun lets you test a notebook from a unit test, modifying the source code before it gets executed.


## How to use

<!-- pytestmark: pytestrun -->
```python name=test_context
from nbrun import runner

def test_notebook() -> None:
    # context manager converts the notebook file to Python source code
    with runner.Notebook("tests/test_data/notebook.ipynb") as nr:
        # This line executes the source code,
        # with the return value of 'execute' holding all variables
        # from the notebook.
        result = nr.execute()

    assert result.result == 3
```

## Mocking external dependencies with unittest.mock

For external API calls and side effects, you can combine nbrun with `unittest.mock.patch`:

<!-- pytestmark: pytestrun -->
```python name=test_requests_mock
from unittest.mock import patch
from nbrun import runner

def test_notebook() -> None:
    with runner.Notebook("tests/test_data/notebook_requests.ipynb") as nr:
        with patch("requests.get") as mock_get:
            mock_get.return_value.text = "foobar"
            result = nr.execute()
            # Verify the mocked function was called.
            assert mock_get.called
            assert result.text == "foobar" 
```

## Overriding values before execution

Python notebooks often contain variables at the top level, which have module-global scope.

```python
INPUT_STR = "FOO"
```
`unittest.mock.patch` can replace module globals, but a notebook's top-level code runs when the module is executed. Patching a value after that execution is too late to affect code that has already run, and a top-level assignment would overwrite a patch made beforehand.

Rather than creating multiple copies of a notebook, nbrun lets you replace variable values in the source code before it gets executed.
This should be used with caution.

To replace variable values, pass in a dictionary where the keys are the variable names (case-sensitive)
and the values are the values to be used.
If a target has multiple assignments in the same scope, `nbrun` raises a `ValueError` rather than
replacing an ambiguous assignment.

<!-- pytestmark: pytestrun -->
```python name=test_replace_global_var
import pytest
from nbrun import runner

@pytest.mark.parametrize(
    ("replacement_value", "expected"),
    [("FOOBAR", "FOOBAR"), ("BARBAZ", "BARBAZ")],
)
def test_notebook_with_replacement(replacement_value: str, expected: str) -> None:
    with runner.Notebook(
        "tests/test_data/notebook.ipynb",
        vars_to_replace={"INPUT_STR": replacement_value},
    ) as nr:
        result = nr.execute()

    assert result.INPUT_STR == expected
```

Parameterizing the replacement checks several controlled input values against the same notebook, without maintaining copies of the notebook.

`vars_to_replace` can also skip a function call by replacing the variable that would receive its return value. It replaces the assignment, not the function itself.

If we have in a notebook:
```python

def calc(a: int, b: int) -> int:
    return sum((a, b))

result = calc(a, b)
```
In a real scenario, this might take a long time to run, or cost money.

We can avoid calling the `calc` function by replacing `result`:

<!-- pytestmark: pytestrun -->
```python name=test_var_replacement_avoid_function
from nbrun import runner

def test_notebook() -> None:    
    NB_PATH = "tests/test_data/notebook.ipynb"
    
    # Without the variable replacement, the 'calc' function gets called.
    with runner.Notebook(NB_PATH) as nr:
        result = nr.execute()
        assert result.result == 3
    
    # With the variable replacement, result is declared as an integer and the calc function
    # is never called.
    with runner.Notebook(NB_PATH, vars_to_replace={"result": 5}) as nr:
        result = nr.execute()
        assert result.result == 5
```


We can also replace variables defined within notebook function bodies:


```python
def computation(n: int):
    var_x = 6
    return var_x * n

result = computation(6)
```
We can just replace the value of `var_x` within the function body
and call the modified definition of the `computation` function:

<!-- pytestmark: pytestrun -->
```python name=test_replace_var_in_function
from nbrun import runner

def test_notebook() -> None:
    with runner.Notebook(
        "tests/test_data/notebook_var_in_function.ipynb", vars_to_replace={"computation:var_x": 1}
    ) as nr:
        result = nr.execute()
        assert result.result == 6
```
nbrun handles the changes to `sys.path` required for this code to run as is.

## Supports notebooks which import .py files
Although an aim of nbrun is to avoid developers moving code to separate .py files solely for testability,
sometimes this is useful for reasons e.g. copy-pasting between code bases, letting multiple notebooks in a directory access shared code etc. 

nbrun supports this out of the box.

For example, in a notebook:
```python
import utils

result = utils.calc(4, 6)
display(result)
```

In a separate .py file in the same directory / subdirectory:
```python
def calc(foo: int, bar: int) -> int:
    return foo // bar
```

# Limitations and caveats

`nbrun` executes notebooks as ordinary Python modules, not as a live Jupyter session. That is the core trade-off: the result is easier to test and debug in Python, but it is not a full notebook runtime.

The following are not supported:
* IPython-specific syntax such as line magics (`%time`), cell magics (`%%bash`), shell escapes (`!echo hello`), and help syntax (`result?`)
* cell-by-cell execution semantics; the notebook is treated as a single Python module
* arbitrary dynamic rewrites of notebook state; replacements are deliberately limited to constant values

`display()` is mocked out, which is usually the right behavior in tests, but it means notebook-only display behavior is not executed.

If your workflow depends on a rich interactive notebook environment, `nbrun` is not meant to replace that experience. It is intended for deterministic automation and testability.

# Installation

```bash
pip install nbrun
```
