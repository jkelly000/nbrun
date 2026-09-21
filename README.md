nbrun — run notebooks programmatically
====================================

# Purpose

While much easier for non-technical users to run, Jupyter notebooks are not trivial to test.
User requirements shift, external libraries change and, without tests, bugs can often surface.

The aim of nbrun is help developers write unit tests which are easy to write and run.

# What makes nbrun different to other approaches to testing Jupyter notebooks?

Most approaches to unit-testing Jupyter notebooks involve either:
1) Writing unit tests within Jupyter notebooks themselves
2) Writing unit tests outside of Jupyter notebooks and using a Jupyter kernel to run the notebooks (e.g. [Testbook](https://pypi.org/project/testbook/))
3) Writing notebooks where the heavy lifting happens in .py files which get imported - the unit tests then cover these .py files.

All of these are valid approaches, but nbrun:
* doesn't need a Jupyter kernel - it uses the active Python environment, allowing you to debug line by line within the notebook code
* lets you test notebooks without significantly rewriting notebooks just to gain test coverage


## How to use

```python
from nbrun import runner

def test_notebook() -> None:
    # context manager converts the notebook file to Python source code
    with runner.Notebook("notebook.ipynb") as nr:
        # This line executes the source code,
        # with the return value of 'execute' holding all variables
        # from the notebook.
        result = nr.execute()

    assert result.result == 5
```

## Mocking external dependencies with unittest.mock

For external API calls and side effects, you can combine nbrun with `unittest.mock.patch`:

```python
from unittest.mock import patch
from nbrun import runner

def test_notebook() -> None:
    with runner.Notebook("notebook.ipynb") as nr:
        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = {"data": "mocked"}
            module = nr.execute()
            # Verify the API was called
            assert mock_get.called
```

For file I/O, variable replacement is usually cleaner—replace the file contents or path directly rather than mocking `open()`.

## Overriding values that unittest.mock can't reach.

Python notebooks will often contain variables at the top level of the notebook which take a global scope.

```python
GLOBAL_VAR = 500
```
This can't be patched with unittest, even after we've converted the Python notebook to Python source code.
Rather than creating multiple copies a notebook, nbrun allows you to replace variable values in the actual source code
before it gets executed.
This should be used with caution.

To replace variable values, pass in a dictionary where the keys are the variable names (case-sensitive)
and the values are the values to be used.

```python
from nbrun import runner

def test_notebook():
    with runner.Notebook("notebook.ipynb", vars_to_replace={"GLOBAL_VAR": 123}) as nr:
        result = nr.execute()
        assert result.GLOBAL_VAR == 123
```

`vars_to_replace` can also be used to replace function calls, but assigning a new value
to the variable which the function's return value is assigned to.

If we have in a notebook:
```python

def expensive_computation():
    return 999

result = expensive_computation()
```

We can avoid calling the `expensive_computation` function by setting `vars_to_replace` as:
```python

def test_notebook() -> None:
    with runner.Notebook("notebook.ipynb", vars_to_replace={"result": 5}) as nr:
        result = nr.execute()
        assert result.result == 5

```


We can also replace variables that are defined within in-notebook function bodies:
```python
def computation():
    var_x = 6
    return var_x

result = computation()
```
We can just replace the value of `var_x` within the function body
and call the modified definition of the `computation` function:

```python

def test_notebook() -> None:
    with runner.Notebook("notebook.ipynb", vars_to_replace={"computation:var_x": 1}) as nr:
        result = nr.execute()
        assert result.result == 1

```

## Supports notebooks which import .py files
Although an aim of nbrun is to avoid developers moving code to separate .py files solely for testability,
sometimes this is useful for reasons e.g. copy-pasting between code bases, letting multiple notebooks in a directory access shared code etc. 

nbrun supports this out of the box.

For example, in a notebook:
```python
result = computation()
```

In a separate .py file in the same directory / subdirectory:
```python
def computation():
    return 6
```

# Limitations

`nbrun` executes notebooks as ordinary Python modules rather than through a
Jupyter kernel.

The following are not supported:
* IPython-specific features, such as:
  * line magics (`%time`)
  * cell magics (`%%bash`)
  * shell escapes (`!echo hello`)
  * help syntax (`result?`)
* executing notebook code cell by cell
  * nbrun has no concept of 'cells' as all Python code in a notebook is glued together

Given how commonly used it is, calls to `display()` is mocked out, but this is currently the only
notebook-specific feature that is not rejected.

# Installation

```bash
pip install nbrun
```
