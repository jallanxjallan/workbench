from __future__ import annotations

import os
import subprocess
from pathlib import Path

WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PYTHON_BIN = os.environ.get("WORKBENCH_PYTHON", str(Path.home() / "Python3.13Env" / "bin" / "python"))
PYTHONPATH_ROOT = WORKBENCH_ROOT / "cli"


def _env_with_pythonpath() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{PYTHONPATH_ROOT}:{existing}" if existing else str(PYTHONPATH_ROOT)
    return env


def run_python_module(module: str, args: list[str]) -> int:
    cmd = [PYTHON_BIN, "-m", module, *args]
    completed = subprocess.run(cmd, env=_env_with_pythonpath(), check=False)
    return int(completed.returncode)


def run_shell_function(module_rel_path: str, function_name: str, args: list[str]) -> int:
    module_path = WORKBENCH_ROOT / module_rel_path
    script = f'source "{module_path}"; {function_name} "$@"'
    cmd = ["zsh", "-c", script, "w", *args]
    completed = subprocess.run(cmd, check=False)
    return int(completed.returncode)


def run_bash_script(script_rel_path: str, args: list[str]) -> int:
    script_path = WORKBENCH_ROOT / script_rel_path
    cmd = ["bash", str(script_path), *args]
    completed = subprocess.run(cmd, check=False)
    return int(completed.returncode)
