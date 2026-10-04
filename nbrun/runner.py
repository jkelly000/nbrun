"""Convert notebooks to Python modules and execute them without a Jupyter kernel."""

import importlib.util
import json
import sys
import warnings
from collections.abc import Iterable
from nbconvert import PythonExporter
from pathlib import Path
from hashlib import sha256
from unittest import mock
from typing import Any, Callable
from types import ModuleType

from .var_replacer import replace_vars

from tempfile import TemporaryDirectory


def find_ipython_feature(line: str) -> str | None:
    """Return the IPython-only feature used on a source line, if any."""
    if line.startswith("%%"):
        return "cell_magic"
    if line.startswith("%"):
        return "line_magic"
    if line.startswith("!"):
        return "shell_escape"
    if line.startswith("?") or line.endswith("?"):
        return "help_syntax"
    return None


def detect_ipython_features(path: str | Path) -> set[str]:
    """Return IPython-only syntax used by code cells in a notebook.

    The returned feature names are ``"cell_magic"``, ``"line_magic"``,
    ``"shell_escape"``, and ``"help_syntax"``.  This inspects the original
    notebook source because nbconvert may rewrite these constructs before they
    can be identified reliably.
    """
    notebook_path = path if isinstance(path, Path) else Path(path)
    with notebook_path.open(encoding="utf-8") as notebook_file:
        notebook = json.load(notebook_file)

    features: set[str] = set()
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = _cell_source(cell.get("source", ""))
        for line in source:
            feature = find_ipython_feature(line.strip())
            if feature is not None:
                features.add(feature)
    return features


def _cell_source(source: str | Iterable[str]) -> list[str]:
    """Normalize a notebook cell's source representation into lines."""
    if isinstance(source, str):
        return source.splitlines()
    return list(source)


class Notebook:
    """Prepare and execute a notebook as a Python module.

    IPython-specific syntax is rejected, and optional variable replacements are
    applied to the exported source before it is loaded. Use this class as a
    context manager or call :meth:`cleanup` to remove its temporary files.
    """

    def __init__(
        self, path: str | Path, vars_to_replace: dict[str, Any] | None = None
    ) -> None:
        """Validate a notebook path, export it, apply replacements, and load it.

        Args:
            path: Path to an ``.ipynb`` notebook.
            vars_to_replace: Optional mapping of variable names or scoped paths
                to constant values used in place of their assignments.

        Raises:
            ValueError: If the path does not exist or is not an ``.ipynb`` file.
            NotImplementedError: If a code cell contains unsupported
                IPython-specific syntax.
        """
        self._path = path if isinstance(path, Path) else Path(path)
        if not self._path.exists():
            raise ValueError(f"No file found at {self._path}.")
        if not self._path.suffix == ".ipynb":
            raise ValueError(
                f"Expecting file to have .ipynb suffix. Got {self._path.suffix}."
            )
        ipython_features = detect_ipython_features(self._path)
        if ipython_features:
            raise NotImplementedError(
                f"Notebook at {self._path} does not support iPython features. Detected: {ipython_features}."
            )
        self._vars_to_replace = vars_to_replace or {}
        self._temp_dir = TemporaryDirectory()
        self.py_path = self._ipynb_to_py()
        self.modified_py_path = self._modify_vars()
        self._module: ModuleType | None = None
        self._execute_module: Callable[[ModuleType], None] | None = None
        self._load_module()

    def _ipynb_to_py(self) -> Path:
        """Export the notebook to an unmodified Python file in the temp directory."""
        python_exporter = PythonExporter()

        out_path = Path(self._temp_dir.name) / self._path.with_suffix(".py").name

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="IPython is needed to transform IPython syntax to pure Python. Install ipython if you need this functionality.",
                category=UserWarning,
            )
            py_source, _ = python_exporter.from_filename(str(self._path))
        with open(str(out_path), "w") as fh:
            fh.write(py_source)
        return out_path

    def _modify_vars(self) -> Path:
        """Write and return the exported Python file with variable replacements applied."""
        with open(str(self.py_path), "r") as fh:
            modified_source = replace_vars(fh.read(), self._vars_to_replace)
        out_path = Path(self._temp_dir.name) / self.py_path.with_stem(
            f"{self.py_path.stem}_modified"
        )
        with open(str(out_path), "w") as fh:
            fh.write(modified_source)
        return out_path

    def _load_module(self) -> None:
        """Create the notebook module and prepare its loader for later execution."""
        # Defensive runtime check: modified_py_path should always be set by modify_vars.
        # If this check ever triggers it's a bug in the construction flow, so raise a
        # clear error. This is not expected during normal operation.
        if self.modified_py_path is None:
            raise ValueError("modified_py_path is unexpectedly None")
        # Take a hash of the filepath as the module name
        module_name = sha256(str(self.modified_py_path).encode("utf-8")).hexdigest()[
            10:
        ]
        spec = importlib.util.spec_from_file_location(
            module_name, str(self.modified_py_path)
        )
        # Defensive runtime validation: importlib may return None for spec or loader in
        # unusual environments. In normal use with a valid Python file this should
        # never happen. The explicit check both makes the failure mode clear at
        # runtime and satisfies the type checker.
        if spec is None or spec.loader is None:
            raise ValueError("Could not create module spec or loader")
        module = importlib.util.module_from_spec(spec)
        setattr(module, "display", mock.MagicMock())
        self._module = module
        loader = spec.loader
        # loader.exec_module is a callable used to execute the module; keep its type clear
        self._execute_module = loader.exec_module
        return None

    def execute(self) -> ModuleType:
        """Execute the prepared notebook module and return it with its variables.

        The notebook's containing directory is temporarily added to ``sys.path``
        so imports of nearby Python files work during execution.
        """
        if self._module is None or self._execute_module is None:
            raise ValueError("Call load_module first")

        # Add the notebook directory to sys.path so that local
        # imports work as expected.
        # This modifies imports globally, so we take a copy of the list
        # and restore it after we finish executing.
        notebook_dir = str(self._path.resolve().parent)
        original_sys_path = sys.path.copy()
        sys.path.insert(0, notebook_dir)
        try:
            self._execute_module(self._module)
        finally:
            sys.path[:] = original_sys_path
        return self._module

    def cleanup(self) -> None:
        """Remove the temporary exported and modified Python files."""
        self._temp_dir.cleanup()

    def __enter__(self):
        """Return this notebook runner for use in a ``with`` statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up temporary files when leaving a ``with`` statement."""
        self.cleanup()
        return False
