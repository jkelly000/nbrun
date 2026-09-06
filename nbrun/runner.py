import importlib.util
import warnings
from nbconvert import PythonExporter
from pathlib import Path
from hashlib import sha256
from unittest import mock
from typing import Any, Callable
from types import ModuleType

from .var_replacer import replace_vars

from tempfile import TemporaryDirectory


class Notebook:
    def __init__(
        self, path: str | Path, vars_to_replace: dict[str, Any] | None = None
    ) -> None:
        self._path = path if isinstance(path, Path) else Path(path)
        self._vars_to_replace = vars_to_replace or {}
        self._temp_dir = TemporaryDirectory()
        self.py_path = self._ipynb_to_py()
        self.modified_py_path = self._modify_vars()
        self._module: ModuleType | None = None
        self._execute_module: Callable[[ModuleType], None] | None = None
        self._load_module()

    def _ipynb_to_py(self) -> Path:
        """
        Given a path of a Jupyter Notebook, export it as a Python file
        to the specified path, without any modification.
        """
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
        with open(str(self.py_path), "r") as fh:
            modified_source = replace_vars(fh.read(), self._vars_to_replace)
        out_path = Path(self._temp_dir.name) / self.py_path.with_stem(
            f"{self.py_path.stem}_modified"
        )
        with open(str(out_path), "w") as fh:
            fh.write(modified_source)
        return out_path

    def _load_module(self) -> None:
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
        if self._module is None or self._execute_module is None:
            raise ValueError("Call load_module first")
        self._execute_module(self._module)
        return self._module

    def cleanup(self) -> None:
        self._temp_dir.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup on exit."""
        self.cleanup()
        return False
