from __future__ import annotations

import os
from pathlib import Path

WORKBENCH_ROOT = Path(os.environ["WORKBENCH_ROOT"]).expanduser()
CONTROL_ROOT = Path(os.environ["CONTROL_ROOT"]).expanduser()
AUTOSCRIBE_ROOT = Path(os.environ["AUTOSCRIBE_ROOT"]).expanduser()
TOOLS_ROOT = Path(os.environ["TOOLS_ROOT"]).expanduser()
PANDOC_DATA_DIR = Path(os.environ["PANDOC_DATA_DIR"]).expanduser()