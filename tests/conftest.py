from pathlib import Path
import importlib.resources


pytest_plugins = 'pytester'


TEST_DATA_PATH = Path(importlib.resources.files(__package__) / "test_data")