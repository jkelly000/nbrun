from unittest import mock
from nbrun import runner
import pytest

from .conftest import TEST_DATA_PATH


@pytest.mark.parametrize(
    "nb_filename",
    [
        "notebook_ipython_features.ipynb",
        "notebook_ipython_features_str_code_cell.ipynb",
    ],
)
def test_detect_ipython_features(nb_filename: str) -> None:
    """
    nbrun must be able to detect typical ipython features, so that it can raise an Exception.
    We must be able to handle code cells formatted in the 2 allowed ways:
    1) where the 'code' is a list of strings
    2) where the 'code' is a single string containing lines separated by newline characters.
    """
    assert runner.detect_ipython_features(TEST_DATA_PATH / nb_filename) == {
        "cell_magic",
        "line_magic",
        "shell_escape",
        "help_syntax",
    }


def test_detect_ipython_features_ignores_non_code_cells() -> None:
    """
    For a notebook with no ipython features, we must detect none.
    """
    assert runner.detect_ipython_features(TEST_DATA_PATH / "notebook.ipynb") == set()


def test_ipynb_to_py() -> None:
    """The notebook should produce a generated Python file and preserve it until cleanup."""
    nb_runner = runner.Notebook(path=TEST_DATA_PATH / "notebook.ipynb")
    assert nb_runner.py_path.exists()
    assert nb_runner.py_path.is_file()
    nb_runner.cleanup()


def test_execute_module() -> None:
    """Executing a notebook should return its computed outputs and clean up temporary files."""
    nb_runner = runner.Notebook(path=TEST_DATA_PATH / "notebook.ipynb")

    result = nb_runner.execute()
    # We must be able to make assertions about the output of the notebook.
    assert result.result == 3
    # If we call cleanup, the temporary files but have been deleted.
    nb_runner.cleanup()
    assert not nb_runner.py_path.exists()
    assert not nb_runner.modified_py_path.exists()


def test_run_notebook_context_manager() -> None:
    """The notebook context manager should remove generated files when the block exits."""
    with runner.Notebook(path=str(TEST_DATA_PATH / "notebook.ipynb")) as nb_runner:
        nb_runner.execute()

    assert not nb_runner.py_path.exists()
    assert not nb_runner.modified_py_path.exists()


def test_local_import() -> None:
    """
    We must be able to run a notebook that imports a Python module from the same directory.
    We must also be able to mock out that function with unittest.mock.patch.
    """
    with runner.Notebook(
        path=str(TEST_DATA_PATH / "notebook_local_import.ipynb")
    ) as nb_runner:
        result = nb_runner.execute()
    assert result.result == 0
    assert result.result2 == 1

    # We must be able to use unittest.mock.patch to override functions
    # imported from modules external to the notebook.

    with runner.Notebook(
        path=str(TEST_DATA_PATH / "notebook_local_import.ipynb")
    ) as nb_runner:
        with mock.patch("utils.calc") as mock_calc:
            with mock.patch("child_folder.utils.calc") as mock_child_calc:
                mock_calc.return_value = 10
                mock_child_calc.return_value = 12
                result = nb_runner.execute()
    assert mock_calc.call_count == 1
    assert mock_child_calc.call_count == 1
    assert result.result == 10
    assert result.result2 == 12
