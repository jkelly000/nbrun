nbrun — run notebooks programmatically
====================================

# Purpose

nbrun helps run Jupyter notebooks (.ipynb) programmatically and deterministically. It is focused on three practical use cases:

- Automated testing: execute notebooks in CI and assert outputs or side effects.
- Deterministic runs: replace variables in exported source to control non-determinism (seeds, cached values).
- Headless execution: run notebooks without interactive Jupyter frontends (mocking display and other side effects).

Use cases and examples

## 1) Quick programmatic run

```python
from nbrun import 

nr = runner.NotebookRunner("notebook.ipynb")
module = nr.execute()
```


## 2) Testing notebook outputs in CI

```python
from nbrun import runner

nr = runner.NotebookRunner("notebook.ipynb")
module = nr.execute()
assert module.result == 42
```

## 3) Replace variable values for deterministic tests

```python
from nbrun import runner

replacements = {"global_seed": 123, "cached_result": expensive_value}
nr = runner.NotebookRunner("notebook.ipynb", vars_to_replace=replacements)
module = nr.execute()
```

This replaces the **value** assigned to variables, which includes function call results. For example, if a notebook contains:
```python
result = expensive_computation()
```

You can replace it with:
```python
vars_to_replace={"result": precomputed_value}
```

This skips the expensive function entirely—the variable just gets the precomputed value instead.

## 4) Mock external dependencies with unittest.mock

For external API calls and side effects, use `unittest.mock`:

```python
from unittest.mock import patch
from nbrun import runner

with runner.load_notebook("notebook.ipynb") as nr:
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"data": "mocked"}
        module = nr.execute()
        # Verify the API was called
        assert mock_get.called
```

For file I/O, variable replacement is usually cleaner—replace the file contents or path directly rather than mocking `open()`.

## 5) Use as a context manager or decorator (convenient in tests)

```python
from nbrun import runner


with runner.load_notebook("notebook.ipynb") as nr:
    nr.execute()
```

```python
from nbrun import runner

@runner.load_notebook("notebook.ipynb")
def test_notebook(nr):
    nr.execute()
```


# Why use nbrun?

* Keeps notebook execution in isolated temporary modules (no import collisions).
* Lets tests control non-determinism via AST-level replacements (no need to edit original notebooks).
* Mocks display to avoid interactive side effects when running headless.

# Installation

```bash
pip install nbrun
```

License

MIT
