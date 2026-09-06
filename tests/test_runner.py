from nbrun import runner

from .conftest import TEST_DATA_PATH


def test_ipynb_to_py() -> None:

    nb_runner = runner.Notebook(path=TEST_DATA_PATH / "notebook.ipynb")
    assert nb_runner.py_path.exists()
    assert nb_runner.py_path.is_file()
    nb_runner.cleanup()


def test_execute_module() -> None:
    nb_runner = runner.Notebook(path=TEST_DATA_PATH / "notebook.ipynb")

    result = nb_runner.execute()
    # We must be able to make assertions about the output of the notebook.
    assert result.result == 3
    # If we call cleanup, the temporary files but have been deleted.
    nb_runner.cleanup()
    assert not nb_runner.py_path.exists()
    assert not nb_runner.modified_py_path.exists()


def test_run_notebook_context_manager() -> None:
    with runner.Notebook(path=str(TEST_DATA_PATH / "notebook.ipynb")) as nb_runner:
        nb_runner.execute()

    assert not nb_runner.py_path.exists()
    assert not nb_runner.modified_py_path.exists()
