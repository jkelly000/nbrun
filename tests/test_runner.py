from nb_runner import runner
import pytest

from pathlib import Path

from .conftest import TEST_DATA_PATH


def test_ipynb_to_py() -> None:
    
    nb_runner = runner.NotebookRunner(notebook_path=TEST_DATA_PATH / "notebook.ipynb")
    
    nb_runner.ipynb_to_py()
    assert nb_runner.py_path is not None
    assert nb_runner.py_path.exists()
    assert nb_runner.py_path.is_file()
    nb_runner.temp_dir.cleanup()

def test_load_module() -> None:
    nb_runner = runner.NotebookRunner(notebook_path=TEST_DATA_PATH / "notebook.ipynb")
    assert nb_runner.module is not None
    assert nb_runner.execute is not None
    assert callable(nb_runner.execute)

def test_execute_module() -> None:
    nb_runner = runner.NotebookRunner(notebook_path=TEST_DATA_PATH / "notebook.ipynb")

    pre_exec_vars_count = len(nb_runner.module.__dict__)
    nb_runner.execute()

    assert len(nb_runner.module.__dict__) > pre_exec_vars_count
    
    # We must be able to make assertions about the output of the notebook.
    assert nb_runner.module.result == 3
    # If we call cleanup, the temporary files but have been deleted.
    nb_runner.temp_dir.cleanup()
    assert not nb_runner.py_path.exists()
    assert not nb_runner.modified_py_path.exists()






def test_run_notebook_context_manager() -> None:
    with runner.load_notebook(notebook_path=str(TEST_DATA_PATH / "notebook.ipynb")) as nb_runner:
        result = nb_runner.execute()
    
    assert not nb_runner.py_path.exists()
    assert not nb_runner.modified_py_path.exists()


def test_run_notebook_decorator() -> None:

    @runner.load_notebook(notebook_path=str(TEST_DATA_PATH / "notebook.ipynb"))
    def test_func(nb_runner) -> str:
        assert isinstance(nb_runner, runner.NotebookRunner)
        nb_runner.execute()
        return nb_runner.temp_dir.name
    
    path = test_func()
    assert not Path(path).exists()