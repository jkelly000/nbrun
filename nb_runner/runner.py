import importlib.util
from nbconvert import PythonExporter
from pathlib import Path
from hashlib import sha256
from unittest import mock
from typing import Any, Callable
import functools

from .var_replacer import replace_vars

from tempfile import TemporaryDirectory




class NotebookRunner:
    def __init__(self, notebook_path: str | Path, vars_to_replace: dict[str, Any] | None = None) -> None:
        self.notebook_path = notebook_path if isinstance(notebook_path, Path) else Path(notebook_path)
        self.vars_to_replace = vars_to_replace or {}
        self.temp_dir = TemporaryDirectory()
        self.py_path = self.ipynb_to_py()
        self.modified_py_path = self.modify_vars()
        self.module = None
        self.execute_module = None
        self.load_module()

    def ipynb_to_py(self) -> Path:
        """
        Given a path of a Jupyter Notebook, export it as a Python file
        to the specified path, without any modification.
        """
        python_exporter = PythonExporter()

        out_path = Path(self.temp_dir.name) / self.notebook_path.with_suffix(".py").name

        py_source,_ = python_exporter.from_filename(str(self.notebook_path))
        with open(str(out_path), "w") as fh:
            fh.write(py_source)
        return out_path

    def modify_vars(self) -> Path:
        with open(str(self.py_path), "r") as fh:
            modified_source = replace_vars(fh.read(), self.vars_to_replace)
        out_path = Path(self.temp_dir.name) / self.py_path.with_stem(f"{self.py_path.stem}_modified")
        with open(str(out_path), "w") as fh:
            fh.write(modified_source)
        return out_path

    def load_module(self) -> None:
        if self.modified_py_path is None:
            raise ValueError
        # Take a hash of the filepath as the module name
        module_name = sha256(str(self.modified_py_path).encode("utf-8")).hexdigest()[10:]
        spec = importlib.util.spec_from_file_location(module_name, str(self.modified_py_path))
        module = importlib.util.module_from_spec(spec)
        module.display = mock.MagicMock()
        self.module = module
        self.execute_module = spec.loader.exec_module
        return None

    def execute(self) -> Any:
        if self.module is None or self.execute_module is None:
            raise ValueError("Call load_module first")
        self.execute_module(self.module)
        return self.module


# TODO: store the module as a hash of the source code/filepath
# Generate a type file based on annotations and store this in a hidden directory, that the IDE will be able to pick up?


class load_notebook:
    def __init__(self, notebook_path: str, vars_to_replace: dict[str, Any] | None = None):
        self.notebook_path = notebook_path
        self.vars_to_replace = vars_to_replace
        self.runner = None
        return


    def __enter__(self):
        self.runner = NotebookRunner(self.notebook_path, self.vars_to_replace)
        return self.runner

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup on exit."""
        self.runner.temp_dir.cleanup()
        return False

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(self.runner, *args, **kwargs)

        return wrapper

