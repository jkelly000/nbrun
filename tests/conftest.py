from pathlib import Path
import importlib.resources

TEST_DATA_PATH = Path(str(importlib.resources.files(__package__) / "test_data"))
