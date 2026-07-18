from pathlib import Path
import importlib.resources


pytest_plugins = "pytester"


TEST_DATA_PATH = Path(str(importlib.resources.files(__package__) / "test_data"))
